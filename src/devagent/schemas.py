from __future__ import annotations
from typing import Literal, List, Optional
from pydantic import BaseModel, Field, field_validator

ActionType = Literal["create", "edit", "delete", "run"]

class Action(BaseModel):
    type: ActionType
    file: Optional[str] = None
    content: Optional[str] = None
    patch: Optional[str] = None
    cmd: Optional[List[str]] = None
    why: Optional[str] = None

    @field_validator("file")
    @classmethod
    def file_required_for_file_ops(cls, v, info):
        t = info.data.get("type")
        if t in ("create","edit","delete") and not v:
            raise ValueError("file required for create/edit/delete")
        return v

    @field_validator("cmd")
    @classmethod
    def cmd_required_for_run(cls, v, info):
        t = info.data.get("type")
        if t == "run" and (not v or len(v)==0):
            raise ValueError("cmd required for run")
        return v

    @field_validator("content")
    @classmethod
    def content_or_patch_for_edit(cls, v, info):
        t = info.data.get("type")
        patch = info.data.get("patch")
        if t == "edit" and not (v or patch):
            raise ValueError("edit requires content or patch")
        return v

class Plan(BaseModel):
    actions: List[Action] = Field(default_factory=list)
