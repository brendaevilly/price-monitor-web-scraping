import axios from 'axios';

const CHAVE_SESSAO = 'auth'; // mesma chave usada no AuthContext

const api = axios.create({
  
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  timeout: 5000,
});

function lerToken() {
  try {
    const bruto = localStorage.getItem(CHAVE_SESSAO);
    return bruto ? JSON.parse(bruto)?.token ?? null : null;
  } catch {
    return null;
  }
}

// Anexa o access token em toda requisição, se houver sessão
api.interceptors.request.use((config) => {
  const token = lerToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});


api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url ?? '';
    const ehRotaDeLogin = url.includes('/usuarios/login');

    if (status === 401 && !ehRotaDeLogin && lerToken()) {
      try {
        localStorage.removeItem(CHAVE_SESSAO);
      } catch {
        // ignorado
      }
      // Recarrega para o AuthContext reler o storage já limpo
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    return Promise.reject(error);
  }
);

export default api;