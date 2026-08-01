# Fase gráfica G3.1 do EduCode — 2026-07-31

## Objetivo

Consolidar a experiência de descoberta e retomada de HQs no EduCode sem criar
uma biblioteca paralela. O incremento cobre o catálogo de autoria em `/hqs` e
a biblioteca de releases publicadas em `/comic-reader`.

## Arquitetura preservada

- `GeneratedComic` continua sendo a fonte canônica de “Minhas HQs”;
- `ComicEditorialRelease` continua sendo a fonte canônica do leitor;
- o frontend mantém o cliente HTTP autenticado existente;
- organização, RBAC, revisão, publicação e apresentação não foram alterados;
- nenhuma rota, API, tabela ou migration foi criada;
- Alembic permanece em `0055_delivery_source_invariant`, head único.

## Linguagem visual compartilhada

O componente `ComicCover` gera capas gráficas determinísticas a partir do ID
do recurso. Ele não simula uma imagem editorial existente e não persiste dados:

- cinco variações cromáticas consistentes;
- título, edição e metadados já disponíveis na API;
- composição CSS responsiva, sem download externo;
- capa decorativa ignorada por leitores de tela, evitando conteúdo duplicado;
- transições de ponteiro respeitando `prefers-reduced-motion` global.

## Minhas HQs

- cabeçalho editorial com ação direta para criação;
- resumo de total, itens em revisão e itens aprovados;
- busca por título ou sinopse;
- filtro por status canônico;
- contagem de resultados com `aria-live`;
- loading compartilhado;
- estados vazios distintos para acervo vazio e filtro sem resultado;
- cards com continuidade, pedagogia, versão e data de atualização;
- ações existentes de canvas, revisão e storyboard preservadas.

O formulário de criação atual permanece funcional e será redesenhado no
incremento G3.2, sem antecipar mudanças no fluxo de geração.

## Biblioteca publicada

- hero próprio para o contexto de leitura;
- busca por título ou notas da publicação;
- capas e metadados de release;
- estado vazio orientativo;
- entrada por código preservada;
- ação de apresentação continua restrita pelo papel atual;
- leitura continua vinculada ao manifest e checkpoint canônicos.

## Responsividade e acessibilidade

- cards mudam de composição lateral para vertical em telas estreitas;
- resumo de autoria muda de três colunas para lista no celular;
- busca e filtro ocupam largura integral abaixo de 760 px;
- alvos principais mantêm altura mínima de 42–46 px;
- foco, teclado e redução de movimento reutilizam a fundação G1;
- estados de erro usam `role="alert"`;
- loading e vazio usam `aria-live`.

## Validação executada

- lint do frontend: aprovado;
- TypeScript e build Vite: aprovados;
- 21 testes focados de HQ, leitor e contratos da Sprint 16.5: aprovados;
- healthcheck da API: HTTP 200;
- conteúdo atualizado confirmado no frontend servido pelo container;
- Alembic current/heads: `0055_delivery_source_invariant`, head único;
- `git diff --check`: aprovado;
- nenhuma migration criada.

O build mantém o aviso conhecido do bundle principal acima de 500 kB. A
inspeção visual automatizada no navegador foi iniciada, mas a conexão do
controle persistente se perdeu durante o reinício do frontend e a contingência
do Windows expirou aguardando autorização do aplicativo. Por isso, não há
declaração de validação visual completa de breakpoints neste registro.

## Próximo incremento

G3.2 deve modernizar a entrada do estúdio e o fluxo de criação, reutilizando o
formulário e os endpoints atuais. Editor, leitor imersivo e monitoramento
permanecem para os incrementos posteriores da G3.
