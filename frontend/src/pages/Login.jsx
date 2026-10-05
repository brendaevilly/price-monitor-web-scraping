import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';
import { useAuth } from '../context/useAuth';

function Login() {
  const { autenticado, entrar } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState('');
  const [enviando, setEnviando] = useState(false);
  const avisoCadastro = location.state?.cadastroOk
    ? 'Conta criada. Entre com o e-mail e a senha.'
    : '';

  if (autenticado) {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErro('');
    setEnviando(true);
    try {
      await entrar(email, senha);
      navigate('/dashboard', { replace: true });
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <AuthLayout>
      <h2>Entrar</h2>
      <p className="auth-subtitle">Acesse sua conta</p>
      {avisoCadastro ? <p className="auth-sucesso">{avisoCadastro}</p> : null}
      {erro ? <p className="auth-erro">{erro}</p> : null}
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
        <input
          type="password"
          placeholder="Senha"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          required
          autoComplete="current-password"
        />
        <button type="submit" disabled={enviando}>
          {enviando ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
      <p className="auth-switch">
        Não tem conta? <Link to="/cadastro">Cadastre-se</Link>
      </p>
    </AuthLayout>
  );
}

export default Login;
