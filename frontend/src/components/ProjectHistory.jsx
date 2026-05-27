import React, { useState, useEffect } from 'react';

function ProjectHistory() {
  // 1. Inicialize sempre como array vazio
  const [projetos, setProjetos] = useState([]);

  useEffect(() => {
    // 2. Verifique se a URL está correta (mude para /historico)
    fetch("http://127.0.0.1:8000/historico")
      .then(res => res.json())
      .then(data => {
        // 3. Garanta que você está setando um array
        // Se a API retornar um objeto, use setProjetos(data.algo)
        setProjetos(Array.isArray(data) ? data : []);
      })
      .catch(err => console.error("Erro ao buscar:", err));
  }, []);

  return (
    <div>
      {/* 4. Validação de segurança antes do .map */}
      {projetos && projetos.length > 0 ? (
        projetos.map((item) => (
          <div key={item.id}>{item.tema}</div>
        ))
      ) : (
        <p>Nenhum projeto encontrado ou carregando...</p>
      )}
    </div>
  );
}

export default ProjectHistory;