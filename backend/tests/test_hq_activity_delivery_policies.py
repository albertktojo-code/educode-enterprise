from app.comic_page_editor.activity_delivery import create_delivery, monitoring_summary
def test_delivery_service_reuses_assessment_delivery():
    source=open("app/comic_page_editor/activity_delivery.py",encoding="utf-8").read()
    assert "AssessmentPublication" in source
    assert "AssessmentTarget" in source
    assert "AssessmentSession" in source
    assert "AssessmentAutosave" not in source
