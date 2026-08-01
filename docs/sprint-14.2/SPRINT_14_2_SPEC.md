# Sprint 14.2 — Avaliação de Intervenções, Modelos Adaptativos e Experimentação Controlada

## Objetivo geral

Transformar os registros produzidos pela Sprint 14 e pela Sprint 14.1 em evidências institucionais para avaliar intervenções, analisar materiais, versionar estratégias adaptativas, simular decisões e comparar abordagens de forma controlada.

## 1. Recomendação baseada no histórico das intervenções

O sistema registra o domínio antes e depois da intervenção, conclusão, uso de pistas, tentativas, material empregado e data. A recomendação considera ganhos ponderados pela recência e pela qualidade da evidência.

Resultados possíveis:

- repetir intervenção com histórico positivo;
- tentar alternativa;
- avançar;
- revisar pré-requisito;
- solicitar revisão docente;
- coletar mais evidências.

Nenhuma recomendação é aplicada automaticamente.

## 2. Análise descritiva da eficácia dos materiais

Indicadores:

- tamanho da amostra;
- taxa de conclusão;
- taxa de acerto;
- ganho médio e mediano;
- média de tentativas;
- média de pistas;
- duração média;
- confiança baseada no tamanho da amostra;
- classificação descritiva.

O painel deve declarar que associação não representa causalidade.

## 3. Painel institucional de trilhas

Consolida:

- trilhas existentes;
- estudantes atribuídos, ativos e concluintes;
- taxa de conclusão;
- progresso médio;
- domínio médio;
- revisões atrasadas;
- intervenções realizadas;
- trilhas que exigem atenção.

## 4. Modelos adaptativos versionados

Cada modelo registra:

- nome e versão semântica;
- escopo;
- algoritmo;
- configuração;
- schemas de entrada e saída;
- hash da configuração;
- status;
- autoria e publicação.

Modelos publicados são imutáveis. Alterações exigem nova versão.

## 5. Simulação de recomendações

A simulação processa perfis anonimizáveis e devolve a distribuição das decisões sem modificar:

- domínio;
- notas;
- trilhas;
- agenda de revisão;
- intervenções;
- publicações.

## 6. Testes controlados

Cada experimento possui hipótese, métrica primária, direção da métrica, estratégias, amostra mínima e status. A atribuição determinística por hash mantém o participante na mesma estratégia.

A comparação inicial apresenta média, mediana, mínimo, máximo, conclusão e suficiência amostral. Não realiza alegações causais nem significância estatística automática.

## Segurança e governança

- isolamento por organização;
- acesso por RBAC;
- revisão humana;
- auditoria;
- versões imutáveis;
- simulação sem efeitos;
- experimentos autorizados;
- transparência metodológica;
- ausência de rótulos negativos ao estudante.

## Critérios de aceitação principais

1. Recomendações usam histórico e apresentam justificativa.
2. Materiais possuem indicadores descritivos reproduzíveis.
3. Painel institucional consolida trilhas sem expor dados indevidos.
4. Modelos publicados não podem ser sobrescritos.
5. Simulações não alteram dados pedagógicos.
6. Participantes mantêm atribuição estável no experimento.
7. Comparações exibem alertas de amostra e causalidade.
8. Toda operação respeita organização e papel.
9. Migration e rollback funcionam.
10. Instalação ocorre por um único comando.
