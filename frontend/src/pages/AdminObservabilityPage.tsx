import { useEffect, useMemo, useState } from 'react'

import { api } from '../lib/api'

type QuotaUsage = {
  quota_key: string
  limit_value: number
  used_value: number
  usage_percentage: number
  status: string
  enforcement_mode: string
  period: string
}

type Overview = {
  generated_at: string
  platform_status: string
  request_metrics: Record<string, number>
  jobs: { status_counts: Record<string, number>; metrics: Record<string, number> }
  workers: { total: number; active: number; queues: string[]; stale_workers: string[] }
  dependencies: Record<string, { status: string; latency_ms: number }>
  incidents: Record<string, number>
  alerts: Record<string, number>
  quotas: QuotaUsage[]
  slo_summary: Record<string, number>
}

type SLO = {
  id: string
  slo_key: string
  name: string
  metric_name: string
  comparator: string
  target_value: number
  observed_value: number | null
  sample_count: number
  status: string
  error_budget_remaining_percent: number | null
  window_minutes: number
}

type Alert = {
  id: string
  title: string
  metric_name: string
  observed_value: number
  threshold_value: number
  severity: string
  status: string
  description: string
  opened_at: string
}

type Diagnostic = {
  id: string
  status: string
  duration_ms: number
  warnings: string[]
  checks: Record<string, unknown>
  created_at: string
}

type MetricSeries = { metric_name: string; unit: string; points: Array<{ measured_at: string; value: number }> }

type Reconciliation = {
  id: string
  run_type: string
  status: string
  findings_count: number
  repaired_count: number
  summary: { findings?: Array<{ code: string; severity: string; count: number; description: string }> }
  created_at: string
}

function MetricBar({ label, value, max, suffix = '' }: { label: string; value: number; max: number; suffix?: string }) {
  const width = Math.max(2, Math.min(100, max > 0 ? value / max * 100 : 0))
  return <div className="metric-bar-row">
    <div><span>{label}</span><strong>{value.toFixed(value < 10 ? 2 : 0)}{suffix}</strong></div>
    <div className="metric-bar-track" aria-label={`${label}: ${value}${suffix}`}><span style={{ width: `${width}%` }} /></div>
  </div>
}

function SparkLine({ series, label }: { series?: MetricSeries; label: string }) {
  const points = series?.points ?? []
  const width = 520
  const height = 150
  if (points.length < 2) return <div className="chart-empty">Ainda não há histórico suficiente para {label}.</div>
  const values = points.map((point) => point.value)
  const minimum = Math.min(...values)
  const maximum = Math.max(...values)
  const range = maximum - minimum || 1
  const coordinates = points.map((point, index) => {
    const x = index / (points.length - 1) * width
    const y = height - ((point.value - minimum) / range * (height - 24) + 12)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  return <figure className="ops-chart">
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${label}: mínimo ${minimum.toFixed(2)}, máximo ${maximum.toFixed(2)}`}>
      <line x1="0" x2={width} y1={height - 12} y2={height - 12} />
      <polyline points={coordinates} fill="none" vectorEffect="non-scaling-stroke" />
    </svg>
    <figcaption><strong>{label}</strong><span>{minimum.toFixed(2)} – {maximum.toFixed(2)} {series?.unit}</span></figcaption>
  </figure>
}

export function AdminObservabilityPage() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [slos, setSlos] = useState<SLO[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([])
  const [reconciliations, setReconciliations] = useState<Reconciliation[]>([])
  const [history, setHistory] = useState<MetricSeries[]>([])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const [overviewData, sloData, alertData, diagnosticData, reconciliationData, historyData] = await Promise.all([
        api.get<Overview>('/observability/overview'),
        api.get<SLO[]>('/observability/slos/evaluate'),
        api.get<Alert[]>('/observability/alerts?limit=30'),
        api.get<Diagnostic[]>('/observability/diagnostics?limit=10'),
        api.get<Reconciliation[]>('/observability/reconciliation?limit=10'),
        api.get<MetricSeries[]>('/observability/metrics/history?hours=24'),
      ])
      setOverview(overviewData)
      setSlos(sloData)
      setAlerts(alertData)
      setDiagnostics(diagnosticData)
      setReconciliations(reconciliationData)
      setHistory(historyData)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    const timer = window.setInterval(() => void load(), 15000)
    return () => window.clearInterval(timer)
  }, [])

  const requestMax = useMemo(() => {
    if (!overview) return 1
    return Math.max(overview.request_metrics.latency_p95_ms ?? 0, overview.request_metrics.latency_p99_ms ?? 0, 1)
  }, [overview])

  async function runDiagnostic() {
    setMessage('Executando diagnóstico integrado...')
    await api.post('/observability/diagnostics', {})
    setMessage('Diagnóstico concluído e registrado.')
    await load()
  }

  async function runReconciliation(repair: boolean) {
    setMessage(repair ? 'Executando reconciliação com reparos operacionais seguros...' : 'Verificando integridade dos vínculos...')
    await api.post('/observability/reconciliation', { run_type: 'full', repair_safe_findings: repair })
    setMessage('Reconciliação concluída.')
    await load()
  }

  async function evaluateAlerts() {
    await api.post('/observability/alert-rules/evaluate', {})
    setMessage('Regras de alerta avaliadas com as métricas atuais.')
    await load()
  }

  async function updateAlert(alert: Alert, status: 'acknowledged' | 'resolved') {
    await api.patch(`/observability/alerts/${alert.id}`, { status })
    await load()
  }

  return <div className="page-stack">
    <header className="page-header">
      <div>
        <span className="eyebrow">Sprint 13.1</span>
        <h1>Observabilidade e confiabilidade</h1>
        <p>Métricas, SLOs, alertas, quotas e integridade da operação em uma visão única.</p>
      </div>
      <button type="button" disabled={loading} onClick={() => void load()}>{loading ? 'Atualizando...' : 'Atualizar agora'}</button>
    </header>

    {message ? <div className="notice">{message}</div> : null}

    {overview ? <>
      <section className="stats stats-four">
        <article><strong>{overview.platform_status}</strong><span>Estado da plataforma</span></article>
        <article><strong>{overview.workers.active}/{overview.workers.total}</strong><span>Workers ativos</span></article>
        <article><strong>{overview.request_metrics.latency_p95_ms?.toFixed(0) ?? 0} ms</strong><span>Latência p95</span></article>
        <article><strong>{overview.request_metrics.error_rate_percent?.toFixed(2) ?? 0}%</strong><span>Erros HTTP</span></article>
      </section>

      <section className="panel-grid two">
        <section className="panel">
          <div className="panel-heading"><div><h2>Desempenho HTTP</h2><p>Métricas do processo atual do backend.</p></div></div>
          <MetricBar label="Latência média" value={overview.request_metrics.latency_avg_ms ?? 0} max={requestMax} suffix=" ms" />
          <MetricBar label="Latência p95" value={overview.request_metrics.latency_p95_ms ?? 0} max={requestMax} suffix=" ms" />
          <MetricBar label="Latência p99" value={overview.request_metrics.latency_p99_ms ?? 0} max={requestMax} suffix=" ms" />
          <div className="metric-grid"><article><strong>{overview.request_metrics.requests_total ?? 0}</strong><span>Requisições</span></article><article><strong>{overview.request_metrics.active_requests ?? 0}</strong><span>Ativas</span></article></div>
        </section>
        <section className="panel">
          <h2>Dependências</h2>
          <div className="card-list">{Object.entries(overview.dependencies).map(([name, item]) => <article className="compact-card" key={name}><strong>{name}</strong><span>{item.status} · {item.latency_ms} ms</span></article>)}</div>
          {overview.workers.stale_workers?.length ? <div className="warning-box">Sem heartbeat: {overview.workers.stale_workers.join(', ')}</div> : null}
        </section>
      </section>

      <section className="panel">
        <div className="panel-heading"><div><h2>Histórico operacional</h2><p>Últimas 24 horas a partir dos snapshots persistidos.</p></div></div>
        <div className="panel-grid two">
          <SparkLine series={history.find((item) => item.metric_name === 'http.latency_p95_ms')} label="Latência HTTP p95" />
          <SparkLine series={history.find((item) => item.metric_name === 'http.error_rate_percent')} label="Taxa de erros HTTP" />
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading"><div><h2>Objetivos de confiabilidade</h2><p>Metas calculadas a partir de snapshots operacionais.</p></div></div>
        <div className="card-list">{slos.length ? slos.map((slo) => <article className="compact-card" key={slo.id}>
          <strong>{slo.name}</strong>
          <span>{slo.metric_name}: {slo.observed_value === null ? 'dados insuficientes' : slo.observed_value.toFixed(2)} {slo.comparator} {slo.target_value}</span>
          <small>{slo.status} · {slo.sample_count} amostras · janela de {slo.window_minutes} min</small>
          {slo.error_budget_remaining_percent !== null ? <div className="quota-progress"><span style={{ width: `${Math.max(0, Math.min(100, slo.error_budget_remaining_percent))}%` }} /></div> : null}
        </article>) : <p>Nenhum SLO configurado. Use a API para cadastrar metas institucionais.</p>}</div>
      </section>

      <section className="panel">
        <h2>Quotas institucionais</h2>
        <div className="quota-grid">{overview.quotas.length ? overview.quotas.map((quota) => <article className={`quota-card quota-${quota.status}`} key={quota.quota_key}>
          <strong>{quota.quota_key}</strong><span>{quota.used_value} de {quota.limit_value}</span>
          <div className="quota-progress"><span style={{ width: `${Math.min(100, quota.usage_percentage)}%` }} /></div>
          <small>{quota.usage_percentage.toFixed(1)}% · {quota.enforcement_mode}</small>
        </article>) : <p>Nenhuma quota configurada.</p>}</div>
      </section>
    </> : <p>Carregando observabilidade...</p>}

    <section className="panel-grid two">
      <section className="panel">
        <div className="panel-heading"><div><h2>Alertas operacionais</h2><p>Eventos explicáveis gerados por regras institucionais.</p></div><button className="secondary-button" type="button" onClick={() => void evaluateAlerts()}>Avaliar regras</button></div>
        <div className="card-list">{alerts.length ? alerts.map((alert) => <article className="compact-card" key={alert.id}>
          <strong>{alert.title}</strong><span>{alert.severity} · {alert.status} · {alert.metric_name}</span>
          <small>{alert.observed_value.toFixed(2)} / limite {alert.threshold_value} · {new Date(alert.opened_at).toLocaleString('pt-BR')}</small>
          <p>{alert.description}</p>
          {alert.status === 'open' ? <button className="secondary-button" type="button" onClick={() => void updateAlert(alert, 'acknowledged')}>Reconhecer</button> : null}
          {['open', 'acknowledged'].includes(alert.status) ? <button className="secondary-button" type="button" onClick={() => void updateAlert(alert, 'resolved')}>Resolver</button> : null}
        </article>) : <p>Nenhum alerta registrado.</p>}</div>
      </section>

      <section className="panel">
        <div className="panel-heading"><div><h2>Diagnóstico</h2><p>PostgreSQL, Redis, armazenamento, workers e migration.</p></div><button type="button" onClick={() => void runDiagnostic()}>Executar</button></div>
        <div className="card-list">{diagnostics.map((run) => <article className="compact-card" key={run.id}><strong>{run.status}</strong><span>{run.duration_ms} ms · {new Date(run.created_at).toLocaleString('pt-BR')}</span><small>{run.warnings.length ? run.warnings.join(' · ') : 'Sem avisos'}</small></article>)}</div>
      </section>
    </section>

    <section className="panel">
      <div className="panel-heading"><div><h2>Reconciliação de dados</h2><p>Localiza vínculos incompletos e recupera somente estados operacionais seguros.</p></div><div className="button-row"><button className="secondary-button" type="button" onClick={() => void runReconciliation(false)}>Somente verificar</button><button type="button" onClick={() => void runReconciliation(true)}>Reparar estados seguros</button></div></div>
      <div className="card-list">{reconciliations.map((run) => <article className="compact-card" key={run.id}><strong>{run.run_type} · {run.status}</strong><span>{run.findings_count} ocorrências · {run.repaired_count} reparadas</span><small>{new Date(run.created_at).toLocaleString('pt-BR')}</small>{run.summary.findings?.slice(0, 3).map((finding) => <p key={finding.code}>{finding.code}: {finding.count} — {finding.description}</p>)}</article>)}</div>
    </section>
  </div>
}
