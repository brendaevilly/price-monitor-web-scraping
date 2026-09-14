import { useState } from 'react';
import Login from './pages/Login';
import Cadastro from './pages/Cadastro';

function App() {
  const [tela, setTela] = useState('login');

  return (
    <div>
      {tela === 'login' ? (
        <Login irParaCadastro={() => setTela('cadastro')} />
      ) : (
        <Cadastro irParaLogin={() => setTela('login')} />
      )}
    </div>
  );
}

export default App;
