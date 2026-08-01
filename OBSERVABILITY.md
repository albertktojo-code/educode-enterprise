# Observabilidade do EduCode

## Métricas internas

O backend expõe métricas Prometheus em:

```text
/api/v1/observability/metrics
```

Métricas iniciais:

- total de requisições por método, rota normalizada e status;
- requisições ativas;
- exceções não tratadas;
- latência média, p95 e p99;
- taxa percentual de erros HTTP;
- informação de versão e ambiente.

Defina `OBSERVABILITY_METRICS_TOKEN` para proteger o endpoint em ambientes expostos. Quando o token estiver definido, o coletor deverá enviar o cabeçalho `X-Metrics-Token`.

## OpenTelemetry

Ative somente quando houver um coletor OTLP disponível:

```env
OTEL_ENABLED=true
OTEL_SERVICE_NAME=educode-backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
TRACE_SAMPLE_RATIO=0.10
```

Falhas no exportador de telemetria não impedem a inicialização da plataforma.

## SLOs

Os SLOs relacionam uma métrica a uma meta, comparador, janela e quantidade mínima de amostras. Exemplos incluídos pelo seed:

- taxa de erros HTTP menor ou igual a 0,5%;
- latência p95 menor ou igual a 500 ms;
- taxa de falha das tarefas menor ou igual a 2%;
- pelo menos quatro workers ativos.

O orçamento de erro mostrado no painel é uma indicação operacional e não substitui análise de capacidade ou planejamento institucional.

## Quotas

Quotas iniciais:

- usuários;
- projetos;
- documentos;
- avaliações;
- tarefas simultâneas;
- custo mensal estimado de IA.

O modo `block` impede novas tarefas quando o limite aplicável é atingido. Conteúdos existentes permanecem disponíveis.

## Reconciliação

A reconciliação procura vínculos incompletos usando as verificações de integridade da Sprint 13. A opção de reparo automático limita-se a estados operacionais seguros, como tarefas abandonadas. Notas, respostas, evidências educacionais e resultados estatísticos nunca são alterados automaticamente.
