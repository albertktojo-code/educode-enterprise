import type { PublicationRelease } from "./types";

export function ReleaseHistory({ releases }: { releases: PublicationRelease[] }) {
  return (
    <section className="crp-card">
      <h2>Historico de publicacao</h2>
      <div className="crp-release-list">
        {releases.map((release) => (
          <article key={release.id}>
            <div>
              <strong>v{release.release_number} · {release.release_name}</strong>
              <small>{release.release_hash.slice(0, 12)}...</small>
            </div>
            <span className={`crp-badge ${release.status.toLowerCase()}`}>{release.status}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
