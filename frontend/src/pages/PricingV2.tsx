/**
 * PricingV2 Page — AutomAção CAD Enterprise v2.0
 * 
 * Luxurious pricing page with glassmorphism and premium feel.
 * Monthly/annual toggle, feature comparison, and trust signals.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Rocket,
  Crown,
  Building2,
  Check,
  X,
  Sparkles,
  Shield,
  Zap,
  HeadphonesIcon,
  ArrowRight,
  Users,
  Server,
  Brain,
  ChartLine,
  Lock,
  Star,
  Clock,
  DollarSign,
} from 'lucide-react';
import { colors, radius, shadows, spacing, blur } from '../design/tokens';
import { fontFamily, fontSize, fontWeight, textStyles } from '../design/typography';
import { Button, Badge, BottomTabBar } from '../components/ui';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ANIMATED BACKGROUND
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const AnimatedBackground: React.FC = () => (
  <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', zIndex: 0 }}>
    {/* Base gradient */}
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: `linear-gradient(135deg, ${colors.dark.base} 0%, #0A0F1A 50%, ${colors.dark.base} 100%)`,
      }}
    />

    {/* Animated orbs */}
    <motion.div
      animate={{
        x: [0, 80, 0],
        y: [0, -40, 0],
        scale: [1, 1.1, 1],
      }}
      transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
      style={{
        position: 'absolute',
        top: '5%',
        left: '10%',
        width: '500px',
        height: '500px',
        borderRadius: '50%',
        background: `radial-gradient(circle, ${colors.primary.glow} 0%, transparent 70%)`,
        filter: 'blur(80px)',
      }}
    />
    <motion.div
      animate={{
        x: [0, -60, 0],
        y: [0, 60, 0],
        scale: [1, 1.2, 1],
      }}
      transition={{ duration: 22, repeat: Infinity, ease: 'linear' }}
      style={{
        position: 'absolute',
        bottom: '10%',
        right: '5%',
        width: '400px',
        height: '400px',
        borderRadius: '50%',
        background: `radial-gradient(circle, ${colors.secondary.glow} 0%, transparent 70%)`,
        filter: 'blur(60px)',
      }}
    />
    <motion.div
      animate={{
        x: [0, 40, 0],
        y: [0, 40, 0],
      }}
      transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
      style={{
        position: 'absolute',
        top: '50%',
        right: '30%',
        width: '300px',
        height: '300px',
        borderRadius: '50%',
        background: `radial-gradient(circle, ${colors.gold.glow} 0%, transparent 70%)`,
        filter: 'blur(50px)',
      }}
    />

    {/* Grid overlay */}
    <div
      style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)
        `,
        backgroundSize: '64px 64px',
      }}
    />
  </div>
);

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface PlanFeature {
  text: string;
  included: boolean;
  highlight?: boolean;
}

interface Plan {
  id: string;
  name: string;
  icon: React.ReactNode;
  monthlyPrice: number;
  yearlyPrice: number;
  description: string;
  color: string;
  popular?: boolean;
  features: PlanFeature[];
  limits: {
    machines: number;
    projects: number | 'unlimited';
    aiQueries: number | 'unlimited';
    support: string;
  };
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// DATA
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const PLANS: Plan[] = [
  {
    id: 'starter',
    name: 'Starter',
    icon: <Rocket size={24} />,
    monthlyPrice: 297,
    yearlyPrice: 2970,
    description: 'Para profissionais autônomos',
    color: colors.success.DEFAULT,
    features: [
      { text: 'Automação CAD básica', included: true },
      { text: 'Geração P&ID', included: true },
      { text: 'Validação ASME básica', included: true },
      { text: 'Exportação DXF/DWG', included: true },
      { text: '5 projetos simultâneos', included: true },
      { text: 'Suporte por email', included: true },
      { text: 'IA Assistente (100 consultas)', included: true },
      { text: 'Controle CNC/Plasma', included: false },
      { text: 'API de integração', included: false },
      { text: 'Suporte prioritário', included: false },
    ],
    limits: {
      machines: 1,
      projects: 5,
      aiQueries: 100,
      support: 'Email (48h)',
    },
  },
  {
    id: 'professional',
    name: 'Professional',
    icon: <Crown size={24} />,
    monthlyPrice: 697,
    yearlyPrice: 6970,
    description: 'Para empresas em crescimento',
    color: colors.primary.DEFAULT,
    popular: true,
    features: [
      { text: 'Tudo do Starter +', included: true, highlight: true },
      { text: 'Automação avançada', included: true },
      { text: 'Validação ASME + Petrobras', included: true },
      { text: 'Controle CNC/Plasma completo', included: true },
      { text: '50 projetos simultâneos', included: true },
      { text: 'Nesting inteligente', included: true },
      { text: 'IA Assistente ilimitada', included: true },
      { text: 'API de integração', included: true },
      { text: 'Suporte prioritário', included: true },
      { text: '5 licenças incluídas', included: true },
    ],
    limits: {
      machines: 5,
      projects: 50,
      aiQueries: 'unlimited',
      support: 'Chat + Tel (4h)',
    },
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    icon: <Building2 size={24} />,
    monthlyPrice: 1997,
    yearlyPrice: 19970,
    description: 'Solução completa para indústrias',
    color: colors.gold.DEFAULT,
    features: [
      { text: 'Tudo do Professional +', included: true, highlight: true },
      { text: 'Deploy on-premise opcional', included: true },
      { text: 'Integrações customizadas', included: true },
      { text: 'SLA garantido 99.9%', included: true },
      { text: 'Projetos ilimitados', included: true },
      { text: 'Licenças ilimitadas', included: true },
      { text: 'Treinamento presencial', included: true },
      { text: 'Gerente de conta dedicado', included: true },
      { text: 'Compliance & Auditoria', included: true },
      { text: 'Suporte 24/7', included: true },
    ],
    limits: {
      machines: Infinity,
      projects: 'unlimited',
      aiQueries: 'unlimited',
      support: '24/7 Dedicado',
    },
  },
];

const TESTIMONIALS = [
  {
    quote: 'Reduziu nosso tempo de projeto em 70%. Imprescindível para nossa operação.',
    author: 'Carlos M.',
    role: 'Gerente de Engenharia',
    company: 'Petroeng Industrial',
  },
  {
    quote: 'A IA de validação detecta erros que passariam despercebidos. Qualidade nota 10.',
    author: 'Ana S.',
    role: 'Projetista Senior',
    company: 'Construtora Atlântica',
  },
];

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ANIMATIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' },
  },
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// PLAN CARD COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface PlanCardProps {
  plan: Plan;
  isYearly: boolean;
  onSelect: (planId: string) => void;
}

const PlanCard: React.FC<PlanCardProps> = ({ plan, isYearly, onSelect }) => {
  const price = isYearly ? plan.yearlyPrice : plan.monthlyPrice;
  const monthlyEquivalent = isYearly ? Math.round(plan.yearlyPrice / 12) : plan.monthlyPrice;
  const savings = isYearly ? Math.round(((plan.monthlyPrice * 12) - plan.yearlyPrice) / (plan.monthlyPrice * 12) * 100) : 0;

  const styles = {
    card: {
      position: 'relative' as const,
      backgroundColor: plan.popular 
        ? 'rgba(255, 255, 255, 0.05)' 
        : 'rgba(255, 255, 255, 0.02)',
      backdropFilter: `blur(${blur.lg})`,
      borderRadius: radius['2xl'],
      border: plan.popular 
        ? `2px solid ${plan.color}` 
        : `1px solid ${colors.border.subtle}`,
      padding: spacing[6],
      display: 'flex',
      flexDirection: 'column' as const,
      height: '100%',
      overflow: 'hidden',
    },

    popularBadge: {
      position: 'absolute' as const,
      top: '-12px',
      left: '50%',
      transform: 'translateX(-50%)',
      padding: `${spacing[1]} ${spacing[4]}`,
      backgroundColor: plan.color,
      borderRadius: radius.full,
      fontFamily: fontFamily.sans,
      fontSize: fontSize.xs,
      fontWeight: fontWeight.semibold,
      color: '#ffffff',
      display: 'flex',
      alignItems: 'center',
      gap: spacing[1],
      boxShadow: `0 4px 20px ${plan.color}40`,
    },

    iconWrapper: {
      width: '56px',
      height: '56px',
      borderRadius: radius.xl,
      backgroundColor: `${plan.color}15`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: plan.color,
      marginBottom: spacing[4],
    },

    name: {
      ...textStyles.heading.h4,
      color: colors.text.primary,
      margin: 0,
      marginBottom: spacing[1],
    },

    description: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      color: colors.text.secondary,
      marginBottom: spacing[4],
    },

    priceContainer: {
      marginBottom: spacing[5],
    },

    price: {
      display: 'flex',
      alignItems: 'baseline',
      gap: spacing[1],
    },

    currency: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.lg,
      fontWeight: fontWeight.medium,
      color: colors.text.secondary,
    },

    amount: {
      fontFamily: fontFamily.display,
      fontSize: fontSize['4xl'],
      fontWeight: fontWeight.bold,
      color: colors.text.primary,
      lineHeight: 1,
    },

    period: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      color: colors.text.tertiary,
    },

    monthlyNote: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.xs,
      color: colors.text.tertiary,
      marginTop: spacing[1],
    },

    savingsBadge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: spacing[1],
      padding: `${spacing[1]} ${spacing[2]}`,
      backgroundColor: colors.success.soft,
      borderRadius: radius.md,
      fontFamily: fontFamily.sans,
      fontSize: fontSize.xs,
      fontWeight: fontWeight.medium,
      color: colors.success.DEFAULT,
      marginTop: spacing[2],
    },

    divider: {
      height: '1px',
      backgroundColor: colors.border.subtle,
      marginBottom: spacing[5],
    },

    featuresList: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column' as const,
      gap: spacing[3],
      marginBottom: spacing[6],
    },

    feature: {
      display: 'flex',
      alignItems: 'center',
      gap: spacing[3],
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
    },

    featureIcon: (included: boolean) => ({
      width: '20px',
      height: '20px',
      borderRadius: radius.full,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: included ? colors.success.soft : colors.dark.subtle,
      color: included ? colors.success.DEFAULT : colors.text.tertiary,
      flexShrink: 0,
    }),

    featureText: (included: boolean, highlight?: boolean) => ({
      color: highlight 
        ? plan.color 
        : included 
          ? colors.text.primary 
          : colors.text.tertiary,
      fontWeight: highlight ? fontWeight.medium : fontWeight.normal,
    }),

    cta: {
      marginTop: 'auto',
    },

    glow: {
      position: 'absolute' as const,
      top: 0,
      left: '50%',
      transform: 'translateX(-50%)',
      width: '80%',
      height: '2px',
      background: `linear-gradient(90deg, transparent, ${plan.color}, transparent)`,
      opacity: plan.popular ? 1 : 0.5,
    },
  };

  return (
    <motion.div
      style={styles.card}
      variants={fadeInUp}
      whileHover={{ 
        y: -8,
        boxShadow: plan.popular 
          ? `0 20px 60px ${plan.color}20` 
          : shadows.xl,
      }}
      transition={{ duration: 0.3 }}
    >
      {/* Top glow */}
      <div style={styles.glow} />

      {/* Popular badge */}
      {plan.popular && (
        <div style={styles.popularBadge}>
          <Star size={12} />
          Mais Popular
        </div>
      )}

      {/* Icon */}
      <div style={styles.iconWrapper}>
        {plan.icon}
      </div>

      {/* Name & Description */}
      <h3 style={styles.name}>{plan.name}</h3>
      <p style={styles.description}>{plan.description}</p>

      {/* Price */}
      <div style={styles.priceContainer}>
        <div style={styles.price}>
          <span style={styles.currency}>R$</span>
          <span style={styles.amount}>
            {isYearly ? monthlyEquivalent.toLocaleString('pt-BR') : price.toLocaleString('pt-BR')}
          </span>
          <span style={styles.period}>/mês</span>
        </div>
        {isYearly && (
          <>
            <p style={styles.monthlyNote}>
              Faturado R$ {price.toLocaleString('pt-BR')}/ano
            </p>
            <div style={styles.savingsBadge}>
              <DollarSign size={12} />
              Economia de {savings}%
            </div>
          </>
        )}
      </div>

      <div style={styles.divider} />

      {/* Features */}
      <div style={styles.featuresList}>
        {plan.features.map((feature, index) => (
          <div key={index} style={styles.feature}>
            <div style={styles.featureIcon(feature.included)}>
              {feature.included ? <Check size={12} /> : <X size={12} />}
            </div>
            <span style={styles.featureText(feature.included, feature.highlight)}>
              {feature.text}
            </span>
          </div>
        ))}
      </div>

      {/* CTA */}
      <div style={styles.cta}>
        <Button
          variant={plan.popular ? 'primary' : 'outline'}
          size="lg"
          fullWidth
          onClick={() => onSelect(plan.id)}
          rightIcon={<ArrowRight size={18} />}
        >
          {plan.id === 'enterprise' ? 'Falar com Vendas' : 'Começar Agora'}
        </Button>
      </div>
    </motion.div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// BILLING TOGGLE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface BillingToggleProps {
  isYearly: boolean;
  onChange: (isYearly: boolean) => void;
}

const BillingToggle: React.FC<BillingToggleProps> = ({ isYearly, onChange }) => {
  const styles = {
    container: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: spacing[4],
      padding: spacing[1],
      backgroundColor: colors.dark.surface,
      borderRadius: radius.full,
      border: `1px solid ${colors.border.subtle}`,
    },

    option: (active: boolean) => ({
      padding: `${spacing[2]} ${spacing[5]}`,
      borderRadius: radius.full,
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      fontWeight: active ? fontWeight.semibold : fontWeight.normal,
      color: active ? colors.text.primary : colors.text.secondary,
      backgroundColor: active ? colors.primary.DEFAULT : 'transparent',
      border: 'none',
      cursor: 'pointer',
      transition: 'all 200ms ease-out',
      display: 'flex',
      alignItems: 'center',
      gap: spacing[2],
    }),

    badge: {
      padding: `${spacing[0]} ${spacing[2]}`,
      backgroundColor: colors.success.soft,
      borderRadius: radius.sm,
      fontFamily: fontFamily.sans,
      fontSize: fontSize.xs,
      fontWeight: fontWeight.medium,
      color: colors.success.DEFAULT,
    },
  };

  return (
    <div style={styles.container}>
      <motion.button
        style={styles.option(!isYearly)}
        onClick={() => onChange(false)}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        Mensal
      </motion.button>
      <motion.button
        style={styles.option(isYearly)}
        onClick={() => onChange(true)}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        Anual
        <span style={styles.badge}>-17%</span>
      </motion.button>
    </div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN PAGE COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const PricingV2: React.FC = () => {
  const navigate = useNavigate();
  const [isYearly, setIsYearly] = useState(true);

  const handleSelectPlan = (planId: string) => {
    if (planId === 'enterprise') {
      // Contact sales
      window.open('mailto:comercial@automacao-cad.com.br?subject=Enterprise Plan', '_blank');
    } else {
      navigate(`/register?plan=${planId}&billing=${isYearly ? 'yearly' : 'monthly'}`);
    }
  };

  const styles = {
    page: {
      minHeight: '100vh',
      backgroundColor: colors.dark.base,
      position: 'relative' as const,
      paddingBottom: '100px',
    },

    content: {
      position: 'relative' as const,
      zIndex: 1,
      maxWidth: '1280px',
      margin: '0 auto',
      padding: `${spacing[12]} ${spacing[4]}`,
    },

    header: {
      textAlign: 'center' as const,
      marginBottom: spacing[10],
    },

    badge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: spacing[2],
      padding: `${spacing[2]} ${spacing[4]}`,
      backgroundColor: colors.primary.soft,
      borderRadius: radius.full,
      marginBottom: spacing[4],
    },

    badgeText: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      fontWeight: fontWeight.medium,
      color: colors.primary.DEFAULT,
    },

    title: {
      ...textStyles.heading.h1,
      color: colors.text.primary,
      marginBottom: spacing[4],
    },

    titleGradient: {
      background: `linear-gradient(135deg, ${colors.primary.DEFAULT} 0%, ${colors.secondary.DEFAULT} 100%)`,
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
      backgroundClip: 'text',
    },

    subtitle: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.lg,
      color: colors.text.secondary,
      maxWidth: '600px',
      margin: '0 auto',
      marginBottom: spacing[8],
      lineHeight: 1.6,
    },

    plansGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
      gap: spacing[6],
      marginBottom: spacing[12],
    },

    trustSection: {
      textAlign: 'center' as const,
      marginBottom: spacing[12],
    },

    trustTitle: {
      ...textStyles.heading.h4,
      color: colors.text.primary,
      marginBottom: spacing[6],
    },

    trustGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: spacing[4],
      maxWidth: '800px',
      margin: '0 auto',
    },

    trustItem: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: spacing[2],
      padding: spacing[4],
      backgroundColor: 'rgba(255, 255, 255, 0.02)',
      borderRadius: radius.lg,
      border: `1px solid ${colors.border.subtle}`,
    },

    trustIcon: {
      color: colors.primary.DEFAULT,
    },

    trustText: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      fontWeight: fontWeight.medium,
      color: colors.text.secondary,
    },

    faqSection: {
      maxWidth: '800px',
      margin: '0 auto',
    },

    faqTitle: {
      ...textStyles.heading.h3,
      color: colors.text.primary,
      textAlign: 'center' as const,
      marginBottom: spacing[8],
    },
  };

  const trustItems = [
    { icon: <Shield size={20} />, text: 'Dados criptografados' },
    { icon: <Clock size={20} />, text: 'Teste grátis 14 dias' },
    { icon: <Lock size={20} />, text: 'Cancele quando quiser' },
    { icon: <HeadphonesIcon size={20} />, text: 'Suporte brasileiro' },
  ];

  return (
    <div style={styles.page}>
      <AnimatedBackground />

      <div style={styles.content}>
        <motion.header
          style={styles.header}
          initial="hidden"
          animate="visible"
          variants={staggerContainer}
        >
          {/* Badge */}
          <motion.div style={styles.badge} variants={fadeInUp}>
            <Sparkles size={16} style={{ color: colors.primary.DEFAULT }} />
            <span style={styles.badgeText}>Planos Flexíveis</span>
          </motion.div>

          {/* Title */}
          <motion.h1 style={styles.title} variants={fadeInUp}>
            Escolha o plano{' '}
            <span style={styles.titleGradient}>perfeito</span>
            {' '}para você
          </motion.h1>

          {/* Subtitle */}
          <motion.p style={styles.subtitle} variants={fadeInUp}>
            Automatize seus projetos CAD com inteligência artificial. 
            Todos os planos incluem acesso completo por 14 dias grátis.
          </motion.p>

          {/* Billing Toggle */}
          <motion.div variants={fadeInUp}>
            <BillingToggle isYearly={isYearly} onChange={setIsYearly} />
          </motion.div>
        </motion.header>

        {/* Plans Grid */}
        <motion.div
          style={styles.plansGrid}
          initial="hidden"
          animate="visible"
          variants={staggerContainer}
        >
          {PLANS.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              isYearly={isYearly}
              onSelect={handleSelectPlan}
            />
          ))}
        </motion.div>

        {/* Trust Signals */}
        <motion.section
          style={styles.trustSection}
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <h3 style={styles.trustTitle}>Por que escolher AutomAção CAD?</h3>
          <div style={styles.trustGrid}>
            {trustItems.map((item, index) => (
              <div key={index} style={styles.trustItem}>
                <span style={styles.trustIcon}>{item.icon}</span>
                <span style={styles.trustText}>{item.text}</span>
              </div>
            ))}
          </div>
        </motion.section>
      </div>

      {/* Bottom Tab Bar */}
      <BottomTabBar />
    </div>
  );
};

export default PricingV2;
