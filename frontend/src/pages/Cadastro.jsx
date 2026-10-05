import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';
import { useAuth } from '../context/useAuth';

function Cadastro() {
  const { autenticado, registrar } = useAuth();
  const navigate = useNavigate();
  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState('');
  const [enviando, setEnviando] = useState(false);

  if (autenticado) {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErro('');
    if (senha.length < 8) {
      setErro('A senha deve ter pelo menos 8 caracteres.');
      return;
    }
    setEnviando(true);
    try {
      await registrar(nome, email, senha);
      navigate('/login', { replace: true, state: { cadastroOk: true } });
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <AuthLayout>
      <h2>Criar conta</h2>
      <p className="auth-subtitle">Comece a monitorar em minutos</p>
      {erro ? <p className="auth-erro">{erro}</p> : null}
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Nome"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          required
          minLength={2}
          autoComplete="name"
        />
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
          placeholder="Senha (mínimo 8 caracteres)"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          required
          minLength={8}
          autoComplete="new-password"
        />
        <button type="submit" disabled={enviando}>
          {enviando ? 'Cadastrando...' : 'Cadastrar'}
        </button>
      </form>
      <p className="auth-switch">
        Já tem conta? <Link to="/login">Fazer login</Link>
      </p>
    </AuthLayout>
  );
}

export default Cadastro;
