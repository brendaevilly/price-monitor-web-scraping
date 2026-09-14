import api from './api';

export async function cadastrar(nome, email, senha) {
  const response = await api.post('/cadastro', { nome, email, senha });
  return response.data;
}

export async function login(email, senha) {
  const response = await api.post('/login', { email, senha });
  return response.data;
}