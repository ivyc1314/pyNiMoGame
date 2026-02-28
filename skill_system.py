from dataclasses import dataclass
from typing import Protocol


Cell = tuple[int, int]
ShieldState = dict[str, dict[str, object]]


@dataclass(frozen=True)
class SkillUseContext:
    rows: list[list[bool]]
    actor: str
    shield_states: ShieldState


@dataclass(frozen=True)
class SkillPreview:
    valid: bool
    hit_cells: list[Cell]
    fx_cells: list[Cell]
    reason: str | None = None


@dataclass(frozen=True)
class SkillExecution:
    consume_skill: bool
    start_animation: bool
    pending_remove_cells: list[Cell]
    fx_cells: list[Cell]
    reason: str | None = None


@dataclass(frozen=True)
class SkillDef:
    id: str
    name: str
    mode: str


class SkillHandler(Protocol):
    def preview(self, context: SkillUseContext, target: Cell) -> SkillPreview:
        ...

    def execute(self, context: SkillUseContext, target: Cell) -> SkillExecution:
        ...


def reset_shield(shield_states: ShieldState, owner: str | None = None) -> None:
    if owner is None:
        for side in ("player", "ai"):
            shield_states[side]["piece"] = None
            shield_states[side]["turns_left"] = 0
            shield_states[side]["action_count"] = 0
        return
    shield_states[owner]["piece"] = None
    shield_states[owner]["turns_left"] = 0
    shield_states[owner]["action_count"] = 0


def set_shield(shield_states: ShieldState, owner: str, row_idx: int, idx: int) -> None:
    shield_states[owner]["piece"] = (row_idx, idx)
    shield_states[owner]["turns_left"] = 2
    shield_states[owner]["action_count"] = 0


def cell_has_shield(shield_states: ShieldState, row_idx: int, idx: int) -> bool:
    return shield_states["player"]["piece"] == (row_idx, idx) or shield_states["ai"][
        "piece"
    ] == (row_idx, idx)


def shield_turns_for_cell(shield_states: ShieldState, row_idx: int, idx: int) -> int:
    turns_left = 0
    for owner in ("player", "ai"):
        if shield_states[owner]["piece"] == (row_idx, idx):
            turns_left = max(turns_left, int(shield_states[owner]["turns_left"]))
    return turns_left


def consume_shield(shield_states: ShieldState, row_idx: int, idx: int) -> bool:
    for owner in ("player", "ai"):
        if shield_states[owner]["piece"] == (row_idx, idx):
            reset_shield(shield_states, owner)
            return True
    return False


def update_shield_states_after_action(
    shield_states: ShieldState, rows: list[list[bool]]
) -> None:
    for owner in ("player", "ai"):
        piece = shield_states[owner]["piece"]
        if piece is None:
            shield_states[owner]["action_count"] = 0
            continue
        shield_row, shield_idx = piece
        shield_valid = (
            0 <= shield_row < len(rows)
            and 0 <= shield_idx < len(rows[shield_row])
            and rows[shield_row][shield_idx]
        )
        if not shield_valid:
            reset_shield(shield_states, owner)
            continue
        if int(shield_states[owner]["turns_left"]) <= 0:
            reset_shield(shield_states, owner)
            continue
        shield_states[owner]["action_count"] = int(shield_states[owner]["action_count"]) + 1
        if int(shield_states[owner]["action_count"]) >= 2:
            shield_states[owner]["action_count"] = 0
            shield_states[owner]["turns_left"] = int(shield_states[owner]["turns_left"]) - 1
            if int(shield_states[owner]["turns_left"]) <= 0:
                reset_shield(shield_states, owner)


def cross_targets(rows: list[list[bool]], center_row: int, center_idx: int) -> tuple[list[Cell], list[Cell]]:
    candidates = [
        (center_row, center_idx),
        (center_row, center_idx - 1),
        (center_row, center_idx + 1),
        (center_row - 1, center_idx),
        (center_row + 1, center_idx),
    ]
    fx_cells: list[Cell] = []
    hit_cells: list[Cell] = []
    for row_idx, idx in candidates:
        if row_idx < 0 or row_idx >= len(rows):
            continue
        if idx < 0 or idx >= len(rows[row_idx]):
            continue
        fx_cells.append((row_idx, idx))
        if rows[row_idx][idx]:
            hit_cells.append((row_idx, idx))
    return hit_cells, fx_cells


class ShieldSkillHandler:
    def preview(self, context: SkillUseContext, target: Cell) -> SkillPreview:
        row_idx, idx = target
        rows = context.rows
        if row_idx < 0 or row_idx >= len(rows):
            return SkillPreview(False, [], [], "out_of_bounds")
        if idx < 0 or idx >= len(rows[row_idx]):
            return SkillPreview(False, [], [], "out_of_bounds")
        if not rows[row_idx][idx]:
            return SkillPreview(False, [], [], "inactive_piece")
        if cell_has_shield(context.shield_states, row_idx, idx):
            return SkillPreview(False, [], [], "already_shielded")
        return SkillPreview(True, [], [])

    def execute(self, context: SkillUseContext, target: Cell) -> SkillExecution:
        preview = self.preview(context, target)
        if not preview.valid:
            return SkillExecution(False, False, [], [], preview.reason)
        row_idx, idx = target
        set_shield(context.shield_states, context.actor, row_idx, idx)
        return SkillExecution(True, False, [], [])


class CrossSkillHandler:
    def preview(self, context: SkillUseContext, target: Cell) -> SkillPreview:
        row_idx, idx = target
        rows = context.rows
        if row_idx < 0 or row_idx >= len(rows):
            return SkillPreview(False, [], [], "out_of_bounds")
        if idx < 0 or idx >= len(rows[row_idx]):
            return SkillPreview(False, [], [], "out_of_bounds")
        if not rows[row_idx][idx]:
            return SkillPreview(False, [], [], "inactive_piece")
        hit_cells, fx_cells = cross_targets(rows, row_idx, idx)
        if not fx_cells:
            return SkillPreview(False, [], [], "no_target")
        return SkillPreview(True, hit_cells, fx_cells)

    def execute(self, context: SkillUseContext, target: Cell) -> SkillExecution:
        preview = self.preview(context, target)
        if not preview.valid:
            return SkillExecution(False, False, [], [], preview.reason)
        return SkillExecution(
            True,
            True,
            preview.hit_cells,
            preview.fx_cells,
        )


_SKILL_DEFS: dict[str, SkillDef] = {
    "shield": SkillDef(id="shield", name="圣盾", mode="shield"),
    "cross": SkillDef(id="cross", name="十字斩", mode="cross"),
}
_SKILL_HANDLERS: dict[str, SkillHandler] = {
    "shield": ShieldSkillHandler(),
    "cross": CrossSkillHandler(),
}


def get_skill_ids() -> list[str]:
    return list(_SKILL_DEFS.keys())


def get_skill_name(skill_id: str) -> str:
    skill = _SKILL_DEFS.get(skill_id)
    if skill is None:
        return skill_id
    return skill.name


def get_skill_mode(skill_id: str) -> str:
    skill = _SKILL_DEFS.get(skill_id)
    if skill is None:
        return skill_id
    return skill.mode


def get_skill_handler(skill_id: str) -> SkillHandler | None:
    return _SKILL_HANDLERS.get(skill_id)


def preview_skill(context: SkillUseContext, skill_id: str, target: Cell) -> SkillPreview:
    handler = get_skill_handler(skill_id)
    if handler is None:
        return SkillPreview(False, [], [], "unknown_skill")
    return handler.preview(context, target)


def execute_skill(context: SkillUseContext, skill_id: str, target: Cell) -> SkillExecution:
    handler = get_skill_handler(skill_id)
    if handler is None:
        return SkillExecution(False, False, [], [], "unknown_skill")
    return handler.execute(context, target)
