from dataclasses import dataclass, field
from typing import Protocol

from constants import BOARD_COLS

Cell = tuple[int, int]
SkillTarget = Cell | tuple[Cell, Cell]
BoardUpdate = tuple[Cell, bool]
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
    board_updates: list[BoardUpdate] = field(default_factory=list)
    shadow_move: tuple[Cell, Cell] | None = None


@dataclass(frozen=True)
class SkillDef:
    id: str
    name: str
    mode: str


class SkillHandler(Protocol):
    def preview(self, context: SkillUseContext, target: SkillTarget) -> SkillPreview:
        ...

    def execute(self, context: SkillUseContext, target: SkillTarget) -> SkillExecution:
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


def cross_targets(
    rows: list[list[bool]], center_row: int, center_idx: int
) -> tuple[list[Cell], list[Cell]]:
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


def _is_cell(value: object) -> bool:
    return (
        isinstance(value, (tuple, list))
        and len(value) == 2
        and isinstance(value[0], int)
        and isinstance(value[1], int)
    )


def _single_cell_target(target: SkillTarget) -> Cell | None:
    if _is_cell(target):
        row_idx = int(target[0])
        idx = int(target[1])
        return (row_idx, idx)
    return None


def _move_target(target: SkillTarget) -> tuple[Cell, Cell] | None:
    if not isinstance(target, (tuple, list)) or len(target) != 2:
        return None
    source = target[0]
    dest = target[1]
    if not _is_cell(source) or not _is_cell(dest):
        return None
    source_cell = (int(source[0]), int(source[1]))
    dest_cell = (int(dest[0]), int(dest[1]))
    return source_cell, dest_cell


def _in_bounds(rows: list[list[bool]], row_idx: int, idx: int) -> bool:
    return 0 <= row_idx < len(rows) and 0 <= idx < len(rows[row_idx])


def shadow_hand_destinations(
    rows: list[list[bool]], source_cell: Cell
) -> list[Cell]:
    source_row, source_idx = source_cell
    if not _in_bounds(rows, source_row, source_idx):
        return []
    if not rows[source_row][source_idx]:
        return []

    destinations: list[Cell] = []
    for target_row, target_cells in enumerate(rows):
        for target_idx, _active in enumerate(target_cells):
            if target_row == source_row and target_idx == source_idx:
                continue
            destinations.append((target_row, target_idx))
        if len(target_cells) < BOARD_COLS:
            destinations.append((target_row, len(target_cells)))
    return destinations


class ShieldSkillHandler:
    def preview(self, context: SkillUseContext, target: SkillTarget) -> SkillPreview:
        cell = _single_cell_target(target)
        if cell is None:
            return SkillPreview(False, [], [], "invalid_target")
        row_idx, idx = cell
        rows = context.rows
        if not _in_bounds(rows, row_idx, idx):
            return SkillPreview(False, [], [], "out_of_bounds")
        if not rows[row_idx][idx]:
            return SkillPreview(False, [], [], "inactive_piece")
        if cell_has_shield(context.shield_states, row_idx, idx):
            return SkillPreview(False, [], [], "already_shielded")
        return SkillPreview(True, [], [])

    def execute(self, context: SkillUseContext, target: SkillTarget) -> SkillExecution:
        preview = self.preview(context, target)
        if not preview.valid:
            return SkillExecution(False, False, [], [], preview.reason)
        row_idx, idx = _single_cell_target(target) or (0, 0)
        set_shield(context.shield_states, context.actor, row_idx, idx)
        return SkillExecution(True, False, [], [])


class CrossSkillHandler:
    def preview(self, context: SkillUseContext, target: SkillTarget) -> SkillPreview:
        cell = _single_cell_target(target)
        if cell is None:
            return SkillPreview(False, [], [], "invalid_target")
        row_idx, idx = cell
        rows = context.rows
        if not _in_bounds(rows, row_idx, idx):
            return SkillPreview(False, [], [], "out_of_bounds")
        if not rows[row_idx][idx]:
            return SkillPreview(False, [], [], "inactive_piece")
        hit_cells, fx_cells = cross_targets(rows, row_idx, idx)
        if not fx_cells:
            return SkillPreview(False, [], [], "no_target")
        return SkillPreview(True, hit_cells, fx_cells)

    def execute(self, context: SkillUseContext, target: SkillTarget) -> SkillExecution:
        preview = self.preview(context, target)
        if not preview.valid:
            return SkillExecution(False, False, [], [], preview.reason)
        return SkillExecution(
            True,
            True,
            preview.hit_cells,
            preview.fx_cells,
        )


class ShadowHandSkillHandler:
    def preview(self, context: SkillUseContext, target: SkillTarget) -> SkillPreview:
        move_target = _move_target(target)
        if move_target is None:
            return SkillPreview(False, [], [], "invalid_target")
        source_cell, dest_cell = move_target
        source_row, source_idx = source_cell
        dest_row, dest_idx = dest_cell
        rows = context.rows
        if not _in_bounds(rows, source_row, source_idx):
            return SkillPreview(False, [], [], "source_out_of_bounds")
        if not rows[source_row][source_idx]:
            return SkillPreview(False, [], [], "inactive_source")
        valid_destinations = set(shadow_hand_destinations(rows, source_cell))
        if (dest_row, dest_idx) not in valid_destinations:
            return SkillPreview(False, [], [], "target_not_reachable")
        return SkillPreview(True, [], [source_cell, dest_cell])

    def execute(self, context: SkillUseContext, target: SkillTarget) -> SkillExecution:
        preview = self.preview(context, target)
        if not preview.valid:
            return SkillExecution(False, False, [], [], preview.reason)
        source_cell, dest_cell = _move_target(target) or ((0, 0), (0, 0))
        rows = context.rows
        source_row, source_idx = source_cell
        dest_row, dest_idx = dest_cell
        source_next = False
        dest_next = True
        if _in_bounds(rows, dest_row, dest_idx):
            source_next = rows[dest_row][dest_idx]
        return SkillExecution(
            True,
            False,
            [],
            preview.fx_cells,
            board_updates=[(source_cell, source_next), (dest_cell, dest_next)],
            shadow_move=(source_cell, dest_cell),
        )


_SKILL_DEFS: dict[str, SkillDef] = {
    "shield": SkillDef(id="shield", name="\u5723\u76fe", mode="shield"),
    "cross": SkillDef(id="cross", name="\u5341\u5b57\u65a9", mode="cross"),
    "shadow_hand": SkillDef(
        id="shadow_hand",
        name="\u6697\u624b",
        mode="shadow_hand",
    ),
}
_SKILL_HANDLERS: dict[str, SkillHandler] = {
    "shield": ShieldSkillHandler(),
    "cross": CrossSkillHandler(),
    "shadow_hand": ShadowHandSkillHandler(),
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


def preview_skill(
    context: SkillUseContext, skill_id: str, target: SkillTarget
) -> SkillPreview:
    handler = get_skill_handler(skill_id)
    if handler is None:
        return SkillPreview(False, [], [], "unknown_skill")
    return handler.preview(context, target)


def execute_skill(
    context: SkillUseContext, skill_id: str, target: SkillTarget
) -> SkillExecution:
    handler = get_skill_handler(skill_id)
    if handler is None:
        return SkillExecution(False, False, [], [], "unknown_skill")
    return handler.execute(context, target)
