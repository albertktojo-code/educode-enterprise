import { useNavigate } from 'react-router-dom';

function Login({ setAuth }) {
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    
    // Captura os dados diretamente do DOM, ignorando estados de input do React
    const formData = new FormData(e.target);
    const email = formData.get('email');
    const senha = formData.get('senha');

    try {
      const response = await fetch('https://educode-enterprise-2.onrender.com/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, senha })
      });

      // Tratamento para o servidor gratuito do Render acordando
      if (response.status >= 500) {
        alert("O servidor está a acordar. Aguarde alguns segundos e clique novamente.");
        return;
      }

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('token', data.token);
        localStorage.setItem('userEmail', email);
        setAuth(true); // Atualiza o estado global no App.jsx
        navigate('/dashboard');
      } else {
        alert("Erro: " + (data.error || "Credenciais inválidas"));
      }
    } catch (error) {
      alert("Erro de conexão com o servidor.");
    }
  };

  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <h2>Login</h2>
      <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'center' }}>
        <input name="email" type="email" placeholder="Seu e-mail" required style={{ padding: '8px' }} />
        <input name="senha" type="password" placeholder="Sua senha" required style={{ padding: '8px' }} />
        <button type="submit" style={{ padding: '8px 20px', cursor: 'pointer' }}>Entrar</button>
      </form>
    </div>
  );
}

export default Login;