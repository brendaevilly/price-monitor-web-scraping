import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const AuthContext = createContext(null);
const CHAVE = 'auth';

function lerSessao() {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (!bruto) return null;
    const sessao = JSON.parse(bruto);
    // Descarta sessão já expirada
    if (sessao?.expiraEm && sessao.expiraEm <= Date.now()) {
      localStorage.removeItem(CHAVE);
      return null;
    }
    return sessao;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [sessao, setSessao] = useState(lerSessao);

  // Recebe a resposta de POST /usuarios/login (LoginOut). Retorna false se não veio token.
  const entrar = useCallback((dados) => {
    const token = dados?.access_token ?? null;
    if (!token) return false;

    const nova = {
      token,
      refreshToken: dados.refresh_token ?? null,
      expiraEm: dados.expires_in ? Date.now() + dados.expires_in * 1000 : null,
      usuario: dados.usuario ?? null,
    };

    try {
      localStorage.setItem(CHAVE, JSON.stringify(nova));
    } catch {
      // storage indisponível: a sessão vale só até recarregar a página
    }
    setSessao(nova);
    return true;
  }, []);

  const sair = useCallback(() => {
    try {
      localStorage.removeItem(CHAVE);
    } catch {
      // ignorado
    }
    setSessao(null);
  }, []);

  const valor = useMemo(
    () => ({
      token: sessao?.token ?? null,
      usuario: sessao?.usuario ?? null,
      autenticado: !!sessao?.token,
      entrar,
      sair,
    }),
    [sessao, entrar, sair]
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth deve ser usado dentro de <AuthProvider>');
  return ctx;
}
