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
    return new ApiError('Dados inválidos na requisição.', 'DADOS_INVALIDOS', status);
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

// UC07: classificação da queda e variações percentuais
export const buscarAnalise = (produtoId) => get(`/produtos/${produtoId}/analise`);

// UC09: alertas mais recentes
export const listarAlertas = (limite = 5) => get('/alertas', { limite });
