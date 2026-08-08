# AGENTS.md — EduCode Enterprise 2.0

## 1. Missão do projeto

O EduCode Enterprise 2.0 é uma plataforma educacional multi-organização para:

- criação de projetos educacionais;
- geração e edição de HQs;
- alinhamento à BNCC;
- desenvolvimento e avaliação de Pensamento Computacional;
- banco de questões;
- aplicação de avaliações;
- correção automática e assistida;
- Learning Analytics;
- intervenções pedagógicas;
- acessibilidade;
- auditoria;
- governança institucional;
- publicação e distribuição de conteúdos.

O objetivo é manter uma arquitetura única e rastreável. Não criar módulos
paralelos para funcionalidades que já possuem domínio canônico.

### 1.1 Arquitetura oficial de produtos

O EduCode é apresentado como nove produtos integrados:

- **EduCode Learn:** cursos, aulas, trilhas e conteúdos;
- **EduCode Studio:** HQs, animes, vídeos, áudios e materiais;
- **EduCode Practice:** exercícios, quizzes, programação e simulações;
- **EduCode Assess:** avaliações, banco de questões e instrumentos;
- **EduCode Tutor:** tutoria de IA e aprendizagem adaptativa;
- **EduCode Analytics:** desempenho, intervenções e eficácia;
- **EduCode Connect:** comunicação, fóruns e colaboração;
- **EduCode Credentials:** portfólio, competências e certificações;
- **EduCode Admin:** instituições, usuários, segurança e governança.

Essa divisão é uma arquitetura de produto e experiência, não uma autorização
para duplicar domínios técnicos. Modelos, tabelas, routers, eventos e serviços
canônicos continuam compartilhados. Em especial, Practice reutiliza itens do
Assessment Hub e execução do Assessment Delivery; Tutor reutiliza aprendizagem
adaptativa; Analytics consome evidências sem se tornar sua fonte primária.

O mapa completo de responsabilidades, limites e transição está em
`docs/PRODUCT_ARCHITECTURE.md`.

---

## 2. Stack principal

### Backend

- Python 3.12;
- FastAPI;
- SQLAlchemy assíncrono;
- Alembic;
- PostgreSQL;
- pgvector;
- Redis;
- Pydantic;
- pytest.

### Frontend

- React;
- TypeScript;
- Vite;
- CSS modularizado por feature;
- cliente HTTP centralizado;
- registro consolidado de rotas.

### Infraestrutura

- Docker Compose;
- Windows PowerShell para instalação;
- containers para backend, frontend, banco e Redis.

---

## 3. Raiz de trabalho

A raiz real do projeto é a pasta que contém:

- `docker-compose.yml`;
- `backend/`;
- `frontend/`;
- `.env`;
- diretórios de migrations e testes.

Nunca trate a pasta de um pacote de sprint como raiz da aplicação.

Os pacotes de sprint apenas atualizam a raiz consolidada.

---

## 4. Regra de continuidade

Antes de implementar qualquer sprint ou correção:

1. Auditar o estado real do repositório.
2. Identificar o head atual do Alembic.
3. Localizar modelos, tabelas, rotas e serviços já existentes.
4. Verificar se a funcionalidade solicitada já pertence a um domínio canônico.
5. Reutilizar estruturas existentes.
6. Não criar tabelas, routers ou páginas paralelas por conveniência.
7. Preservar compatibilidade com os dados e APIs anteriores.
8. Executar testes antes de concluir.

Não assumir que a documentação histórica representa exatamente o estado
instalado. O código e o banco são a fonte de verdade.

---

## 5. Hierarquia dos domínios

### 5.1 Fundação

Responsável por:

- organizações;
- usuários;
- autenticação;
- sessões;
- RBAC;
- auditoria;
- configurações;
- segurança;
- saúde da aplicação.

Esses módulos não devem ser duplicados por features.

### 5.2 Núcleo educacional

Responsável por:

- projetos;
- turmas;
- estudantes;
- professores;
- conteúdos;
- disciplinas;
- anos escolares;
- habilidades BNCC;
- Pensamento Computacional.

### 5.3 Conteúdo, biblioteca e RAG

Responsável por:

- materiais;
- documentos;
- chunks;
- embeddings;
- busca semântica;
- biblioteca institucional;
- referências;
- licenças;
- versões;
- aprovação de conteúdos.

### 5.4 Assessment Hub

É a fonte canônica para:

- itens de questão;
- versões de questão;
- habilidades associadas;
- instrumentos;
- bancos de questões;
- metadados pedagógicos;
- pontuação máxima;
- explicações;
- rubricas relacionadas.

Atividades criadas em HQs devem gerar ou vincular itens no Assessment Hub.
Não criar um banco de questões exclusivo para HQ.

### 5.5 Assessment Delivery

É a fonte canônica para:

- publicação de avaliações;
- público-alvo;
- turmas, grupos e estudantes;
- disponibilidade;
- tentativas;
- sessões;
- itens de sessão;
- respostas;
- autosave;
- retomada;
- tempo;
- eventos de execução;
- acomodações.

Não criar tentativas, sessões ou respostas em módulos de HQ.

### 5.6 Assessment Review

É a fonte canônica para:

- rubricas;
- versões de rubrica;
- revisão humana;
- pontuação por critério;
- feedback;
- contestação;
- recorreção;
- preservação de resultados anteriores.

A IA pode sugerir. O professor mantém a decisão final.

### 5.7 Assessment Analytics

É a fonte canônica para análises avaliativas.

Snapshots específicos de HQ podem consolidar dados, mas não devem substituir
eventos, resultados, tentativas ou métricas canônicas.

### 5.8 Aprendizagem adaptativa

Domínios:

- `adaptive_learning`;
- `adaptive_evolution`;
- `adaptive_insights`.

Responsáveis por:

- recomendações;
- trilhas adaptativas;
- evolução;
- evidências;
- explicabilidade das sugestões.

### 5.9 Intervenções

Domínios:

- `intervention_orchestration`;
- `intervention_effectiveness`.

Responsáveis por:

- planos de intervenção;
- grupos;
- ações;
- responsáveis;
- acompanhamento;
- eficácia;
- avaliação longitudinal.

### 5.10 HQ e narrativa

Domínios canônicos:

- editor de páginas;
- quadros;
- camadas;
- balões;
- personagens;
- capas;
- layouts;
- snapshots;
- autosave;
- continuidade narrativa;
- revisão editorial;
- publicação;
- leitor;
- acessibilidade;
- Analytics de leitura.

A estrutura narrativa utiliza tipos de página:

- `COVER`;
- `STORY`;
- `ACTIVITY`;
- `ANSWER_KEY`;
- `BACK_COVER`.

A contagem narrativa deve permanecer separada da contagem total do documento.

---

## 6. Evolução conhecida das sprints

### Sprint 16.3

Biblioteca visual institucional para HQs.

### Sprint 16.4

Revisão e publicação.

### Sprint 16.5

Leitor e acessibilidade.

### Sprint 16.6

Analytics de leitura.

### Sprint 16.7

Orquestração de intervenções.

### Sprint 16.8

Avaliação longitudinal da eficácia.

### Sprint 16.9

Governança institucional.

### Sprint 16.10

Editor visual inteligente e narrativa multipágina.

### Sprint 16.10.1

Capa, continuidade, autosave e estabilização do foco.

### Sprint 16.10.2

Produtividade avançada e assistente narrativo.

### Sprint 16.10.3

Balões inteligentes e revisão editorial.

### Sprint 16.11

Atividades interativas e avaliação pós-HQ.

### Sprint 16.11.1

Correção, rubricas e feedback.

### Sprint 16.11.2

Aplicação para turmas e monitoramento.

### Sprint 16.11.3

Experiência digital do estudante.

### Sprint 16.11.4

Analytics pós-HQ.

A próxima migration deve ser baseada no head real encontrado no repositório,
e não somente nesta lista.

---

## 7. Regras de banco e Alembic

Antes de criar uma migration:

1. Executar `alembic current`.
2. Executar `alembic heads`.
3. Confirmar que há apenas um head.
4. Pesquisar tabelas e colunas equivalentes.
5. Verificar migrations anteriores.
6. Evitar duplicação conceitual.
7. Criar constraints, índices e rollback.
8. Manter IDs de revision curtos e válidos.
9. Não editar migrations já aplicadas, salvo hotfix explicitamente aprovado.
10. Testar upgrade e downgrade.

Uma sprint funcional deve preferir zero ou uma nova tabela quando a estrutura
canônica já existe.

---

## 8. Regras de backend

- Usar `AsyncSession`.
- Restringir sempre por `organization_id`.
- Aplicar RBAC e dependências de autenticação existentes.
- Usar o sistema canônico de auditoria.
- Não criar autenticação alternativa.
- Não usar SQL textual quando `bulk_insert`, ORM ou Core tipado resolverem.
- Validar payloads com Pydantic.
- Retornar erros HTTP claros.
- Preservar idempotência.
- Manter imports compatíveis com a aplicação completa.
- Não incluir dados de demonstração em produção sem flag explícita.
- Não chamar serviços externos de IA diretamente quando existir orquestrador
  interno.
- Toda sugestão de IA deve manter revisão humana e rastreabilidade.

---

## 9. Regras de frontend

- Usar React e TypeScript.
- Reutilizar o cliente HTTP central.
- Reutilizar o registro consolidado de rotas.
- Não usar `fetch` bruto sem autenticação.
- Não criar páginas isoladas fora da navegação principal.
- Preservar responsividade.
- Preservar navegação por teclado.
- Usar labels, foco visível, `aria-live` e textos alternativos.
- Não depender apenas de cor.
- Exibir loading, erro e estado vazio.
- Não publicar automaticamente conteúdo gerado por IA.
- Não ocultar falhas de API com mocks silenciosos em produção.

---

## 10. Segurança e multi-organização

Toda consulta e escrita deve considerar:

- organização atual;
- usuário autenticado;
- papel;
- propriedade ou permissão;
- trilha de auditoria;
- isolamento dos dados;
- proteção de recursos docentes e gabaritos;
- minimização de dados do estudante.

Nunca confiar em `organization_id` enviado pelo cliente quando ele pode ser
obtido da sessão autenticada.

---

## 11. Acessibilidade

Toda nova interface deve considerar:

- WCAG;
- navegação por teclado;
- foco;
- leitor de tela;
- alto contraste;
- aumento de fonte;
- ordem de leitura;
- descrição de imagens;
- alternativa textual para atividades visuais;
- tempo adicional;
- redução de movimento quando aplicável.

---

## 12. Testes obrigatórios

Antes de concluir uma tarefa:

### Backend

- compilar os arquivos Python alterados;
- executar pytest focado;
- executar testes de contratos estáticos;
- verificar imports no container;
- testar autorização e isolamento organizacional;
- testar casos de erro;
- testar idempotência.

### Frontend

- executar TypeScript;
- executar `npm run build`;
- testar estados de loading, erro e vazio;
- testar navegação;
- testar responsividade;
- testar acessibilidade básica.

### Banco

- executar `alembic upgrade head`;
- executar `alembic current`;
- executar `alembic heads`;
- testar downgrade da nova migration.

### Docker

- executar `docker compose config --quiet`;
- construir backend e frontend;
- subir serviços;
- executar healthcheck;
- verificar `docker compose ps`.

Não declarar sucesso de testes que não foram realmente executados.

---

## 13. Padrão de sprint

Cada sprint deve conter:

- código completo;
- migration, quando necessária;
- testes;
- documentação;
- changelog;
- critérios de aceitação;
- instalador PowerShell;
- rollback;
- backup;
- verificação de compatibilidade;
- manifesto;
- SHA-256;
- instalação idempotente;
- relatório de instalação.

O instalador deve:

1. validar o pacote;
2. validar a sprint-base;
3. bloquear modificações externas inesperadas;
4. criar backup;
5. aplicar o payload;
6. executar validações locais;
7. executar build e testes;
8. aplicar migration;
9. subir os serviços;
10. registrar estado para rollback.

Não utilizar `-Force` como comportamento padrão.

---

## 14. Fluxo obrigatório do Codex

Ao receber uma nova tarefa:

1. Ler este `AGENTS.md`.
2. Ler o `README.md`.
3. Inspecionar `docker-compose.yml`.
4. Mapear backend, frontend, migrations e testes.
5. Executar `git status`.
6. Identificar o head Alembic.
7. Pesquisar implementações equivalentes.
8. Produzir um plano curto.
9. Implementar em mudanças pequenas.
10. Executar testes.
11. Corrigir falhas.
12. Resumir arquivos alterados, comandos executados e riscos restantes.

Não começar criando arquivos antes da auditoria.

---

## 15. Definição de pronto

Uma tarefa só está pronta quando:

- não duplica domínios;
- respeita multi-organização;
- respeita RBAC;
- possui auditoria;
- possui validação;
- possui testes;
- compila;
- mantém upgrade e rollback;
- preserva acessibilidade;
- documenta limitações;
- informa com exatidão o que foi ou não executado.
