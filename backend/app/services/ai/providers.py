from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx


class AIProviderError(RuntimeError):
    pass


@dataclass(slots=True)
class ProviderOutput:
    text: str
    structured: dict[str, Any]
    storage_reference: str | None
    input_units: int
    output_units: int
    image_count: int
    raw_metadata: dict[str, Any]


class BaseRuntimeProvider:
    def __init__(self, *, name: str, model_identifier: str) -> None:
        self.name = name
        self.model_identifier = model_identifier

    async def generate(
        self,
        *,
        request_type: str,
        system_instructions: str,
        prompt: str,
        output_schema: dict[str, Any],
        parameters: dict[str, Any],
    ) -> ProviderOutput:
        raise NotImplementedError


class MockRuntimeProvider(BaseRuntimeProvider):
    async def generate(
        self,
        *,
        request_type: str,
        system_instructions: str,
        prompt: str,
        output_schema: dict[str, Any],
        parameters: dict[str, Any],
    ) -> ProviderOutput:
        purpose = str(parameters.get("purpose") or "generic")
        topic = str(parameters.get("topic") or parameters.get("title") or "conteúdo educacional")
        if request_type == "image":
            payload = {
                "image_prompt": prompt,
                "alt_text": f"Ilustração educacional mock sobre {topic}.",
                "style": parameters.get("style", "cartoon_educational"),
                "mock": True,
            }
            return ProviderOutput(
                text="Imagem mock preparada para o canvas.",
                structured=payload,
                storage_reference=f"mock://image/{abs(hash(prompt))}",
                input_units=max(len(prompt) // 4, 1),
                output_units=32,
                image_count=1,
                raw_metadata={"provider_mode": "mock"},
            )

        if purpose == "assessment_questions":
            quantity = min(max(int(parameters.get("quantity", 5)), 1), 30)
            questions: list[dict[str, Any]] = []
            pillars = parameters.get("ct_pillars") or ["abstraction", "decomposition", "pattern_recognition", "algorithms"]
            skills = parameters.get("curriculum_skills") or []
            for index in range(quantity):
                correct = index % 4
                options = [
                    {"id": chr(65 + opt), "text": f"Alternativa {chr(65 + opt)} sobre {topic}"}
                    for opt in range(4)
                ]
                questions.append(
                    {
                        "title": f"Questão {index + 1} — {topic}",
                        "item_type": "multiple_choice",
                        "prompt": f"Qual alternativa representa melhor o conceito {index + 1} de {topic}?",
                        "options": options,
                        "answer_key": {"correct_option_ids": [chr(65 + correct)]},
                        "explanation": f"A alternativa {chr(65 + correct)} organiza corretamente o conceito solicitado.",
                        "points": 1.0,
                        "difficulty": parameters.get("difficulty", "medium"),
                        "curriculum_skill_codes": skills,
                        "ct_pillar_codes": [pillars[index % len(pillars)]] if pillars else [],
                        "requires_manual_grading": False,
                    }
                )
            structured = {"questions": questions, "teacher_review_required": True}
        elif purpose == "comic_script":
            panels = min(max(int(parameters.get("panel_count", 6)), 1), 40)
            structured = {
                "title": parameters.get("title") or f"A missão de {topic}",
                "pedagogical_objective": parameters.get("pedagogical_objective", "Resolver o desafio com Pensamento Computacional."),
                "panels": [
                    {
                        "sequence": index + 1,
                        "scene": f"Cena {index + 1} que desenvolve {topic} com continuidade narrativa.",
                        "dialogue": f"Vamos analisar a etapa {index + 1} sem perder as pistas anteriores.",
                        "ct_pillar": ["abstraction", "decomposition", "pattern_recognition", "algorithms"][index % 4],
                        "image_prompt": f"Quadro educacional {index + 1}, {topic}, personagens consistentes, sem texto embutido.",
                    }
                    for index in range(panels)
                ],
                "teacher_review_required": True,
            }
        elif purpose == "intervention":
            structured = {
                "title": f"Intervenção sobre {topic}",
                "evidence_summary": parameters.get("evidence_summary", "Indicadores pedagógicos selecionados pelo professor."),
                "actions": [
                    "Apresentar explicação alternativa com exemplo concreto.",
                    "Aplicar atividade curta com feedback formativo.",
                    "Reavaliar a habilidade após nova evidência.",
                ],
                "success_criteria": parameters.get("success_criteria", "Melhora de 10 pontos percentuais ou domínio adequado."),
                "teacher_review_required": True,
            }
        elif purpose == "statistical_report":
            structured = {
                "draft": True,
                "summary": f"Rascunho interpretativo para o estudo sobre {topic}.",
                "method_note": "Os cálculos são fornecidos exclusivamente pelo motor estatístico determinístico do EduCode.",
                "limitations": parameters.get("limitations", ["Revisar tamanho amostral e desenho do estudo."]),
                "causal_language_allowed": False,
            }
        elif purpose == "lesson_plan":
            structured = {
                "title": f"Plano de aula — {topic}",
                "objectives": parameters.get("objectives", ["Compreender o tema", "Aplicar Pensamento Computacional"]),
                "steps": ["Problematização", "Exploração guiada", "Produção", "Avaliação formativa"],
                "assessment": "Quiz e atividade prática vinculados ao Núcleo de Avaliação Integrada.",
                "teacher_review_required": True,
            }
        else:
            structured = {
                "draft": True,
                "content": f"Conteúdo educacional mock gerado para {topic}.",
                "request_summary": " ".join(prompt.split())[:1000],
                "teacher_review_required": True,
            }

        text = json.dumps(structured, ensure_ascii=False)
        return ProviderOutput(
            text=text,
            structured=structured,
            storage_reference=None,
            input_units=max((len(system_instructions) + len(prompt)) // 4, 1),
            output_units=max(len(text) // 4, 1),
            image_count=0,
            raw_metadata={"provider_mode": "mock", "schema_supplied": bool(output_schema)},
        )


class GenericHTTPRuntimeProvider(BaseRuntimeProvider):
    def __init__(
        self,
        *,
        name: str,
        model_identifier: str,
        base_url: str,
        secret_env_var: str | None,
        timeout_seconds: int,
        configuration: dict[str, Any],
    ) -> None:
        super().__init__(name=name, model_identifier=model_identifier)
        self.base_url = base_url.rstrip("/")
        self.secret_env_var = secret_env_var
        self.timeout_seconds = timeout_seconds
        self.configuration = configuration

    @staticmethod
    def _read_path(payload: Any, path: str) -> Any:
        current = payload
        for part in path.split("."):
            if isinstance(current, list):
                current = current[int(part)]
            elif isinstance(current, dict):
                current = current[part]
            else:
                raise AIProviderError(f"Caminho de resposta inválido: {path}")
        return current

    async def generate(
        self,
        *,
        request_type: str,
        system_instructions: str,
        prompt: str,
        output_schema: dict[str, Any],
        parameters: dict[str, Any],
    ) -> ProviderOutput:
        endpoint = str(self.configuration.get("endpoint") or "/generate")
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        if self.secret_env_var:
            secret = os.getenv(self.secret_env_var)
            if not secret:
                raise AIProviderError(f"Segredo não configurado na variável {self.secret_env_var}")
            header_name = str(self.configuration.get("auth_header") or "Authorization")
            prefix = str(self.configuration.get("auth_prefix") or "Bearer")
            headers[header_name] = f"{prefix} {secret}".strip()
        payload = {
            "model": self.model_identifier,
            "request_type": request_type,
            "system": system_instructions,
            "input": prompt,
            "output_schema": output_schema,
            "parameters": parameters,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AIProviderError(f"Falha no provedor HTTP: {exc}") from exc

        text_path = str(self.configuration.get("text_path") or "text")
        structured_path = str(self.configuration.get("structured_path") or "structured")
        storage_path = self.configuration.get("storage_path")
        usage_path = self.configuration.get("usage_path")
        text = str(self._read_path(data, text_path))
        try:
            structured_value = self._read_path(data, structured_path)
            structured = structured_value if isinstance(structured_value, dict) else {"value": structured_value}
        except (KeyError, IndexError, TypeError, AIProviderError):
            try:
                parsed = json.loads(text)
                structured = parsed if isinstance(parsed, dict) else {"value": parsed}
            except json.JSONDecodeError:
                structured = {"text": text}
        storage_reference = str(self._read_path(data, str(storage_path))) if storage_path else None
        usage: dict[str, Any] = {}
        if usage_path:
            value = self._read_path(data, str(usage_path))
            if isinstance(value, dict):
                usage = value
        return ProviderOutput(
            text=text,
            structured=structured,
            storage_reference=storage_reference,
            input_units=int(usage.get("input_units", max(len(prompt) // 4, 1))),
            output_units=int(usage.get("output_units", max(len(text) // 4, 1))),
            image_count=int(usage.get("image_count", 1 if request_type == "image" else 0)),
            raw_metadata={"http_status": 200, "endpoint": endpoint},
        )
