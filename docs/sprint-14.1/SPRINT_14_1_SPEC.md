# EduCode Enterprise 2.0
## Sprint 14.1 — Adaptação Pedagógica, Revisão Espaçada e Acessibilidade Automática

## 1. Posição no cronograma

A Sprint 14.1 pertence à **Etapa 6 — Evoluções depois da Sprint 14**. Ela pressupõe que a Sprint 14 já entregou domínio de aprendizagem, evidências, recomendações e trilhas personalizadas.

Agentes autônomos permanecem fora do escopo.

## 2. Objetivo

Ajustar o apoio apresentado durante a aprendizagem sem criar um fluxo paralelo de avaliações. As adaptações utilizam as tentativas, respostas, evidências, habilidades BNCC e pilares de Pensamento Computacional já registrados.

## 3. Entregas

### 3.1 Pistas graduais

- cinco níveis de ajuda;
- liberação manual ou por regra;
- limite de nível por atividade;
- registro por tentativa;
- configuração de eventual impacto na pontuação;
- proibição de revelar automaticamente a resposta final;
- análise do desempenho após o uso da pista.

### 3.2 Revisão espaçada

- agenda por estudante e habilidade;
- intervalos configuráveis;
- redução do intervalo após erro ou pista elevada;
- ampliação após desempenho consistente;
- eventos de início e conclusão;
- registro da versão da regra;
- prioridade e situação da revisão.

### 3.3 Feedback adaptado

- adaptação ao tipo de erro;
- adaptação ao nível de domínio;
- consideração do número da tentativa;
- consideração do nível de pista usado;
- próxima ação explícita;
- encaminhamento à revisão docente em casos ambíguos.

### 3.4 Dificuldade individual

- perfil por estudante e habilidade;
- score entre 0 e 1;
- classificação qualitativa;
- limite configurável de mudança por ciclo;
- revisão docente para alterações bruscas;
- justificativa do cálculo.

### 3.5 Dificuldade prevista e observada

A dificuldade observada combina:

- taxa de acerto;
- média de tentativas;
- média de pistas;
- abandono;
- tempo em relação ao esperado.

A análise classifica o recurso como coerente, mais fácil ou mais difícil que o previsto e só produz alerta com amostra suficiente.

### 3.6 Regras de avanço configuráveis

Condições disponíveis:

- domínio mínimo;
- confiança mínima;
- evidências mínimas;
- pré-requisitos;
- limite de pistas elevadas;
- revisão pendente;
- validação docente;
- desempenho recente.

Ações disponíveis:

- avançar;
- manter;
- revisar;
- reforçar;
- retornar ao pré-requisito;
- encaminhar ao professor;
- concluir trilha;
- suspender adaptação.

### 3.7 Versões acessíveis automáticas

Adaptações iniciais:

- linguagem simples;
- leitura fácil;
- instruções passo a passo;
- fonte ampliada;
- alto contraste;
- redução de estímulos;
- leitor de tela;
- descrição de imagens;
- audiodescrição;
- legendas;
- navegação por teclado;
- apoio visual.

A versão acessível:

- permanece vinculada ao original;
- não sobrescreve o original;
- preserva objetivo, resposta esperada e critérios;
- recebe versão própria;
- exige revisão antes da publicação quando houver risco de alteração pedagógica.

## 4. Segurança e governança

- isolamento por organização;
- autorização por papel;
- acesso docente limitado ao escopo institucional existente;
- auditoria estruturada;
- nenhuma alteração automática de notas;
- nenhuma decisão pedagógica irreversível;
- nenhuma exposição de diagnóstico;
- mensagens não depreciativas;
- versionamento das regras.

## 5. Modelo de dados

A migration `0029_adaptive_learning_evolution` cria:

- `graduated_hints`;
- `hint_usages`;
- `spaced_review_schedules`;
- `spaced_review_events`;
- `adaptive_feedbacks`;
- `student_difficulty_profiles`;
- `resource_difficulty_metrics`;
- `progression_rules`;
- `progression_decisions`;
- `accessible_resource_versions`.

## 6. Interface docente

Rotas entregues:

- `/teacher/adaptive-evolution`;
- `/teacher/adaptive-evolution/hints`;
- `/teacher/adaptive-evolution/reviews`;
- `/teacher/adaptive-evolution/feedback`;
- `/teacher/adaptive-evolution/difficulty`;
- `/teacher/adaptive-evolution/progression`;
- `/teacher/adaptive-evolution/accessibility`.

## 7. Eventos de auditoria

- `hint.created`, `hint.selected`, `hint.used`;
- `spaced_review.rescheduled`, `spaced_review.completed`;
- `adaptive_feedback.generated`;
- `student_difficulty.calculated`;
- `resource_difficulty.observed`;
- `progression_rule.created`, `progression_rule.published`;
- `progression_decision.created`, `progression_decision.approved`;
- `accessible_version.generated`, `accessible_version.reviewed`, `accessible_version.published`.

## 8. Definition of Done

- migration com upgrade e downgrade;
- módulo backend compilando;
- testes automatizados aprovados;
- rotas integráveis ao `/api/v1`;
- telas React com sintaxe validada;
- pistas cadastráveis e consultáveis;
- agenda de revisão persistente;
- feedback adaptado registrável;
- dificuldades calculáveis e persistentes;
- regras de avanço cadastráveis e publicáveis;
- decisões auditáveis;
- versões acessíveis geráveis, revisáveis e publicáveis;
- ausência de dependência obrigatória de IA externa;
- ausência de agentes autônomos.

## 9. Fora do escopo

Itens reservados à Sprint 14.2:

- recomendação baseada no histórico das intervenções;
- eficácia descritiva dos materiais;
- painel institucional de trilhas;
- modelos adaptativos avançados versionados;
- simulação de recomendações;
- testes controlados entre estratégias.
