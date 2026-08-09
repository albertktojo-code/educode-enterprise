import { useEffect, useState, type FormEvent } from 'react'

import {
  schoolAdmissionsApi,
  type EnrollmentApplication,
  type EnrollmentContract,
  type EnrollmentContractTemplate,
  type EnrollmentGuardianOption,
  type SchoolUnit,
} from '../features/schoolAdmissions/api'

import './schoolContracts.css'

const defaultTemplate = `CONTRATO DE MATRÍCULA

Responsável: {{nome_responsavel}}
Estudante: {{nome_aluno}}
Unidade: {{unidade_escolar}}
Turma: {{turma}} — {{serie}} — {{turno}}
Ano letivo: {{ano_letivo}}

Declaro ciência das condições institucionais apresentadas neste contrato.
Gerado em {{data_geracao}}.`

const statusLabels: Record<string, string> = {
  generated: 'Aguardando aceite', accepted: 'Aceito', voided: 'Cancelado',
}

export function SchoolContractsPage() {
  const [applications, setApplications] = useState<EnrollmentApplication[]>([])
  const [templates, setTemplates] = useState<EnrollmentContractTemplate[]>([])
  const [contracts, setContracts] = useState<EnrollmentContract[]>([])
  const [units, setUnits] = useState<SchoolUnit[]>([])
  const [guardians, setGuardians] = useState<EnrollmentGuardianOption[]>([])
  const [applicationId, setApplicationId] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  async function load() {
    const [dashboard, templateItems, contractItems, unitItems] = await Promise.all([
      schoolAdmissionsApi.dashboard(), schoolAdmissionsApi.contractTemplates(),
      schoolAdmissionsApi.contracts(), schoolAdmissionsApi.units(),
    ])
    setApplications(dashboard.applications)
    setTemplates(templateItems)
    setContracts(contractItems)
    setUnits(unitItems)
  }

  useEffect(() => {
    void load()
      .catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Não foi possível carregar contratos.'))
      .finally(() => setLoading(false))
  }, [])

  async function chooseApplication(id: string) {
    setApplicationId(id)
    setGuardians([])
    if (!id) return
    try { setGuardians(await schoolAdmissionsApi.applicationGuardians(id)) }
    catch (error) { setNotice(error instanceof Error ? error.message : 'Não foi possível carregar responsáveis.') }
  }

  async function createTemplate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    setBusy(true)
    try {
      await schoolAdmissionsApi.createContractTemplate({
        school_unit_id: String(data.get('school_unit_id') ?? '') || null,
        code: String(data.get('code') ?? '').toLowerCase(),
        name: String(data.get('name') ?? ''),
        body_template: String(data.get('body_template') ?? ''),
      })
      form.reset()
      setNotice('Template criado.')
      await load()
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Não foi possível criar o template.') }
    finally { setBusy(false) }
  }

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true)
    try {
      await schoolAdmissionsApi.generateContract(applicationId, {
        template_id: String(data.get('template_id')),
        guardian_profile_id: String(data.get('guardian_profile_id')),
      })
      setNotice('Contrato gerado como versão imutável.')
      await load()
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Não foi possível gerar o contrato.') }
    finally { setBusy(false) }
  }

  async function voidContract(contractId: string) {
    const reason = window.prompt('Informe o motivo do cancelamento do contrato:')?.trim()
    if (!reason) return
    setBusy(true)
    try {
      await schoolAdmissionsApi.voidContract(contractId, reason)
      setNotice('Contrato cancelado.')
      await load()
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Não foi possível cancelar o contrato.') }
    finally { setBusy(false) }
  }

  return <main className="school-secretariat-module" aria-busy={loading}>
    <div className="school-secretariat-heading"><div><span>CONTRATOS</span><h2>Contratos de matrícula</h2></div><p>Templates institucionais, versões imutáveis e aceite digital rastreável.</p></div>
    <p className="school-secretariat-notice" aria-live="polite">{notice}</p>
    <div className="school-secretariat-columns">
      <form className="panel" onSubmit={(event) => void createTemplate(event)}>
        <h3>Novo template</h3>
        <label>Unidade (opcional)<select name="school_unit_id"><option value="">Toda a organização</option>{units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}</select></label>
        <label>Código<input name="code" pattern="[a-z0-9_-]+" required /></label>
        <label>Nome<input name="name" required /></label>
        <label>Conteúdo<textarea name="body_template" rows={12} defaultValue={defaultTemplate} required /></label>
        <small>Variáveis: nome_aluno, nome_responsavel, unidade_escolar, turma, serie, turno, ano_letivo e data_geracao.</small>
        <button disabled={busy}>Criar template</button>
      </form>
      <form className="panel" onSubmit={(event) => void generate(event)}>
        <h3>Gerar contrato</h3>
        <label>Pré-matrícula<select value={applicationId} onChange={(event) => void chooseApplication(event.target.value)} required><option value="">Selecione</option>{applications.map((item) => <option key={item.id} value={item.id}>{item.student_name} · {item.classroom_name}</option>)}</select></label>
        <label>Template<select name="template_id" required><option value="">Selecione</option>{templates.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Responsável signatário<select name="guardian_profile_id" required disabled={!applicationId}><option value="">Selecione</option>{guardians.map((item) => <option key={item.id} value={item.id}>{item.full_name} · {item.email}</option>)}</select></label>
        <button disabled={busy || !applicationId}>Gerar nova versão</button>
      </form>
    </div>
    <section className="school-document-list" aria-label="Contratos gerados">
      {!contracts.length && !loading ? <p className="panel">Nenhum contrato gerado.</p> : contracts.map((contract) => <article className="panel" key={contract.id}>
        <div className="school-document-title"><div><strong>{contract.template_name}</strong><small>{contract.guardian_name || 'Responsável não identificado'}</small></div><span data-status={contract.status}>{statusLabels[contract.status] ?? contract.status}</span></div>
        {contract.versions.map((version) => <details key={version.id}><summary>Versão {version.version_number} · SHA-256 {version.content_sha256.slice(0, 12)}…</summary><pre className="school-contract-preview">{version.rendered_content}</pre></details>)}
        {contract.acceptance ? <p><strong>Aceito por {contract.acceptance.accepted_name}</strong> em {new Date(contract.acceptance.accepted_at).toLocaleString('pt-BR')}</p> : null}
        {contract.status === 'generated' ? <button type="button" disabled={busy} onClick={() => void voidContract(contract.id)}>Cancelar contrato</button> : null}
        {contract.void_reason ? <small>Motivo: {contract.void_reason}</small> : null}
      </article>)}
    </section>
  </main>
}
