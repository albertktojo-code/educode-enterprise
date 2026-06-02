import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';

// Um componente simples para o seu Dashboard (pode ser movido para um arquivo separado depois)
function Dashboard() {
  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <h1>Bem-vindo ao Sistema!</h1>
      <button onClick={() => { localStorage.removeItem('token'); window.location.reload(); }}>
        Sair
      </button>
    </div>
  );
}

function App() {
  // Verifica se o usuário está logado olhando o localStorage
  const isAuthenticated = !!localStorage.getItem('token');

  return (
    <Router>
      <Routes>
        {/* Rota de Login */}
        <Route path="/login" element={<Login />} />
        
        {/* Rota Protegida (Dashboard) */}
        <Route 
          path="/dashboard" 
          element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} 
        />
        
        {/* Rota padrão: redireciona tudo para /login */}
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}

export default App;