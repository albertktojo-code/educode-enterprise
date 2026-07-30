from app.services.ai.advanced import accessibility_payload, checkpoint_checksum, continuity_findings, score_quality

def test_quality_score_prioritizes_safe_structured_content():
    result=score_quality({"questions":[{"statement":"Q"}],"bncc_skills":["EF06MA07"]},{"valid":True,"warnings":[]},{"safe":True})
    assert result["confidence_score"] >= .8
    assert result["pedagogical_alignment"] == .9

def test_continuity_finds_missing_canonical_trait():
    findings=continuity_findings({"canonical_characters":[{"name":"Luna","immutable_traits":["óculos redondos"]}]},{"panels":[{"characters":["Luna"],"description":"Luna entra na sala"}]})
    assert findings and findings[0]["character"]=="Luna"

def test_checkpoint_checksum_is_stable():
    assert checkpoint_checksum({"b":2,"a":1})==checkpoint_checksum({"a":1,"b":2})

def test_accessibility_outputs_require_teacher_review():
    item=accessibility_payload("alt_text",{"title":"Laboratório"})
    assert item["teacher_review_required"] is True
