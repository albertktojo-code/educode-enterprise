import hashlib
from dataclasses import dataclass
from typing import Any, TypedDict

from app.models.comic import BalloonType


class ComicGenerationError(ValueError):
    pass


class GeneratedBalloon(TypedDict):
    sequence_number: int
    speaker_name_snapshot: str | None
    balloon_type: str
    text: str
    emotion: str | None
    pedagogical_function: str | None
    position_x: float
    position_y: float
    width: float
    height: float


class GeneratedPanel(TypedDict):
    narrative_goal: str
    pedagogical_goal: str
    ct_pillar_codes: list[str]
    scene_description: str
    previous_panel_summary: str
    next_panel_hook: str
    initial_state: dict[str, Any]
    final_state: dict[str, Any]
    emotion: str
    plot_function: str
    balloons: list[GeneratedBalloon]


@dataclass(frozen=True)
class StoryInput:
    title: str
    topic: str
    disciplinary_objective: str
    ct_objective: str
    facts: list[str]
    pillar_codes: list[str]
    characters: list[str]
    scenes: list[str]
    narrative_profile: dict[str, Any]


_BEATS = [
    ("hook", "curiosity"),
    ("setup", "joy"),
    ("comic_misunderstanding", "humor"),
    ("clue", "curiosity"),
    ("false_solution", "confidence"),
    ("setback", "tension"),
    ("emotional_low", "sadness"),
    ("discovery", "hope"),
    ("plot_twist", "surprise"),
    ("application", "excitement"),
    ("resolution", "relief"),
    ("reflection", "pride"),
]


def _stable_index(seed: str, modulo: int) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % max(modulo, 1)


def _select_beat(index: int, total: int) -> tuple[str, str]:
    if total <= 1:
        return "resolution", "surprise"
    mapped = round(index * (len(_BEATS) - 1) / (total - 1))
    return _BEATS[mapped]


def _speaker(characters: list[str], index: int, offset: int = 0) -> str:
    if not characters:
        return ["Lia", "Caio", "Professor Byte"][(index + offset) % 3]
    return characters[(index + offset) % len(characters)]


def _fact(facts: list[str], index: int) -> str:
    if not facts:
        return "O conceito precisa ser investigado por etapas e confirmado com evidências."
    return facts[index % len(facts)]


def _dialogues(
    *,
    beat: str,
    index: int,
    story: StoryInput,
    fact: str,
    previous_discovery: str,
) -> list[GeneratedBalloon]:
    first = _speaker(story.characters, index)
    second = _speaker(story.characters, index, 1)
    mentor = _speaker(story.characters, index, 2)
    lines: list[tuple[str | None, BalloonType, str, str | None, str | None]]

    if beat == "hook":
        lines = [
            (
                None,
                BalloonType.NARRATION,
                f"Tudo parecia comum até que um detalhe sobre {story.topic} mudou a missão.",
                "curiosity",
                "contextualization",
            ),
            (
                first,
                BalloonType.SPEECH,
                "Vocês também perceberam que alguma coisa aqui não combina?",
                "surprise",
                "problem_statement",
            ),
        ]
    elif beat == "setup":
        lines = [
            (
                second,
                BalloonType.SPEECH,
                "Talvez seja fácil. Eu já tenho uma resposta!",
                "confidence",
                "hypothesis",
            ),
            (
                first,
                BalloonType.SPEECH,
                "Antes, vamos separar o que sabemos do que estamos imaginando.",
                "focus",
                "decomposition",
            ),
        ]
    elif beat == "comic_misunderstanding":
        lines = [
            (
                second,
                BalloonType.SPEECH,
                "Eu separei tudo: o lanche, os lápis e até as minhas desculpas!",
                "humor",
                "engagement",
            ),
            (
                first,
                BalloonType.THOUGHT,
                "Ele entendeu decomposição de um jeito... muito pessoal.",
                "amusement",
                "concept_bridge",
            ),
        ]
    elif beat == "clue":
        lines = [
            (mentor, BalloonType.WHISPER, f"Pista: {fact}", "mystery", "evidence"),
            (
                first,
                BalloonType.SPEECH,
                "Essa pista parece pequena, mas pode mudar toda a sequência.",
                "curiosity",
                "pattern_recognition",
            ),
        ]
    elif beat == "false_solution":
        lines = [
            (
                second,
                BalloonType.SHOUT,
                "Resolvido! Só precisamos repetir a primeira ideia!",
                "triumph",
                "misconception",
            ),
            (
                first,
                BalloonType.SPEECH,
                "Espera... ela funciona em todos os casos ou apenas neste?",
                "doubt",
                "validation",
            ),
        ]
    elif beat == "setback":
        lines = [
            (
                None,
                BalloonType.NARRATION,
                "O teste seguinte derrubou a solução que parecia perfeita.",
                "tension",
                "counterexample",
            ),
            (
                second,
                BalloonType.SPEECH,
                "Então eu estava completamente errado?",
                "frustration",
                "reflection",
            ),
        ]
    elif beat == "emotional_low":
        lines = [
            (
                first,
                BalloonType.SPEECH,
                "Errar não apaga o caminho. O erro mostrou exatamente onde devemos olhar.",
                "hope",
                "debugging",
            ),
            (
                second,
                BalloonType.SPEECH,
                "Então ainda podemos descobrir juntos?",
                "sadness",
                "collaboration",
            ),
        ]
    elif beat == "discovery":
        lines = [
            (
                mentor,
                BalloonType.SPEECH,
                f"Compare com o que já descobrimos: {previous_discovery}",
                "encouragement",
                "connection",
            ),
            (
                first,
                BalloonType.SPEECH,
                f"Agora faz sentido: {fact}",
                "discovery",
                "concept_construction",
            ),
        ]
    elif beat == "plot_twist":
        lines = [
            (
                None,
                BalloonType.NARRATION,
                (
                    "A pista não indicava um erro. Ela havia sido deixada para "
                    "testar a hipótese do grupo."
                ),
                "surprise",
                "plot_twist",
            ),
            (
                second,
                BalloonType.SPEECH,
                "Então quem parecia atrapalhar estava nos ajudando desde o começo!",
                "astonishment",
                "reinterpretation",
            ),
        ]
    elif beat == "application":
        lines = [
            (
                first,
                BalloonType.SPEECH,
                (
                    "Vamos transformar a descoberta em uma sequência que qualquer "
                    "pessoa consiga repetir."
                ),
                "excitement",
                "algorithm",
            ),
            (mentor, BalloonType.PEDAGOGICAL, fact, "focus", "mandatory_fact"),
        ]
    elif beat == "resolution":
        lines = [
            (
                second,
                BalloonType.SPEECH,
                "A resposta estava nas pistas, nos erros e no padrão entre eles.",
                "relief",
                "synthesis",
            ),
            (
                first,
                BalloonType.SPEECH,
                "E a melhor parte é que agora conseguimos explicar por que funciona.",
                "pride",
                "explanation",
            ),
        ]
    else:
        lines = [
            (
                None,
                BalloonType.CAPTION,
                f"Desafio final: aplique a descoberta a uma nova situação de {story.topic}.",
                "curiosity",
                "assessment",
            ),
            (
                mentor,
                BalloonType.SPEECH,
                "Uma boa solução não termina a investigação. Ela abre uma pergunta melhor.",
                "inspiration",
                "metacognition",
            ),
        ]

    balloons: list[GeneratedBalloon] = []
    for sequence, (speaker, balloon_type, text, emotion, function) in enumerate(lines, start=1):
        balloons.append(
            {
                "sequence_number": sequence,
                "speaker_name_snapshot": speaker,
                "balloon_type": balloon_type.value,
                "text": text,
                "emotion": emotion,
                "pedagogical_function": function,
                "position_x": 8.0 if sequence == 1 else 52.0,
                "position_y": 8.0 if sequence == 1 else 64.0,
                "width": 40.0,
                "height": 22.0,
            }
        )
    return balloons


def build_story(story: StoryInput, panel_total: int) -> list[GeneratedPanel]:
    if panel_total < 1:
        raise ComicGenerationError("A HQ precisa ter pelo menos um quadro")

    panels: list[GeneratedPanel] = []
    previous_summary = "A história ainda não começou."
    known_facts: list[str] = []
    open_questions = [f"Como compreender e aplicar {story.topic}?"]
    seed = f"{story.title}|{story.topic}|{story.narrative_profile}"
    scene_offset = _stable_index(seed, len(story.scenes) or 1)

    for index in range(panel_total):
        beat, emotion = _select_beat(index, panel_total)
        fact = _fact(story.facts, index)
        scene = (
            story.scenes[(index + scene_offset) % len(story.scenes)]
            if story.scenes
            else "ambiente pedagógico que combina com a missão"
        )
        previous_discovery = (
            known_facts[-1] if known_facts else "a primeira pista ainda precisa ser confirmada"
        )
        if beat in {"clue", "discovery", "application", "resolution"} and fact not in known_facts:
            known_facts.append(fact)
        if beat == "resolution":
            open_questions = []

        narrative_goal = {
            "hook": "Apresentar um acontecimento inesperado e despertar curiosidade.",
            "setup": "Organizar o problema e levantar uma hipótese inicial.",
            "comic_misunderstanding": "Criar humor sem perder o vínculo com o conceito.",
            "clue": "Introduzir uma pista que sustentará a reviravolta.",
            "false_solution": "Apresentar uma solução plausível, mas incompleta.",
            "setback": "Confrontar a hipótese com uma evidência contrária.",
            "emotional_low": "Transformar frustração em colaboração e depuração.",
            "discovery": "Conectar pistas e construir o conceito.",
            "plot_twist": "Reinterpretar acontecimentos anteriores de modo coerente.",
            "application": "Aplicar o conceito em uma sequência reproduzível.",
            "resolution": "Resolver o conflito e explicar a solução.",
            "reflection": "Consolidar a aprendizagem com um novo desafio.",
        }[beat]
        pedagogical_goal = (
            story.disciplinary_objective
            if beat in {"clue", "discovery", "application", "resolution"}
            else story.ct_objective
        )
        scene_description = (
            f"No cenário {scene}, {_speaker(story.characters, index)} conduz a ação do momento "
            f"'{beat}'. A composição visual destaca a emoção {emotion} e preserva os elementos "
            "introduzidos nos quadros anteriores."
        )
        next_hook = (
            "Uma nova pista questiona a conclusão atual."
            if index < panel_total - 1
            else "O encerramento deixa um desafio aplicável a outra situação."
        )
        initial_state: dict[str, Any] = {
            "known_facts": list(
                known_facts[:-1] if known_facts and known_facts[-1] == fact else known_facts
            ),
            "open_questions": list(open_questions),
            "scene": scene,
            "characters_present": [
                _speaker(story.characters, index),
                _speaker(story.characters, index, 1),
            ],
        }
        final_state: dict[str, Any] = {
            "known_facts": list(known_facts),
            "open_questions": list(open_questions),
            "scene": scene,
            "last_event": narrative_goal,
        }
        balloons = _dialogues(
            beat=beat,
            index=index,
            story=story,
            fact=fact,
            previous_discovery=previous_discovery,
        )
        panel_summary = f"No quadro {index + 1}, {narrative_goal.lower()}"
        panels.append(
            {
                "narrative_goal": narrative_goal,
                "pedagogical_goal": pedagogical_goal,
                "ct_pillar_codes": list(story.pillar_codes),
                "scene_description": scene_description,
                "previous_panel_summary": previous_summary,
                "next_panel_hook": next_hook,
                "initial_state": initial_state,
                "final_state": final_state,
                "emotion": emotion,
                "plot_function": beat,
                "balloons": balloons,
            }
        )
        previous_summary = panel_summary
    return panels


def regenerate_panel_content(
    panel: GeneratedPanel,
    *,
    scope: str,
    instruction: str | None,
    preserve_dialogue: bool,
    preserve_scene: bool,
) -> GeneratedPanel:
    result: GeneratedPanel = {
        "narrative_goal": panel["narrative_goal"],
        "pedagogical_goal": panel["pedagogical_goal"],
        "ct_pillar_codes": list(panel["ct_pillar_codes"]),
        "scene_description": panel["scene_description"],
        "previous_panel_summary": panel["previous_panel_summary"],
        "next_panel_hook": panel["next_panel_hook"],
        "initial_state": dict(panel["initial_state"]),
        "final_state": dict(panel["final_state"]),
        "emotion": panel["emotion"],
        "plot_function": panel["plot_function"],
        "balloons": [dict(balloon) for balloon in panel["balloons"]],  # type: ignore[misc]
    }
    note = (
        instruction.strip() if instruction else "mais claro, natural e conectado ao quadro anterior"
    )
    if scope in {"scene", "panel"} and not preserve_scene:
        result["scene_description"] = (
            f"Versão regenerada: {note}. {panel['scene_description']} "
            "A continuidade visual e os objetos existentes foram preservados."
        )
    if scope in {"balloons", "dialogue", "panel"} and not preserve_dialogue:
        for index, balloon in enumerate(result["balloons"], start=1):
            balloon["text"] = f"{balloon['text']} [Revisão {index}: {note}]"
    return result
