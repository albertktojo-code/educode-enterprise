import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { api, apiBlob } from '../lib/api'
import type {
  MethodComparison,
  ReviewComment,
  SampleSizePlan,
  SensitivityRun,
  StatisticalAnalysis,
  StatisticalChart,
  StatisticalReportSummary,
  StatisticalStudy,
} from '../types/statistics'

const scenarioLabels: Record<string, string> = {
  complete_cases: 'Somente casos completos',
  without_iqr_outliers: 'Sem outliers por IQR',
  winsorized_5: 'Winsorização de 5%',
  alternative_method: 'Método alternativo',
}

const compatibleMethods: Record<string, string[]> = {
  paired_t: ['paired_t', 'wilcoxon'],
  wilcoxon: ['wilcoxon', 'paired_t'],
  independent_t: ['independent_t', 'welch_t', 'mann_whitney'],
  welch_t: ['welch_t', 'independent_t', 'mann_whitney'],
  mann_whitney: ['mann_whitney', 'welch_t', 'independent_t'],
  anova: ['anova', 'kruskal_wallis'],
  kruskal_wallis: ['kruskal_wallis', 'anova'],
  pearson: ['pearson', 'spearman'],
  spearman: ['spearman', 'pearson'],
  chi_square: ['chi_square', 'fisher_exact'],
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function StatisticsAdvancedPage() {
  const [studies, setStudies] = useState<StatisticalStudy[]>([])
  const [studyId, setStudyId] = useState('')
  const [analyses, setAnalyses] = useState<StatisticalAnalysis[]>([])
  const [analysisId, setAnalysisId] = useState('')
  const [sensitivity, setSensitivity] = useState<SensitivityRun[]>([])
  const [comparisons, setComparisons] = useState<MethodComparison[]>([])
  const [comments, setComments] = useState<ReviewComment[]>([])
  const [reports, setReports] = useState<StatisticalReportSummary[]>([])
  const [charts, setCharts] = useState<StatisticalChart[]>([])
  const [plans, setPlans] = useState<SampleSizePlan[]>([])
  const [comment, setComment] = useState('')
  const [message, setMessage] = useState('')
  const [design, setDesign] = useState('paired')
  const [effectSize, setEffectSize] = useState('0.5')
  const [power, setPower] = useState('0.80')
  const [planTitle, setPlanTitle] = useState('Planejamento do estudo')

  const activeAnalysis = useMemo(
    () => analyses.find((item) => item.id === analysisId),
    [analyses, analysisId],
  )

  async function loadStudies() {
    const data = await api<StatisticalStudy[]>('/statistics/studies')
    setStudies(data)
    if (!studyId && data[0]) setStudyId(data[0].id)
  }

  async function loadAnalyses(id: string) {
    if (!id) return
    const data = await api<StatisticalAnalysis[]>(`/statistics/studies/${id}/analyses`)
    setAnalyses(data)
    if (!data.some((item) => item.id === analysisId)) setAnalysisId(data[0]?.id ?? '')
  }

  async function loadAdvanced(id: string) {
    if (!id) {
      setSensitivity([])
      setComparisons([])
      setComments([])
      setReports([])
      setCharts([])
      return
    }
    const [sensitivityData, comparisonData, commentData, reportData, chartData] = await Promise.all([
      api<SensitivityRun[]>(`/statistics/analyses/${id}/sensitivity`),
      api<MethodComparison[]>(`/statistics/analyses/${id}/method-comparisons`),
      api<ReviewComment[]>(`/statistics/review-comments?entity_type=analysis&entity_id=${id}`),
      api<StatisticalReportSummary[]>(`/statistics/analyses/${id}/reports`),
      api<StatisticalChart[]>(`/statistics/analyses/${id}/charts`),
    ])
    setSensitivity(sensitivityData)
    setComparisons(comparisonData)
    setComments(commentData)
    setReports(reportData)
    setCharts(chartData)
  }

  async function loadPlans() {
    setPlans(await api<SampleSizePlan[]>('/statistics/sample-size-plans'))
  }

  useEffect(() => {
    void Promise.all([loadStudies(), loadPlans()]).catch((error: Error) => setMessage(error.message))
  }, [])
  useEffect(() => {
    void loadAnalyses(studyId).catch((error: Error) => setMessage(error.message))
  }, [studyId])
  useEffect(() => {
    void loadAdvanced(analysisId).catch((error: Error) => setMessage(error.message))
  }, [analysisId])

  async function runSensitivity() {
    if (!analysisId) return
    try {
      await api(`/statistics/analyses/${analysisId}/sensitivity`, {
        method: 'POST',
        body: JSON.stringify({
          scenario_keys: ['complete_cases', 'without_iqr_outliers', 'winsorized_5', 'alternative_method'],
        }),
      })
      await loadAdvanced(analysisId)
      setMessage('Análise de sensibilidade concluída.')
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function compare() {
    if (!analysisId || !activeAnalysis) return
    const methods = compatibleMethods[activeAnalysis.analysis_type] ?? [activeAnalysis.analysis_type]
    if (methods.length < 2) {
      setMessage('Não há comparação automática configurada para este método.')
      return
    }
    try {
      await api(`/statistics/analyses/${analysisId}/method-comparisons`, {
        method: 'POST',
        body: JSON.stringify({ methods }),
      })
      await loadAdvanced(analysisId)
      setMessage('Métodos comparados com o mesmo dataset congelado.')
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function createVersion() {
    if (!analysisId) return
    try {
      const version = await api<StatisticalAnalysis>(`/statistics/analyses/${analysisId}/versions`, {
        method: 'POST',
        body: JSON.stringify({ change_summary: 'Nova versão criada pela interface avançada.' }),
      })
      await loadAnalyses(studyId)
      setAnalysisId(version.id)
      setMessage(`Versão ${version.version_number} criada sem substituir a análise anterior.`)
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function addComment() {
    if (!analysisId || comment.trim().length < 3) return
    try {
      await api('/statistics/review-comments', {
        method: 'POST',
        body: JSON.stringify({ entity_type: 'analysis', entity_id: analysisId, body: comment }),
      })
      setComment('')
      await loadAdvanced(analysisId)
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function resolveComment(id: string) {
    try {
      await api(`/statistics/review-comments/${id}/resolve`, { method: 'PATCH' })
      await loadAdvanced(analysisId)
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function updateReviewStatus(status: string) {
    if (!analysisId) return
    try {
      await api(`/statistics/analyses/${analysisId}/review-status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      })
      await loadAnalyses(studyId)
      setMessage('Status de revisão atualizado.')
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function downloadScript(language: 'python' | 'r') {
    if (!analysisId) return
    try {
      const blob = await apiBlob(`/statistics/analyses/${analysisId}/scripts/${language}/download`)
      downloadBlob(blob, `analysis-${analysisId}.${language === 'python' ? 'py' : 'R'}`)
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function createPlan() {
    try {
      await api('/statistics/sample-size-plans', {
        method: 'POST',
        body: JSON.stringify({
          study_id: studyId || null,
          title: planTitle,
          design,
          significance_level: 0.05,
          power: Number(power),
          expected_effect_size: Number(effectSize),
          group_ratio: 1,
        }),
      })
      await loadPlans()
      setMessage('Planejamento amostral calculado. A margem recomendada inclui 15% de perdas.')
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function downloadReport(report: StatisticalReportSummary, format: 'html' | 'pdf' | 'docx') {
    try {
      const blob = await apiBlob(`/statistics/reports/${report.id}/download/${format}`)
      downloadBlob(blob, `relatorio-${report.id}.${format}`)
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function downloadChart(chart: StatisticalChart, format: 'png' | 'svg' | 'pdf') {
    try {
      const blob = await apiBlob(`/statistics/charts/${chart.id}/export/${format}`)
      downloadBlob(blob, `grafico-${chart.id}.${format}`)
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function createReportRevision(report: StatisticalReportSummary) {
    try {
      await api(`/statistics/reports/${report.id}/revisions`, {
        method: 'POST',
        body: JSON.stringify({ change_summary: 'Nova versão preservada após revisão.' }),
      })
      await loadAdvanced(analysisId)
      setMessage('Nova versão do relatório criada sem apagar a anterior.')
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  return <section>
    <header className="page-header statistics-header">
      <div>
        <span className="eyebrow">SPRINT 11.1</span>
        <h1>Pesquisa, reprodutibilidade e revisão</h1>
        <p>Teste a robustez das conclusões, compare métodos, planeje a amostra e exporte relatórios científicos.</p>
      </div>
      <Link className="secondary-button" to="/estatistica">Voltar ao laboratório</Link>
    </header>

    {message ? <div className="inline-message">{message}</div> : null}

    <div className="statistics-advanced-selector panel">
      <label>Estudo<select value={studyId} onChange={(event) => setStudyId(event.target.value)}><option value="">Selecione</option>{studies.map((study) => <option key={study.id} value={study.id}>{study.title}</option>)}</select></label>
      <label>Análise<select value={analysisId} onChange={(event) => setAnalysisId(event.target.value)}><option value="">Selecione</option>{analyses.map((analysis) => <option key={analysis.id} value={analysis.id}>v{analysis.version_number ?? 1} — {analysis.title}</option>)}</select></label>
      {activeAnalysis ? <div className="analysis-identity"><strong>{activeAnalysis.analysis_type}</strong><span>Revisão: {activeAnalysis.review_status ?? 'draft'}</span><code>{activeAnalysis.result_signature?.slice(0, 14) || 'assinatura pendente'}…</code></div> : null}
    </div>

    <div className="statistics-advanced-grid">
      <article className="panel">
        <h2>Análise de sensibilidade</h2>
        <p>Compara casos completos, exclusão determinística de outliers, winsorização e método alternativo.</p>
        <button disabled={!analysisId} onClick={() => void runSensitivity()} type="button">Executar cenários</button>
        <div className="advanced-result-list">{sensitivity.map((run) => <div className={run.conclusion_changed ? 'changed' : ''} key={run.id}><strong>{scenarioLabels[run.scenario_key] ?? run.scenario_key}</strong><span>{run.analysis_type}</span><b>{run.conclusion_changed ? 'Conclusão mudou' : 'Conclusão estável'}</b></div>)}</div>
      </article>

      <article className="panel">
        <h2>Comparador de métodos</h2>
        <p>Executa alternativas paramétricas e não paramétricas usando os mesmos dados e parâmetros.</p>
        <button disabled={!analysisId} onClick={() => void compare()} type="button">Comparar métodos</button>
        {comparisons[0] ? <div className="comparison-result"><strong>{comparisons[0].conclusions_consistent ? 'Conclusões consistentes' : 'Conclusões divergentes'}</strong><p>{comparisons[0].recommendation}</p><small>{comparisons[0].methods.join(' × ')}</small></div> : null}
      </article>

      <article className="panel">
        <h2>Versão e scripts</h2>
        <p>Preserve a execução atual e gere código equivalente com o checksum do dataset.</p>
        <div className="button-row"><button disabled={!analysisId} onClick={() => void createVersion()} type="button">Criar nova versão</button><button disabled={!analysisId} onClick={() => void downloadScript('python')} type="button">Baixar Python</button><button disabled={!analysisId} onClick={() => void downloadScript('r')} type="button">Baixar R</button></div>
      </article>

      <article className="panel">
        <h2>Revisão colaborativa</h2>
        <div className="button-row"><button disabled={!analysisId} onClick={() => void updateReviewStatus('in_review')} type="button">Enviar para revisão</button><button disabled={!analysisId} onClick={() => void updateReviewStatus('approved')} type="button">Aprovar</button></div>
        <label>Comentário<textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Ex.: justificar o uso do teste de Welch." /></label>
        <button disabled={!analysisId || comment.trim().length < 3} onClick={() => void addComment()} type="button">Comentar</button>
        <div className="review-comment-list">{comments.map((item) => <div key={item.id}><p>{item.body}</p><span>{item.status}</span>{item.status !== 'resolved' ? <button onClick={() => void resolveComment(item.id)} type="button">Resolver</button> : null}</div>)}</div>
      </article>
    </div>

    <article className="panel sample-size-panel">
      <div><h2>Planejamento amostral</h2><p>Estimativa orientativa; não substitui a avaliação metodológica do desenho da pesquisa.</p></div>
      <div className="sample-size-form"><label>Título<input value={planTitle} onChange={(event) => setPlanTitle(event.target.value)} /></label><label>Desenho<select value={design} onChange={(event) => setDesign(event.target.value)}><option value="paired">Pareado</option><option value="independent">Dois grupos</option><option value="correlation">Correlação</option><option value="proportion">Proporções</option></select></label><label>Efeito esperado<input min="0.01" step="0.05" type="number" value={effectSize} onChange={(event) => setEffectSize(event.target.value)} /></label><label>Poder<input min="0.51" max="0.99" step="0.01" type="number" value={power} onChange={(event) => setPower(event.target.value)} /></label><button onClick={() => void createPlan()} type="button">Calcular</button></div>
      <div className="sample-plan-list">{plans.slice(0, 5).map((plan) => <div key={plan.id}><strong>{plan.title}</strong><span>{plan.design} · efeito {plan.expected_effect_size}</span><b>{String(plan.result.recommendation ?? plan.result.total_participants ?? '—')} participantes recomendados</b></div>)}</div>
    </article>

    <div className="statistics-advanced-grid exports-grid">
      <article className="panel">
        <h2>Gráficos exportáveis</h2>
        <p>Os arquivos usam o mesmo snapshot exibido no programa e inserido no relatório.</p>
        <div className="report-export-list">{charts.map((chart) => <div key={chart.id}><span><strong>{chart.title}</strong><small>{chart.chart_type} · {chart.alt_text}</small></span><div className="button-row"><button onClick={() => void downloadChart(chart, 'png')} type="button">PNG</button><button onClick={() => void downloadChart(chart, 'svg')} type="button">SVG</button><button onClick={() => void downloadChart(chart, 'pdf')} type="button">PDF</button></div></div>)}{!charts.length ? <p className="muted">Crie um gráfico na tela principal do Laboratório Estatístico.</p> : null}</div>
      </article>
      <article className="panel">
        <h2>Relatórios exportáveis</h2>
        <p>HTML para revisão, PDF para distribuição e DOCX para edição acadêmica.</p>
        <div className="report-export-list">{reports.map((report) => <div key={report.id}><span><strong>{report.title}</strong><small>v{report.version_number} · {report.review_status}</small></span><div className="button-row"><button onClick={() => void downloadReport(report, 'html')} type="button">HTML</button><button onClick={() => void downloadReport(report, 'pdf')} type="button">PDF</button><button onClick={() => void downloadReport(report, 'docx')} type="button">DOCX</button><button onClick={() => void createReportRevision(report)} type="button">Nova versão</button></div></div>)}{!reports.length ? <p className="muted">Crie um relatório na tela principal do Laboratório Estatístico.</p> : null}</div>
      </article>
    </div>
  </section>
}
