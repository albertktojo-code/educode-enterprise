import "./styles.css";

export function InstrumentResultsPage() {
  return (
    <main className="instrument-governance-page">
      <header>
        <p className="eyebrow">Resultados externos</p>
        <h1>Interpretacoes com revisao humana</h1>
        <p>
          Consulte escores brutos, padronizados, classificacoes autorizadas e o grupo normativo utilizado.
        </p>
      </header>
      <section className="governance-card">
        <h2>Regra de seguranca</h2>
        <p>
          Os resultados sao educacionais e descritivos. A plataforma nao produz diagnosticos clinicos ou psicologicos.
        </p>
      </section>
    </main>
  );
}
