# Auditoria visual do EduCode — 2026-07-31

## Objetivo

Iniciar a evolução gráfica do EduCode sobre a arquitetura existente, sem criar
uma interface paralela, sem reescrever features funcionais e sem comprometer
acessibilidade, responsividade ou fluxos autenticados.

## Evidências analisadas

- tela de login em `1280 × 720` e `390 × 844`;
- DOM, dimensões, foco e console do navegador;
- shell autenticado e registro consolidado de rotas no código;
- CSS global e estilos por feature;
- build de produção da versão `0.16.11.6`.

O fluxo autenticado visual completo depende de uma credencial docente válida.
A credencial de bootstrap documentada não corresponde ao usuário instalado e
nenhuma senha foi redefinida durante esta auditoria.

## Inventário real

- 19 arquivos CSS;
- 5.868 linhas físicas de CSS;
- `global.css` com 2.869 linhas;
- estilos do editor de HQ com 1.841 linhas;
- 1.130 ocorrências de cores hexadecimais diretas;
- 43 ocorrências de `!important`;
- 33 ocorrências de estilos inline em componentes TSX;
- 174 nomes de seletores repetidos no CSS global;
- bundle principal com 901,51 kB, ou 226,58 kB comprimido.

Algumas folhas de features estão minificadas em uma única linha. Portanto, o
número físico de linhas subestima a complexidade real.

## Pontos fortes

1. A marca EduCode já possui uma direção reconhecível em azul, índigo e tons
   escuros.
2. A tela pública responde sem overflow horizontal em desktop e mobile.
3. O shell possui menu compacto, oculto, automático e modo foco.
4. O leitor e o editor já consideram redução de movimento e preferências de
   acessibilidade.
5. Features recentes usam CSS próprio e estados de loading, erro e vazio.

## Problemas prioritários

### Alta prioridade

1. Não existe um conjunto canônico de tokens globais para cor, tipografia,
   espaçamento, raio, sombra e foco.
2. Features como editor de HQ, biblioteca visual, layout studio e módulos
   adaptativos mantêm pequenos sistemas visuais independentes.
3. O CSS global funciona como um histórico acumulado e possui seletores
   repetidos cuja aparência depende da ordem da cascata.
4. Botões, cards, badges, tabelas e cabeçalhos usam diversas convenções de
   classe e proporção.
5. A navegação docente concentra criação, avaliação, analytics, IA, HQ,
   administração e operação em uma lista muito densa.

### Acessibilidade

No login mobile, a auditoria encontrou:

- botão de mostrar senha com 31 px de altura;
- checkbox e seu label com 13 px e 19 px;
- link de recuperação com 19 px de altura.

Esses alvos foram elevados para pelo menos 44 px nesta primeira mudança. Um
anel de foco global com contraste visível também foi introduzido.

### Performance e manutenção

1. O bundle principal excede o limite de 500 kB.
2. Há folhas extensas e parcialmente minificadas difíceis de revisar.
3. Cores diretas impedem temas consistentes e aumentam o custo de mudanças.
4. Glifos de texto são usados como ícones no menu e podem variar entre sistemas.

## Direção visual recomendada

Manter a identidade atual, com evolução gradual para uma linguagem de
“tecnologia educacional acolhedora”:

- azul como ação e confiança;
- índigo como criatividade e IA;
- verde-petróleo como progresso e intervenção pedagógica;
- superfícies claras e neutras para áreas densas;
- tipografia de alta legibilidade;
- hierarquia forte, menos ruído e menos elementos competindo pela atenção;
- ilustrações e grafismos ligados a aprendizagem, HQ e pensamento
  computacional, sem infantilizar áreas docentes.

## Roadmap gráfico

### Fase G0 — Fundação visual

- tokens `--ec-*`;
- foco, alvos de toque e redução de movimento;
- escalas de tipografia, espaçamento, raio e sombra;
- componentes básicos: botão, campo, card, badge, alerta e skeleton.

### Fase G1 — Autenticação e shell

- consolidar login, recuperação e redefinição de senha;
- reorganizar navegação por tarefas e perfis;
- substituir glifos por ícones consistentes e acessíveis;
- revisar cabeçalhos, breadcrumb e busca global.

### Fase G2 — Dashboards e dados

- padronizar métricas, gráficos, tabelas, filtros e estados vazios;
- reduzir densidade visual por nível de prioridade;
- unificar cores semânticas e legendas.

### Fase G3 — Experiência HQ

- alinhar biblioteca, editor, monitoramento e leitor ao sistema visual;
- preservar o modo foco do editor;
- criar padrões de toolbar, inspector, canvas e timeline;
- validar desktop, tablet, teclado e leitor de tela.

### Fase G4 — Qualidade visual

- regressão visual automatizada;
- auditoria WCAG por fluxo;
- code splitting por rota;
- documentação de componentes e critérios de uso.

## Primeira entrega aplicada

- branch: `feat/educode-visual-foundation`;
- tokens iniciais da marca aplicados ao login;
- anel de foco global consistente;
- alvos de toque do login ajustados para 44 px;
- nenhuma rota, API, regra de negócio ou tabela alterada.

## Próxima decisão

A próxima mudança deve consolidar autenticação e shell antes de redesenhar
dashboards isolados. Isso cria a base compartilhada que as demais features
podem adotar progressivamente.
