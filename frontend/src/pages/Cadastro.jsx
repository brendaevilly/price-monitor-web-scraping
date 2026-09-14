import { useState } from 'react';
import AuthLayout from '../components/AuthLayout';

function Cadastro({ irParaLogin }) {
  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    console.log('Cadastro simulado:', { nome, email, senha });
  }

  return (
    <AuthLayout>
      <h2>Criar conta</h2>
      <p className="auth-subtitle">Comece a monitorar em minutos</p>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Nome"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
        />
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
        <button type="submit">Cadastrar</button>
      </form>
      <p className="auth-switch">
        Já tem conta?{' '}
        <button type="button" onClick={irParaLogin}>
          Fazer login
        </button>
      </p>
    </AuthLayout>
  );
}

export default Cadastro;