import { useAuth } from '../context/useAuth';

function Dashboard() {
  const { usuario, sair } = useAuth();

  return (
    <div className="dash-page">
      <header className="dash-header">
        <div className="auth-logo">
          <div className="auth-logo-mark"></div>
          <span className="auth-logo-text">PriceBrother</span>
        </div>
        <div className="dash-user">
          <span>{usuario?.nome || usuario?.email}</span>
          <button type="button" onClick={sair}>
            Sair
          </button>
        </div>
      </header>
      <main className="dash-main">
        <h1>Dashboard</h1>
        <p className="dash-lead">
          Você está autenticado. O cadastro de produtos monitorados e o histórico
          entram nas próximas telas.
        </p>
        <section className="dash-card">
          <h2>Monitoramentos</h2>
          <p>Nenhum produto monitorado ainda.</p>
        </section>
      </main>
    </div>
  );
}

export default Dashboard;
