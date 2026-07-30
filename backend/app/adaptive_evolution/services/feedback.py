from __future__ import annotations

from ..enums import ErrorType, FeedbackType, ProgressionAction
from ..schemas import FeedbackAdaptInput, FeedbackAdaptResult


ERROR_GUIDANCE: dict[ErrorType, str] = {
    ErrorType.CONCEPTUAL: "Retome o conceito principal e explique com suas próprias palavras antes de tentar novamente.",
    ErrorType.CALCULATION: "Revise cada operação separadamente e confira o resultado intermediário.",
    ErrorType.INTERPRETATION: "Sublinhe no enunciado o que a questão pede e separe os dados relevantes dos detalhes de contexto.",
    ErrorType.SEQUENCE: "Organize as etapas na ordem em que precisam ser executadas.",
    ErrorType.REPRESENTATION: "Tente representar o problema com desenho, tabela, símbolos ou esquema.",
    ErrorType.INCOMPLETE: "Confira quais partes do enunciado ainda não foram respondidas.",
    ErrorType.RANDOM_CHOICE: "Explique por que cada alternativa poderia estar correta ou incorreta antes de escolher.",
    ErrorType.STRATEGY: "Experimente outra estratégia e compare os passos usados nas duas tentativas.",
    ErrorType.ABSTRACTION: "Identifique apenas as informações essenciais e ignore detalhes que não alteram a solução.",
    ErrorType.DECOMPOSITION: "Divida o problema em partes menores e resolva uma parte de cada vez.",
    ErrorType.ALGORITHMIC: "Escreva uma sequência clara de passos antes de executar a solução.",
    ErrorType.DEBUGGING: "Localize o primeiro passo em que o resultado deixou de corresponder ao esperado.",
    ErrorType.NONE: "Revise sua estratégia e tente explicar o raciocínio usado.",
}


def adapt_feedback(payload: FeedbackAdaptInput) -> FeedbackAdaptResult:
    level = payload.mastery_level.strip().upper()
    low_mastery = level in {"INITIAL", "INICIAL", "EM_DESENVOLVIMENTO", "DEVELOPING"}
    high_mastery = level in {"ADVANCED", "AVANÇADO", "MASTERED", "DOMINADO"}

    if payload.is_correct:
        if high_mastery:
            content = (
                f"Você resolveu corretamente a habilidade “{payload.skill_name}”. "
                "Agora compare sua estratégia com outra possível solução ou avance para um desafio maior."
            )
            feedback_type = FeedbackType.METACOGNITIVE
            action = ProgressionAction.ADVANCE
        elif payload.hint_level_used >= 3:
            content = (
                f"A resposta está correta. As pistas ajudaram na habilidade “{payload.skill_name}”. "
                "Faça uma nova questão semelhante com menos ajuda para consolidar a aprendizagem."
            )
            feedback_type = FeedbackType.REVIEW_SUGGESTION
            action = ProgressionAction.MAINTAIN
        else:
            content = (
                f"Resposta correta em “{payload.skill_name}”. Explique o passo principal usado; "
                "isso ajuda a consolidar a estratégia."
            )
            feedback_type = FeedbackType.CORRECT_CONFIRMATION
            action = ProgressionAction.MAINTAIN
        return FeedbackAdaptResult(
            feedback_type=feedback_type,
            content=content,
            next_action=action,
            explanation="Feedback selecionado pelo acerto, domínio atual e nível de pista utilizado.",
            requires_teacher_review=False,
        )

    guidance = ERROR_GUIDANCE[payload.error_type]
    if low_mastery:
        content = (
            f"Vamos por partes em “{payload.skill_name}”. {guidance} "
            "Depois, faça uma nova tentativa usando apenas a primeira etapa."
        )
        feedback_type = FeedbackType.CONCEPT_REINFORCEMENT
        action = ProgressionAction.REINFORCE
    elif high_mastery:
        content = (
            f"Revise o ponto específico da tentativa em “{payload.skill_name}”. {guidance} "
            "Compare o erro com o procedimento que você normalmente usa."
        )
        feedback_type = FeedbackType.ATTEMPT_COMPARISON
        action = ProgressionAction.REVIEW
    else:
        content = f"Sua tentativa mostra um ponto que precisa de ajuste em “{payload.skill_name}”. {guidance}"
        feedback_type = FeedbackType.STRATEGY_GUIDANCE
        action = ProgressionAction.REVIEW

    if payload.preferred_language_complexity.upper() in {"SIMPLE", "SIMPLIFIED", "PLAIN"}:
        content = content.replace("consolidar", "fixar").replace("procedimento", "modo de resolver")

    return FeedbackAdaptResult(
        feedback_type=feedback_type,
        content=payload.original_feedback or content,
        next_action=action,
        explanation=f"Feedback adaptado ao erro {payload.error_type.value}, domínio {payload.mastery_level} e tentativa {payload.attempt_number}.",
        requires_teacher_review=payload.error_type in {ErrorType.RANDOM_CHOICE, ErrorType.NONE} and payload.attempt_number >= 3,
    )
