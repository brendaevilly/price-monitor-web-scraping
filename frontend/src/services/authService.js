import api from './api';

const CHAVE_TOKEN = 'pb_access_token';
const CHAVE_REFRESH = 'pb_refresh_token';
const CHAVE_USUARIO = 'pb_usuario';

export function mensagemErroAuth(erro, fallback) {
  const detalhe = erro?.response?.data?.detail;
  if (typeof detalhe === 'string' && detalhe.trim()) {
    return detalhe;
  }
  if (Array.isArray(detalhe) && detalhe[0]?.msg) {
    return detalhe[0].msg;
  }
  if (!erro?.response) {
    return 'Não foi possível conectar à API. Confira se o backend está no ar.';
  }
  return fallback;
}

export async function cadastrar(nome, email, senha) {
  try {
    const response = await api.post('/usuarios', { nome, email, senha });
    return response.data;
  } catch (erro) {
    if (erro.response?.status === 409) {
      throw new Error('Já existe um usuário cadastrado com este e-mail.', { cause: erro });
    }
    throw new Error(mensagemErroAuth(erro, 'Não foi possível concluir o cadastro.'), { cause: erro });
  }
}

export async function login(email, senha) {
  try {
    const response = await api.post('/usuarios/login', { email, senha });
    const dados = response.data;
    salvarSessao(dados);
    return dados;
  } catch (erro) {
    if (erro.response?.status === 401) {
      throw new Error('E-mail ou senha incorretos.', { cause: erro });
    }
    throw new Error(mensagemErroAuth(erro, 'Não foi possível entrar. Tente novamente.'), { cause: erro });
  }
}

export function salvarSessao(dados) {
  if (dados?.access_token) {
    localStorage.setItem(CHAVE_TOKEN, dados.access_token);
  }
  if (dados?.refresh_token) {
    localStorage.setItem(CHAVE_REFRESH, dados.refresh_token);
  }
  if (dados?.usuario) {
    localStorage.setItem(CHAVE_USUARIO, JSON.stringify(dados.usuario));
  }
}

export function obterUsuario() {
  const bruto = localStorage.getItem(CHAVE_USUARIO);
  if (!bruto) {
    return null;
  }
  try {
    return JSON.parse(bruto);
  } catch {
    return null;
  }
}

export function obterToken() {
  return localStorage.getItem(CHAVE_TOKEN);
}

export function estaAutenticado() {
  return Boolean(obterToken());
}

export function logout() {
  localStorage.removeItem(CHAVE_TOKEN);
  localStorage.removeItem(CHAVE_REFRESH);
  localStorage.removeItem(CHAVE_USUARIO);
}
