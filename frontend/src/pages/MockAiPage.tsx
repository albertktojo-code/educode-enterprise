import { FormEvent, useState } from 'react'

import { api } from '../lib/api'

type TextResponse = { text: string; provider: string }
type EmbeddingResponse = {
  embedding: number[]
  dimensions: number
  provider: string
}

export function MockAiPage() {
  const [prompt, setPrompt] = useState(
    'Crie uma introdução sobre decomposição no Pensamento Computacional.',
  )
  const [context, setContext] = useState('BNCC\nEnsino Fundamental\nHQ educativa')
  const [textResult, setTextResult] = useState<TextResponse | null>(null)
  const [embeddingText, setEmbeddingText] = useState(
    'Pensamento Computacional aplicado à educação',
  )
  const [embedding, setEmbedding] = useState<EmbeddingResponse | null>(null)
  const [error, setError] = useState('')
  const [loadingText, setLoadingText] = useState(false)
  const [loadingEmbedding, setLoadingEmbedding] = useState(false)

  async function generateText(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoadingText(true)
    try {
      setTextResult(
        await api<TextResponse>('/mock-ai/generate', {
          method: 'POST',
          body: JSON.stringify({
            prompt,
            context: context
              .split('\n')
              .map((item) => item.trim())
              .filter(Boolean),
          }),
        }),
      )
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha na IA mock.')
    } finally {
      setLoadingText(false)
    }
  }

  async function generateEmbedding(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoadingEmbedding(true)
    try {
      setEmbedding(
        await api<EmbeddingResponse>('/mock-ai/embed', {
          method: 'POST',
          body: JSON.stringify({ text: embeddingText }),
        }),
      )
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha no embedding mock.')
    } finally {
      setLoadingEmbedding(false)
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 01 — IA DESACOPLADA</span>
          <h1>Laboratório de IA mock</h1>
          <p>
            Teste geração de texto e embeddings determinísticos sem consumir
            OpenAI ou qualquer serviço externo.
          </p>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}

      <div className="two-columns wide-left">
        <form className="panel form-grid" onSubmit={generateText}>
          <h2>Geração de texto</h2>
          <label>
            Prompt
            <textarea rows={6} value={prompt} onChange={(event) => setPrompt(event.target.value)} required />
          </label>
          <label>
            Contexto, um item por linha
            <textarea rows={5} value={context} onChange={(event) => setContext(event.target.value)} />
          </label>
          <button className="primary" disabled={loadingText}>
            {loadingText ? 'Gerando...' : 'Gerar resposta mock'}
          </button>
          {textResult ? (
            <div className="result-box">
              <span>{textResult.provider}</span>
              <p>{textResult.text}</p>
              <button type="button" onClick={() => navigator.clipboard.writeText(textResult.text)}>
                Copiar resposta
              </button>
            </div>
          ) : null}
        </form>

        <form className="panel form-grid" onSubmit={generateEmbedding}>
          <h2>Embedding determinístico</h2>
          <label>
            Texto
            <textarea rows={6} value={embeddingText} onChange={(event) => setEmbeddingText(event.target.value)} required />
          </label>
          <button className="primary" disabled={loadingEmbedding}>
            {loadingEmbedding ? 'Calculando...' : 'Gerar embedding mock'}
          </button>
          {embedding ? (
            <div className="result-box">
              <span>{embedding.provider}</span>
              <strong>{embedding.dimensions} dimensões</strong>
              <code>{JSON.stringify(embedding.embedding.slice(0, 16))}...</code>
              <button type="button" onClick={() => navigator.clipboard.writeText(JSON.stringify(embedding.embedding))}>
                Copiar vetor completo
              </button>
            </div>
          ) : null}
        </form>
      </div>
    </section>
  )
}
