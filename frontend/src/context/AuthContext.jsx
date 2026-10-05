import { useCallback, useMemo, useState } from 'react';
import {
  cadastrar as cadastrarApi,
  estaAutenticado,
  login as loginApi,
  logout as logoutApi,
  obterUsuario,
} from '../services/authService';
import { AuthContext } from './auth-context';

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(() => obterUsuario());
  const [autenticado, setAutenticado] = useState(() => estaAutenticado());

  const entrar = useCallback(async (email, senha) => {
    const dados = await loginApi(email, senha);
    setUsuario(dados.usuario);
    setAutenticado(true);
    return dados;
  }, []);

  const registrar = useCallback(async (nome, email, senha) => {
    return cadastrarApi(nome, email, senha);
  }, []);

  const sair = useCallback(() => {
    logoutApi();
    setUsuario(null);
    setAutenticado(false);
  }, []);

  const valor = useMemo(
    () => ({ usuario, autenticado, entrar, registrar, sair }),
    [usuario, autenticado, entrar, registrar, sair],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
