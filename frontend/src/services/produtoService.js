import api from './api';

export async function buscarHistorico(produtoId) {
  const response = await api.get(`/produtos/${produtoId}/historico`);
  return response.data;
}

export async function buscarAnalise(produtoId, janelaDias) {
  const response = await api.get(`/produtos/${produtoId}/analise`, {
    params: janelaDias === undefined || janelaDias === null ? undefined : { janela_dias: janelaDias },
  });
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

// ---- UC04: cadastrar produto monitorado ----

// Erro padronizado para a tela: { message, status, campos: { nome|url|loja|preco: msg } }
export class ProdutoError extends Error {
  constructor(message, { status = 0, campos = {} } = {}) {
    super(message);
    this.name = 'ProdutoError';
    this.status = status;
    this.campos = campos;
  }
}

// Nome do campo no backend -> nome do campo no formulário
const CAMPO_POR_LOC = { nome: 'nome', url_produto: 'url', loja_id: 'loja', dominio: 'loja', preco_alvo: 'preco' };
const limparMsg = (msg) => String(msg || '').replace(/^Value error,\s*/i, '');

function traduzirErro(error) {
  if (!error.response) {
    return new ProdutoError('Não foi possível conectar ao servidor. Tente novamente.');
  }
  const { status, data } = error.response;
  const detail = data?.detail;

  if (status === 401) return new ProdutoError('Sua sessão expirou. Entre novamente.', { status });

  // 422 do Pydantic: lista de { loc: ['body', 'url_produto'], msg }
  if (Array.isArray(detail)) {
    const campos = {};
    for (const item of detail) {
      const campo = CAMPO_POR_LOC[item.loc?.[item.loc.length - 1]];
      if (campo && !campos[campo]) campos[campo] = limparMsg(item.msg);
    }
    const message = Object.keys(campos).length ? 'Corrija os campos destacados.' : 'Dados inválidos.';
    return new ProdutoError(message, { status, campos });
  }

  if (status >= 500) {
    return new ProdutoError('Serviço indisponível no momento. Tente novamente em instantes.', { status });
  }

  if (typeof detail === 'string') {
    // Ex.: loja inexistente / URL que não pertence à loja -> mostra no campo Loja
    if ([400, 404, 422].includes(status) && /loja/i.test(detail)) {
      return new ProdutoError(detail, { status, campos: { loja: detail } });
    }
    return new ProdutoError(detail, { status });
  }
  return new ProdutoError('Erro inesperado.', { status });
}

// Passa o token explicitamente: funciona com ou sem interceptor no `api`.
const auth = (token) => ({ headers: { Authorization: `Bearer ${token}` } });

async function chamar(promessa) {
  try {
    const { data } = await promessa;
    return data;
  } catch (error) {
    throw traduzirErro(error);
  }
}

export const listarLojas = (token) => chamar(api.get('/lojas', auth(token)));

export const criarLoja = (token, { nome, dominio }) =>
  chamar(api.post('/lojas', { nome, dominio }, auth(token)));

// precoAlvo vai como string ("1299.90") para o Decimal do Pydantic não sofrer com float
export const criarProduto = (token, { nome, urlProduto, lojaId, precoAlvo }) =>
  chamar(
    api.post(
      '/produtos',
      {
        nome,
        url_produto: urlProduto,
        loja_id: lojaId,
        ...(precoAlvo != null ? { preco_alvo: precoAlvo.toFixed(2) } : {}),
      },
      auth(token)
    )
  );