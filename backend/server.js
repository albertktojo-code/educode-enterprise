const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
require('dotenv').config();

const app = express();

// Middlewares
app.use(cors({ origin: '*' }));
app.use(express.json());

const JWT_SECRET = process.env.JWT_SECRET || 'segredo_super_seguro';

// Pool de Conexão
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

console.log("Servidor iniciado. Conectado ao banco.");

// --- ROTAS ---

// Rota de Teste/Listagem
app.get('/api/itens', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM projetos ORDER BY id ASC');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: "Erro no banco de dados" });
  }
});

// Rota de Login Corrigida
app.post('/api/login', async (req, res) => {
  const { email, senha } = req.body;

  if (!email || !senha) {
    return res.status(400).json({ error: "Email e senha são obrigatórios" });
  }

  const emailLimpo = email.trim().toLowerCase();

  try {
    const result = await pool.query('SELECT * FROM usuarios WHERE LOWER(email) = $1', [emailLimpo]);
    
    if (result.rows.length === 0) {
      return res.status(401).json({ error: "Usuário não encontrado" });
    }

    const usuario = result.rows[0];
    const senhaValida = await bcrypt.compare(senha, usuario.senha);
    
    if (!senhaValida) {
      return res.status(401).json({ error: "Senha incorreta" });
    }

    const token = jwt.sign({ id: usuario.id, email: usuario.email }, JWT_SECRET, { expiresIn: '1h' });
    res.json({ token, message: "Login realizado com sucesso!" });
  } catch (err) {
    console.error("Erro no login:", err);
    res.status(500).json({ error: "Erro interno no servidor" });
  }
});

// Rota de Registro
app.post('/api/registro', async (req, res) => {
  const { email, senha } = req.body;
  try {
    const salt = await bcrypt.genSalt(10);
    const senhaHash = await bcrypt.hash(senha, salt);
    await pool.query('INSERT INTO usuarios (email, senha) VALUES ($1, $2)', [email.toLowerCase(), senhaHash]);
    res.status(201).json({ message: "Usuário criado com sucesso!" });
  } catch (err) {
    console.error("Erro no registro:", err);
    res.status(500).json({ error: "Erro ao registrar usuário" });
  }
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(`Servidor rodando na porta ${PORT}`));