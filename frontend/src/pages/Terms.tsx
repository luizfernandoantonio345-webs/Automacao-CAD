/**
 * Terms of Service - Termos de Uso
 */

import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { FaArrowLeft, FaShieldAlt } from "react-icons/fa";

const Terms: React.FC = () => {
  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "linear-gradient(135deg, #0a0f1a 0%, #0d1929 50%, #0a1628 100%)",
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
                background: "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <FaShieldAlt size={24} color="white" />
            </div>
            <div>
              <h1
                style={{
                  color: "#fff",
                  fontSize: "32px",
                  fontWeight: 700,
                  margin: 0,
                }}
              >
                Termos de Uso
              </h1>
              <p style={{ color: "#64748b", fontSize: "14px", margin: 0 }}>
                Última atualização:{" "}
                {new Date().toLocaleDateString("pt-BR", {
                  month: "long",
                  year: "numeric",
                })}
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
            <section style={{ marginBottom: "32px" }}>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                1. Aceitação dos Termos
              </h2>
              <p>
                Ao acessar e utilizar a plataforma Engenharia CAD ("Serviço"),
                você concorda em cumprir e estar vinculado a estes Termos de
                Uso. Se você não concordar com qualquer parte destes termos, não
                poderá acessar o Serviço.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                2. Descrição do Serviço
              </h2>
              <p>
                O Engenharia CAD é uma plataforma de automação para projetos de
                engenharia que oferece:
              </p>
              <ul style={{ marginTop: "12px", paddingLeft: "24px" }}>
                <li>Integração com AutoCAD e outros softwares CAD</li>
                <li>Geração de código G-Code para máquinas CNC</li>
                <li>Assistente de IA para projetos de engenharia</li>
                <li>Gerenciamento de projetos e documentos técnicos</li>
                <li>APIs para integração com sistemas externos</li>
              </ul>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                3. Conta de Usuário
              </h2>
              <p>
                Para utilizar o Serviço, você deve criar uma conta fornecendo
                informações precisas e completas. Você é responsável por:
              </p>
              <ul style={{ marginTop: "12px", paddingLeft: "24px" }}>
                <li>Manter a confidencialidade de sua senha</li>
                <li>Todas as atividades realizadas em sua conta</li>
                <li>Notificar imediatamente qualquer uso não autorizado</li>
                <li>Manter suas informações de contato atualizadas</li>
              </ul>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                4. Assinaturas e Pagamentos
              </h2>
              <p>
                <strong style={{ color: "#fff" }}>4.1 Planos:</strong>{" "}
                Oferecemos planos Starter, Professional e Enterprise com
                diferentes níveis de recursos e limites de uso.
              </p>
              <p style={{ marginTop: "12px" }}>
                <strong style={{ color: "#fff" }}>4.2 Cobrança:</strong> As
                cobranças são realizadas mensalmente ou anualmente, conforme o
                ciclo de faturamento escolhido. O pagamento é processado
                automaticamente através do método de pagamento cadastrado.
              </p>
              <p style={{ marginTop: "12px" }}>
                <strong style={{ color: "#fff" }}>4.3 Reembolsos:</strong>{" "}
                Oferecemos garantia de reembolso de 14 dias para novos
                assinantes. Após este período, não são oferecidos reembolsos
                para períodos parciais.
              </p>
              <p style={{ marginTop: "12px" }}>
                <strong style={{ color: "#fff" }}>
                  4.4 Alterações de Preço:
                </strong>{" "}
                Reservamo-nos o direito de alterar os preços com aviso prévio de
                30 dias.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                5. Uso Aceitável
              </h2>
              <p>Você concorda em NÃO utilizar o Serviço para:</p>
              <ul style={{ marginTop: "12px", paddingLeft: "24px" }}>
                <li>Violar leis ou regulamentos aplicáveis</li>
                <li>
                  Infringir direitos de propriedade intelectual de terceiros
                </li>
                <li>Transmitir malware, vírus ou código malicioso</li>
                <li>Realizar engenharia reversa do software</li>
                <li>Compartilhar credenciais de acesso com terceiros</li>
                <li>
                  Utilizar sistemas automatizados para sobrecarregar o Serviço
                </li>
                <li>Coletar dados de outros usuários sem consentimento</li>
              </ul>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                6. Propriedade Intelectual
              </h2>
              <p>
                <strong style={{ color: "#fff" }}>6.1 Nossos Direitos:</strong>{" "}
                Todo o conteúdo, código, design e funcionalidades do Serviço são
                de propriedade exclusiva do Engenharia CAD e protegidos por leis
                de direitos autorais.
              </p>
              <p style={{ marginTop: "12px" }}>
                <strong style={{ color: "#fff" }}>6.2 Seus Direitos:</strong>{" "}
                Você mantém todos os direitos sobre seus projetos, desenhos CAD
                e dados enviados à plataforma. Concedemos a você uma licença
                limitada para usar o Serviço conforme estes termos.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                7. Limitação de Responsabilidade
              </h2>
              <p>
                O Serviço é fornecido "como está". Não garantimos que o Serviço
                será ininterrupto, seguro ou livre de erros. Em nenhuma
                circunstância seremos responsáveis por danos indiretos,
                incidentais, especiais ou consequenciais decorrentes do uso do
                Serviço.
              </p>
              <p style={{ marginTop: "12px" }}>
                Nossa responsabilidade total não excederá o valor pago por você
                nos últimos 12 meses de assinatura.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                8. Rescisão
              </h2>
              <p>
                Podemos suspender ou encerrar sua conta a qualquer momento por
                violação destes termos. Você pode cancelar sua assinatura a
                qualquer momento através das configurações da conta. Após o
                cancelamento, você terá acesso até o final do período de
                faturamento atual.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                9. Alterações nos Termos
              </h2>
              <p>
                Reservamo-nos o direito de modificar estes termos a qualquer
                momento. Notificaremos sobre alterações significativas por email
                ou através do Serviço. O uso continuado após as alterações
                constitui aceitação dos novos termos.
              </p>
            </section>

            <section style={{ marginBottom: "32px" }}>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                10. Lei Aplicável
              </h2>
              <p>
                Estes termos são regidos pelas leis do Brasil. Qualquer disputa
                será resolvida nos tribunais da cidade de São Paulo, SP.
              </p>
            </section>

            <section>
              <h2
                style={{
                  color: "#fff",
                  fontSize: "20px",
                  fontWeight: 600,
                  marginBottom: "16px",
                }}
              >
                11. Contato
              </h2>
              <p>Para dúvidas sobre estes Termos de Uso, entre em contato:</p>
              <ul style={{ marginTop: "12px", paddingLeft: "24px" }}>
                <li>
                  Email:{" "}
                  <a
                    href="mailto:legal@engenharia-cad.com"
                    style={{ color: "#00A1FF" }}
                  >
                    legal@engenharia-cad.com
                  </a>
                </li>
                <li>
                  Suporte:{" "}
                  <a
                    href="mailto:suporte@engenharia-cad.com"
                    style={{ color: "#00A1FF" }}
                  >
                    suporte@engenharia-cad.com
                  </a>
                </li>
              </ul>
            </section>
          </div>
        </motion.div>

        {/* Footer Links */}
        <div style={{ marginTop: "32px", textAlign: "center" }}>
          <Link
            to="/privacy"
            style={{
              color: "#00A1FF",
              fontSize: "14px",
              textDecoration: "none",
            }}
          >
            Ver Política de Privacidade →
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Terms;
