import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './AppLayout.css';

const icone = {
  width: 16,
  height: 16,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
};

const IconeInicio = () => (
  <svg {...icone}>
    <path d="M3 11l9-8 9 8" />
    <path d="M5 10v10h14V10" />
  </svg>
);

const IconeProdutos = () => (
  <svg {...icone}>
    <path d="M21 8l-9-5-9 5 9 5 9-5z" />
    <path d="M3 8v8l9 5 9-5V8" />
    <path d="M12 13v8" />
  </svg>
);

const IconeAlertas = () => (
  <svg {...icone}>
    <path d="M3 11v2a1 1 0 001 1h2l7 4V6L6 10H4a1 1 0 00-1 1z" />
    <path d="M16 9a4 4 0 010 6" />
  </svg>
);

const IconeConfiguracoes = () => (
  <svg {...icone}>
    <circle cx="12" cy="12" r="3" />
    <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9L7 7M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" />
  </svg>
);

const classeLink = ({ isActive }) => (isActive ? 'app-nav-item ativo' : 'app-nav-item');

function AppLayout() {
  const { usuario, sair } = useAuth();
  const inicial = (usuario?.nome || usuario?.email || '?').slice(0, 2).toUpperCase();

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="app-logo">
          <svg {...icone} width={15} height={15}>
            <circle cx="12" cy="12" r="9" />
            <circle cx="12" cy="12" r="3" fill="currentColor" />
          </svg>
          PriceBrother
        </div>

        <nav className="app-nav" aria-label="Navegação principal">
          <NavLink to="/dashboard" className={classeLink}>
            <IconeInicio /> Início
          </NavLink>
          <NavLink to="/produtos/novo" className={classeLink}>
            <IconeProdutos /> Produtos
          </NavLink>
          {/* Ainda sem tela: ficam visíveis como no protótipo, sem link */}
          <span className="app-nav-item desativado">
            <IconeAlertas /> Alertas
          </span>
          <span className="app-nav-item desativado">
            <IconeConfiguracoes /> Configurações
          </span>
        </nav>
      </aside>

      <div className="app-conteudo">
        <header className="app-topo">
          <button type="button" className="app-sair" onClick={sair}>
            Sair
          </button>
          <span className="app-avatar" aria-label={usuario?.nome || usuario?.email}>
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
