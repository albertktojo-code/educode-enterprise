import { useEffect, useState } from 'react';

function ListaRegistros() {
  const [dados, setDados] = useState([]);
  const [novoNome, setNovoNome] = useState('');

  // Função para buscar dados
  const buscarDados = async () => {
    try {
      const response = await fetch('https://educode-enterprise-2.onrender.com/api/itens', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const json = await response.json();
      setDados(json);
    } catch (error) {
      console.error("Erro ao buscar dados:", error);
    }
  };

  // Função para adicionar item
  const adicionar = async () => {
    if (!novoNome.trim()) return;
    await fetch('https://educode-enterprise-2.onrender.com/api/itens', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}` 
      },
      body: JSON.stringify({ nome: novoNome })
    });
    setNovoNome('');
    buscarDados();
  };

  // Função para excluir item
  const deletar = async (id) => {
    if (!window.confirm("Deseja realmente excluir este projeto?")) return;
    
    await fetch(`https://educode-enterprise-2.onrender.com/api/itens/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    buscarDados();
  };

  useEffect(() => { buscarDados(); }, []);

  return (
    <div style={{ padding: '20px' }}>
      <h3>Meus Projetos</h3>
      
      <div style={{ marginBottom: '20px' }}>
        <input 
          value={novoNome} 
          onChange={(e) => setNovoNome(e.target.value)} 
          placeholder="Nome do novo projeto..."
          style={{ padding: '8px', marginRight: '10px' }}
        />
        <button onClick={adicionar} style={{ padding: '8px 15px' }}>Adicionar</button>
      </div>

      <table border="1" style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ padding: '10px' }}>ID</th>
            <th style={{ padding: '10px' }}>Nome do Projeto</th>
            <th style={{ padding: '10px' }}>Ações</th>
          </tr>
        </thead>
        <tbody>
          {dados.map((item) => (
            <tr key={item.id}>
              <td style={{ padding: '8px', textAlign: 'center' }}>{item.id}</td>
              <td style={{ padding: '8px' }}>{item.nome}</td>
              <td style={{ padding: '8px', textAlign: 'center' }}>
                <button 
                  onClick={() => deletar(item.id)} 
                  style={{ 
                    color: 'white', 
                    background: '#ff4d4d', 
                    border: 'none', 
                    padding: '5px 10px', 
                    cursor: 'pointer',
                    borderRadius: '4px' 
                  }}
                >
                  Excluir
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}