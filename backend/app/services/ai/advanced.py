from __future__ import annotations
import hashlib, json
from typing import Any

def score_quality(content: dict[str,Any], validation: dict[str,Any], safety: dict[str,Any]) -> dict[str,Any]:
    valid = 1.0 if validation.get("valid", True) else 0.25
    warnings = len(validation.get("warnings", []))
    findings=[]
    if warnings: findings.append({"type":"validation_warning","count":warnings})
    safety_ok = 0.2 if safety.get("blocked") or safety.get("prompt_injection_detected") else 1.0
    has_sources = bool(content.get("citations") or content.get("sources"))
    panels = content.get("panels", [])
    narrative = 1.0
    names=[]
    for p in panels:
        names.extend(p.get("characters", []))
    if panels and not names: narrative=.65; findings.append({"type":"narrative","message":"Quadros sem personagens identificados"})
    pedagogical=.9 if any(k in content for k in ("learning_objective","bncc_skills","ct_pillars","questions")) else .7
    values={"structural_validity":valid,"pedagogical_alignment":pedagogical,"source_coverage":1.0 if has_sources else .65,"age_appropriateness":.9,"narrative_consistency":narrative,"safety_score":safety_ok}
    values["confidence_score"]=round(sum(values.values())/6,3); values["findings"]=findings
    return values

def continuity_findings(memory: dict[str,Any], content: dict[str,Any]) -> list[dict[str,Any]]:
    findings=[]
    canon={c.get("name"):c for c in memory.get("canonical_characters",[]) if c.get("name")}
    for i,panel in enumerate(content.get("panels",[]),1):
        text=json.dumps(panel,ensure_ascii=False).lower()
        for name,cfg in canon.items():
            if name.lower() in text:
                for trait in cfg.get("immutable_traits",[]):
                    if trait.lower() not in text:
                        findings.append({"panel":i,"character":name,"severity":"warning","message":f"Característica canônica ausente: {trait}"})
    return findings

def checkpoint_checksum(payload: dict[str,Any]) -> str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()

def accessibility_payload(kind: str, content: dict[str,Any]) -> dict[str,Any]:
    title=content.get("title") or content.get("summary") or "Conteúdo educacional"
    if kind=="alt_text": return {"text":f"Descrição acessível de {title}.","source":"ai-assisted","teacher_review_required":True}
    if kind=="simplified_text": return {"text":content.get("summary") or title,"reading_level":"simplified","teacher_review_required":True}
    return {"summary":content.get("summary") or title,"navigation_hints":["Use títulos e descrições para navegar"],"teacher_review_required":True}
