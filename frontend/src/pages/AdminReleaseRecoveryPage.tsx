import { useEffect, useMemo, useState } from 'react'

import { api } from '../lib/api'

type Release = {
  id: string
  version: string
  build_identifier: string
  commit_sha: string
  environment: string
  migration_revision: string
  status: string
  release_notes: string
  created_at: string
}

type Readiness = {
  release_id: string
  ready: boolean
  score: number
  blockers: string[]
  warnings: string[]
  completed_steps: number
  total_steps: number
  approvals: Record<string, string>
  artifact_count: number
  backup_ready: boolean
  migration_safe: boolean
}

type Step = {
  id: string
  step_order: number
  step_key: string
  title: string
  status: string
  is_blocking: boolean
}

type RecoveryObjective = {
  id: string
  environment: string
  service_name: string
  rpo_minutes: number
  rto_minutes: number
  backup_frequency_minutes: number
  last_exercised_at: string | null
}

type MaintenanceWindow = {
  id: string
  environment: string
  mode: string
  status: string
  title: string
  message: string
  starts_at: string
  ends_at: string
}

type Preflight = {
  ready: boolean
  environment: string
  strategy: string
  migration_revision: string
  warnings: string[]
  blockers: string[]
  backup_required: boolean
  approval_required: boolean
}

export function AdminReleaseRecoveryPage() {
  const [releases, setReleases] = useState<Release[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [readiness, setReadiness] = useState<Readiness | null>(null)
  const [steps, setSteps] = useState<Step[]>([])
  const [objectives, setObjectives] = useState<RecoveryObjective[]>([])
  const [maintenance, setMaintenance] = useState<MaintenanceWindow[]>([])
  const [preflight, setPreflight] = useState<Preflight | null>(null)
  const [message, setMessage] = useState('')
  const [version, setVersion] = useState('13.2.0')
  const [build, setBuild] = useState('sprint-13.2')
  const [maintenanceTitle, setMaintenanceTitle] = useState('Atualização programada')
  const [artifactDigest, setArtifactDigest] = useState('')

  const selected = useMemo(
    () => releases.find((item) => item.id === selectedId) ?? null,
    [releases, selectedId],
  )

  async function loadBase() {
    const [releaseData, objectivesData, maintenanceData, preflightData] = await Promise.all([
      api.get<Release[]>('/release-management/releases'),
      api.get<RecoveryObjective[]>('/release-management/recovery-objectives'),
      api.get<MaintenanceWindow[]>('/release-management/maintenance'),
      api.get<Preflight>('/release-management/preflight'),
    ])
    setReleases(releaseData)
    setObjectives(objectivesData)
    setMaintenance(maintenanceData)
    setPreflight(preflightData)
    if (!selectedId && releaseData[0]) setSelectedId(releaseData[0].id)
  }

  async function loadRelease(releaseId: string) {
    const [readinessData, stepsData] = await Promise.all([
      api.get<Readiness>(`/release-management/releases/${releaseId}/readiness`),
      api.get<Step[]>(`/release-management/releases/${releaseId}/steps`),
    ])
    setReadiness(readinessData)
    setSteps(stepsData)
  }

  useEffect(() => {
    void loadBase()
  }, [])

  useEffect(() => {
    if (selectedId) void loadRelease(selectedId)
  }, [selectedId])

  async function createRelease() {
    setMessage('Criando release e checklist controlado...')
    const created = await api.post<Release>('/release-management/releases', {
      version,
      build_identifier: build,
      commit_sha: '',
      release_notes: 'Release preparada pela Sprint 13.2.',
    })
    setSelectedId(created.id)
    setMessage('Release criada. Registre artefatos, validações e aprovações antes da implantação.')
    await loadBase()
  }

  async function completeStep(step: Step) {
    await api.patch(`/release-management/releases/${selectedId}/steps/${step.id}`, {
      status: 'completed',
      details: { confirmed_in_ui: true },
    })
    await loadRelease(selectedId)
  }

  async function approve(stage: string) {
    await api.post(`/release-management/releases/${selectedId}/approvals`, {
      approval_stage: stage,
      decision: 'approved',
      notes: 'Aprovado no painel administrativo.',
    })
    await loadRelease(selectedId)
  }

  async function addArtifact() {
    const digest = artifactDigest.trim().toLowerCase()
    if (!/^[a-f0-9]{64}$/.test(digest)) {
      setMessage('Informe o SHA-256 real do artefato antes de registrar o manifesto.')
      return
    }
    await api.post(`/release-management/releases/${selectedId}/artifacts`, {
      artifact_type: 'manifest',
      name: `release-${selected?.version ?? version}-manifest.json`,
      version: selected?.version ?? version,
      digest_sha256: digest,
      image_digest: '',
      storage_reference: 'registry://educode/release-manifest',
      sbom_reference: 'sbom://educode/release',
      signature_reference: '',
      metadata_json: { demonstration: true },
    })
    setArtifactDigest('')
    setMessage('Manifesto e digest real registrados para a release.')
    await loadRelease(selectedId)
  }

  async function configureObjectives() {
    await api.put('/release-management/recovery-objectives', {
      environment: preflight?.environment === 'production' ? 'production' : 'homologation',
      service_name: 'educode-platform',
      rpo_minutes: 1440,
      rto_minutes: 240,
      backup_frequency_minutes: 1440,
      notes: 'Objetivos iniciais da continuidade operacional.',
    })
    await loadBase()
  }

  async function scheduleMaintenance() {
    const start = new Date(Date.now() + 60 * 60 * 1000)
    const end = new Date(start.getTime() + 60 * 60 * 1000)
    await api.post('/release-management/maintenance', {
      environment: preflight?.environment ?? 'development',
      mode: 'read_only',
      title: maintenanceTitle,
      message: 'Durante a janela, novas alterações ficam temporariamente indisponíveis.',
      starts_at: start.toISOString(),
      ends_at: end.toISOString(),
      allow_admin_access: true,
    })
    await loadBase()
  }

  return <div className="page-stack">
    <header className="page-header">
      <div>
        <span className="eyebrow">Sprint 13.2</span>
        <h1>Releases e continuidade</h1>
        <p>Implantação controlada, artefatos imutáveis, aprovações, RPO/RTO, manutenção e recuperação seletiva.</p>
      </div>
      <button type="button" onClick={() => void loadBase()}>Atualizar</button>
    </header>

    {message ? <div className="notice">{message}</div> : null}

    {preflight ? <section className="stats stats-four">
      <article><strong>{preflight.ready ? 'Pronto' : 'Bloqueado'}</strong><span>Preflight</span></article>
      <article><strong>{preflight.environment}</strong><span>Ambiente</span></article>
      <article><strong>{preflight.strategy}</strong><span>Estratégia</span></article>
      <article><strong>{preflight.migration_revision}</strong><span>Migration atual</span></article>
    </section> : null}

    {preflight && (preflight.warnings.length || preflight.blockers.length) ? <section className="panel">
      <h2>Verificações de implantação</h2>
      {preflight.blockers.map((item) => <p key={item}><strong>Bloqueio:</strong> {item}</p>)}
      {preflight.warnings.map((item) => <p key={item}><strong>Aviso:</strong> {item}</p>)}
    </section> : null}

    <section className="panel">
      <div className="panel-heading"><div><h2>Nova release</h2><p>Cria checklist, aprovações e rastreabilidade.</p></div></div>
      <div className="inline-form">
        <input value={version} onChange={(event) => setVersion(event.target.value)} placeholder="Versão" />
        <input value={build} onChange={(event) => setBuild(event.target.value)} placeholder="Build" />
        <button type="button" onClick={() => void createRelease()}>Criar release</button>
      </div>
    </section>

    <section className="panel-grid two">
      <section className="panel">
        <h2>Releases</h2>
        <div className="card-list">{releases.length ? releases.map((release) => <button className="compact-card" type="button" key={release.id} onClick={() => setSelectedId(release.id)}>
          <strong>{release.version} · {release.status}</strong>
          <span>{release.environment} · {release.build_identifier}</span>
          <small>{release.migration_revision}</small>
        </button>) : <p>Nenhuma release registrada.</p>}</div>
      </section>

      <section className="panel">
        <h2>Prontidão da release</h2>
        {readiness ? <>
          <div className="stats"><article><strong>{readiness.score.toFixed(0)}%</strong><span>Score</span></article><article><strong>{readiness.completed_steps}/{readiness.total_steps}</strong><span>Etapas</span></article></div>
          <p><strong>Status:</strong> {readiness.ready ? 'pronta para implantação' : 'ainda bloqueada'}</p>
          {readiness.blockers.map((item) => <p key={item}>{item}</p>)}
          <div className="inline-form"><input value={artifactDigest} onChange={(event) => setArtifactDigest(event.target.value)} placeholder="SHA-256 real do artefato" /><button type="button" onClick={() => void addArtifact()}>Registrar manifesto</button>{['technical', 'security', 'business', 'production'].map((stage) => <button className="secondary-button" type="button" key={stage} onClick={() => void approve(stage)}>Aprovar {stage}</button>)}</div>
        </> : <p>Selecione uma release.</p>}
      </section>
    </section>

    <section className="panel">
      <h2>Etapas controladas</h2>
      <div className="card-list">{steps.map((step) => <article className="compact-card" key={step.id}>
        <strong>{step.step_order}. {step.title}</strong><span>{step.status}{step.is_blocking ? ' · obrigatória' : ''}</span>
        {step.status !== 'completed' ? <button className="secondary-button" type="button" onClick={() => void completeStep(step)}>Marcar concluída</button> : null}
      </article>)}</div>
    </section>

    <section className="panel-grid two">
      <section className="panel">
        <div className="panel-heading"><div><h2>Objetivos de recuperação</h2><p>RPO e RTO por ambiente e serviço.</p></div><button type="button" onClick={() => void configureObjectives()}>Configurar padrão</button></div>
        <div className="card-list">{objectives.map((item) => <article className="compact-card" key={item.id}><strong>{item.service_name}</strong><span>{item.environment} · RPO {item.rpo_minutes} min · RTO {item.rto_minutes} min</span></article>)}</div>
      </section>
      <section className="panel">
        <h2>Janela de manutenção</h2>
        <div className="inline-form"><input value={maintenanceTitle} onChange={(event) => setMaintenanceTitle(event.target.value)} /><button type="button" onClick={() => void scheduleMaintenance()}>Agendar</button></div>
        <div className="card-list">{maintenance.map((item) => <article className="compact-card" key={item.id}><strong>{item.title}</strong><span>{item.mode} · {item.status}</span><small>{new Date(item.starts_at).toLocaleString('pt-BR')} — {new Date(item.ends_at).toLocaleString('pt-BR')}</small></article>)}</div>
      </section>
    </section>
  </div>
}
