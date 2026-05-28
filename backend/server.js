const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
require('dotenv').config();

const app = express();

// --- MIDDLEWARES ESSENCIAIS ---
app.use(cors({ origin: '*' }));
app.use(express.json()); // SE ISSO FALHAR, O POST NÃO FUNCIONA

// Configurações
const JWT_SECRET = process.env.JWT_SECRET || 'segredo_super_seguro';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

// --- ROTAS ---

// 1. Rota de Listagem
app.get('/api/itens', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM projetos ORDER BY id ASC');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: "Erro no banco de dados" });
  }
});

// 2. Rota de Login (POST)
app.post('/api/login', async (req, res) => {
  const { email, senha } = req.body;

  try {
    const result = await pool.query('SELECT * FROM usuarios WHERE email = $1', [email]);
    const usuario = result.rows[0];

    if (!usuario) {
      return res.status(401).json({ error: "Usuário não encontrado" });
    }

    const senhaValida = await bcrypt.compare(senha, usuario.senha);
    if (!senhaValida) {
      return res.status(401).json({ error: "Senha incorreta" });
    }

    const token = jwt.sign({ id: usuario.id, email: usuario.email }, JWT_SECRET, { expiresIn: '1h' });

    res.json({ token, message: "Login realizado com sucesso!" });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Erro no servidor" });
  }
});

// 3. Rota de Registro
app.post('/api/registro', async (req, res) => {
  const { email, senha } = req.body;
  
  try {
    const salt = await bcrypt.genSalt(10);
    const senhaHash = await bcrypt.hash(senha, salt);
    
    await pool.query('INSERT INTO usuarios (email, senha) VALUES ($1, $2)', [email, senhaHash]);
    res.status(201).json({ message: "Usuário criado com sucesso!" });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Erro ao registrar usuário" });
  }
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(`Servidor rodando na porta ${PORT}`));