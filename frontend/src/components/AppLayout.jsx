import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  IconeAlertas,
  IconeConfig,
  IconeInicio,
  IconeLogo,
  IconePacoteBusca,
} from './Icones';
import './AppLayout.css';

const classeLink = ({ isActive }) =>
  isActive ? 'app-nav-item ativo' : 'app-nav-item';

function AppLayout() {
  const { usuario, sair } = useAuth();
  const inicial = (usuario?.nome || usuario?.email || '?')
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="app-logo">
          <IconeLogo />
          PriceBrother
        </div>

        <nav className="app-nav" aria-label="Navegação principal">
          <NavLink to="/dashboard" className={classeLink}>
            <IconeInicio /> Início
          </NavLink>

          <NavLink to="/produtos" className={classeLink}>
            <IconePacoteBusca /> Produtos
          </NavLink>
        </nav>
      </aside>

      <div className="app-conteudo">
        <header className="app-topo">
          <button type="button" className="app-sair" onClick={sair}>
            Sair
          </button>
          <span
            className="app-avatar"
            aria-label={usuario?.nome || usuario?.email}
          >
            {inicial}
          </span>
        </header>

        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AppLayout;
