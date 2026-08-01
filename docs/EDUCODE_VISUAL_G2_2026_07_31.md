# Fase gráfica G2 do EduCode — 2026-07-31

## Objetivo

Padronizar a apresentação de dados do EduCode sobre a arquitetura existente,
sem criar rotas, APIs, tabelas ou fluxos paralelos. A entrega cobre métricas,
filtros, carregamento, estados vazios e tabelas nas páginas de maior alcance.

## Componentes canônicos

### `StatusCard`

O componente existente foi consolidado como fonte compartilhada para métricas:

- valores numéricos ou textuais;
- estados neutro, informativo, positivo, atenção e crítico;
- indicador semântico que não depende somente de cor;
- skeleton interno com `aria-busy` durante carregamento;
- grade responsiva de uma a seis colunas.

### `LoadingState`

- skeleton reutilizável para listas e painéis;
- descrição invisível para leitores de tela;
- animação desativada por `reduce-motion` ou `prefers-reduced-motion`.

### `EmptyState`

- ícones SVG consistentes;
- título, explicação e ação opcional;
- estado anunciado por `role="status"` e `aria-live`;
- diferencia ausência inicial de dados de busca sem resultado.

## Páginas consolidadas

- painel operacional principal;
- dashboard de Learning Analytics;
- dashboard de aprendizagem adaptativa;
- alertas pedagógicos;
- projetos educacionais.

As tabelas existentes em Assessment Review, Analytics de HQ e outros domínios
receberam estilos compartilhados sem alterar suas fontes canônicas de dados.

## Filtros e interação

- filtros de projeto expõem `aria-pressed`;
- busca usa `type="search"` e nome acessível;
- alvos de filtro possuem pelo menos 44 px;
- controles mudam de uma linha para grade no celular;
- tabelas mantêm rolagem horizontal local sem provocar overflow no documento;
- ações internas de Analytics e adaptação usam navegação React sem recarga
  completa da aplicação.

## Inconsistência corrigida

O CSS do painel de Analytics do editor de HQ usava o seletor genérico
`.analytics-actions`. Como a folha da feature é carregada pelo registro
consolidado, ela sobrescrevia os controles do dashboard global. O seletor foi
isolado como `.hq-analytics-actions`, eliminando a dependência da ordem de
imports sem alterar o comportamento do editor.

## Evidências visuais

- desktop `1280 × 720`: cinco métricas no painel e três por linha nos
  dashboards analíticos;
- tablet `820 × 1180`: formulários e painéis em coluna, filtros preservados;
- celular `390 × 844`: filtros em grade, busca com largura integral e nenhum
  overflow horizontal;
- tabela de revisão no celular: rolagem interna de 433 px em viewport local de
  317 px, sem overflow no documento;
- skeletons observados durante a carga real de Analytics;
- estados vazios observados em projetos, turmas, atividades, alertas,
  recomendações e domínio adaptativo;
- foco de teclado visível com outline da marca;
- console do navegador sem erros da aplicação.

## Validação técnica

- lint e build do frontend aprovados;
- suíte backend preservada;
- smoke autenticado preservado;
- Alembic mantido em `0055_delivery_source_invariant`, head único;
- nenhuma migration criada.

O bundle principal continua acima de 500 kB. O aviso é conhecido e permanece
como trabalho de performance e code splitting.

## Próxima fase

A Fase G3 deve trabalhar a experiência gráfica de HQ em sequência controlada:

1. biblioteca e catálogo visual;
2. entrada do estúdio e fluxo de criação;
3. editor, canvas, toolbar e inspetor;
4. leitor e acessibilidade;
5. monitoramento docente e Analytics pós-HQ.

Os domínios canônicos de HQ, Assessment Hub, Delivery, Review e Analytics
devem permanecer inalterados durante essa evolução visual.
