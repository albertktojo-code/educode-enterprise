import { FormEvent, useState } from "react";
import { assessmentAnalyticsApi } from "./api";
import "./styles.css";

export function ItemAnalyticsPage() {
  const [result, setResult] = useState<unknown>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    const data = await assessmentAnalyticsApi.simulateItem({
      predicted_difficulty: 0.5, item_scores: [1, 1, 0, 1, 0, 1], total_scores: [90, 80, 45, 75, 40, 70],
      omitted: 0, upper_correct: 3, upper_total: 3, lower_correct: 1, lower_total: 3, minimum_sample: 5,
    });
    setResult(data);
  }
  return <main className="analytics-page"><h1>Análise de itens</h1><p>Simule indicadores antes de publicar uma interpretação institucional.</p><button onClick={submit}>Executar simulação</button><pre>{result === null || result === undefined ? "Nenhuma simulação executada." : JSON.stringify(result, null, 2)}</pre></main>;
}
