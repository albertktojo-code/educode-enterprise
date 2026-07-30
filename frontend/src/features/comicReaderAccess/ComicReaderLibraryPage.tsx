import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../../contexts/AuthContext";
import { comicReaderApi } from "./api";
import type { ReaderRelease } from "./types";
import "./styles.css";

export function ComicReaderLibraryPage() {
  const [releases, setReleases] = useState<ReaderRelease[]>([]);
  const [message, setMessage] = useState("Carregando HQs...");
  const [busyId, setBusyId] = useState<string | null>(null);
  const navigate = useNavigate();
  const { user } = useAuth();
  const role = user?.memberships[0]?.role;
  const canPresent = role !== "member";

  useEffect(() => {
    comicReaderApi
      .releases()
      .then((items) => {
        setReleases(items);
        setMessage(items.length ? "" : "Nenhuma HQ publicada está disponível.");
      })
      .catch((error: Error) => setMessage(error.message));
  }, []);

  async function present(release: ReaderRelease) {
    setBusyId(release.id);
    try {
      const presentation = await comicReaderApi.createPresentation(
        release.id,
        `Apresentação — ${release.release_name}`,
      );
      navigate(`/teacher/comic-reader/presentations/${presentation.id}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao criar apresentação.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="reader-library">
      <header className="page-header">
        <div>
          <span className="eyebrow">SPRINT 16.5</span>
          <h1>Leitor interativo de HQs</h1>
          <p>Leia, retome sua posição ou apresente a HQ em sala.</p>
        </div>
        <Link to="/comic-reader/join">Entrar com código</Link>
      </header>

      {message ? <div className="inline-message">{message}</div> : null}

      <div className="reader-release-grid">
        {releases.map((release) => (
          <article className="panel reader-release-card" key={release.id}>
            <span>Release {release.release_number}</span>
            <h2>{release.release_name}</h2>
            <p>{release.release_notes || "HQ publicada pelo EduCode."}</p>
            <div className="button-row">
              <Link to={`/comic-reader/releases/${release.id}`}>Ler HQ</Link>
              {canPresent ? (
                <button
                  type="button"
                  disabled={busyId === release.id}
                  onClick={() => void present(release)}
                >
                  {busyId === release.id ? "Preparando..." : "Apresentar"}
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
