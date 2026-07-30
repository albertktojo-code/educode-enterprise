from __future__ import annotations

from typing import Any


class AIOutputValidationError(ValueError):
    pass


def validate_output(purpose: str, content: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not content:
        errors.append("A saída estruturada está vazia")
    if purpose == "assessment_questions":
        questions = content.get("questions")
        if not isinstance(questions, list) or not questions:
            errors.append("A saída deve conter uma lista não vazia de questões")
        else:
            for index, question in enumerate(questions, start=1):
                if not isinstance(question, dict):
                    errors.append(f"Questão {index} não é um objeto")
                    continue
                for field in ("prompt", "item_type", "answer_key"):
                    if not question.get(field):
                        errors.append(f"Questão {index} sem {field}")
                if question.get("item_type") in {"multiple_choice", "multiple_choice"}:
                    options = question.get("options")
                    if not isinstance(options, list) or len(options) < 2:
                        errors.append(f"Questão {index} precisa de pelo menos duas alternativas")
                if not question.get("curriculum_skill_codes") and not question.get("ct_pillar_codes"):
                    warnings.append(f"Questão {index} sem classificação BNCC ou PC")
    elif purpose == "comic_script":
        panels = content.get("panels")
        if not isinstance(panels, list) or not panels:
            errors.append("O roteiro deve conter quadros")
        else:
            sequences = [panel.get("sequence") for panel in panels if isinstance(panel, dict)]
            if sequences != list(range(1, len(sequences) + 1)):
                errors.append("A sequência dos quadros é inválida")
            for index, panel in enumerate(panels, start=1):
                if not panel.get("scene") or not panel.get("image_prompt"):
                    errors.append(f"Quadro {index} sem cena ou prompt visual")
    elif purpose == "intervention":
        if not isinstance(content.get("actions"), list) or not content.get("actions"):
            errors.append("A intervenção deve conter ações")
        if not content.get("evidence_summary"):
            warnings.append("Intervenção sem resumo explícito das evidências")
    elif purpose == "statistical_report":
        if "summary" not in content:
            errors.append("Relatório sem resumo")
        if content.get("causal_language_allowed") is True:
            warnings.append("A linguagem causal deve ser revisada conforme o desenho do estudo")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "purpose": purpose}
