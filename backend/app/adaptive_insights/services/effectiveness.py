from __future__ import annotations

from statistics import mean, median

from ..schemas import MaterialEffectivenessInput, MaterialEffectivenessResult


def calculate_material_effectiveness(
    payload: MaterialEffectivenessInput,
) -> MaterialEffectivenessResult:
    observations = payload.observations
    sample_size = len(observations)
    completed = [item for item in observations if item.completed]
    completion_rate = len(completed) / sample_size

    correctness = [item.correct for item in observations if item.correct is not None]
    accuracy_rate = (
        sum(1 for value in correctness if value) / len(correctness)
        if correctness
        else None
    )

    gains = [
        item.score_after - item.score_before
        for item in observations
        if item.score_before is not None and item.score_after is not None
    ]
    average_gain = mean(gains) if gains else None
    median_gain = median(gains) if gains else None
    average_attempts = mean(item.attempts for item in observations)
    average_hints = mean(item.hints_used for item in observations)
    average_duration = mean(item.duration_seconds for item in observations)

    confidence = min(1.0, sample_size / 100)
    warnings = [
        "Análise descritiva: não estabelece causalidade entre o material e o resultado.",
        "Compare grupos e períodos equivalentes antes de decisões institucionais.",
    ]
    if sample_size < 20:
        classification = "EVIDENCIA_INSUFICIENTE"
        warnings.append("Amostra abaixo de 20 observações.")
    elif completion_rate < 0.50:
        classification = "BAIXA_CONCLUSAO"
    elif average_gain is not None and average_gain >= 0.12 and completion_rate >= 0.75:
        classification = "DESEMPENHO_DESCRITIVO_FORTE"
    elif average_gain is not None and average_gain >= 0.04:
        classification = "DESEMPENHO_DESCRITIVO_MODERADO"
    elif accuracy_rate is not None and accuracy_rate < 0.35:
        classification = "REQUER_REVISAO"
    else:
        classification = "DESEMPENHO_DESCRITIVO_ESTAVEL"

    return MaterialEffectivenessResult(
        sample_size=sample_size,
        completion_rate=round(completion_rate, 4),
        accuracy_rate=round(accuracy_rate, 4) if accuracy_rate is not None else None,
        average_gain=round(average_gain, 4) if average_gain is not None else None,
        median_gain=round(median_gain, 4) if median_gain is not None else None,
        average_attempts=round(average_attempts, 4),
        average_hints=round(average_hints, 4),
        average_duration_seconds=round(average_duration, 2),
        confidence=round(confidence, 4),
        classification=classification,
        warnings=warnings,
    )
