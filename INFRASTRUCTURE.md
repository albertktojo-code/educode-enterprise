# Infraestrutura distribuída do EduCode

A Sprint 13.3 adiciona uma camada opcional de infraestrutura distribuída sem remover o ambiente Docker Compose usado no desenvolvimento.

## Modos suportados

- **Docker local:** PostgreSQL, Redis, volumes e object storage local.
- **Docker com MinIO:** `docker compose --profile cloud up -d`.
- **Kubernetes:** Helm chart em `infra/kubernetes/helm/educode`.
- **GitOps:** overlays e aplicações Argo CD em `infra/gitops` e `infra/argocd`.

## Object storage

`OBJECT_STORAGE_PROVIDER=local` mantém o comportamento local. Para MinIO ou AWS S3:

```env
OBJECT_STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET_NAME=educode
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=educode
S3_SECRET_ACCESS_KEY=troque-a-senha
S3_PREFIX=educode
S3_USE_SSL=false
```

As credenciais são lidas apenas pelo backend. A API administrativa armazena somente referências de segredos e metadados.

## Kubernetes

Validação sem aplicar recursos:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/k8s-preflight.ps1
```

Renderização manual:

```bash
helm lint infra/kubernetes/helm/educode
helm template educode-homolog infra/kubernetes/helm/educode \
  -f infra/kubernetes/helm/educode/values-homologation.yaml
```

O chart inclui:

- deployments de backend, frontend e workers;
- probes de vida e prontidão;
- HPA;
- PodDisruptionBudget;
- NetworkPolicy;
- security contexts sem root;
- Ingress TLS;
- CronJob de backup;
- ConfigMap e referência a Secret existente.

PostgreSQL e Redis são tratados como serviços externos em produção. A instalação não cria bancos de produção dentro do chart.

## GitOps

O `ApplicationSet` separa homologação e produção. Antes de aplicar, substitua a URL `ORGANIZATION/educode-infra.git` e revise os destinos.

A promoção recomendada é:

1. atualizar imagens por digest;
2. abrir pull request no repositório de infraestrutura;
3. validar chart, SBOM e vulnerabilidades;
4. sincronizar homologação;
5. executar smoke tests;
6. aprovar produção;
7. sincronizar produção.

## Disaster recovery

A área `/admin/infraestrutura` registra clusters, replicação e planos. Drills podem ser planejados por administradores. Failover e failback exigem operador global e nunca são executados automaticamente nesta sprint.

Regras:

- cluster de recuperação saudável;
- replicação configurada;
- atraso menor que o RPO;
- runbook preenchido;
- drill periódico;
- aprovação humana antes do failover.

## Limitações honestas

- O EduCode não cria clusters Kubernetes automaticamente.
- A API não recebe kubeconfig nem segredos de nuvem.
- Failover real permanece sob runbook institucional.
- Replicação de banco deve ser fornecida pelo serviço PostgreSQL gerenciado ou pela infraestrutura da instituição.
- O chart prepara alta disponibilidade da aplicação, mas não substitui arquitetura HA do banco, Redis ou storage.
