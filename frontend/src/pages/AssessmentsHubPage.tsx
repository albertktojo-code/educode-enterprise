import { FormEvent, useEffect, useMemo, useState } from 'react'

import { api } from '../lib/api'

type Assessment = {
  id: string
  title: string
  description: string
  status: string
  source_type: string
  current_version_number: number
  versions: Array<{ id: string; items: unknown[] }>
}

type BankItem = {
  id: string
  title: string
  prompt: string
  item_type: string
  source_type: string
  status: string
  curriculum_skill_codes: string[]
  ct_pillar_codes: string[]
}

const sourceLabel: Record<string, string> = {
  teacher: 'Professor',
  ai: 'IA revisável',
  imported: 'Importada',
  external: 'Sistema externo',
}

export function AssessmentsHubPage() {
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [items, setItems] = useState<BankItem[]>([])
  const [title, setTitle] = useState('')
  const [topic, setTopic] = useState('Pensamento Computacional')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    const [assessmentRows, bankRows] = await Promise.all([
      api.get<Assessment[]>('/assessments'),
      api.get<BankItem[]>('/assessments/question-bank/items'),
    ])
    setAssessments(assessmentRows)
    setItems(bankRows)
  }

  useEffect(() => { void load() }, [])

  async function createAssessment(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      await api.post('/assessments', {
        title,
        description: 'Avaliação criada no Núcleo de Avaliação Integrada.',
        assessment_type: 'assessment',
        source_type: 'teacher',
        instructions: 'Leia cada questão com atenção.',
        item_ids: [],
      })
      setTitle('')
      setMessage('Avaliação criada como rascunho.')
      await load()
    } finally { setBusy(false) }
  }

  async function generateWithAi() {
    const assessment = assessments[0]
    if (!assessment) {
      setMessage('Crie uma avaliação antes de solicitar questões à IA.')
      return
    }
    setBusy(true)
    try {
      const request = await api.post<{ id: string }>('/ai/requests', {
        module_name: 'assessments',
        action_name: 'generate_questions',
        request_type: 'structured_text',
        target_type: 'assessment',
        target_id: assessment.id,
        input_data: {
          purpose: 'assessment_questions',
          quantity: 5,
          topic,
          difficulty: 'medium',
          curriculum_skill_codes: [],
          ct_pillar_codes: ['abstraction', 'decomposition', 'pattern_recognition', 'algorithms'],
        },
        parameters: { quantity: 5 },
        queue_immediately: false,
      })
      await api.post(`/ai/requests/${request.id}/run`)
      setMessage('Proposta criada pelo AI Fabric. Revise, aprove e aplique antes de publicar.')
    } finally { setBusy(false) }
  }

  const counts = useMemo(() => ({
    assessments: assessments.length,
    questions: items.length,
    ai: items.filter((item) => item.source_type === 'ai').length,
    external: items.filter((item) => ['imported', 'external'].includes(item.source_type)).length,
  }), [assessments, items])

  return <div className="page-stack">
    <header className="page-header">
      <div><span className="eyebrow">Sprint 12</span><h1>Núcleo de Avaliação Integrada</h1>
      <p>Crie, importe, publique, corrija e analise exercícios usando uma única trilha de evidências.</p></div><a className="secondary-button" href="/ia?module=assessments&action=generate_questions">Gerar com AI Fabric</a>
    </header>

    {message ? <div className="notice success">{message}</div> : null}

    <section className="dashboard-grid four">
      <article className="metric-card"><span>Avaliações</span><strong>{counts.assessments}</strong></article>
      <article className="metric-card"><span>Questões</span><strong>{counts.questions}</strong></article>
      <article className="metric-card"><span>Geradas pela IA</span><strong>{counts.ai}</strong></article>
      <article className="metric-card"><span>Importadas/externas</span><strong>{counts.external}</strong></article>
    </section>

    <section className="panel-grid two">
      <form className="panel" onSubmit={createAssessment}>
        <h2>Nova avaliação</h2>
        <label>Título<input value={title} onChange={(event) => setTitle(event.target.value)} minLength={3} required /></label>
        <button disabled={busy} type="submit">Criar rascunho</button>
      </form>
      <div className="panel">
        <h2>Gerar questões com EduCode AI Fabric</h2>
        <label>Tema<input value={topic} onChange={(event) => setTopic(event.target.value)} /></label>
        <button disabled={busy || assessments.length === 0} onClick={generateWithAi} type="button">Gerar proposta para avaliação mais recente</button>
        <a className="secondary-button" href="/ia?module=assessments&action=generate_questions">Abrir revisão da IA</a>
        <small>A publicação e a incorporação ao banco sempre exigem revisão humana.</small>
      </div>
    </section>

    <section className="panel">
      <h2>Avaliações versionadas</h2>
      <div className="table-wrap"><table><thead><tr><th>Título</th><th>Origem</th><th>Status</th><th>Versão</th><th>Itens</th></tr></thead>
      <tbody>{assessments.map((assessment) => {
        const current = assessment.versions.find((version) => version.items) ?? assessment.versions[0]
        return <tr key={assessment.id}><td><strong>{assessment.title}</strong><br/><small>{assessment.description}</small></td>
        <td>{sourceLabel[assessment.source_type] ?? assessment.source_type}</td><td>{assessment.status}</td>
        <td>v{assessment.current_version_number}</td><td>{current?.items.length ?? 0}</td></tr>
      })}</tbody></table></div>
    </section>

    <section className="panel">
      <h2>Banco de questões e exercícios</h2>
      <p>Questões do professor, da IA e de integrações externas compartilham o mesmo modelo versionado.</p>
      <div className="card-list">{items.slice(0, 12).map((item) => <article className="compact-card" key={item.id}>
        <strong>{item.title || item.prompt.slice(0, 80)}</strong><span>{sourceLabel[item.source_type] ?? item.source_type} · {item.item_type}</span>
        <small>{[...item.curriculum_skill_codes, ...item.ct_pillar_codes].join(' · ') || 'Sem classificação curricular'}</small>
      </article>)}</div>
    </section>

    <section className="panel">
      <h2>Integração ponta a ponta</h2>
      <p>Avaliação → versão → publicação → tentativa → resposta → correção → evidência BNCC/PC → Analytics → Laboratório Estatístico.</p>
      <p><strong>Importações preparadas:</strong> CSV, XLSX, JSON, QTI, LTI, xAPI e SCORM.</p>
    </section>
  </div>
}
