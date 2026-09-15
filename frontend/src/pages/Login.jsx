import { useState } from 'react';
import AuthLayout from '../components/AuthLayout';

function Login({ irParaCadastro }) {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    console.log('Tentando logar com:', email, senha);
  }

  return (
    <AuthLayout>
      <h2>Entrar</h2>
      <p className="auth-subtitle">Acesse sua conta</p>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder="Senha"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
        />
        <button type="submit">Entrar</button>
      </form>
      <p className="auth-switch">
        Não tem conta?{' '}
        <button type="button" onClick={irParaCadastro}>
          Cadastre-se
        </button>
      </p>
    </AuthLayout>
  );
}

export default Login;