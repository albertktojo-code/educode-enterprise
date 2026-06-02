import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Login({ setAuth }) {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async () => {
    if (!email || !senha) return alert("Preencha todos os campos");
    
    setLoading(true);
    try {
      const response = await fetch('https://educode-enterprise-2.onrender.com/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, senha })
      });

      if (response.status >= 500) {
        alert("O servidor está a acordar. Aguarde 5 segundos e clique novamente.");
        setLoading(false);
        return;
      }

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('token', data.token);
        localStorage.setItem('userEmail', email);
        
        // Força a atualização do estado global antes de navegar
        setAuth(true); 
        navigate('/dashboard');
      } else {
        alert("Erro no Login: " + (data.error || "Credenciais inválidas"));
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'center' }}>
        <input 
          type="text" 
          placeholder="Seu e-mail" 
          value={email} 
          onChange={(e) => setEmail(e.target.value)} 
          autoComplete="off"
        />
        <input 
          type="password" 
          placeholder="Sua senha" 
          value={senha} 
          onChange={(e) => setSenha(e.target.value)} 
          autoComplete="new-password"
        />
        <button onClick={handleLogin} disabled={loading}>
          {loading ? "A processar..." : "Entrar"}
        </button>
      </div>
    </div>
  );
}

export default Login;