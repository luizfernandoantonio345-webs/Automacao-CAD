import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface RefineryConfig {
  name: string;
  location: string;
  norms: string[];
  material_database: string;
  default_pressure_class: string;
  clash_detection_tolerance_mm: number;
}

interface GlobalContextType {
  selectedRefinery: string | null;
  refineryConfig: RefineryConfig | null;
  setSelectedRefinery: (refinery: string, config: RefineryConfig) => void;
  clearRefinery: () => void;
}

const GlobalContext = createContext<GlobalContextType | undefined>(undefined);

export const GlobalProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedRefinery, setSelectedRefineryState] = useState<string | null>(() => {
    return localStorage.getItem('selected-refinery');
  });
  
  const [refineryConfig, setRefineryConfigState] = useState<RefineryConfig | null>(() => {
    const saved = localStorage.getItem('refinery-config');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });

  const setSelectedRefinery = (refinery: string, config: RefineryConfig) => {
    setSelectedRefineryState(refinery);
    setRefineryConfigState(config);
    localStorage.setItem('selected-refinery', refinery);
    localStorage.setItem('refinery-config', JSON.stringify(config));
  };

  const clearRefinery = () => {
    setSelectedRefineryState(null);
    setRefineryConfigState(null);
    localStorage.removeItem('selected-refinery');
    localStorage.removeItem('refinery-config');
  };

  return (
    <GlobalContext.Provider
      value={{
        selectedRefinery,
        refineryConfig,
        setSelectedRefinery,
        clearRefinery,
      }}
    >
      {children}
    </GlobalContext.Provider>
  );
};

export const useGlobal = (): GlobalContextType => {
  const context = useContext(GlobalContext);
  if (!context) {
    throw new Error('useGlobal deve ser usado dentro de GlobalProvider');
  }
  return context;
};
