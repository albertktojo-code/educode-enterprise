# Sprint 13.3 — Infraestrutura Distribuída, GitOps e Disaster Recovery

## Objetivo

Preparar o EduCode para execução distribuída e continuidade operacional, mantendo compatibilidade integral com Docker Compose.

## Entregas

- inventário de clusters e snapshots de saúde;
- object storage local ou S3 compatível;
- MinIO opcional no Compose;
- replicação de storage;
- planos, drills e registros de failover;
- aplicações GitOps e manifesto Argo CD exportável;
- políticas de autoscaling e recomendações de capacidade;
- Helm chart com HPA, PDB, NetworkPolicy e Ingress;
- overlays de homologação e produção;
- workflow CI para manifests;
- replicação opcional dos backups no object storage.

## Segurança

- segredos não são persistidos nas tabelas de infraestrutura;
- failover/failback exigem operador global;
- execução automática de failover vem desativada;
- Kubernetes usa `runAsNonRoot`, seccomp e capabilities removidas;
- storage keys bloqueiam traversal;
- isolamento por organização em todas as rotas.

## Migration

```text
0026_release_recovery
        ↓
0027_infra_continuity
```

## Interface

```text
/admin/infraestrutura
```

## Critério de conclusão

A sprint é considerada concluída quando o Docker local continua válido, o profile MinIO é renderizado, o chart Helm é validável, o administrador consegue registrar topologia/DR e nenhum failover destrutivo ocorre sem operador global e aprovação institucional.
