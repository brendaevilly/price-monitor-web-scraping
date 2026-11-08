import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';
import { login } from '../services/authService';
import { useAuth } from '../contexts/AuthContext';

function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { entrar } = useAuth();

  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(false);

  // Aviso vindo do cadastro ("conta criada...")
  const aviso = location.state?.aviso || '';
  // Volta para a página que o usuário tentou acessar antes de ser barrado
  const destino = location.state?.from?.pathname || '/dashboard';

  async function handleSubmit(e) {
    e.preventDefault();
    if (carregando) return;

    setErro('');

    if (!email.trim() || !senha) {
      setErro('Informe e-mail e senha.');
      return;
    }

    setCarregando(true);
    try {
      const dados = await login(email.trim(), senha);
      if (!entrar(dados)) {
        setErro('Resposta de login inesperada do servidor.');
        return;
      }
      navigate(destino, { replace: true });
    } catch (err) {
      setErro(err.message || 'Erro ao entrar.');
    } finally {
      setCarregando(false);
    }
  }

  return (
    <AuthLayout>
      <h2>Entrar</h2>
      <p className="auth-subtitle">Acesse sua conta</p>
      {aviso && (
        <p className="auth-success" role="status">
          {aviso}
        </p>
      )}
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={carregando}
        />
        <input
          type="password"
          placeholder="Senha"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          disabled={carregando}
        />
        {erro && (
          <p className="auth-error" role="alert">
            {erro}
          </p>
        )}
        <button type="submit" disabled={carregando}>
          {carregando ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
      <p className="auth-switch">
        Não tem conta?{' '}
        <button type="button" onClick={() => navigate('/cadastro')}>
          Cadastre-se
        </button>
      </p>
    </AuthLayout>
  );
}

export default Login;
