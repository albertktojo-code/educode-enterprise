import { useEffect, useState } from 'react';

function App() {
  const [status, setStatus] = useState("Conectando...");
  const [error, setError] = useState(null);

  // A variável de ambiente VITE_API_URL é definida no painel da Vercel
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

  useEffect(() => {
    async function checkBackend() {
      try {
        const response = await fetch(`${API_URL}/status`);
        if (!response.ok) throw new Error("Servidor não respondeu corretamente");
        
        const data = await response.json();
        setStatus(data.mensagem);
      } catch (err) {
        console.error("Erro na conexão:", err);
        setError("Não foi possível conectar ao backend.");
        setStatus("Offline");
      }
    }

    checkBackend();
  }, [API_URL]);

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-4">
      <h1 className="text-4xl font-bold mb-4">EduCode Enterprise</h1>
      
      <div className={`p-6 rounded-lg shadow-lg border ${error ? 'border-red-500 bg-red-900/20' : 'border-green-500 bg-green-900/20'}`}>
        <p className="text-xl">
          Status da API: 
          <span className="ml-2 font-mono font-bold">
            {status}
          </span>
        </p>
        {error && <p className="text-red-400 mt-2">{error}</p>}
      </div>

      <p className="mt-8 text-gray-500 text-sm">
        API Conectada em: {API_URL}
      </p>
    </div>
  );
}

export default App;