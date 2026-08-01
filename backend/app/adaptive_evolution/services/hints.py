from __future__ import annotations

from collections.abc import Iterable

from ..enums import HINT_LEVEL_ORDER, HintLevel
from ..models import GraduatedHint
from ..schemas import HintSelectionInput, HintSelectionResult


def select_next_hint(
    hints: Iterable[GraduatedHint],
    context: HintSelectionInput,
) -> HintSelectionResult:
    used = {str(item) for item in context.used_hint_ids}
    eligible = [
        hint
        for hint in hints
        if str(hint.id) not in used
        and hint.level_order <= context.max_level_order
        and hint.status in {"PUBLISHED", "APPROVED", "ACTIVE"}
    ]
    eligible.sort(key=lambda item: (item.level_order, item.version))

    if not eligible:
        return HintSelectionResult(
            selected_hint_id=None,
            selected_level=None,
            reason="Não há novas pistas elegíveis para esta tentativa.",
            exhausted=True,
        )

    reason = "solicitação manual do estudante"
    if context.accessibility_required:
        reason = "apoio de acessibilidade configurado"
    elif context.incorrect_attempts > 0:
        reason = f"{context.incorrect_attempts} tentativa(s) incorreta(s)"
    elif context.elapsed_seconds >= 120:
        reason = "tempo prolongado sem conclusão"
    elif not context.requested_manually:
        reason = "regra adaptativa da atividade"

    selected = eligible[0]
    try:
        level = HintLevel(selected.level)
    except ValueError:
        level = min(HINT_LEVEL_ORDER, key=lambda item: abs(HINT_LEVEL_ORDER[item] - selected.level_order))

    return HintSelectionResult(
        selected_hint_id=selected.id,
        selected_level=level,
        reason=reason,
        exhausted=False,
    )
