const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
require('dotenv').config();

const app = express();

app.use(cors({ origin: '*' }));
app.use(express.json());

const JWT_SECRET = process.env.JWT_SECRET || 'segredo_super_seguro';

// Configuração do pool com log da URL (para confirmar o ambiente)
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

console.log("Servidor iniciado. Conectado ao banco: " + process.env.DATABASE_URL.substring(0, 20) + "...");

// Rota de Login com Diagnóstico
app.post('/api/login', async (req, res) => {
  const { email, senha } = req.body;
  
  console.log("Tentativa de login recebida para:", email);

  try {
    const result = await pool.query('SELECT * FROM usuarios WHERE email = $1', [email]);
    
    if (result.rows.length === 0) {
      console.log("Erro: Usuário não encontrado no banco.");
      return res.status(401).json({ error: "Usuário não encontrado" });
    }

    const usuario = result.rows[0];
    console.log("Usuário encontrado. Verificando senha...");

    const senhaValida = await bcrypt.compare(senha, usuario.senha);
    if (!senhaValida) {
      console.log("Erro: Senha incorreta.");
      return res.status(401).json({ error: "Senha incorreta" });
    }

    const token = jwt.sign({ id: usuario.id, email: usuario.email }, JWT_SECRET, { expiresIn: '1h' });
    console.log("Login realizado com sucesso para:", email);

    res.json({ token, message: "Login realizado com sucesso!" });
  } catch (err) {
    console.error("Erro interno do servidor:", err);
    res.status(500).json({ error: "Erro no servidor" });
  }
});

// Outras rotas permanecem iguais...
app.get('/api/itens', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM projetos ORDER BY id ASC');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: "Erro ao listar itens" });
  }
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(`Servidor rodando na porta ${PORT}`));