import { useEffect, useState } from 'react';

function App() {
  const [itens, setItens] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Substitua pela sua URL real do Render
  const API_URL = "https://educode-enterprise-2.onrender.com";

  useEffect(() => {
    fetch(`${API_URL}/api/itens`)
      .then(res => res.json())
      .then(data => {
        setItens(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Erro na busca:", err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-3xl font-bold mb-6 text-center">EduCode Enterprise</h1>
      
      {loading ? (
        <p className="text-center">Carregando dados...</p>
      ) : (
        <div className="max-w-4xl mx-auto bg-gray-800 rounded-lg shadow-xl border border-gray-700">
          <table className="w-full text-left">
            <thead className="bg-gray-700">
              <tr>
                <th className="p-4">ID</th>
                <th className="p-4">Projeto</th>
                <th className="p-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((item) => (
                <tr key={item.id} className="border-b border-gray-600 hover:bg-gray-700">
                  <td className="p-4">{item.id}</td>
                  <td className="p-4">{item.nome}</td>
                  <td className="p-4 text-blue-400 font-semibold">{item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default App;