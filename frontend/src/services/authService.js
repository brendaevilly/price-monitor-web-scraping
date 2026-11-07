import api from './api';

// Erro padronizado para as telas: { message, code, status }
export class AuthError extends Error {
  constructor(message, code, status) {
    super(message);
    this.name = 'AuthError';
    this.code = code;
    this.status = status;
  }
}

// FastAPI manda `detail` como string (HTTPException) ou lista (422 do Pydantic)
function detalheString(data) {
  return typeof data?.detail === 'string' ? data.detail : null;
}

function traduzirErro(error, contexto) {
  // Sem resposta do servidor: rede caiu, backend fora do ar, CORS, etc.
  if (!error.response) {
    return new AuthError(
      'Não foi possível conectar ao servidor. Tente novamente.',
      'REDE',
      0
    );
  }

  const { status, data } = error.response;
  const detalhe = detalheString(data);

  // Cadastro: e-mail já existe
  if (contexto === 'cadastro' && status === 409) {
    return new AuthError(
      detalhe || 'Já existe um usuário cadastrado com este e-mail.',
      'EMAIL_DUPLICADO',
      status
    );
  }

  // Login: e-mail ou senha incorretos
  if (contexto === 'login' && status === 401) {
    return new AuthError(
      detalhe || 'E-mail ou senha incorretos.',
      'CREDENCIAIS_INVALIDAS',
      status
    );
  }

  // Login: e-mail não confirmado ou cadastro incompleto
  if (contexto === 'login' && status === 403) {
    const naoConfirmado = (detalhe || '').toLowerCase().includes('confirmado');
    return new AuthError(
      detalhe || 'Acesso negado.',
      naoConfirmado ? 'EMAIL_NAO_CONFIRMADO' : 'ACESSO_NEGADO',
      status
    );
  }

  // Validação do Pydantic (e-mail malformado, campo faltando, senha curta...)
  if (status === 422 || status === 400) {
    return new AuthError(
      'Dados inválidos. Verifique nome, e-mail e senha.',
      'DADOS_INVALIDOS',
      status
    );
  }

  // 502/5xx: o detail pode conter texto interno do Supabase, então não exibimos
  if (status >= 500) {
    return new AuthError(
      'Serviço indisponível no momento. Tente novamente em instantes.',
      'ERRO_SERVIDOR',
      status
    );
  }

  return new AuthError(detalhe || 'Erro inesperado.', 'DESCONHECIDO', status);
}

export async function cadastrar(nome, email, senha) {
  try {
    const response = await api.post('/usuarios', { nome, email, senha });
    return response.data;
  } catch (error) {
    throw traduzirErro(error, 'cadastro');
  }
}

export async function login(email, senha) {
  try {
    const response = await api.post('/usuarios/login', { email, senha });
    return response.data;
  } catch (error) {
    throw traduzirErro(error, 'login');
  }
}