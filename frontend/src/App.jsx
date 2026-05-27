import { useState } from 'react';

// Esta variável busca a URL do backend nas variáveis de ambiente do deploy (Vercel)
// Ou usa o localhost se estiver rodando na sua máquina
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file) {
      alert("Por favor, selecione um arquivo PDF primeiro.");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_URL}/processar`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Erro na comunicação com o servidor");

      const data = await response.json();
      setResult(data.texto);
    } catch (error) {
      console.error("Erro:", error);
      alert("Erro ao processar o arquivo. Verifique se o servidor está rodando.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8 font-sans text-slate-900">
      <header className="mb-10 text-center">
        <h1 className="text-4xl font-extrabold text-blue-900 tracking-tight">
          EduCode Enterprise
        </h1>
        <p className="text-slate-600 mt-2">
          Transformando documentos educacionais em narrativas lógicas
        </p>
      </header>

      <main className="max-w-3xl mx-auto bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-200">
        <div className="flex flex-col gap-4">
          <label className="block text-sm font-medium text-slate-700">
            Selecione o arquivo PDF
          </label>
          <input 
            type="file" 
            accept=".pdf"
            onChange={(e) => setFile(e.target.files[0])}
            className="block w-full text-sm text-slate-500 
              file:mr-4 file:py-2.5 file:px-4 
              file:rounded-full file:border-0 
              file:text-sm file:font-semibold 
              file:bg-blue-50 file:text-blue-700 
              hover:file:bg-blue-100 transition-all cursor-pointer"
          />
          
          <button 
            onClick={handleUpload}
            disabled={loading}
            className={`w-full py-3 rounded-xl font-bold text-white transition-all
              ${loading 
                ? 'bg-blue-400 cursor-not-allowed' 
                : 'bg-blue-900 hover:bg-blue-800 active:scale-[0.98]'}`}
          >
            {loading ? "Processando com IA..." : "Gerar Conteúdo"}
          </button>
        </div>

        {result && (
          <div className="mt-8 border-t border-slate-100 pt-8 animate-in fade-in duration-500">
            <h2 className="text-xl font-bold text-blue-900 mb-4">Resultado:</h2>
            <div 
              className="prose prose-slate max-w-none text-slate-700 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: result }} 
            />
          </div>
        )}
      </main>
      
      <footer className="mt-12 text-center text-slate-400 text-sm">
        EduCode AI © 2026
      </footer>
    </div>
  );
}

export default App;