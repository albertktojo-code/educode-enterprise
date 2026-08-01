# Sprint 07 — HQs estruturadas, continuidade e edição granular

## Objetivo

Transformar um contexto RAG aprovado em uma HQ estruturada por páginas, quadros e balões. A geração continua mock e determinística, mas a arquitetura já separa narrativa, conteúdo pedagógico, layout e elementos editáveis para futura geração real de imagens.

## Fluxo

1. Selecione um planejamento pedagógico.
2. Selecione um contexto RAG aprovado.
3. Escolha quantidade de páginas e quadros por página.
4. Defina gênero, emoção, surpresa e número de reviravoltas.
5. Gere a HQ estruturada.
6. Edite página, quadro ou balão específico.
7. Regere somente o elemento necessário.
8. Verifique a continuidade.
9. Aprove e exporte JSON ou pacote para canvas.

## Continuidade com liberdade criativa

O gerador mock usa arcos com humor, pistas, hipótese incorreta, frustração, descoberta, reviravolta, aplicação e encerramento. A reviravolta só é validada quando existe uma pista anterior. Os fatos do contexto RAG são mantidos como conteúdo obrigatório, sem impor uma narrativa única.

## Composição de páginas

- 1 a 8 quadros por página;
- quantidades diferentes em cada página;
- A4, quadrado, celular, Instagram, 16:9 e personalizado;
- orientação vertical ou horizontal;
- ordem de leitura explícita;
- layouts prontos e estrutura para layout livre.

Modelos iniciais:

- página inteira;
- dois horizontais;
- dois verticais;
- destaque superior;
- destaque inferior;
- grade 2 × 2;
- dramático;
- cinco dinâmicos;
- grade de seis.

## Formatos de quadro

- retangular;
- quadrado;
- horizontal;
- vertical;
- circular;
- oval;
- panorâmico;
- personalizado.

Cada quadro armazena posição, largura, altura, rotação, camada, borda, recorte, função narrativa, emoção, objetivo pedagógico, estado inicial, estado final e ligação com os quadros vizinhos.

## Edição granular

### Modo professor

- objetivo narrativo;
- objetivo pedagógico;
- resumo do quadro anterior;
- descrição da cena;
- gancho seguinte;
- emoção e função no enredo;
- edição individual de cada balão;
- personagem, tipo, texto, emoção e função pedagógica do balão.

### Modo designer

- quantidade de quadros;
- modelo da página;
- formato e orientação;
- forma e tamanho do quadro;
- posição, dimensões e rotação;
- reordenação dos quadros antes/depois;
- estrutura pronta para drag-and-drop na Sprint 08.

## Regeneração parcial

Escopos disponíveis:

- HQ inteira;
- página;
- quadro;
- balões;
- diálogos;
- descrição da cena;
- quadro selecionado e todos os seguintes.

É possível preservar os diálogos ou a descrição visual. Cada regeneração cria uma nova versão.

## Versionamento

Toda edição relevante cria um snapshot JSON com:

- páginas;
- quadros;
- balões;
- posições;
- objetivos;
- estado narrativo;
- regras de composição.

Versões anteriores podem ser restauradas no editor sem apagar o histórico.

## Exportações

- JSON estruturado `educode.comic.v1`;
- pacote `educode.canvas.v1` com sistema de coordenadas percentuais e camadas editáveis.

A exportação para PDF, DOCX, SVG, PPTX, PNG e ZIP visual será consolidada nas próximas sprints após a implementação do renderizador/canvas.

## API

Prefixo: `/api/v1/comics`

Principais operações:

- `GET /comics/layout-templates`
- `GET /comics`
- `POST /comics`
- `GET /comics/{comic_id}`
- `PATCH /comics/{comic_id}`
- `PATCH /comics/{comic_id}/pages/{page_id}`
- `POST /comics/{comic_id}/pages/{page_id}/reorder`
- `PATCH /comics/{comic_id}/panels/{panel_id}`
- `POST /comics/{comic_id}/panels/{panel_id}/duplicate`
- `DELETE /comics/{comic_id}/panels/{panel_id}`
- `POST /comics/{comic_id}/panels/{panel_id}/balloons`
- `PATCH /comics/{comic_id}/balloons/{balloon_id}`
- `DELETE /comics/{comic_id}/balloons/{balloon_id}`
- `POST /comics/{comic_id}/regenerate`
- `GET /comics/{comic_id}/continuity`
- `POST /comics/{comic_id}/approve`
- `GET /comics/{comic_id}/versions`
- `POST /comics/{comic_id}/versions/{version_id}/restore`
- `GET /comics/{comic_id}/export/json`
- `GET /comics/{comic_id}/export/canvas`

## Migration

```text
0009_rag_context_orchestration
        ↓
0010_comic_generation_editor
```

Novas tabelas:

- `generated_comics`;
- `comic_pages`;
- `comic_panels`;
- `comic_balloons`;
- `comic_versions`;
- `comic_generation_runs`.

## Interface

- `/hqs` — geração e biblioteca;
- `/hqs/{comic_id}` — editor granular.

## Validação

- Ruff;
- mypy estrito;
- 38 testes automatizados;
- TypeScript/Vite;
- ESLint;
- OpenAPI com 89 caminhos;
- migration compilada em SQL PostgreSQL.
