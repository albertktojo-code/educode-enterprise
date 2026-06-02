import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Login() {
  // 1. Estados para armazenar o que o usuário digita
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const navigate = useNavigate();

  // 2. Função que dispara ao clicar no botão "Entrar"
  const handleLogin = async (e) => {
    e.preventDefault(); // Impede o comportamento padrão do form (recarregar a página)

    try {
      // 3. Chamada para a API do seu servidor no Render
      const response = await fetch('https://educode-enterprise-2.onrender.com/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, senha })
      });

      const data = await response.json();

      // 4. Verificação da resposta
      if (response.ok) {
        localStorage.setItem('token', data.token); // Salva o token no navegador
        alert("Login realizado com sucesso!");
        navigate('/dashboard'); // Redireciona para a página interna
      } else {
        alert("Erro: " + (data.error || "Falha no login"));
      }
    } catch (error) {
      alert("Erro de conexão com o servidor. Verifique se o backend está online.");
    }
  };

  // 5. Estrutura visual do formulário
  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <h2>Login</h2>
      <form onSubmit={handleLogin} style={{ display: 'inline-flex', flexDirection: 'column', gap: '10px' }}>
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
        <button type="submit">Entrar</button>
      </form>
    </div>
  );
}

export default Login;