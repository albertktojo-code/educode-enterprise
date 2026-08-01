from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


SidebarMode = Literal["expanded", "compact", "hidden", "auto"]


class InterfacePreferenceUpsert(BaseModel):
    sidebar_mode: SidebarMode = "expanded"
    sidebar_width: int = Field(default=260, ge=210, le=340)
    editor_focus_default: bool = False
    reduce_motion: bool = False
    last_open_section: str = Field(default="", max_length=120)

    @model_validator(mode="after")
    def normalize_compact_width(self):
        if self.sidebar_mode == "compact":
            self.sidebar_width = 64
        return self
