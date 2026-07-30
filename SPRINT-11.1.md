# Sprint 11.1 — Pesquisa Estatística Avançada

A Sprint 11.1 amplia o Laboratório Estatístico Educacional sem substituir os estudos, datasets, análises, gráficos ou relatórios da Sprint 11.

## Entregas principais

- nova página `/estatistica/avancado`;
- versões imutáveis de análises;
- checksum da configuração e assinatura dos resultados;
- análise de sensibilidade com casos completos, exclusão de outliers por IQR, winsorização de 5% e método alternativo;
- comparação de métodos paramétricos e não paramétricos;
- planejamento amostral para desenhos pareados, independentes, correlação e proporções;
- margem recomendada de 15% para perdas;
- exportação de scripts reproduzíveis em Python e R;
- comentários de revisão, resolução e estados de aprovação;
- versões de relatórios sem sobrescrever o histórico;
- exportação dos relatórios em HTML, PDF e DOCX;
- exportação dos gráficos em PNG, SVG e PDF;
- exportação dos datasets em CSV e XLSX com dicionário e metadados;
- correções de p por Holm, Bonferroni e Benjamini–Hochberg;
- Friedman, McNemar, Fisher exato e resumo de escalas Likert;
- interpretação com tamanho do efeito e alertas contra conclusões indevidas.

## Nova migration

```text
0018_statistical_research_lab
        ↓
0019_statistical_lab_advanced
```

## Novas tabelas

- `statistical_sensitivity_runs`;
- `statistical_method_comparisons`;
- `statistical_review_comments`;
- `statistical_report_revisions`;
- `statistical_sample_size_plans`.

A tabela `statistical_analyses` também recebeu:

- `parent_analysis_id`;
- `version_number`;
- `configuration_checksum`;
- `result_signature`;
- `review_status`.

## Novas rotas principais

```text
POST /api/v1/statistics/analyses/{id}/versions
POST /api/v1/statistics/analyses/{id}/sensitivity
POST /api/v1/statistics/analyses/{id}/method-comparisons
GET  /api/v1/statistics/analyses/{id}/scripts/python/download
GET  /api/v1/statistics/analyses/{id}/scripts/r/download
POST /api/v1/statistics/sample-size-plans
POST /api/v1/statistics/review-comments
POST /api/v1/statistics/reports/{id}/revisions
GET  /api/v1/statistics/reports/{id}/download/pdf
GET  /api/v1/statistics/reports/{id}/download/docx
GET  /api/v1/statistics/charts/{id}/export/png
GET  /api/v1/statistics/charts/{id}/export/svg
GET  /api/v1/statistics/charts/{id}/export/pdf
POST /api/v1/statistics/p-values/adjust
GET  /api/v1/statistics/datasets/{id}/xlsx
```

## Atualização preservando os dados

```powershell
docker compose down --remove-orphans
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose up -d --build
docker compose run --rm backend alembic current
```

Resultado esperado:

```text
0019_statistical_lab_advanced (head)
```

Não utilize `docker compose down -v`.
