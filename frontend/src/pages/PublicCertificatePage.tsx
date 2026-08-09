import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { API_URL, api } from '../lib/api'
import './publicCertificate.css'

interface PublicCertificateEvidence { title: string; assignment_type: string; percentage: number }
interface PublicCertificate {
  title: string
  description: string
  verification_code: string
  status: string
  issued_at: string
  revoked_at: string | null
  revocation_reason: string
  student_name: string
  issuer_name: string
  organization_name: string
  evidence: PublicCertificateEvidence[]
}

function date(value: string | null): string {
  return value
    ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'long' }).format(new Date(value))
    : 'não informada'
}

export function PublicCertificatePage() {
  const { verificationCode = '' } = useParams()
  const navigate = useNavigate()
  const normalizedCode = verificationCode.trim().toUpperCase()
  const [certificate, setCertificate] = useState<PublicCertificate | null>(null)
  const [loading, setLoading] = useState(Boolean(normalizedCode))
  const [error, setError] = useState('')

  useEffect(() => {
    if (!normalizedCode) {
      setCertificate(null)
      setLoading(false)
      setError('')
      return
    }
    let active = true
    setLoading(true)
    setError('')
    void api.get<PublicCertificate>(`/student/portfolio/certificates/verify/${encodeURIComponent(normalizedCode)}`, { auth: false })
      .then((value) => { if (active) setCertificate(value) })
      .catch((reason: unknown) => {
        if (!active) return
        setCertificate(null)
        setError(reason instanceof Error ? reason.message : 'Não foi possível verificar este certificado.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [normalizedCode])

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const code = String(new FormData(event.currentTarget).get('code') ?? '').trim().toUpperCase()
    if (code) navigate(`/credentials/verificar/${encodeURIComponent(code)}`)
  }

  const qrUrl = certificate
    ? `${API_URL}/student/portfolio/certificates/verify/${encodeURIComponent(certificate.verification_code)}/qr?origin=${encodeURIComponent(window.location.origin)}`
    : ''

  return (
    <main className="public-certificate">
      <header className="public-certificate-topbar"><a href="/">EC <strong>EduCode Credentials</strong></a><span>Verificação pública</span></header>
      <section className="public-certificate-search" aria-label="Consultar certificado">
        <form onSubmit={search}><label htmlFor="public-certificate-code">Código de verificação</label><div><input id="public-certificate-code" name="code" defaultValue={normalizedCode} minLength={8} maxLength={32} required autoComplete="off" placeholder="Digite o código do certificado" /><button type="submit">Verificar</button></div></form>
      </section>

      <p className="public-certificate-status" aria-live="polite">{loading ? 'Consultando registro oficial…' : error}</p>
      {!normalizedCode && !loading ? <section className="public-certificate-intro"><span aria-hidden="true">◆</span><h1>Confirme uma conquista EduCode</h1><p>Digite o código impresso no certificado ou leia o QR Code para consultar seu estado e as evidências vinculadas.</p></section> : null}

      {certificate ? <article className={`public-certificate-sheet ${certificate.status === 'revoked' ? 'is-revoked' : ''}`}>
        <div className="public-certificate-seal" aria-hidden="true">EC</div>
        <header><span>EDUCODE CREDENTIALS</span><p>Certificado verificável de aprendizagem</p></header>
        <div className="public-certificate-result" role="status"><strong>{certificate.status === 'active' ? '✓ CERTIFICADO VÁLIDO' : '× CERTIFICADO REVOGADO'}</strong><small>Consulta realizada no registro oficial do EduCode</small></div>
        <section className="public-certificate-content"><p>Certificamos que</p><h1>{certificate.student_name}</h1><p>recebeu o reconhecimento</p><h2>{certificate.title}</h2><p>{certificate.description}</p></section>
        <dl><div><dt>Instituição emissora</dt><dd>{certificate.organization_name}</dd></div><div><dt>Emitido por</dt><dd>{certificate.issuer_name}</dd></div><div><dt>Data de emissão</dt><dd>{date(certificate.issued_at)}</dd></div><div><dt>Código</dt><dd><code>{certificate.verification_code}</code></dd></div></dl>
        <section className="public-certificate-evidence"><h3>Evidências vinculadas</h3><ul>{certificate.evidence.map((item) => <li key={`${item.title}-${item.assignment_type}`}><div><strong>{item.title}</strong><small>{item.assignment_type.replaceAll('_', ' ')}</small></div><b>{item.percentage.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%</b></li>)}</ul></section>
        {certificate.status === 'revoked' ? <aside><strong>Revogado em {date(certificate.revoked_at)}</strong><p>{certificate.revocation_reason}</p></aside> : null}
        <footer><div><img src={qrUrl} alt={`QR Code para verificar o certificado ${certificate.verification_code}`} /><small>Leia para verificar</small></div><p>Este documento referencia evidências preservadas no EduCode. A consulta pública não expõe respostas, e-mail ou dados acadêmicos adicionais.</p></footer>
        <div className="public-certificate-actions"><button type="button" onClick={() => window.print()}>Imprimir ou salvar em PDF</button><a href="/">Acessar o EduCode</a></div>
      </article> : null}
    </main>
  )
}
