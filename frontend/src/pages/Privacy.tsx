/**
 * Privacy Policy - Política de Privacidade
 */

import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { FaArrowLeft, FaLock } from "react-icons/fa";

const Privacy: React.FC = () => {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0a0f1a 0%, #0d1929 50%, #0a1628 100%)",
        padding: "40px 20px",
      }}
    >
      <div style={{ maxWidth: "900px", margin: "0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom: "40px" }}>
          <Link
            to="/"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              color: "#00A1FF",
              fontSize: "14px",
              textDecoration: "none",
              marginBottom: "24px",
            }}
          >
            <FaArrowLeft />
            Voltar ao início
          </Link>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "16px",
              marginBottom: "16px",
            }}
          >
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "14px",
                background: "linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <FaLock size={24} color="white" />
            </div>
            <div>
              <h1 style={{ color: "#fff", fontSize: "32px", fontWeight: 700, margin: 0 }}>
                Política de Privacidade
              </h1>
              <p style={{ color: "#64748b", fontSize: "14px", margin: 0 }}>
                Última atualização: {new Date().toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}
              </p>
            </div>
          </motion.div>
        </div>

        {/* Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          style={{
            background: "#0a1628",
            border: "1px solid #1e3a5f",
            borderRadius: "16px",
            padding: "40px",
          }}
        >
          <div style={{ color: "#94a3b8", fontSize: "15px", lineHeight: 1.8 }}>
            {/* Introduction */}
            <section style={{ marginBottom: "32px" }}>
              <p>
                A Engenharia CAD ("nós", "nosso") está comprometida em proteger sua privacidade. 
                Esta Política de Privacidade explica como coletamos, usamos e protegemos suas 
                informações pessoais quando você utiliza nossa plataforma.
              </p>
              <p style={{ marginTop: "12px" }}>
                Esta política está em conformidade com a Lei Geral de Proteção de Dados (LGPD) - 
                Lei nº 13.709/2018.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                1. Dados que Coletamos
              </h2>
              
              <h3 style={{ color: "#00A1FF", fontSize: "16px", fontWeight: 500, marginBottom: "12px" }}>
                1.1 Informações fornecidas por você:
              </h3>
              <ul style={{ paddingLeft: "24px", marginBottom: "16px" }}>
                <li>Nome e email ao criar uma conta</li>
                <li>Nome da empresa (opcional)</li>
                <li>Telefone de contato (opcional)</li>
                <li>Informações de pagamento (processadas pelo Stripe)</li>
                <li>Projetos CAD e documentos técnicos enviados</li>
                <li>Mensagens no chat com a IA</li>
              </ul>

              <h3 style={{ color: "#00A1FF", fontSize: "16px", fontWeight: 500, marginBottom: "12px" }}>
                1.2 Informações coletadas automaticamente:
              </h3>
              <ul style={{ paddingLeft: "24px" }}>
                <li>Endereço IP e localização aproximada</li>
                <li>Tipo de navegador e dispositivo</li>
                <li>Sistema operacional</li>
                <li>Páginas visitadas e tempo de uso</li>
                <li>Hardware ID (HWID) para licenciamento</li>
                <li>Logs de atividades no sistema</li>
              </ul>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                2. Como Usamos seus Dados
              </h2>
              <p>Utilizamos suas informações para:</p>
              <ul style={{ paddingLeft: "24px", marginTop: "12px" }}>
                <li>Fornecer e manter o Serviço</li>
                <li>Processar pagamentos e gerenciar assinaturas</li>
                <li>Validar licenças de software</li>
                <li>Enviar comunicações importantes sobre sua conta</li>
                <li>Melhorar nossos produtos e serviços</li>
                <li>Treinar modelos de IA (com dados anonimizados)</li>
                <li>Prevenir fraudes e garantir segurança</li>
                <li>Cumprir obrigações legais</li>
              </ul>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                3. Compartilhamento de Dados
              </h2>
              <p>Seus dados podem ser compartilhados com:</p>
              <ul style={{ paddingLeft: "24px", marginTop: "12px" }}>
                <li><strong style={{ color: "#fff" }}>Stripe:</strong> Processamento de pagamentos</li>
                <li><strong style={{ color: "#fff" }}>OpenAI/Anthropic:</strong> Processamento de IA (prompts anonimizados)</li>
                <li><strong style={{ color: "#fff" }}>Vercel/Neon:</strong> Hospedagem e banco de dados</li>
                <li><strong style={{ color: "#fff" }}>Autoridades:</strong> Quando exigido por lei</li>
              </ul>
              <p style={{ marginTop: "12px" }}>
                <strong style={{ color: "#fff" }}>Não vendemos</strong> seus dados pessoais a terceiros.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                4. Segurança dos Dados
              </h2>
              <p>Implementamos medidas de segurança incluindo:</p>
              <ul style={{ paddingLeft: "24px", marginTop: "12px" }}>
                <li>Criptografia TLS/SSL em todas as comunicações</li>
                <li>Criptografia de senhas com Argon2</li>
                <li>Autenticação de dois fatores (2FA)</li>
                <li>Backups regulares com criptografia</li>
                <li>Monitoramento de segurança 24/7</li>
                <li>Auditorias de segurança periódicas</li>
                <li>Acesso restrito a dados por funcionários</li>
              </ul>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                5. Seus Direitos (LGPD)
              </h2>
              <p>Você tem direito a:</p>
              <ul style={{ paddingLeft: "24px", marginTop: "12px" }}>
                <li><strong style={{ color: "#fff" }}>Acesso:</strong> Solicitar cópia dos seus dados pessoais</li>
                <li><strong style={{ color: "#fff" }}>Correção:</strong> Corrigir dados incompletos ou incorretos</li>
                <li><strong style={{ color: "#fff" }}>Exclusão:</strong> Solicitar exclusão dos seus dados</li>
                <li><strong style={{ color: "#fff" }}>Portabilidade:</strong> Receber seus dados em formato estruturado</li>
                <li><strong style={{ color: "#fff" }}>Revogação:</strong> Retirar consentimento a qualquer momento</li>
                <li><strong style={{ color: "#fff" }}>Informação:</strong> Saber com quem seus dados são compartilhados</li>
              </ul>
              <p style={{ marginTop: "12px" }}>
                Para exercer seus direitos, acesse as configurações da conta ou entre em contato 
                com nosso DPO em <a href="mailto:dpo@engenharia-cad.com" style={{ color: "#00A1FF" }}>dpo@engenharia-cad.com</a>.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                6. Retenção de Dados
              </h2>
              <p>Mantemos seus dados pelo tempo necessário para:</p>
              <ul style={{ paddingLeft: "24px", marginTop: "12px" }}>
                <li>Fornecer o Serviço enquanto sua conta estiver ativa</li>
                <li>Cumprir obrigações legais (até 5 anos para dados fiscais)</li>
                <li>Resolver disputas e fazer cumprir acordos</li>
              </ul>
              <p style={{ marginTop: "12px" }}>
                Após exclusão da conta, seus dados são removidos em até 30 dias, exceto quando 
                a retenção for exigida por lei.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                7. Cookies e Tecnologias Similares
              </h2>
              <p>Utilizamos cookies para:</p>
              <ul style={{ paddingLeft: "24px", marginTop: "12px" }}>
                <li><strong style={{ color: "#fff" }}>Essenciais:</strong> Manter sua sessão ativa e preferências</li>
                <li><strong style={{ color: "#fff" }}>Analytics:</strong> Entender como você usa o Serviço</li>
                <li><strong style={{ color: "#fff" }}>Funcionais:</strong> Lembrar configurações e preferências</li>
              </ul>
              <p style={{ marginTop: "12px" }}>
                Você pode gerenciar cookies nas configurações do seu navegador. Desabilitar 
                cookies essenciais pode afetar o funcionamento do Serviço.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                8. Transferência Internacional
              </h2>
              <p>
                Seus dados podem ser transferidos e processados em servidores localizados fora 
                do Brasil (Estados Unidos). Garantimos que essas transferências estão protegidas 
                por medidas de segurança adequadas, incluindo cláusulas contratuais padrão 
                aprovadas pela ANPD.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                9. Menores de Idade
              </h2>
              <p>
                O Serviço não é destinado a menores de 18 anos. Não coletamos intencionalmente 
                dados de menores. Se você acredita que um menor forneceu dados pessoais, entre 
                em contato conosco imediatamente.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                10. Alterações nesta Política
              </h2>
              <p>
                Podemos atualizar esta política periodicamente. Notificaremos sobre alterações 
                significativas por email ou através do Serviço. A data da última atualização 
                sempre estará indicada no topo desta página.
              </p>
            </section>

            <section>
              <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 600, marginBottom: "16px" }}>
                11. Contato
              </h2>
              <p>Para questões sobre privacidade:</p>
              <ul style={{ paddingLeft: "24px", marginTop: "12px" }}>
                <li>
                  <strong style={{ color: "#fff" }}>Encarregado de Dados (DPO):</strong>{" "}
                  <a href="mailto:dpo@engenharia-cad.com" style={{ color: "#00A1FF" }}>dpo@engenharia-cad.com</a>
                </li>
                <li>
                  <strong style={{ color: "#fff" }}>Suporte:</strong>{" "}
                  <a href="mailto:suporte@engenharia-cad.com" style={{ color: "#00A1FF" }}>suporte@engenharia-cad.com</a>
                </li>
              </ul>
              <p style={{ marginTop: "16px", padding: "16px", background: "rgba(0, 161, 255, 0.1)", borderRadius: "8px", borderLeft: "3px solid #00A1FF" }}>
                Você também pode registrar reclamações junto à Autoridade Nacional de Proteção 
                de Dados (ANPD) em <a href="https://www.gov.br/anpd" style={{ color: "#00A1FF" }} target="_blank" rel="noopener noreferrer">www.gov.br/anpd</a>.
              </p>
            </section>
          </div>
        </motion.div>

        {/* Footer Links */}
        <div style={{ marginTop: "32px", textAlign: "center" }}>
          <Link
            to="/terms"
            style={{
              color: "#00A1FF",
              fontSize: "14px",
              textDecoration: "none",
            }}
          >
            Ver Termos de Uso →
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Privacy;
