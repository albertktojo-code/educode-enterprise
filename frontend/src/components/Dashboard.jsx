import { useState } from 'react';
import ListaRegistros from './ListaRegistros';

function Dashboard({ setAuth }) {
  const [novoNome, setNovoNome] = useState('');

  const handleAdicionar = async () => {
    const token = localStorage.getItem('token');
    
    // Diagnóstico rápido de autenticação
    if (!token) {
      alert("Erro: Você não está logado. Faça o login novamente.");
      setAuth(false);
      return;
    }

    try {
      const response = await fetch('https://educode-enterprise-2.onrender.com/api/itens', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ nome: novoNome })
      });

      if (response.ok) {
        setNovoNome('');
        window.location.reload(); 
      } else {
        const errorData = await response.json().catch(() => ({}));
        alert(`Erro do Servidor (${response.status}): ${errorData.message || "Falha na criação"}`);
      }
    } catch (error) {
      alert("Erro de Conexão: Verifique se o backend está online.");
      console.error(error);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#f4f4f9' }}>
      {/* Menu Lateral */}
      <nav style={{ width: '220px', backgroundColor: '#2c3e50', color: 'white', padding: '20px' }}>
        <h2>EduCode AI</h2>
        <button 
          onClick={() => { localStorage.clear(); setAuth(false); }}
          style={{ marginTop: '20px', width: '100%', padding: '10px', cursor: 'pointer' }}
        >
          Sair
        </button>
      </nav>

      {/* Área Principal */}
      <main style={{ flex: 1, padding: '40px' }}>
        <h1>Painel de Controle</h1>
        
        {/* Formulário de Criação */}
        <div style={{ background: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
          <input 
            value={novoNome} 
            onChange={(e) => setNovoNome(e.target.value)} 
            placeholder="Nome do novo item..."
            style={{ padding: '8px', width: '250px' }}
          />
          <button 
            onClick={handleAdicionar}
            style={{ marginLeft: '10px', padding: '8px 16px', cursor: 'pointer' }}
          >
            Adicionar
          </button>
        </div>

        {/* Tabela de Registros */}
        <div style={{ background: 'white', padding: '20px', borderRadius: '8px' }}>
          <ListaRegistros />
        </div>
      </main>
    </div>
  );
}

export default Dashboard;