import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

function Dashboard() {
  const { usuario, sair } = useAuth();

  return (
    <div>
      <h1>Dashboard</h1>
      <p>Olá{usuario?.nome ? `, ${usuario.nome}` : ''}!</p>
      <p><Link to="/produtos/novo">Cadastrar produto</Link></p>
      <button type="button" onClick={sair}>
        Sair
      </button>
    </div>
  );
}

export default Dashboard;