const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors({ origin: "*" }));
app.use(express.json());

// Rota de status para verificar se o backend está vivo
app.get('/status', (req, res) => {
    res.json({ status: "online", mensagem: "Backend conectado com sucesso!" });
});

// Rota de itens (sua funcionalidade principal)
app.get('/api/itens', (req, res) => {
    const dados = [
        { id: 1, nome: "Dashboard Administrativo", status: "Concluído" },
        { id: 2, nome: "Autenticação de Usuários", status: "Em progresso" },
        { id: 3, nome: "Relatórios de Vendas", status: "Pendente" }
    ];
    res.json(dados);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Servidor rodando na porta ${PORT}`);
});