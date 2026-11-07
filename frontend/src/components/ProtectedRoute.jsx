import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

// Rotas que exigem login. Sem autenticação, vai para /login guardando a origem.
export function ProtectedRoute() {
  const { autenticado } = useAuth();
  const location = useLocation();

  if (!autenticado) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

// Rotas de visitante (login/cadastro): quem já está logado vai para o dashboard.
export function PublicOnlyRoute() {
  const { autenticado } = useAuth();

  if (autenticado) {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}