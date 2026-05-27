import { useEffect, useState } from 'react';

function App() {
  const [itens, setItens] = useState([]);
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

  useEffect(() => {
    fetch(`${API_URL}/api/itens`)
      .then(res => res.json())
      .then(data => setItens(data))
      .catch(err => console.error("Erro ao carregar itens:", err));
  }, [API_URL]);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-3xl font-bold mb-6 text-center">EduCode Enterprise</h1>
      
      <div className="max-w-4xl mx-auto bg-gray-800 rounded-lg overflow-hidden shadow-xl border border-gray-700">
        <table className="w-full text-left">
          <thead className="bg-gray-700">
            <tr>
              <th className="p-4">ID</th>
              <th className="p-4">Nome do Projeto</th>
              <th className="p-4">Status</th>
            </tr>
          </thead>
          <tbody>
            {itens.map((item) => (
              <tr key={item.id} className="border-b border-gray-600 hover:bg-gray-700 transition">
                <td className="p-4">{item.id}</td>
                <td className="p-4">{item.nome}</td>
                <td className="p-4 text-blue-400 font-semibold">{item.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <p className="mt-8 text-center text-gray-500 text-xs">
        Conectado em: {API_URL}
      </p>
    </div>
  );
}

export default App;