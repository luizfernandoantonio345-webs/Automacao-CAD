import { ApiService } from "../services/api";

export const gerarTesteStress50Porticos = () => {
  const configuracao = {
    vao: 25,
    altura: 8,
    espacamento: 6,
    qtdPorticos: 50,
    perfil: "W310x32.7",
    gerarCotas: true,
  };

  const entidadesPorticos = [];

  for (let i = 0; i < configuracao.qtdPorticos; i += 1) {
    const posicaoZ = i * configuracao.espacamento * 1000;

    entidadesPorticos.push({
      tipo: "PORTICO_COMPLETO",
      id: `P-${i + 1}`,
      coordenadas: { x: 0, y: 0, z: posicaoZ },
      dimensoes: {
        vao: configuracao.vao * 1000,
        altura: configuracao.altura * 1000,
      },
      detalhes: {
        perfil: configuracao.perfil,
        inclinacao_telhado: "10%",
        gerar_cotas_auto: true,
      },
    });
  }

  return {
    header: {
      projeto: "TESTE_STRESS_PETROBRAS_50",
      versao: "1.0.0_ENTERPRISE",
      timestamp: new Date().toISOString(),
    },
    entidades: entidadesPorticos,
  };
};

export const dispararTesteStress50Porticos = async () => {
  const resposta = await ApiService.dispararTesteStress50Porticos();
  return resposta;
};
