from app.models.assets import InstitutionalAssetStatus, InstitutionalAssetType
from app.schemas.assets import GeneratedCharacterSaveRequest, InstitutionalAssetCreate

def test_asset_types_include_core_library():
    assert {InstitutionalAssetType.CHARACTER, InstitutionalAssetType.SCENE, InstitutionalAssetType.OBJECT}.issubset(set(InstitutionalAssetType))

def test_asset_create_requires_structured_data():
    data=InstitutionalAssetCreate(asset_type="character",name="Luna",rights_confirmed=True,tags=["anime","ciências"])
    assert data.name=="Luna" and data.tags==["anime","ciências"]

def test_generated_character_destinations():
    data=GeneratedCharacterSaveRequest(name="Luna",destination="institutional_review",rights_confirmed=True)
    assert data.destination=="institutional_review"

def test_workflow_contains_review_and_publish():
    assert InstitutionalAssetStatus.IN_REVIEW.value=="in_review"
    assert InstitutionalAssetStatus.PUBLISHED.value=="published"
