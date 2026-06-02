import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import Login from './components/Login';

function Dashboard({ setAuth }) {
  const emailUsuario = localStorage.getItem('userEmail') || 'Usuário';
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.clear();
    setAuth(false);
    navigate('/login');
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <nav style={{ width: '200px', background: '#f4f4f4', padding: '20px', borderRight: '1px solid #ccc' }}>
        <h3>Menu</h3>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          <li style={{ margin: '10px 0' }}>Início</li>
          <li style={{ margin: '10px 0' }}>Relatórios</li>
          <li style={{ margin: '10px 0' }}>Configurações</li>
        </ul>
        <button onClick={handleLogout}>Sair</button>
      </nav>
      <main style={{ flex: 1, padding: '20px' }}>
        <h1>Bem-vindo ao Sistema!</h1>
        <p>Olá, <strong>{emailUsuario}</strong>.</p>
      </main>
    </div>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login setAuth={setIsAuthenticated} />} />
        <Route 
          path="/dashboard" 
          element={isAuthenticated ? <Dashboard setAuth={setIsAuthenticated} /> : <Navigate to="/login" />} 
        />
        <Route path="*" element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} />} />
      </Routes>
    </Router>
  );
}

export default App;