const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
    res.send('Backend rodando com sucesso!');
});

const PORT = 3000;
app.listen(PORT, () => console.log(`Servidor rodando na porta ${PORT}`));