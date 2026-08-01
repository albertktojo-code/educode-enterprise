import { useEffect, useMemo, useState } from 'react'

import { api } from '../lib/api'

type Overview = {
  clusters: number
  healthy_clusters: number
  storage_targets: number
  healthy_storage_targets: number
  replication_links: number
  dr_plans: number
  gitops_applications: number
  autoscaling_policies: number
  kubernetes_enabled: boolean
  gitops_enabled: boolean
  object_storage_provider: string
}

type Cluster = {
  id: string
  name: string
  environment: string
  provider: string
  region: string
  namespace: string
  status: string
  is_primary: boolean
  kubernetes_version: string
}

type StorageTarget = {
  id: string
  name: string
  provider: string
  bucket_name: string
  endpoint_url: string
  status: string
  is_primary: boolean
  versioning_enabled: boolean
  encryption_mode: string
}

type ReplicationLink = {
  id: string
  source_target_id: string
  destination_target_id: string
  mode: string
  status: string
  lag_seconds: number
}

type DRPlan = {
  id: string
  name: string
  environment: string
  status: string
  primary_cluster_id: string
  recovery_cluster_id: string
  replication_link_id: string | null
  rpo_minutes: number
  rto_minutes: number
}

type GitOpsApp = {
  id: string
  name: string
  environment: string
  repository_url: string
  target_revision: string
  namespace: string
  sync_policy: string
  sync_status: string
  health_status: string
}

type AutoscalingPolicy = {
  id: string
  environment: string
  component: string
  enabled: boolean
  min_replicas: number
  max_replicas: number
  target_cpu_percent: number
  target_memory_percent: number
  queue_depth_target: number
}

type Readiness = {
  plan_id: string
  ready: boolean
  score: number
  blockers: string[]
  warnings: string[]
  primary_status: string
  recovery_status: string
  replication_status: string
}

export function AdminInfrastructurePage() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [clusters, setClusters] = useState<Cluster[]>([])
  const [storageTargets, setStorageTargets] = useState<StorageTarget[]>([])
  const [replicationLinks, setReplicationLinks] = useState<ReplicationLink[]>([])
  const [plans, setPlans] = useState<DRPlan[]>([])
  const [gitOpsApps, setGitOpsApps] = useState<GitOpsApp[]>([])
  const [policies, setPolicies] = useState<AutoscalingPolicy[]>([])
  const [readiness, setReadiness] = useState<Record<string, Readiness>>({})
  const [message, setMessage] = useState('')
  const [clusterName, setClusterName] = useState('educode-homolog')
  const [storageName, setStorageName] = useState('minio-homolog')
  const [bucketName, setBucketName] = useState('educode')
  const [repositoryUrl, setRepositoryUrl] = useState('https://github.com/organizacao/educode-infra.git')

  const primaryCluster = useMemo(
    () => clusters.find((item) => item.is_primary) ?? clusters[0] ?? null,
    [clusters],
  )

  async function load() {
    const [summary, clusterData, storageData, replicationData, planData, appData, policyData] = await Promise.all([
      api.get<Overview>('/infrastructure/overview'),
      api.get<Cluster[]>('/infrastructure/clusters'),
      api.get<StorageTarget[]>('/infrastructure/storage-targets'),
      api.get<ReplicationLink[]>('/infrastructure/replication-links'),
      api.get<DRPlan[]>('/infrastructure/dr-plans'),
      api.get<GitOpsApp[]>('/infrastructure/gitops-applications'),
      api.get<AutoscalingPolicy[]>('/infrastructure/autoscaling-policies'),
    ])
    setOverview(summary)
    setClusters(clusterData)
    setStorageTargets(storageData)
    setReplicationLinks(replicationData)
    setPlans(planData)
    setGitOpsApps(appData)
    setPolicies(policyData)
  }

  useEffect(() => {
    void load()
  }, [])

  async function createCluster() {
    setMessage('Registrando cluster...')
    await api.post('/infrastructure/clusters', {
      name: clusterName,
      environment: 'homologation',
      provider: 'kubernetes',
      region: 'br-southeast',
      api_endpoint: '',
      namespace: 'educode-homolog',
      is_primary: clusters.length === 0,
      kubernetes_version: '1.31+',
      capabilities: { hpa: true, pdb: true, network_policy: true },
      labels_json: { managed_by: 'gitops' },
    })
    setMessage('Cluster registrado. A saúde deve ser atualizada pelo agente de infraestrutura.')
    await load()
  }

  async function createStorage() {
    await api.post('/infrastructure/storage-targets', {
      name: storageName,
      provider: 's3',
      bucket_name: bucketName,
      endpoint_url: 'http://minio:9000',
      region: 'us-east-1',
      prefix: 'educode',
      secret_reference: 'platform-default',
      is_primary: storageTargets.length === 0,
      versioning_enabled: true,
      encryption_mode: 'provider_managed',
      object_lock_enabled: false,
      configuration_json: { compatible_with: 'MinIO/AWS S3' },
    })
    setMessage('Destino S3 registrado. Use o botão Testar para validar credenciais e bucket.')
    await load()
  }

  async function testStorage(target: StorageTarget) {
    const result = await api.post<{ status: string; warnings: string[] }>(`/infrastructure/storage-targets/${target.id}/test`)
    setMessage(`Teste ${target.name}: ${result.status}${result.warnings.length ? ` — ${result.warnings.join('; ')}` : ''}`)
    await load()
  }

  async function createReplication() {
    if (storageTargets.length < 2) {
      setMessage('Cadastre pelo menos dois destinos de armazenamento para criar replicação.')
      return
    }
    await api.post('/infrastructure/replication-links', {
      source_target_id: storageTargets[0].id,
      destination_target_id: storageTargets[1].id,
      mode: 'asynchronous',
      schedule: '*/15 * * * *',
      configuration_json: { verify_checksums: true },
    })
    setMessage('Replicação configurada com verificação de checksum.')
    await load()
  }

  async function createPlan() {
    if (clusters.length < 2) {
      setMessage('Cadastre dois clusters para criar o plano de disaster recovery.')
      return
    }
    await api.post('/infrastructure/dr-plans', {
      name: 'Continuidade EduCode',
      environment: 'production',
      primary_cluster_id: clusters[0].id,
      recovery_cluster_id: clusters[1].id,
      replication_link_id: replicationLinks[0]?.id ?? null,
      rpo_minutes: 60,
      rto_minutes: 240,
      approval_required: true,
      runbook_json: {
        steps: ['confirmar incidente', 'drenar workers', 'validar replicação', 'promover cluster de recuperação', 'executar smoke tests'],
      },
    })
    setMessage('Plano de continuidade criado. Execute primeiro um drill controlado.')
    await load()
  }

  async function checkReadiness(plan: DRPlan) {
    const result = await api.get<Readiness>(`/infrastructure/dr-plans/${plan.id}/readiness`)
    setReadiness((current) => ({ ...current, [plan.id]: result }))
  }

  async function createDrill(plan: DRPlan) {
    await api.post(`/infrastructure/dr-plans/${plan.id}/runs`, {
      run_type: 'drill',
      reason: 'Exercício controlado da Sprint 13.3',
    })
    setMessage('Drill registrado como planejado. A execução automática destrutiva permanece desativada.')
  }

  async function createGitOps() {
    if (!primaryCluster) {
      setMessage('Cadastre um cluster antes da aplicação GitOps.')
      return
    }
    await api.post('/infrastructure/gitops-applications', {
      cluster_id: primaryCluster.id,
      name: 'educode-homolog',
      environment: 'homologation',
      repository_url: repositoryUrl,
      manifest_path: 'infra/gitops/overlays/homologation',
      target_revision: 'main',
      namespace: 'educode-homolog',
      sync_policy: 'automated_prune',
      configuration_json: { self_heal: true },
    })
    setMessage('Aplicação GitOps registrada.')
    await load()
  }

  async function saveAutoscaling() {
    await api.put('/infrastructure/autoscaling-policies', {
      environment: 'homologation',
      component: 'backend',
      enabled: true,
      min_replicas: 2,
      max_replicas: 10,
      target_cpu_percent: 70,
      target_memory_percent: 75,
      queue_depth_target: 20,
      scale_down_stabilization_seconds: 300,
      configuration_json: { strategy: 'horizontal' },
    })
    setMessage('Política de autoscaling salva.')
    await load()
  }

  return <div className="page-stack">
    <header className="page-header">
      <div>
        <span className="eyebrow">Sprint 13.3</span>
        <h1>Infraestrutura distribuída</h1>
        <p>Kubernetes, GitOps, armazenamento S3, replicação, autoscaling e disaster recovery com aprovação humana.</p>
      </div>
      <button type="button" onClick={() => void load()}>Atualizar</button>
    </header>

    {message ? <div className="notice">{message}</div> : null}

    {overview ? <section className="stats stats-four">
      <article><strong>{overview.healthy_clusters}/{overview.clusters}</strong><span>Clusters saudáveis</span></article>
      <article><strong>{overview.healthy_storage_targets}/{overview.storage_targets}</strong><span>Storages saudáveis</span></article>
      <article><strong>{overview.dr_plans}</strong><span>Planos de DR</span></article>
      <article><strong>{overview.gitops_applications}</strong><span>Aplicações GitOps</span></article>
    </section> : null}

    <section className="panel-grid two">
      <section className="panel">
        <h2>Clusters</h2>
        <div className="inline-form">
          <input value={clusterName} onChange={(event) => setClusterName(event.target.value)} />
          <button type="button" onClick={() => void createCluster()}>Cadastrar cluster</button>
        </div>
        <div className="card-list">{clusters.map((cluster) => <article className="compact-card" key={cluster.id}>
          <strong>{cluster.name} · {cluster.status}</strong>
          <span>{cluster.environment} · {cluster.provider} · {cluster.region}</span>
          <small>{cluster.namespace}{cluster.is_primary ? ' · primário' : ''}</small>
        </article>)}</div>
      </section>

      <section className="panel">
        <h2>Object storage</h2>
        <div className="inline-form">
          <input value={storageName} onChange={(event) => setStorageName(event.target.value)} placeholder="Nome" />
          <input value={bucketName} onChange={(event) => setBucketName(event.target.value)} placeholder="Bucket" />
          <button type="button" onClick={() => void createStorage()}>Cadastrar S3/MinIO</button>
        </div>
        <div className="card-list">{storageTargets.map((target) => <article className="compact-card" key={target.id}>
          <strong>{target.name} · {target.status}</strong>
          <span>{target.provider} · {target.bucket_name || 'storage local'}</span>
          <small>Versões: {target.versioning_enabled ? 'sim' : 'não'} · {target.encryption_mode}</small>
          <button className="secondary-button" type="button" onClick={() => void testStorage(target)}>Testar</button>
        </article>)}</div>
        <button className="secondary-button" type="button" onClick={() => void createReplication()}>Criar replicação entre os dois primeiros</button>
      </section>
    </section>

    <section className="panel-grid two">
      <section className="panel">
        <h2>Disaster recovery</h2>
        <button type="button" onClick={() => void createPlan()}>Criar plano</button>
        <div className="card-list">{plans.map((plan) => <article className="compact-card" key={plan.id}>
          <strong>{plan.name} · {plan.status}</strong>
          <span>RPO {plan.rpo_minutes} min · RTO {plan.rto_minutes} min</span>
          {readiness[plan.id] ? <small>Prontidão: {readiness[plan.id].score.toFixed(0)}% · {readiness[plan.id].ready ? 'pronto' : readiness[plan.id].blockers.join('; ')}</small> : null}
          <div className="inline-form">
            <button className="secondary-button" type="button" onClick={() => void checkReadiness(plan)}>Verificar prontidão</button>
            <button className="secondary-button" type="button" onClick={() => void createDrill(plan)}>Planejar drill</button>
          </div>
        </article>)}</div>
      </section>

      <section className="panel">
        <h2>GitOps</h2>
        <div className="inline-form">
          <input value={repositoryUrl} onChange={(event) => setRepositoryUrl(event.target.value)} />
          <button type="button" onClick={() => void createGitOps()}>Registrar aplicação</button>
        </div>
        <div className="card-list">{gitOpsApps.map((app) => <article className="compact-card" key={app.id}>
          <strong>{app.name} · {app.health_status}</strong>
          <span>{app.environment} · {app.sync_policy}</span>
          <small>{app.target_revision} · {app.namespace}</small>
        </article>)}</div>
      </section>
    </section>

    <section className="panel">
      <div className="panel-heading"><div><h2>Autoscaling</h2><p>Políticas exportáveis para o Helm chart do EduCode.</p></div><button type="button" onClick={() => void saveAutoscaling()}>Salvar padrão do backend</button></div>
      <div className="card-list">{policies.map((policy) => <article className="compact-card" key={policy.id}>
        <strong>{policy.component} · {policy.environment}</strong>
        <span>{policy.min_replicas}–{policy.max_replicas} réplicas · CPU {policy.target_cpu_percent}% · memória {policy.target_memory_percent}%</span>
        <small>Fila-alvo: {policy.queue_depth_target}</small>
      </article>)}</div>
    </section>
  </div>
}
