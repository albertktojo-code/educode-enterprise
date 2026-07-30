# Sprint 08 — Estúdio do Professor, HQ multipágina e canvas visual

A Sprint 08 transforma a estrutura criada nas Sprints 07–07.2 em uma experiência orientada ao professor. Ela separa a área docente das telas técnicas e oferece criação guiada, direção de arte, pacotes pedagógicos coerentes e um canvas visual para páginas, quadros e balões.

## Objetivos

- reduzir a complexidade apresentada ao professor;
- permitir HQs com várias páginas e funções diferentes;
- manter imagem, balões e metadados em camadas independentes;
- criar materiais complementares usando o mesmo contexto pedagógico;
- preparar o pacote para publicação e futura distribuição às turmas;
- preservar versionamento, concorrência e rastreabilidade das versões anteriores.

## Estúdio do Professor

Nova rota web:

```text
/estudio-professor
```

O assistente possui os modos rápido e avançado e orienta o usuário por cinco etapas:

1. objetivo, disciplina, turma e planejamento pedagógico;
2. materiais desejados;
3. direção de arte;
4. planejamento multipágina;
5. revisão e geração do pacote.

Quando um planejamento e um contexto RAG aprovado são selecionados, a HQ é gerada automaticamente e incluída no pacote. Sem contexto aprovado, o rascunho e o pacote continuam disponíveis para planejamento e revisão.

## Materiais no mesmo pacote

O professor poderá combinar:

- HQ;
- quiz;
- exercícios;
- atividade prática;
- jogo;
- plano de aula;
- sequência didática;
- gabarito;
- orientações ao professor.

Todos recebem o mesmo tema, objetivo, faixa escolar, contexto e direção de arte.

## HQ multipágina

O planejador pode criar:

- capa;
- páginas narrativas;
- página de exercícios;
- gabarito;
- orientações ao professor.

Cada página armazena função, quantidade de quadros, layout e função narrativa. A recomendação determinística distribui contextualização, problema, investigação, complicação, pista, plot twist, aplicação e resolução.

## Direção de arte

Presets iniciais:

- Mangá educativo;
- HQ americana;
- Quadrinho europeu;
- Cartoon educativo;
- Anime escolar;
- Anime de aventura;
- Infantil lúdico;
- Ficção científica educativa.

A direção de arte registra intensidade, cor, detalhamento, expressividade, paleta emocional, sentido de leitura e mudanças intencionais de estilo. O texto continua fora da imagem.

## Canvas visual

Nova rota:

```text
/canvas/{comic_id}
```

Recursos implementados:

- miniaturas de páginas;
- adicionar, duplicar, excluir e reorganizar páginas;
- arrastar quadros;
- redimensionar quadros;
- arrastar e redimensionar balões;
- selecionar formatos retangular, horizontal, vertical, quadrado, circular, oval e panorâmico;
- editar descrição da cena e texto dos balões;
- zoom;
- painel de propriedades contextual;
- painel de camadas;
- margens seguras;
- salvamento em lote com controle de revisão;
- criação automática de uma nova versão após salvar.

## Preparação para publicação

O pacote possui checklist para:

- materiais gerados;
- contexto compartilhado;
- direção de arte;
- páginas da HQ;
- prontidão do canvas;
- separação entre imagem e balões.

Estados:

```text
not_ready
ready_with_warnings
ready
```

A Sprint 09 utilizará esse pacote para publicar materiais para turmas, grupos e estudantes específicos.

## API

Prefixo principal:

```text
/api/v1/teacher-studio
```

Recursos:

- templates de criação;
- presets de direção de arte;
- CRUD de rascunhos;
- recomendação de páginas;
- geração de pacotes;
- preparação para publicação;
- salvamento em lote do canvas;
- adição, duplicação, exclusão e reordenação de páginas.

## Migration

```text
0012_comic_stabilization
        ↓
0013_teacher_studio_canvas
```

Novas tabelas:

- `teacher_studio_drafts`;
- `art_direction_presets`;
- `pedagogical_packages`;
- `package_materials`;
- `publication_preparations`.

Novos campos em HQs e páginas:

- `generated_comics.art_direction`;
- `generated_comics.canvas_config`;
- `generated_comics.publication_status`;
- `comic_pages.page_role`;
- `comic_pages.background_config`;
- `comic_pages.guides_config`.

## Próxima etapa

Sprint 09 — publicação e área do estudante:

- atribuição para turma, grupo ou usuário;
- prazo e disponibilidade;
- tentativas;
- área do estudante;
- realização de exercícios;
- armazenamento das respostas;
- correção automática de itens objetivos.
