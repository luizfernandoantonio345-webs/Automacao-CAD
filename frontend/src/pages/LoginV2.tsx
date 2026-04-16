/**
 * Login v2.0 — AutomAção CAD Enterprise
 * 
 * Redesigned with enterprise/luxury styling:
 * - Animated mesh gradient background
 * - Glass card form with blur effect
 * - Float labels on inputs
 * - Shimmer effect on CTA button
 * - Responsive mobile-first design
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Shield,
  Zap,
  Layers,
  CheckCircle,
  AlertCircle,
  Sparkles,
  ChevronRight,
} from 'lucide-react';

// Design System
import { colors, spacing, radius, shadows, breakpoints, blur, media } from '../design/tokens';
import { fontFamily, textStyles, fontSize } from '../design/typography';
import {
  fadeIn,
  fadeInScale,
  slideUp,
  slideRight,
  staggerContainer,
  staggerItem,
  hoverLift,
  tapScale,
  shimmer,
} from '../design/animations';

// UI Components
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import Card from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

// Services
import { API_BASE_URL, ApiService } from '../services/api';
import { useLicense } from '../context/LicenseContext';


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ANIMATED BACKGROUND
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const AnimatedBackground: React.FC = () => (
  <div
    style={{
      position: 'fixed',
      inset: 0,
      zIndex: 0,
      overflow: 'hidden',
    }}
  >
    {/* Base gradient */}
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: colors.dark.base,
      }}
    />

    {/* Animated mesh gradient */}
    <motion.div
      animate={{
        backgroundPosition: ['0% 0%', '100% 100%', '0% 0%'],
      }}
      transition={{
        duration: 20,
        repeat: Infinity,
        ease: 'linear',
      }}
      style={{
        position: 'absolute',
        inset: 0,
        background: `
          radial-gradient(at 0% 0%, ${colors.primary.DEFAULT}15 0px, transparent 50%),
          radial-gradient(at 100% 0%, ${colors.secondary.DEFAULT}12 0px, transparent 50%),
          radial-gradient(at 100% 100%, ${colors.primary.DEFAULT}10 0px, transparent 50%),
          radial-gradient(at 0% 100%, ${colors.secondary.DEFAULT}08 0px, transparent 50%)
        `,
        backgroundSize: '200% 200%',
      }}
    />

    {/* Floating orbs */}
    <motion.div
      animate={{
        x: [0, 100, 0],
        y: [0, -50, 0],
        scale: [1, 1.2, 1],
      }}
      transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
      style={{
        position: 'absolute',
        top: '15%',
        left: '5%',
        width: '500px',
        height: '500px',
        borderRadius: '50%',
        background: `radial-gradient(circle, ${colors.primary.DEFAULT}12 0%, transparent 70%)`,
        filter: 'blur(60px)',
      }}
    />
    <motion.div
      animate={{
        x: [0, -80, 0],
        y: [0, 80, 0],
        scale: [1, 1.3, 1],
      }}
      transition={{ duration: 25, repeat: Infinity, ease: 'easeInOut' }}
      style={{
        position: 'absolute',
        bottom: '10%',
        right: '0%',
        width: '600px',
        height: '600px',
        borderRadius: '50%',
        background: `radial-gradient(circle, ${colors.secondary.DEFAULT}10 0%, transparent 70%)`,
        filter: 'blur(80px)',
      }}
    />

    {/* Grid overlay */}
    <div
      style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: `
          linear-gradient(${colors.primary.DEFAULT}04 1px, transparent 1px),
          linear-gradient(90deg, ${colors.primary.DEFAULT}04 1px, transparent 1px)
        `,
        backgroundSize: '80px 80px',
        opacity: 0.5,
      }}
    />
  </div>
);


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FEATURE LIST
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const features = [
  {
    icon: <Shield size={20} />,
    title: 'Segurança Enterprise',
    description: 'Criptografia AES-256 e autenticação multifator',
  },
  {
    icon: <Layers size={20} />,
    title: 'AutoCAD Integration',
    description: 'Conexão direta com AutoCAD via plugin dedicado',
  },
  {
    icon: <Zap size={20} />,
    title: 'IA Generativa',
    description: 'Geração automática de desenhos e validação de normas',
  },
];


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// LOGIN COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { refreshTier } = useLicense();
  
  // Form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');

  // Clear error when switching modes
  useEffect(() => {
    setError('');
  }, [mode]);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (mode === 'register') {
        await ApiService.register({ email, senha: password });
      }
      
      const response = await ApiService.login({ email, senha: password });
      
      if (response.access_token) {
        localStorage.setItem('access_token', response.access_token);
        refreshTier();
        navigate('/dashboard');
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao conectar. Tente novamente.');
    } finally {
      setIsLoading(false);
    }
  };

  // Enter demo mode
  const enterDemoMode = async () => {
    try {
      await ApiService.demoLogin();
      refreshTier();
      navigate('/dashboard');
    } catch (err) {
      // fallback to local demo
      localStorage.setItem('access_token', 'demo_token');
      refreshTier();
      navigate('/dashboard');
    }
  };

  // Page styles
  const containerStyles: React.CSSProperties = {
    minHeight: '100vh',
    display: 'flex',
    position: 'relative',
  };

  const leftPanelStyles: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    padding: spacing[12],
    position: 'relative',
    zIndex: 1,
  };

  const rightPanelStyles: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing[8],
    position: 'relative',
    zIndex: 1,
  };

  const formCardStyles: React.CSSProperties = {
    width: '100%',
    maxWidth: '420px',
    padding: spacing[10],
    borderRadius: radius['2xl'],
    background: 'rgba(255, 255, 255, 0.03)',
    backdropFilter: `blur(${blur.xl})`,
    WebkitBackdropFilter: `blur(${blur.xl})`,
    border: `1px solid ${colors.border.subtle}`,
    boxShadow: shadows.modal,
  };

  return (
    <div style={containerStyles}>
      <AnimatedBackground />

      {/* Left Panel - Branding (hidden on mobile) */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        style={leftPanelStyles}
        className="login-left"
      >
        {/* Logo */}
        <motion.div variants={slideRight} style={{ marginBottom: spacing[12] }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: spacing[3] }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: radius.lg,
                background: colors.gradient.primary,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: shadows.glowPrimary,
              }}
            >
              <Layers size={24} color="#FFF" />
            </div>
            <div>
              <h1
                style={{
                  margin: 0,
                  ...textStyles.heading.h2,
                  color: colors.text.primary,
                }}
              >
                AutomAção CAD
              </h1>
              <p
                style={{
                  margin: 0,
                  ...textStyles.body.sm,
                  color: colors.text.tertiary,
                }}
              >
                Enterprise Engineering Platform
              </p>
            </div>
          </div>
        </motion.div>

        {/* Tagline */}
        <motion.div variants={slideRight} style={{ marginBottom: spacing[10] }}>
          <h2
            style={{
              margin: 0,
              ...textStyles.display.lg,
              color: colors.text.primary,
              maxWidth: '500px',
            }}
          >
            Automação{' '}
            <span
              style={{
                background: colors.gradient.primary,
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              inteligente
            </span>
            <br />
            para engenharia.
          </h2>
          <p
            style={{
              margin: `${spacing[4]} 0 0`,
              ...textStyles.body.lg,
              color: colors.text.secondary,
              maxWidth: '450px',
            }}
          >
            Transforme seus fluxos de trabalho com IA, integração AutoCAD e geração automática de documentação técnica.
          </p>
        </motion.div>

        {/* Features */}
        <motion.div
          variants={staggerContainer}
          style={{ display: 'flex', flexDirection: 'column', gap: spacing[4] }}
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              variants={staggerItem}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: spacing[4],
                padding: spacing[4],
                borderRadius: radius.lg,
                background: 'rgba(255, 255, 255, 0.02)',
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: radius.md,
                  background: colors.primary.soft,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: colors.primary.DEFAULT,
                  flexShrink: 0,
                }}
              >
                {feature.icon}
              </div>
              <div>
                <h4
                  style={{
                    margin: 0,
                    ...textStyles.label.lg,
                    color: colors.text.primary,
                  }}
                >
                  {feature.title}
                </h4>
                <p
                  style={{
                    margin: `${spacing[1]} 0 0`,
                    ...textStyles.body.sm,
                    color: colors.text.tertiary,
                  }}
                >
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Trust badges */}
        <motion.div
          variants={fadeIn}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: spacing[6],
            marginTop: 'auto',
            paddingTop: spacing[12],
          }}
        >
          {['Petrobras', 'Vale', 'Braskem'].map((company, i) => (
            <span
              key={i}
              style={{
                ...textStyles.caption,
                color: colors.text.tertiary,
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
              }}
            >
              {company}
            </span>
          ))}
        </motion.div>
      </motion.div>

      {/* Right Panel - Form */}
      <motion.div
        variants={fadeInScale}
        initial="hidden"
        animate="visible"
        style={rightPanelStyles}
        className="login-right"
      >
        <div style={formCardStyles}>
          {/* Mode Toggle */}
          <div
            style={{
              display: 'flex',
              marginBottom: spacing[8],
              padding: spacing[1],
              borderRadius: radius.lg,
              background: colors.dark.elevated,
            }}
          >
            {(['login', 'register'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  flex: 1,
                  padding: `${spacing[2]} ${spacing[4]}`,
                  borderRadius: radius.md,
                  border: 'none',
                  background: mode === m ? colors.primary.DEFAULT : 'transparent',
                  color: mode === m ? '#FFF' : colors.text.tertiary,
                  ...textStyles.label.md,
                  cursor: 'pointer',
                  transition: 'all 200ms ease-out',
                }}
              >
                {m === 'login' ? 'Entrar' : 'Criar Conta'}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[5] }}>
              <Input
                type="email"
                label="Email"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                leftIcon={<Mail size={18} />}
                variant="filled"
                required
                autoComplete="email"
              />

              <Input
                type={showPassword ? 'text' : 'password'}
                label="Senha"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                leftIcon={<Lock size={18} />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      padding: 0,
                      color: colors.text.tertiary,
                    }}
                    aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                }
                variant="filled"
                required
                minLength={6}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />

              {/* Error message */}
              <AnimatePresence mode="wait">
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: spacing[2],
                      padding: spacing[3],
                      borderRadius: radius.md,
                      background: colors.danger.soft,
                      color: colors.danger.DEFAULT,
                      ...textStyles.body.sm,
                    }}
                  >
                    <AlertCircle size={16} />
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                fullWidth
                glow
                isLoading={isLoading}
                rightIcon={<ArrowRight size={18} />}
              >
                {mode === 'login' ? 'Entrar' : 'Criar Conta'}
              </Button>
            </div>
          </form>

          {/* Divider */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: spacing[4],
              margin: `${spacing[6]} 0`,
            }}
          >
            <div style={{ flex: 1, height: '1px', background: colors.border.subtle }} />
            <span style={{ ...textStyles.caption, color: colors.text.tertiary }}>
              ou
            </span>
            <div style={{ flex: 1, height: '1px', background: colors.border.subtle }} />
          </div>

          {/* Demo Mode */}
          <Button
            variant="outline"
            size="lg"
            fullWidth
            leftIcon={<Sparkles size={18} />}
            onClick={enterDemoMode}
          >
            Explorar Demonstração
          </Button>

          {/* Footer links */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              gap: spacing[4],
              marginTop: spacing[6],
            }}
          >
            {['Termos', 'Privacidade', 'Suporte'].map((link, i) => (
              <a
                key={i}
                href={`/${link.toLowerCase()}`}
                style={{
                  ...textStyles.caption,
                  color: colors.text.tertiary,
                  textDecoration: 'none',
                }}
              >
                {link}
              </a>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Responsive styles */}
      <style>{`
        @media (max-width: ${breakpoints.lg}px) {
          .login-left {
            display: none !important;
          }
          .login-right {
            flex: 1 !important;
            padding: ${spacing[4]} !important;
          }
        }
      `}</style>
    </div>
  );
};

export default Login;
