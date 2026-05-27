import React, { useState, useEffect } from 'react';

const HABILIDADES = ["Abstração", "Decomposição", "Reconhecimento de Padrões", "Algoritmos"];
const DISCIPLINAS = ["Matemática", "Português", "Ciências", "História", "Geografia", "Artes"];
const SERIES = ["1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano", "6º Ano", "7º Ano", "8º Ano", "9º Ano", "Ensino Médio"];

function App() {
  const [form, setForm] = useState({ disciplina: "", serie: "", estilo: "HQ", hab: [], cenario: "", personagens: "", arqCen: null, arqPer: null });
  const [historico, setHistorico] = useState([]);

  const carregar = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/historico");
      const data = await res.json();
      setHistorico(Array.isArray(data) ? data : []);
    } catch (e) { setHistorico([]); }
  };

  useEffect(() => { carregar(); }, []);

  const enviar = async () => {
    const data = new FormData();
    data.append("disciplina", form.disciplina);
    data.append("serie", form.serie);
    data.append("estilo", form.estilo);
    data.append("habilidades", JSON.stringify(form.hab));
    data.append("cenario", form.cenario);
    data.append("personagens", form.personagens);
    if (form.arqCen) data.append("arquivo_cenario", form.arqCen);
    if (form.arqPer) data.append("arquivo_personagens", form.arqPer);
    
    await fetch("http://127.0.0.1:8000/gerar-conteudo", { method: "POST", body: data });
    carregar();
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans text-gray-900">
      <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-sm border p-8">
        <h1 className="text-3xl font-bold mb-6 text-blue-900">Gerador Pedagógico (PC)</h1>
        
        <div className="grid grid-cols-2 gap-4 mb-6">
          <select className="p-3 border rounded-lg" onChange={e => setForm({...form, disciplina: e.target.value})}>
            <option>Selecione a Disciplina</option>
            {DISCIPLINAS.map(d => <option key={d}>{d}</option>)}
          </select>
          <select className="p-3 border rounded-lg" onChange={e => setForm({...form, serie: e.target.value})}>
            <option>Selecione a Série</option>
            {SERIES.map(s => <option key={s}>{s}</option>)}
          </select>
        </div>

        <div className="mb-6">
          <label className="font-bold mb-2 block">Habilidades Trabalhadas:</label>
          <div className="flex gap-2 flex-wrap">
            {HABILIDADES.map(h => (
              <button key={h} onClick={() => setForm(p => ({...p, hab: p.hab.includes(h) ? p.hab.filter(i=>i!==h) : [...p.hab, h]}))}
                className={`px-4 py-2 rounded-full border ${form.hab.includes(h) ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>
                {h}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6 mb-6">
          <div className="border p-4 rounded-xl">
            <label className="font-bold">Cenário</label>
            <textarea className="w-full mt-2 border p-2 rounded" placeholder="Descreva..." onChange={e => setForm({...form, cenario: e.target.value})} />
            <input type="file" className="mt-2 text-xs" onChange={e => setForm({...form, arqCen: e.target.files[0]})} />
          </div>
          <div className="border p-4 rounded-xl">
            <label className="font-bold">Personagens</label>
            <textarea className="w-full mt-2 border p-2 rounded" placeholder="Descreva..." onChange={e => setForm({...form, personagens: e.target.value})} />
            <input type="file" className="mt-2 text-xs" onChange={e => setForm({...form, arqPer: e.target.files[0]})} />
          </div>
        </div>

        <button onClick={enviar} className="w-full bg-blue-900 text-white py-4 rounded-xl font-bold hover:bg-blue-800 transition">GERAR CONTEÚDO</button>

        <div className="mt-10 border-t pt-6">
          <h2 className="font-bold text-lg mb-4">Histórico</h2>
          {historico.map(h => <div key={h.id} className="p-3 border-b">{h.tema} - {h.disciplina} ({h.serie})</div>)}
        </div>
      </div>
    </div>
  );
}
export default App;