import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';

function RotaProtegida({ children }) {
  const { autenticado } = useAuth();

  if (!autenticado) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default RotaProtegida;
