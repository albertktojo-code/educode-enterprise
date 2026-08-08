from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_official_product_catalog_contains_all_nine_products() -> None:
    catalog = (
        PROJECT_ROOT / "frontend/src/config/productCatalog.ts"
    ).read_text(encoding="utf-8")

    expected = [
        "EduCode Learn",
        "EduCode Studio",
        "EduCode Practice",
        "EduCode Assess",
        "EduCode Tutor",
        "EduCode Analytics",
        "EduCode Connect",
        "EduCode Credentials",
        "EduCode Admin",
    ]
    assert all(name in catalog for name in expected)
    assert catalog.count("name: 'EduCode ") == 9


def test_product_directory_is_registered_and_role_aware() -> None:
    app = (PROJECT_ROOT / "frontend/src/App.tsx").read_text(encoding="utf-8")
    catalog = (
        PROJECT_ROOT / "frontend/src/config/productCatalog.ts"
    ).read_text(encoding="utf-8")
    layout = (
        PROJECT_ROOT / "frontend/src/components/AppLayout.tsx"
    ).read_text(encoding="utf-8")

    assert 'path="produtos" element={<ProductDirectoryPage />}' in app
    assert "productRoute" in catalog
    assert "role === 'member'" in catalog
    assert 'to: "/produtos"' in layout


def test_documented_boundaries_preserve_canonical_domains() -> None:
    architecture = (
        PROJECT_ROOT / "docs/PRODUCT_ARCHITECTURE.md"
    ).read_text(encoding="utf-8")
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "Assessment Hub" in architecture
    assert "Assessment Delivery" in architecture
    assert "não fragmenta a arquitetura técnica" in architecture
    assert "Essa divisão é uma arquitetura de produto" in agents
