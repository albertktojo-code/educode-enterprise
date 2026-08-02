from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EDITOR_ROOT = PROJECT_ROOT / "frontend/src/features/comicPageEditor"


def test_story_page_count_excludes_cover_and_back_cover_in_editor() -> None:
    collection = (EDITOR_ROOT / "pageCollection.ts").read_text(encoding="utf-8")
    editor = (EDITOR_ROOT / "ComicPageEditor.tsx").read_text(encoding="utf-8")
    thumbnails = (EDITOR_ROOT / "PageThumbnailStrip.tsx").read_text(
        encoding="utf-8"
    )
    layout_panel = (EDITOR_ROOT / "LayoutLibraryPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "{ length: normalizedTotal }" in collection
    assert 'page.pageType === "STORY"' in collection
    assert 'page.pageType === "COVER"' in collection
    assert 'page.pageType === "BACK_COVER"' in collection
    assert "...covers" in collection
    assert "...storyPages" in collection
    assert "...backCovers" in collection
    assert "synchronizeStoryPages(pages, next.totalPages, layouts)" in editor
    assert 'pages.filter((page) => page.pageType === "STORY")' in thumbnails
    assert "storyPages.length" in thumbnails
    assert "varyStoryPageLayouts" in collection
    assert "previousLayoutId" in collection
    assert "applyLayoutToStoryPage(selectedPage, layout)" in editor
    assert "varyLayoutsWithAi" in editor
    assert "IA variar grids por página" in layout_panel
    assert "Ver mais grids" not in layout_panel
