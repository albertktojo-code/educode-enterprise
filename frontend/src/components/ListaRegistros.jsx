import { useEffect, useState } from 'react';

function ListaRegistros() {
  const [dados, setDados] = useState([]);
  const [novoNome, setNovoNome] = useState('');

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
      <h3>Gerenciar Projetos</h3>
      
      <div style={{ marginBottom: '20px' }}>
        <input 
          value={novoNome} 
          onChange={(e) => setNovoNome(e.target.value)} 
          placeholder="Nome do projeto..."
          style={{ padding: '8px', marginRight: '10px' }}
        />
        <button onClick={adicionar} style={{ padding: '8px 15px' }}>Adicionar</button>
      </div>

      <table border="1" style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nome do Projeto</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {dados.map((item) => (
            <tr key={item.id}>
              <td style={{ padding: '8px' }}>{item.id}</td>
              <td style={{ padding: '8px' }}>{item.nome}</td>
              <td style={{ padding: '8px', textAlign: 'center' }}>
                <button onClick={() => deletar(item.id)} style={{ color: 'white', background: 'red', border: 'none', padding: '5px 10px', cursor: 'pointer' }}>
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

export default ListaRegistros;