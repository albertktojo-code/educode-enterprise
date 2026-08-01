from __future__ import annotations

import random
from statistics import fmean

from ..schemas import AssemblySimulationInput, AssemblySimulationResult


def assemble_assessment(payload: AssemblySimulationInput) -> AssemblySimulationResult:
    rng = random.Random(payload.seed)
    allowed = set(payload.allowed_question_types)
    candidates = [
        item for item in payload.candidates
        if not allowed or item.question_type in allowed
    ]
    rng.shuffle(candidates)

    required = set(payload.required_skill_codes)
    selected = []
    covered: set[str] = set()

    # Primeira passagem: maximiza cobertura de habilidades obrigatorias.
    for item in sorted(
        candidates,
        key=lambda candidate: (
            -len(required.intersection(candidate.skill_codes)),
            abs(candidate.difficulty - payload.target_average_difficulty),
            str(candidate.question_version_id),
        ),
    ):
        if len(selected) >= payload.target_count:
            break
        new_skills = required.intersection(item.skill_codes) - covered
        if new_skills:
            selected.append(item)
            covered.update(item.skill_codes)

    # Segunda passagem: completa o tamanho aproximando a dificuldade alvo.
    selected_ids = {item.question_version_id for item in selected}
    remaining = [item for item in candidates if item.question_version_id not in selected_ids]
    remaining.sort(
        key=lambda candidate: (
            abs(candidate.difficulty - payload.target_average_difficulty),
            str(candidate.question_version_id),
        )
    )
    for item in remaining:
        if len(selected) >= payload.target_count:
            break
        selected.append(item)
        covered.update(item.skill_codes)

    warnings: list[str] = []
    if len(selected) < payload.target_count:
        warnings.append("Quantidade de candidatos insuficiente para atingir o total solicitado.")
    missing = sorted(required - covered)
    if missing:
        warnings.append("Nem todas as habilidades obrigatorias foram cobertas.")

    average = fmean(item.difficulty for item in selected) if selected else 0.0
    return AssemblySimulationResult(
        selected_question_ids=[item.question_version_id for item in selected],
        selected_count=len(selected),
        average_difficulty=round(average, 4),
        covered_skill_codes=sorted(covered),
        missing_skill_codes=missing,
        total_score=round(sum(item.max_score for item in selected), 4),
        deterministic_seed=payload.seed,
        warnings=warnings,
    )
