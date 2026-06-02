import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Login({ setAuth }) {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await fetch('https://educode-enterprise-2.onrender.com/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, senha })
      });

      // Tratamento para servidor em modo de espera
      if (response.status >= 500) {
        alert("O servidor está a acordar (modo inativo). Aguarde 5 segundos e tente novamente.");
        setLoading(false);
        return;
      }

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('token', data.token);
        localStorage.setItem('userEmail', email);
        setAuth(true); // Atualiza o estado global e redireciona
        navigate('/dashboard');
      } else {
        alert("Erro: " + (data.error || "Credenciais inválidas"));
      }
    } catch (error) {
      alert("Erro de conexão. Verifique a rede.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <h2>Login</h2>
      <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'center' }}>
        <input 
          type="email" 
          placeholder="Seu e-mail" 
          value={email} 
          onChange={(e) => setEmail(e.target.value)} 
          required
        />
        <input 
          type="password" 
          placeholder="Sua senha" 
          value={senha} 
          onChange={(e) => setSenha(e.target.value)} 
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? "A entrar..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}

export default Login;