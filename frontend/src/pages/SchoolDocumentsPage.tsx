import { useEffect, useState, type FormEvent } from 'react'

import {
  schoolAdmissionsApi,
  type EnrollmentApplication,
  type EnrollmentDocumentChecklistItem,
  type EnrollmentDocumentRequirement,
  type SchoolUnit,
} from '../features/schoolAdmissions/api'

const statusLabels: Record<string, string> = {
  submitted: 'Enviado', under_review: 'Em análise', approved: 'Aprovado', rejected: 'Rejeitado',
  illegible: 'Ilegível', expired: 'Vencido', resubmission_requested: 'Reenvio solicitado',
}

export function SchoolDocumentsPage() {
  const [applications, setApplications] = useState<EnrollmentApplication[]>([])
  const [requirements, setRequirements] = useState<EnrollmentDocumentRequirement[]>([])
  const [units, setUnits] = useState<SchoolUnit[]>([])
  const [checklist, setChecklist] = useState<EnrollmentDocumentChecklistItem[]>([])
  const [applicationId, setApplicationId] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  async function loadBase() {
    const [dashboard, requirementItems, unitItems] = await Promise.all([
      schoolAdmissionsApi.dashboard(),
      schoolAdmissionsApi.documentRequirements(),
      schoolAdmissionsApi.units(),
    ])
    setApplications(dashboard.applications)
    setRequirements(requirementItems)
    setUnits(unitItems.filter((item) => item.is_active))
  }

  async function loadChecklist(selectedId = applicationId) {
    if (!selectedId) { setChecklist([]); return }
    setChecklist(await schoolAdmissionsApi.documentChecklist(selectedId))
  }

  useEffect(() => {
    void loadBase()
      .catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Não foi possível carregar documentos.'))
      .finally(() => setLoading(false))
  }, [])

  async function submitRequirement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    setBusy(true)
    try {
      await schoolAdmissionsApi.createDocumentRequirement({
        school_unit_id: String(values.get('school_unit_id') ?? '') || null,
        code: String(values.get('code') ?? '').toLowerCase(),
        name: String(values.get('name') ?? ''),
        description: String(values.get('description') ?? ''),
        is_required: values.get('is_required') === 'on',
        accepted_mime_types: ['application/pdf', 'image/jpeg', 'image/png'],
        max_size_bytes: Number(values.get('max_size_mb')) * 1024 * 1024,
        retention_days: Number(values.get('retention_days')),
      })
      form.reset(); setNotice('Item adicionado ao checklist.'); await loadBase(); await loadChecklist()
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Não foi possível criar o requisito.') } finally { setBusy(false) }
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    const file = values.get('file')
    if (!(file instanceof File) || !file.size) { setNotice('Selecione um arquivo.'); return }
    setBusy(true)
    try {
      await schoolAdmissionsApi.uploadDocument(applicationId, String(values.get('requirement_id')), file)
      form.reset(); setNotice('Documento enviado como nova versão.'); await loadChecklist()
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Não foi possível enviar o documento.') } finally { setBusy(false) }
  }

  async function submitReview(event: FormEvent<HTMLFormElement>, documentId: string) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    setBusy(true)
    try {
      await schoolAdmissionsApi.reviewDocument(documentId, {
        decision: String(values.get('decision')),
        note: String(values.get('note') ?? ''),
      })
      setNotice('Análise registrada no histórico.'); await loadChecklist()
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Não foi possível registrar a análise.') } finally { setBusy(false) }
  }

  async function download(path: string, filename: string) {
    try {
      const blob = await schoolAdmissionsApi.downloadDocument(path)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click()
      URL.revokeObjectURL(url)
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Não foi possível baixar o arquivo.') }
  }

  return <main className="school-secretariat-module" aria-busy={loading}>
    <div className="school-secretariat-heading"><div><span>DOCUMENTOS</span><h2>Checklist e análise</h2></div><p>Arquivos privados, versões imutáveis e decisões auditadas.</p></div>
    <p className="school-secretariat-notice" aria-live="polite">{notice}</p>
    <div className="school-secretariat-columns">
      <form className="panel" onSubmit={(event) => void submitRequirement(event)}>
        <h3>Configurar checklist</h3>
        <label htmlFor="requirement-unit">Unidade (opcional)<select id="requirement-unit" name="school_unit_id"><option value="">Toda a organização</option>{units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}</select></label>
        <label htmlFor="requirement-code">Código<input id="requirement-code" name="code" pattern="[a-z0-9_-]+" required /></label>
        <label htmlFor="requirement-name">Documento<input id="requirement-name" name="name" required /></label>
        <label htmlFor="requirement-description">Orientação<textarea id="requirement-description" name="description" rows={2} /></label>
        <label htmlFor="requirement-size">Limite (MB)<input id="requirement-size" name="max_size_mb" type="number" min={1} max={25} defaultValue={10} /></label>
        <label htmlFor="requirement-retention">Retenção (dias)<input id="requirement-retention" name="retention_days" type="number" min={30} max={36500} defaultValue={1825} /></label>
        <label className="school-secretariat-check"><input name="is_required" type="checkbox" defaultChecked /> Obrigatório</label>
        <button disabled={busy}>Adicionar requisito</button>
      </form>
      <section className="panel">
        <h3>Documentos da matrícula</h3>
        <label htmlFor="document-application">Pré-matrícula<select id="document-application" value={applicationId} onChange={(event) => { setApplicationId(event.target.value); void loadChecklist(event.target.value) }}><option value="">Selecione</option>{applications.map((item) => <option key={item.id} value={item.id}>{item.student_name} · {item.classroom_name}</option>)}</select></label>
        <form onSubmit={(event) => void submitUpload(event)}>
          <label htmlFor="upload-requirement">Tipo<select id="upload-requirement" name="requirement_id" required disabled={!applicationId}><option value="">Selecione</option>{checklist.map((item) => <option key={item.requirement.id} value={item.requirement.id}>{item.requirement.name}</option>)}</select></label>
          <label htmlFor="enrollment-file">Arquivo PDF, JPG ou PNG<input id="enrollment-file" name="file" type="file" accept="application/pdf,image/jpeg,image/png" required /></label>
          <button disabled={busy || !applicationId}>Enviar nova versão</button>
        </form>
      </section>
    </div>
    <section className="school-document-list" aria-label="Checklist documental">
      {applicationId && !checklist.length ? <p className="panel">Nenhum requisito configurado para esta unidade.</p> : checklist.map((item) => <article className="panel" key={item.requirement.id}>
        <div className="school-document-title"><div><strong>{item.requirement.name}</strong><small>{item.requirement.is_required ? 'Obrigatório' : 'Opcional'}</small></div><span data-status={item.document?.status ?? 'missing'}>{item.document ? statusLabels[item.document.status] ?? item.document.status : 'Pendente'}</span></div>
        <p>{item.requirement.description || 'Sem orientação adicional.'}</p>
        {item.document ? <>
          <div className="school-document-versions">{item.document.versions.map((version) => <button type="button" key={version.id} onClick={() => void download(version.download_path, version.original_filename)}>Versão {version.version_number} · {version.original_filename}</button>)}</div>
          <form className="school-document-review" onSubmit={(event) => void submitReview(event, item.document!.id)}><label>Decisão<select name="decision" defaultValue="approved"><option value="approved">Aprovar</option><option value="under_review">Em análise</option><option value="rejected">Rejeitar</option><option value="illegible">Ilegível</option><option value="resubmission_requested">Solicitar reenvio</option></select></label><label>Observação<input name="note" maxLength={2000} /></label><button disabled={busy}>Registrar análise</button></form>
          {item.document.reviews.length ? <details><summary>Histórico ({item.document.reviews.length})</summary><ul>{item.document.reviews.map((review) => <li key={review.id}><strong>{statusLabels[review.decision] ?? review.decision}</strong> · {new Date(review.created_at).toLocaleString('pt-BR')} {review.note && `— ${review.note}`}</li>)}</ul></details> : null}
        </> : <small>Aguardando envio.</small>}
      </article>)}
    </section>
    {!requirements.length && !loading ? <p className="panel">Crie o primeiro requisito para iniciar o checklist.</p> : null}
  </main>
}
