function AuthLayout({ children }) {
  return (
    <div className="auth-page">
      <div className="auth-hero">
        <div className="auth-logo">
          <div className="auth-logo-mark"></div>
          <span className="auth-logo-text">PriceBrother</span>
        </div>
        <div className="auth-radar auth-radar-desktop">
          <div className="auth-radar-ring auth-radar-ring-1"></div>
          <div className="auth-radar-ring auth-radar-ring-2"></div>
          <div className="auth-radar-ring auth-radar-ring-3"></div>
          <div className="auth-radar-sweep"></div>
          <span className="auth-radar-chip auth-radar-chip-1">-18%</span>
          <span className="auth-radar-chip auth-radar-chip-2">-7%</span>
        </div>
        <div>
          <p className="auth-hero-title">Seu irmão avisa quando o preço cai</p>
          <p className="auth-hero-subtitle">Monitore produtos e receba um aviso na hora certa.</p>
        </div>
      </div>
      <div className="auth-form-panel">
        <div className="auth-radar auth-radar-mobile">
          <div className="auth-radar-ring auth-radar-ring-1"></div>
          <div className="auth-radar-ring auth-radar-ring-2"></div>
          <div className="auth-radar-ring auth-radar-ring-3"></div>
          <div className="auth-radar-sweep"></div>
          <span className="auth-radar-chip auth-radar-chip-1">-18%</span>
          <span className="auth-radar-chip auth-radar-chip-2">-7%</span>
        </div>
        <div className="auth-form-inner">
          <div className="auth-logo auth-logo-mobile">
            <div className="auth-logo-mark"></div>
            <span className="auth-logo-text">PriceBrother</span>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

export default AuthLayout;