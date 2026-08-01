import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ComicCover } from "../../components/ComicCover";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { useAuth } from "../../contexts/AuthContext";
import { comicReaderApi } from "./api";
import type { ReaderRelease } from "./types";
import "./styles.css";

export function ComicReaderLibraryPage() {
  const [releases, setReleases] = useState<ReaderRelease[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const navigate = useNavigate();
  const { user } = useAuth();
  const role = user?.memberships[0]?.role;
  const canPresent = role !== "member";

  useEffect(() => {
    comicReaderApi
      .releases()
      .then((items) => setReleases(items))
      .catch((caughtError: Error) => setError(caughtError.message))
      .finally(() => setLoading(false));
  }, []);

  const filteredReleases = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase("pt-BR");
    if (!normalizedSearch) return releases;
    return releases.filter(
      (release) =>
        release.release_name.toLocaleLowerCase("pt-BR").includes(normalizedSearch) ||
        release.release_notes.toLocaleLowerCase("pt-BR").includes(normalizedSearch),
    );
  }, [releases, search]);

  async function present(release: ReaderRelease) {
    setBusyId(release.id);
    setError("");
    try {
      const presentation = await comicReaderApi.createPresentation(
        release.id,
        `Apresentação — ${release.release_name}`,
      );
      navigate(`/teacher/comic-reader/presentations/${presentation.id}`);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Falha ao criar apresentação.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="reader-library reader-library--catalog">
      <header className="page-header reader-library-hero">
        <div>
          <span className="eyebrow">BIBLIOTECA EDUCODE</span>
          <h1>Histórias para aprender</h1>
          <p>Descubra HQs publicadas, retome sua leitura e apresente histórias em sala.</p>
        </div>
        <Link className="primary-link" to="/comic-reader/join">Entrar com código</Link>
      </header>

      {error ? <div className="alert error" role="alert">{error}</div> : null}

      <section className="panel reader-library-panel" aria-labelledby="reader-library-title">
        <div className="panel-title-row">
          <div>
            <span className="eyebrow">CATÁLOGO PUBLICADO</span>
            <h2 id="reader-library-title">Escolha sua próxima leitura</h2>
          </div>
          <span className="hq-result-count" aria-live="polite">
            {filteredReleases.length} {filteredReleases.length === 1 ? "história" : "histórias"}
          </span>
        </div>

        <div className="hq-catalog-toolbar reader-catalog-toolbar" role="search">
          <label className="hq-search-field">
            <span className="sr-only">Buscar HQ publicada</span>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="m20 20-4.4-4.4m2.15-5.35a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z" />
            </svg>
            <input
              type="search"
              placeholder="Buscar por título ou assunto"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        </div>

        {loading ? <LoadingState label="Carregando biblioteca de HQs" rows={3} /> : null}

        {!loading && filteredReleases.length ? (
          <div className="reader-release-grid">
            {filteredReleases.map((release) => (
              <article className="reader-release-card" key={release.id}>
                <Link
                  className="reader-release-cover-link"
                  to={`/comic-reader/releases/${release.id}`}
                  aria-label={`Ler ${release.release_name}`}
                >
                  <ComicCover
                    compact
                    title={release.release_name}
                    eyebrow={`Edição ${release.release_number}`}
                    footer="HQ publicada · EduCode"
                    seed={release.id}
                  />
                </Link>
                <div className="reader-release-copy">
                  <span className="status-chip approved">Disponível</span>
                  <h3>{release.release_name}</h3>
                  <p>{release.release_notes || "Uma história pedagógica publicada pelo EduCode."}</p>
                  <div className="reader-release-meta">
                    <span>Edição {release.release_number}</span>
                    <span>
                      {release.published_at
                        ? `Publicada em ${new Intl.DateTimeFormat("pt-BR").format(new Date(release.published_at))}`
                        : "Publicação institucional"}
                    </span>
                  </div>
                  <div className="button-row reader-release-actions">
                    <Link className="primary-link" to={`/comic-reader/releases/${release.id}`}>Ler HQ</Link>
                    {canPresent ? (
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={busyId === release.id}
                        onClick={() => void present(release)}
                      >
                        {busyId === release.id ? "Preparando..." : "Apresentar"}
                      </button>
                    ) : null}
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : null}

        {!loading && !filteredReleases.length ? (
          <EmptyState
            icon={releases.length ? "search" : "folder"}
            title={releases.length ? "Nenhuma história encontrada" : "A biblioteca está pronta para novas histórias"}
            description={
              releases.length
                ? "Tente outro título ou assunto para encontrar a HQ que procura."
                : "Quando uma HQ for revisada e publicada, ela aparecerá aqui para leitura e apresentação."
            }
            action={
              releases.length ? (
                <button type="button" className="secondary-button" onClick={() => setSearch("")}>
                  Limpar busca
                </button>
              ) : (
                <Link className="secondary-button" to="/comic-reader/join">Entrar com código</Link>
              )
            }
          />
        ) : null}
      </section>
    </section>
  );
}
