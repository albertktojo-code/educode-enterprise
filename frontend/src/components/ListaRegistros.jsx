import { useEffect, useState } from 'react';

function ListaRegistros({ onUpdate }) {
  const [dados, setDados] = useState([]);

  const buscarDados = async () => {
    try {
      const response = await fetch('https://educode-enterprise-2.onrender.com/api/itens', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const json = await response.json();
      setDados(Array.isArray(json) ? json : []);
    } catch (error) {
      console.error("Erro ao buscar dados:", error);
    }
  };

  const deletar = async (id) => {
    if (!window.confirm("Deseja realmente excluir este item?")) return;
    await fetch(`https://educode-enterprise-2.onrender.com/api/itens/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    buscarDados(); // Atualiza a lista localmente
    if (onUpdate) onUpdate(); // Notifica o Dashboard
  };

  useEffect(() => { buscarDados(); }, []);

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
      <thead>
        <tr style={{ background: '#eee' }}>
          <th style={{ border: '1px solid #ccc', padding: '8px' }}>ID</th>
          <th style={{ border: '1px solid #ccc', padding: '8px' }}>Nome</th>
          <th style={{ border: '1px solid #ccc', padding: '8px' }}>Ações</th>
        </tr>
      </thead>
      <tbody>
        {dados.map((item) => (
          <tr key={item.id}>
            <td style={{ border: '1px solid #ccc', padding: '8px' }}>{item.id}</td>
            <td style={{ border: '1px solid #ccc', padding: '8px' }}>{item.nome}</td>
            <td style={{ border: '1px solid #ccc', padding: '8px', textAlign: 'center' }}>
              <button 
                onClick={() => deletar(item.id)} 
                style={{ background: '#ff4d4d', color: 'white', border: 'none', padding: '5px 10px', cursor: 'pointer' }}
              >
                Excluir
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default ListaRegistros;