import api from './api';

export async function buscarHistorico(produtoId) {
  const response = await api.get(`/produtos/${produtoId}/historico`);
  return response.data;
}

export async function buscarAnalise(produtoId) {
  const response = await api.get(`/produtos/${produtoId}/analise`);
  return response.data;
}

// Classificações do UC11 (Comparar Preços e Identificar Queda), na ordem de gravidade.
// As chaves são exatamente os valores devolvidos por GET /produtos/{id}/analise.
export const CLASSIFICACAO_UC11 = {
  sem_dados: { rotulo: 'Sem dados suficientes', faixa: 'histórico insuficiente para classificar' },
  sem_queda: { rotulo: 'Sem queda', faixa: 'redução inferior a 5%' },
  pequena_queda: { rotulo: 'Pequena queda', faixa: 'redução entre 5% e 9%' },
  queda_relevante: { rotulo: 'Queda relevante', faixa: 'redução entre 10% e 19%' },
  grande_queda: { rotulo: 'Grande queda', faixa: 'redução igual ou superior a 20%' },
};
