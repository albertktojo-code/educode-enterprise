# Sprint 12 — EduCode AI Fabric

## Objetivo

Integrar IA ponta a ponta aos módulos do EduCode sem transformá-la em uma área isolada, mantendo segurança, governança, revisão humana, rastreabilidade, isolamento por organização e controle de custos.

## Arquitetura

```text
AI Gateway
├── Provider Registry
├── Model Router
├── Prompt Registry
├── Module Policy Engine
├── Context and RAG Builder
├── Privacy and Safety Layer
├── Structured Output Validator
├── Usage and Cost Recorder
├── Human Review Workflow
├── Module Link Registry
└── AI Activity Audit
```

## Adaptadores funcionais

| Módulo | Ações principais |
|---|---|
| Planejamento | plano de aula, sequência, alinhamento |
| RAG | síntese, fatos, redação com fontes |
| HQs | roteiro, quadro, imagem, regeneração granular |
| Biblioteca | descrição, personagem, tags |
| Avaliações | questões, rubricas, feedback |
| Correção | sugestão discursiva e feedback |
| Analytics | explicação e intervenção |
| Intervenções | plano e adaptação de material |
| Estatística | interpretação e relatório, sem recalcular dados |
| Relatórios | rascunhos e descrição de gráficos |
| Acessibilidade | texto alternativo, simplificação e audiodescrição |

## Fluxo ponta a ponta

1. O professor seleciona o módulo e a ação contextual.
2. A política da organização valida permissão, limite e modelo.
3. Dados pessoais são removidos quando não autorizados.
4. Entradas e fontes passam por verificação de prompt injection.
5. O contexto RAG é congelado com versão, fatos e citações.
6. Um template institucional ou interno monta a solicitação.
7. O roteador escolhe mock ou provedor real autorizado.
8. A saída passa por validação específica do conteúdo.
9. Uso, custo, modelo, latência e resultado são registrados.
10. O usuário revisa e aprova ou rejeita.
11. O resultado aprovado é aplicado ao módulo e vinculado à entidade.
12. Todo o ciclo fica acessível pelo identificador `AI-FLOW`.

## Aplicação no Núcleo de Avaliação

Resultados com finalidade `assessment_questions` podem ser aprovados e aplicados a uma avaliação. O EduCode:

- cria questões como rascunho no Banco de Questões;
- preserva o checksum da geração;
- registra origem, fluxo, request e resultado;
- associa BNCC e pilares de PC;
- adiciona os itens à versão editável da avaliação;
- mantém revisão do professor obrigatória antes da publicação.

## Segurança

- segredos apenas em variáveis de ambiente;
- nenhum segredo retornado pela API;
- isolamento por `organization_id`;
- conteúdo externo tratado como não confiável;
- detecção de instruções maliciosas;
- anonimização de e-mail, telefone, documento e campos identificadores;
- proibição de publicação automática por padrão;
- políticas independentes por módulo;
- resultados estatísticos calculados somente pelo motor determinístico.

## Estrutura de dados

- `ai_providers`
- `ai_models`
- `ai_prompt_templates`
- `ai_module_policies`
- `ai_generation_requests`
- `ai_generation_results`
- `ai_usage_records`
- `ai_generation_reviews`
- `ai_module_links`
- `ai_activity_events`

## Migration

```text
0020_integrated_assessment_core
        ↓
0021_ai_orchestration_runtime
```

A migration utiliza colunas textuais para estados e não cria novos enums PostgreSQL, evitando duplicações de tipos.

## Limites desta entrega

- o adaptador real é HTTP genérico, configurável para gateways institucionais;
- a execução em background ocorre no processo FastAPI;
- vídeo, voz, anime e workers distribuídos permanecem para uma evolução futura;
- a aplicação automática específica está completa para avaliações; os demais módulos recebem vínculo auditável e permanecem editáveis antes da incorporação final.
