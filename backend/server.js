require('dotenv').config();
const { Pool } = require('pg');
const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// A URL de conexão vem da variável configurada no painel do Render
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

// Rota para listar dados do Postgres
app.get('/api/itens', async (req, res) => {
  try {
    const { rows } = await pool.query('SELECT * FROM projetos ORDER BY id ASC');
    res.json(rows);
  } catch (err) {
    console.error("Erro ao buscar no banco:", err);
    res.status(500).json({ error: "Erro interno no servidor" });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Servidor rodando na porta ${PORT}`));