# Sprint 07.1 — Revisão controlada e preparação visual

## Objetivo

Aprimorar o editor granular da Sprint 07 para que professores, revisores e designers possam corrigir somente o necessário, comparar propostas antes de substituir conteúdo, preservar elementos já aprovados e preparar cada quadro para a futura geração visual e para o canvas da Sprint 08.

## Recursos principais

### Bloqueios granulares

Cada quadro pode bloquear individualmente:

- quadro inteiro;
- cena;
- diálogos;
- balões;
- layout;
- objetivo pedagógico;
- prompt visual.

Balões também podem ser bloqueados separadamente. A regeneração respeita esses bloqueios.

### Comparação de alternativas

O professor pode gerar três propostas sem alterar a versão atual:

- mais engraçada;
- mais emocionante;
- mais misteriosa.

Cada alternativa mantém os fatos pedagógicos e pode ser aceita como nova versão. As demais ficam marcadas como superadas.

### Prompt visual estruturado

Cada quadro armazena separadamente:

- enquadramento;
- personagens;
- ação;
- expressões;
- cenário;
- iluminação;
- elementos obrigatórios;
- elementos proibidos;
- indicação de imagem sem balões.

A imagem permanece separada da camada de textos e balões.

### Assets congelados

Personagens, cenários e estilos usados no projeto são copiados para a HQ com:

- `creative_item_id`;
- `creative_version_id`;
- nome;
- prompt canônico;
- prompt negativo;
- perfil;
- papel narrativo.

Alterações posteriores na Biblioteca Criativa não modificam silenciosamente uma HQ existente.

### Mapa narrativo

O editor apresenta, na ordem de leitura:

- página e quadro;
- função no enredo;
- ritmo;
- emoção;
- objetivo narrativo;
- perguntas abertas;
- pistas;
- número de palavras;
- alerta de excesso de texto.

Também sinaliza ritmo uniforme e pistas ainda não resolvidas.

### Revisão por especialidade

Aprovações independentes:

- narrativa;
- pedagógica;
- visual;
- acessibilidade.

Comentários podem ser vinculados à HQ, página, quadro ou balão e possuem estados aberto, em análise, resolvido ou descartado.

A aprovação final exige:

- ausência de erros bloqueantes de continuidade;
- quatro especialidades aprovadas;
- nenhum comentário aberto.

### Acessibilidade

Cada quadro possui:

- texto alternativo;
- audiodescrição;
- ordem de leitura;
- balões estruturados;
- imagem sem texto incorporado.

### Autosave, desfazer e refazer

- autosave a cada 30 segundos;
- revisão de cliente para evitar sobrescrita de rascunho mais recente;
- histórico de operações;
- desfazer a última edição;
- refazer a última edição desfeita;
- versões completas continuam disponíveis para restauração.

### Validação visual e textual

O validador verifica:

- quadros fora dos limites da página;
- sobreposição relevante de quadros;
- balões fora dos limites;
- excesso de palavras por quadro;
- risco de texto incorporado na imagem;
- sequência de páginas, quadros e balões;
- salto de conhecimento;
- plot twist sem pista anterior.

## Migration

```text
0010_comic_generation_editor
        ↓
0011_comic_review_control
```

Novas tabelas:

- `comic_review_comments`;
- `comic_review_approvals`;
- `comic_regeneration_proposals`;
- `comic_edit_operations`.

Campos adicionais foram incluídos em:

- `generated_comics`;
- `comic_panels`;
- `comic_balloons`.

## Novas rotas

- `POST /comics/{comic_id}/panels/{panel_id}/locks`
- `POST /comics/{comic_id}/regeneration-proposals`
- `POST /comics/{comic_id}/regeneration-proposals/{proposal_id}/accept`
- `GET /comics/{comic_id}/narrative-map`
- `GET|POST /comics/{comic_id}/comments`
- `PATCH /comics/{comic_id}/comments/{comment_id}`
- `POST /comics/{comic_id}/review-approvals`
- `POST /comics/{comic_id}/autosave`
- `POST /comics/{comic_id}/undo`
- `POST /comics/{comic_id}/redo`

## Limites desta sprint

A Sprint 07.1 ainda não implementa o canvas visual completo. Arrastar, redimensionar e reposicionar elementos diretamente pelo mouse serão entregues na Sprint 08. A geração de imagens permanece mock, mas o contrato visual já está estruturado.
