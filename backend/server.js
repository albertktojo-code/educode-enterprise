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

// --- ROTAS ---

// Rota de Listagem
app.get('/api/itens', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM projetos ORDER BY id ASC');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: "Erro no banco de dados" });
  }
});

// Rota de Login (Otimizada)
app.post('/api/login', async (req, res) => {
  let { email, senha } = req.body;

  if (!email || !senha) {
    return res.status(400).json({ error: "Email e senha são obrigatórios" });
  }

  // Sanitização
  const emailLimpo = email.trim().toLowerCase();

  try {
    console.log(`Tentando login para: ${emailLimpo}`);
    
    // Busca normalizada
    const result = await pool.query('SELECT * FROM usuarios WHERE LOWER(email) = $1', [emailLimpo]);
    
    if (result.rows.length === 0) {
      return res.status(401).json({ error: "Usuário não encontrado" });
    }

    const usuario = result.rows[0];

    // Comparação de senha
    const senhaValida = await bcrypt.compare(senha, usuario.senha);
    if (!senhaValida) {
      return res.status(401).json({ error: "Senha incorreta" });
    }

    // Geração de token
    const token = jwt.sign({ id: usuario.id, email: usuario.email }, JWT_SECRET, { expiresIn: '1h' });
    
    res.json({ token, message: "Login realizado com sucesso!" });
  } catch (err) {
    console.error("Erro no login:", err);
    res.status(500).json({ error: "Erro interno no servidor" });
  }
});

// Rota de Registro
app.