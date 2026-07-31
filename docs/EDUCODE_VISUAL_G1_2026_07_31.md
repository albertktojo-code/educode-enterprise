# Fase gráfica G1 do EduCode — 2026-07-31

## Objetivo

Consolidar a autenticação e o shell responsivo do EduCode sem alterar rotas,
APIs, regras de negócio, modelos ou banco de dados. A interface deve comunicar
mudança de contexto, responder a clique e ponteiro e continuar utilizável com
teclado, toque e redução de movimento.

## Entrega

### Navegação

- os domínios existentes continuam no registro consolidado de rotas;
- o menu organiza os links nos grupos já existentes e mantém aberto somente o
  grupo da rota atual;
- o grupo ativo acompanha a navegação e preserva o destaque da página;
- no modo compacto, todos os destinos continuam disponíveis pelos ícones;
- em tablet e celular, o menu usa painel lateral, overlay e fechamento após a
  escolha de um destino;
- perfil, organização, papel e saída permanecem no rodapé do menu.

### Movimento e interação

- cada mudança de rota possui entrada curta com opacidade e deslocamento;
- links, botões, cartões e ações rápidas respondem a hover em ponteiros finos;
- o estado pressionado fornece feedback imediato de clique ou toque;
- grupos do menu possuem abertura visual e indicador de estado;
- o movimento ambiente da autenticação é decorativo e não interfere no
  conteúdo;
- `prefers-reduced-motion` e a preferência interna `reduce-motion` neutralizam
  animações e transições.

### Linguagem visual

- superfícies claras, sombras graduais e bordas suaves aumentam a hierarquia;
- o menu usa profundidade em azul, índigo e verde-petróleo, mantendo a marca;
- fundos radiais sutis reduzem a aparência plana sem competir com os dados;
- cartões e formulários usam raios, sombras, foco e durações canônicas
  `--ec-*`;
- a autenticação usa superfície translúcida, grade decorativa e contraste
  preservado.

### Responsividade e acessibilidade

- conteúdo sem overflow horizontal nas larguras validadas;
- alvo mínimo de 44 px para controles principais;
- foco visível preservado para links, botões, campos e seletores;
- menu móvel com rótulos, estado `aria-expanded`, `aria-controls` e overlay
  nomeado;
- interação não depende somente de cor;
- efeitos de hover são limitados a dispositivos com ponteiro fino.

## Evidências executadas

- desktop: `1280 × 720`, sem overflow horizontal;
- tablet: `820 × 1180`, menu fechado fora da tela e aberto com 330 px;
- celular: `390 × 844`, conteúdo com 16 px de margem e sem overflow;
- navegação real de `/projetos` para `/estudio-professor`;
- fechamento automático do menu após seleção no celular;
- grupo ativo atualizado entre `Planejamento` e `Área do professor`;
- animação `ec-route-enter` detectada no estágio de rota;
- console sem erros ou avisos da aplicação;
- `npm run lint` aprovado;
- `npm run build` aprovado.

O build mantém um aviso não bloqueante já conhecido: o bundle JavaScript
principal supera 500 kB e deve ser tratado por code splitting em uma fase de
performance.

## Principal local de qualidade visual

Foi criado, com autorização, o usuário local
`visual.teacher@educode.example.com`, papel `teacher`, na organização
`educode-enterprise`. A criação e a normalização do e-mail foram registradas
em `system_audit_events`. A senha não é armazenada neste documento.

## Arquivos da entrega

- `frontend/src/components/AppLayout.tsx`;
- `frontend/src/styles/global.css`;
- `docs/EDUCODE_VISUAL_AUDIT_2026_07_31.md`;
- `docs/EDUCODE_VISUAL_G1_2026_07_31.md`.

## Limites e próxima fase

Esta fase não substitui glifos por um sistema de ícones vetoriais e não
redesenha individualmente as dezenas de páginas de feature. A Fase G2 deve
padronizar dashboards, métricas, tabelas, filtros, estados vazios, skeletons e
gráficos. Depois disso, a Fase G3 pode concentrar a identidade gráfica da
biblioteca, editor, leitor e monitoramento de HQ.
