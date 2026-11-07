import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';
import { cadastrar } from '../services/authService';

function Cadastro() {
  const navigate = useNavigate();

  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState('');
  const [erroEmail, setErroEmail] = useState('');
  const [carregando, setCarregando] = useState(false);

  const irParaLogin = () => navigate('/login');

  async function handleSubmit(e) {
    e.preventDefault();
    if (carregando) return;

    setErro('');
    setErroEmail('');

    if (!nome.trim() || !email.trim() || !senha) {
      setErro('Preencha nome, e-mail e senha.');
      return;
    }

    setCarregando(true);
    try {
      await cadastrar(nome.trim(), email.trim(), senha);
      navigate('/login', {
        state: {
          aviso: 'Conta criada! Se pedirmos, confirme seu e-mail antes de entrar.',
        },
      });
    } catch (err) {
      if (err.code === 'EMAIL_DUPLICADO') {
        setErroEmail(err.message);
      } else {
        setErro(err.message || 'Erro ao cadastrar.');
      }
    } finally {
      setCarregando(false);
    }
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
          disabled={carregando}
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (erroEmail) setErroEmail('');
          }}
          disabled={carregando}
          aria-invalid={!!erroEmail}
        />
        {erroEmail && (
          <p className="auth-error" role="alert">
            {erroEmail}{' '}
            <button type="button" onClick={irParaLogin}>
              Fazer login
            </button>
          </p>
        )}
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
          {carregando ? 'Cadastrando...' : 'Cadastrar'}
        </button>
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
