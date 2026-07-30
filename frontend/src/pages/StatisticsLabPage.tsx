import { useEffect, useMemo, useState } from 'react'
import { api, apiBlob } from '../lib/api'
import type { StatisticalAnalysis, StatisticalDataset, StatisticalStudy, TestRecommendation } from '../types/statistics'

const testLabels: Record<string,string> = {
  descriptive:'Estatística descritiva', paired_t:'Teste t pareado', independent_t:'Teste t independente', welch_t:'Teste t de Welch', wilcoxon:'Wilcoxon', mann_whitney:'Mann–Whitney', anova:'ANOVA', kruskal_wallis:'Kruskal–Wallis', pearson:'Pearson', spearman:'Spearman', cronbach_alpha:'Alfa de Cronbach', chi_square:'Qui-quadrado'
}


function MeanChart({ analysis }: { analysis: StatisticalAnalysis }) {
  const entries = Object.entries(analysis.descriptive_results)
    .filter(([key, item]) => key !== 'difference' && typeof item === 'object' && item !== null && typeof (item as { mean?: unknown }).mean === 'number')
    .map(([label, item]) => ({ label, mean: (item as { mean: number }).mean }))
    .slice(0, 8)
  if (!entries.length) return null
  const max = Math.max(...entries.map((item) => item.mean), 1)
  const slot = 300 / entries.length
  return <figure className="statistics-inline-chart">
    <svg viewBox="0 0 380 230" role="img" aria-label={`Comparação das médias: ${entries.map((item) => `${item.label} ${item.mean.toFixed(1)}`).join(', ')}`}>
      <line x1="40" y1="185" x2="355" y2="185" stroke="currentColor" />
      {entries.map((item, index) => {
        const height = (item.mean / max) * 140
        const x = 48 + index * slot
        const width = Math.max(24, slot - 14)
        return <g key={item.label}>
          <rect x={x} y={185-height} width={width} height={height} rx="6" />
          <text x={x+width/2} y="208" textAnchor="middle">{item.label.slice(0, 10)}</text>
          <text x={x+width/2} y={175-height} textAnchor="middle">{item.mean.toFixed(1)}</text>
        </g>
      })}
    </svg>
    <figcaption>Médias do dataset congelado. O relatório utiliza o mesmo snapshot, filtros e política de tentativas.</figcaption>
  </figure>
}

export function StatisticsLabPage() {
  const [studies,setStudies]=useState<StatisticalStudy[]>([])
  const [selected,setSelected]=useState<string>('')
  const [datasets,setDatasets]=useState<StatisticalDataset[]>([])
  const [analyses,setAnalyses]=useState<StatisticalAnalysis[]>([])
  const [title,setTitle]=useState('Estudo pré e pós-teste')
  const [question,setQuestion]=useState('Os estudantes melhoraram após a intervenção?')
  const [datasetTitle,setDatasetTitle]=useState('Dataset congelado')
  const [manualRows,setManualRows]=useState('[{"student_id":"EST-0001","pre":55,"post":78},{"student_id":"EST-0002","pre":62,"post":81},{"student_id":"EST-0003","pre":48,"post":70},{"student_id":"EST-0004","pre":64,"post":82}]')
  const [analysisType,setAnalysisType]=useState('paired_t')
  const [message,setMessage]=useState('')
  const [recommendation,setRecommendation]=useState<TestRecommendation|null>(null)
  const activeStudy=useMemo(()=>studies.find(s=>s.id===selected),[studies,selected])

  async function loadStudies(){ const data=await api<StatisticalStudy[]>('/statistics/studies'); setStudies(data); if(!selected&&data[0]) setSelected(data[0].id) }
  async function loadStudy(id:string){ if(!id){setDatasets([]);setAnalyses([]);return}; const [d,a]=await Promise.all([api<StatisticalDataset[]>(`/statistics/studies/${id}/datasets`),api<StatisticalAnalysis[]>(`/statistics/studies/${id}/analyses`)]);setDatasets(d);setAnalyses(a) }
  useEffect(()=>{void loadStudies().catch((e:Error)=>setMessage(e.message))},[])
  useEffect(()=>{void loadStudy(selected).catch((e:Error)=>setMessage(e.message))},[selected])

  async function createStudy(){ try{const study=await api<StatisticalStudy>('/statistics/studies',{method:'POST',body:JSON.stringify({title,research_question:question,null_hypothesis:'Não existe diferença entre os momentos.',alternative_hypothesis:'Existe diferença entre os momentos.',study_design:'pre_post',significance_level:0.05})});await loadStudies();setSelected(study.id);setMessage('Estudo criado.')}catch(e){setMessage((e as Error).message)} }
  async function freezeDataset(){ if(!selected)return; try{const rows=JSON.parse(manualRows) as Array<Record<string,unknown>>;await api(`/statistics/studies/${selected}/datasets`,{method:'POST',body:JSON.stringify({title:datasetTitle,manual_rows:rows,attempt_policy:'first',anonymized:true})});await loadStudy(selected);setMessage('Dataset congelado e identificado por checksum.')}catch(e){setMessage((e as Error).message)} }
  async function runAnalysis(){if(!selected||!datasets[0])return;try{await api(`/statistics/studies/${selected}/analyses`,{method:'POST',body:JSON.stringify({dataset_id:datasets[0].id,title:testLabels[analysisType]??analysisType,analysis_type:analysisType,parameters:{x_key:'pre',y_key:'post',value_key:'score',group_key:'group'}})});await loadStudy(selected);setMessage('Análise executada.')}catch(e){setMessage((e as Error).message)} }
  async function recommend(){try{const r=await api<TestRecommendation>('/statistics/recommend-test',{method:'POST',body:JSON.stringify({goal:'pre_post',same_participants:true,variable_type:'numeric',group_count:1})});setRecommendation(r);setAnalysisType(r.recommended_test)}catch(e){setMessage((e as Error).message)} }
  async function createChart(a:StatisticalAnalysis){try{await api(`/statistics/analyses/${a.id}/charts`,{method:'POST',body:JSON.stringify({chart_type:'paired',title:'Evolução pré e pós-teste',description:'Valores individuais do dataset congelado.',x_key:'student_id',y_key:'post',include_in_report:true})});setMessage('Gráfico criado e pronto para o relatório.')}catch(e){setMessage((e as Error).message)} }
  async function createReport(a:StatisticalAnalysis){try{const r=await api<{id:string}>(`/statistics/analyses/${a.id}/reports`,{method:'POST',body:JSON.stringify({report_type:'statistical',title:`Relatório — ${a.title}`,include_charts:true,include_assumptions:true,include_limitations:true})});const blob=await apiBlob(`/statistics/reports/${r.id}/html`);window.open(URL.createObjectURL(blob),'_blank');setMessage('Relatório criado como rascunho para revisão.')}catch(e){setMessage((e as Error).message)} }

  return <section>
    <header className="page-header statistics-header"><div><span className="eyebrow">LABORATÓRIO ESTATÍSTICO</span><h1>Análises educacionais reproduzíveis</h1><p>Congele os dados, escolha o teste com orientação, visualize gráficos e gere relatórios revisáveis.</p></div><div className="button-row"><button className="secondary-button" onClick={()=>void recommend()} type="button">Recomendar teste</button><a className="secondary-button" href="/ia?module=statistics&action=draft_report">Interpretar com IA</a></div></header>
    {message?<div className="inline-message">{message}</div>:null}
    {recommendation?<article className="statistics-recommendation"><strong>Recomendação: {testLabels[recommendation.recommended_test]??recommendation.recommended_test}</strong><p>{recommendation.rationale}</p><small>Colunas necessárias: {recommendation.required_columns.join(', ')}</small></article>:null}
    <div className="statistics-grid">
      <article className="panel"><h2>1. Novo estudo</h2><label>Título<input value={title} onChange={e=>setTitle(e.target.value)}/></label><label>Pergunta de pesquisa<textarea value={question} onChange={e=>setQuestion(e.target.value)}/></label><button className="primary-button" onClick={()=>void createStudy()} type="button">Criar estudo</button></article>
      <article className="panel"><h2>2. Estudos</h2><select value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Selecione</option>{studies.map(s=><option key={s.id} value={s.id}>{s.title}</option>)}</select>{activeStudy?<div className="study-summary"><strong>{activeStudy.title}</strong><span>α = {activeStudy.significance_level}</span><p>{activeStudy.research_question}</p></div>:null}</article>
      <article className="panel"><h2>3. Congelar dataset</h2><label>Nome<input value={datasetTitle} onChange={e=>setDatasetTitle(e.target.value)}/></label><label>Dados JSON<textarea className="code-area" value={manualRows} onChange={e=>setManualRows(e.target.value)}/></label><button disabled={!selected} onClick={()=>void freezeDataset()} type="button">Congelar dados</button>{datasets.map(d=><div className="dataset-chip" key={d.id}><strong>{d.title}</strong><small>{d.participant_count} participantes · {d.row_count} linhas</small><code>{d.dataset_checksum.slice(0,12)}…</code></div>)}</article>
      <article className="panel"><h2>4. Executar análise</h2><label>Teste<select value={analysisType} onChange={e=>setAnalysisType(e.target.value)}>{Object.entries(testLabels).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><button className="primary-button" disabled={!datasets.length} onClick={()=>void runAnalysis()} type="button">Executar análise</button></article>
    </div>
    <article className="panel statistics-results"><h2>Resultados</h2>{analyses.map(a=><article className="analysis-result" key={a.id}><div><span>{testLabels[a.analysis_type]??a.analysis_type}</span><h3>{a.title}</h3><p>{a.interpretation_teacher}</p><code>{a.interpretation_researcher}</code></div><dl><div><dt>p</dt><dd>{String(a.test_results.p_value??'—')}</dd></div><div><dt>Efeito</dt><dd>{String(a.effect_size.value??'—')}</dd></div><div><dt>Status</dt><dd>{a.status}</dd></div></dl><MeanChart analysis={a}/><div className="analysis-actions"><button onClick={()=>void createChart(a)} type="button">Criar gráfico</button><button onClick={()=>void createReport(a)} type="button">Gerar relatório</button></div>{a.limitations.length?<ul>{a.limitations.map(l=><li key={l}>{l}</li>)}</ul>:null}</article>)}{!analyses.length?<p className="muted">Nenhuma análise executada.</p>:null}</article>
  </section>
}
