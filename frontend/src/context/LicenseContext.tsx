/**
 * ENGENHARIA CAD – LicenseContext
 * Gerencia modo demo vs. licença paga.
 * Expõe canUse() para qualquer componente limitar funcionalidades no demo.
 */
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";

export type PlanTier = "demo" | "starter" | "professional" | "enterprise";

export interface LicenseInfo {
  tier: PlanTier;
  isDemo: boolean;
  isPaid: boolean;
  planName: string;
  aiQueriesUsed: number;
  aiQueriesLimit: number;
  projectsUsed: number;
  projectsLimit: number | "unlimited";
  machinesAllowed: number;
}

interface LicenseContextType {
  license: LicenseInfo;
  canUse: (feature: FeatureKey) => boolean;
  consumeAiQuery: () => boolean; // returns false if limit hit
  showUpgradeModal: boolean;
  upgradeReason: string;
  triggerUpgrade: (reason: string) => void;
  dismissUpgrade: () => void;
  activateLicense: (key: string, machineId: string) => Promise<boolean>;
}

export type FeatureKey =
  | "cnc"
  | "nesting"
  | "api"
  | "multiLicense"
  | "reports"
  | "ai_unlimited"
  | "ai_query"
  | "export_dwg"
  | "analytics"
  | "autocad"
  | "realtime";

const TIER_FEATURES: Record<PlanTier, Set<FeatureKey>> = {
  demo: new Set<FeatureKey>(["ai_query", "export_dwg"]),
  starter: new Set<FeatureKey>([
    "ai_query",
    "export_dwg",
    "reports",
    "autocad",
  ]),
  professional: new Set<FeatureKey>([
    "ai_query",
    "cnc",
    "nesting",
    "reports",
    "analytics",
    "autocad",
    "export_dwg",
    "realtime",
  ]),
  enterprise: new Set<FeatureKey>([
    "ai_query",
    "ai_unlimited",
    "cnc",
    "nesting",
    "api",
    "multiLicense",
    "reports",
    "analytics",
    "autocad",
    "export_dwg",
    "realtime",
  ]),
};

const TIER_META: Record<PlanTier, Omit<LicenseInfo, "aiQueriesUsed" | "projectsUsed">> = {
  demo: {
    tier: "demo",
    isDemo: true,
    isPaid: false,
    planName: "Demonstração",
    aiQueriesLimit: 10,
    projectsLimit: 2,
    machinesAllowed: 1,
  },
  starter: {
    tier: "starter",
    isDemo: false,
    isPaid: true,
    planName: "Starter",
    aiQueriesLimit: 100,
    projectsLimit: 5,
    machinesAllowed: 1,
  },
  professional: {
    tier: "professional",
    isDemo: false,
    isPaid: true,
    planName: "Professional",
    aiQueriesLimit: 500,
    projectsLimit: 20,
    machinesAllowed: 2,
  },
  enterprise: {
    tier: "enterprise",
    isDemo: false,
    isPaid: true,
    planName: "Enterprise",
    aiQueriesLimit: 999999,
    projectsLimit: "unlimited",
    machinesAllowed: 10,
  },
};

const DEFAULT_DEMO: LicenseInfo = {
  ...TIER_META.demo,
  aiQueriesUsed: 0,
  projectsUsed: 0,
};

const LicenseContext = createContext<LicenseContextType | undefined>(undefined);

function detectTier(): PlanTier {
  try {
    const raw = localStorage.getItem("license");
    if (!raw) return "demo";
    const parsed = JSON.parse(raw);
    if (parsed?.tier && parsed.tier !== "demo") return parsed.tier as PlanTier;
    // Legacy: check if license key present and validated
    if (parsed?.licenseKey && parsed?.validated) {
      return (parsed.tier as PlanTier) || "starter";
    }
  } catch {
    // ignore
  }
  return "demo";
}

export const LicenseProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [tier, setTier] = useState<PlanTier>(detectTier);
  const [aiQueriesUsed, setAiQueriesUsed] = useState<number>(() => {
    const saved = sessionStorage.getItem("ai_queries_used");
    return saved ? parseInt(saved, 10) : 0;
  });
  const [projectsUsed] = useState<number>(0);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeReason, setUpgradeReason] = useState("");

  const license: LicenseInfo = {
    ...TIER_META[tier],
    aiQueriesUsed,
    projectsUsed,
  };

  const canUse = useCallback(
    (feature: FeatureKey): boolean => {
      return TIER_FEATURES[tier].has(feature);
    },
    [tier]
  );

  const consumeAiQuery = useCallback((): boolean => {
    const meta = TIER_META[tier];
    const limit = meta.aiQueriesLimit;
    if (aiQueriesUsed >= limit) {
      setUpgradeReason(
        tier === "demo"
          ? `Você atingiu o limite de ${limit} consultas de IA no modo demo. Faça upgrade para continuar!`
          : `Você atingiu o limite de ${limit} consultas de IA do seu plano ${meta.planName}.`
      );
      setShowUpgradeModal(true);
      return false;
    }
    const next = aiQueriesUsed + 1;
    setAiQueriesUsed(next);
    sessionStorage.setItem("ai_queries_used", String(next));
    return true;
  }, [aiQueriesUsed, tier]);

  const triggerUpgrade = useCallback((reason: string) => {
    setUpgradeReason(reason);
    setShowUpgradeModal(true);
  }, []);

  const dismissUpgrade = useCallback(() => {
    setShowUpgradeModal(false);
    setUpgradeReason("");
  }, []);

  const activateLicense = useCallback(
    async (key: string, machineId: string): Promise<boolean> => {
      try {
        const response = await fetch(
          `${process.env.REACT_APP_LICENSING_URL || "https://automacao-cad-backend.vercel.app"}/validate`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ license_key: key, machine_id: machineId }),
          }
        );
        if (response.ok) {
          const data = await response.json();
          const newTier: PlanTier = data.tier || "starter";
          setTier(newTier);
          localStorage.setItem(
            "license",
            JSON.stringify({ licenseKey: key, machineId, tier: newTier, validated: true })
          );
          return true;
        }
      } catch {
        // offline — accept locally for demo purposes
      }
      return false;
    },
    []
  );

  // Sync tier if localStorage changes (e.g., after checkout)
  useEffect(() => {
    const handler = () => setTier(detectTier());
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  return (
    <LicenseContext.Provider
      value={{
        license,
        canUse,
        consumeAiQuery,
        showUpgradeModal,
        upgradeReason,
        triggerUpgrade,
        dismissUpgrade,
        activateLicense,
      }}
    >
      {children}
    </LicenseContext.Provider>
  );
};

export const useLicense = (): LicenseContextType => {
  const ctx = useContext(LicenseContext);
  if (!ctx) throw new Error("useLicense deve ser usado dentro de LicenseProvider");
  return ctx;
};
