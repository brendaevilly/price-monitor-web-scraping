import api from './api';

// Erro padronizado para as telas: { message, code, status }
export class ApiError extends Error {
  constructor(message, code, status) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

// FastAPI manda `detail` como string (HTTPException) ou lista (422 do Pydantic)
function detalheString(data) {
  return typeof data?.detail === 'string' ? data.detail : null;
}

function traduzirErro(error) {
  if (error.code === 'ECONNABORTED') {
    return new ApiError(
      'O servidor demorou para responder. Tente novamente.',
      'TIMEOUT',
      0
    );
  }

  // Sem resposta do servidor: rede caiu, backend fora do ar, CORS, etc.
  if (!error.response) {
    return new ApiError(
      'Não foi possível conectar ao servidor. Tente novamente.',
      'REDE',
      0
    );
  }

  const { status, data } = error.response;
  const detalhe = detalheString(data);

  // O 401 é tratado no interceptor de api.js (limpa a sessão e vai para /login)
  if (status === 404) {
    return new ApiError(detalhe || 'Produto não encontrado.', 'NAO_ENCONTRADO', status);
  }
  if (status === 422 || status === 400) {
    // 422 do Pydantic traz lista em `detail`; mensagens de regra de negócio vêm como string
    return new ApiError(detalhe || 'Dados inválidos na requisição.', 'DADOS_INVALIDOS', status);
  }
  if (status >= 500) {
    return new ApiError(
      'Serviço indisponível no momento. Tente novamente em instantes.',
      'ERRO_SERVIDOR',
      status
    );
  }
  return new ApiError(detalhe || 'Erro inesperado.', 'DESCONHECIDO', status);
}

async function get(url, params) {
  try {
    const response = await api.get(url, { params });
    return response.data;
  } catch (error) {
    throw traduzirErro(error);
  }
}

// UC06: produtos que o usuário monitora
export const listarProdutos = () => get('/produtos');

// Preço atual, menor preço, média e classificação de todos os produtos (1 chamada)
export const resumoAnalise = () => get('/analise/resumo');

// UC06/UC07: coletas válidas em ordem cronológica + preço atual, menor preço e média
export const buscarHistorico = (produtoId) => get(`/produtos/${produtoId}/historico`);

// UC07/UC11: classificação da queda e variações percentuais.
// janelaDias: janela da média em dias (0 = todo o histórico); omitido = padrão do servidor.
export const buscarAnalise = (produtoId, janelaDias) =>
  get(
    `/produtos/${produtoId}/analise`,
    janelaDias === undefined || janelaDias === null ? undefined : { janela_dias: janelaDias }
  );

// UC09: alertas mais recentes
export const listarAlertas = (limite = 5) => get('/alertas', { limite });

// UC08: ativar/desativar alerta e definir/limpar o preço-alvo.
// `campos` aceita { alertaAtivo?: boolean, precoAlvo?: number | null }.
// precoAlvo null limpa o preço-alvo; vai como string ("1299.90") para o Decimal do Pydantic.
export async function atualizarMonitoramento(monitoramentoId, { alertaAtivo, precoAlvo }) {
  const corpo = {};
  if (alertaAtivo !== undefined) corpo.alerta_ativo = alertaAtivo;
  if (precoAlvo !== undefined) {
    corpo.preco_alvo = precoAlvo === null ? null : Number(precoAlvo).toFixed(2);
  }
  try {
    const response = await api.patch(`/monitoramentos/${monitoramentoId}`, corpo);
    return response.data;
  } catch (error) {
    throw traduzirErro(error);
  }
}

// RF17/RN05: remove só o vínculo do usuário; o histórico de preços do produto é preservado.
export async function removerMonitoramento(monitoramentoId) {
  try {
    await api.delete(`/monitoramentos/${monitoramentoId}`);
  } catch (error) {
    throw traduzirErro(error);
  }
}
