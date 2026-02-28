from game_logic import (
    active_count,
    all_normal_moves,
    apply_normal,
    copy_rows,
    evaluate_result,
    nim_sum,
)
from skill_system import cross_targets, shadow_hand_destinations


def _blocked_edges_from_context(ai_context):
    if not isinstance(ai_context, dict):
        return set()
    blocked_edges = ai_context.get("blocked_edges")
    if not blocked_edges:
        return set()
    normalized = set()
    for edge in blocked_edges:
        if (
            isinstance(edge, (tuple, list))
            and len(edge) == 2
            and isinstance(edge[0], int)
            and isinstance(edge[1], int)
        ):
            normalized.add((int(edge[0]), int(edge[1])))
    return normalized


def _best_cross_action(rows, ai_context):
    blocked_edges = _blocked_edges_from_context(ai_context)
    remaining = active_count(rows)
    best_action = None
    best_score = -10**9
    best_removed = -1

    for row_idx, row in enumerate(rows):
        for idx, active in enumerate(row):
            if not active:
                continue
            hit_cells, _fx_cells = cross_targets(rows, row_idx, idx, blocked_edges)
            removed = len(hit_cells)
            if removed <= 0:
                continue
            board = copy_rows(rows)
            for hit_row, hit_idx in hit_cells:
                board[hit_row][hit_idx] = False
            score = evaluate_result(rows, board, removed, ai_context, blocked_edges)
            if score > best_score or (score == best_score and removed > best_removed):
                best_score = score
                best_removed = removed
                best_action = {
                    "type": "skill",
                    "skill_id": "cross",
                    "target": (row_idx, idx),
                }

    immediate_win = best_removed >= remaining and remaining > 0
    return best_action, best_score, immediate_win


def _count_cell_threat(rows, target_row, target_idx, blocked_edges):
    threat = 0
    for row_idx, start_idx, end_idx in all_normal_moves(rows, blocked_edges):
        if row_idx == target_row and start_idx <= target_idx <= end_idx:
            threat += 1
    return threat


def _opponent_can_finish_by_normal(rows, blocked_edges):
    for move in all_normal_moves(rows, blocked_edges):
        next_rows, _removed = apply_normal(rows, move)
        if active_count(next_rows) == 0:
            return True
    return False


def _best_shield_action(rows, ai_context):
    blocked_edges = _blocked_edges_from_context(ai_context)
    shielded_cells = {
        tuple(cell)
        for cell in ai_context.get("shielded_cells", [])
        if isinstance(cell, (tuple, list)) and len(cell) == 2
    }
    remaining = active_count(rows)
    base_nim = nim_sum(rows, blocked_edges)
    opp_can_finish = _opponent_can_finish_by_normal(rows, blocked_edges)
    if not opp_can_finish and not ai_context.get("opponent_skill_used", True):
        opponent_checker = ai_context.get("opponent_can_finish_with_skill")
        if callable(opponent_checker):
            opp_can_finish = bool(opponent_checker(rows, ai_context))

    best_action = None
    best_score = -10**9
    for row_idx, row in enumerate(rows):
        for idx, active in enumerate(row):
            if not active or (row_idx, idx) in shielded_cells:
                continue
            threat = _count_cell_threat(rows, row_idx, idx, blocked_edges)
            if remaining <= 4:
                threat *= 2
            if remaining <= 2:
                threat *= 2
            score = threat * 9
            if base_nim == 0:
                score += 14
            if opp_can_finish:
                score += 30
            if score > best_score:
                best_score = score
                best_action = {
                    "type": "skill",
                    "skill_id": "shield",
                    "target": (row_idx, idx),
                }
    return best_action, best_score, False


def _best_shadow_hand_action(rows, ai_context):
    blocked_edges = _blocked_edges_from_context(ai_context)
    best_action = None
    best_score = -10**9
    for source_row, row in enumerate(rows):
        for source_idx, active in enumerate(row):
            if not active:
                continue
            for target_row, target_idx in shadow_hand_destinations(
                rows, (source_row, source_idx)
            ):
                board = copy_rows(rows)
                if 0 <= target_row < len(board) and 0 <= target_idx < len(board[target_row]):
                    board[source_row][source_idx], board[target_row][target_idx] = (
                        board[target_row][target_idx],
                        board[source_row][source_idx],
                    )
                elif (
                    0 <= target_row < len(board)
                    and target_idx == len(board[target_row])
                ):
                    board[source_row][source_idx] = False
                    board[target_row].append(True)
                else:
                    continue
                score = evaluate_result(rows, board, 0, ai_context, blocked_edges)
                if score > best_score:
                    best_score = score
                    best_action = {
                        "type": "skill",
                        "skill_id": "shadow_hand",
                        "target": (
                            (source_row, source_idx),
                            (target_row, target_idx),
                        ),
                    }
    return best_action, best_score, False


def _best_inlay_bar_action(rows, ai_context):
    blocked_edges = _blocked_edges_from_context(ai_context)
    candidates = []
    for row_idx, row in enumerate(rows):
        for left_idx in range(len(row) - 1):
            edge = (row_idx, left_idx)
            if edge in blocked_edges:
                continue
            candidates.append(edge)
    if not candidates:
        return None, -10**9, False

    opp_moves_before = len(all_normal_moves(rows, blocked_edges))
    opp_finish_before = _opponent_can_finish_by_normal(rows, blocked_edges)
    base_nim = nim_sum(rows, blocked_edges)

    best_action = None
    best_score = -10**9
    for row_idx, left_idx in candidates:
        next_blocked_edges = set(blocked_edges)
        next_blocked_edges.add((row_idx, left_idx))

        opp_moves_after = len(all_normal_moves(rows, next_blocked_edges))
        opp_finish_after = _opponent_can_finish_by_normal(rows, next_blocked_edges)
        next_nim = nim_sum(rows, next_blocked_edges)

        score = (opp_moves_before - opp_moves_after) * 8
        if opp_finish_before and not opp_finish_after:
            score += 42
        if next_nim == 0:
            score += 12
        if base_nim == 0 and next_nim != 0:
            score -= 6
        score += max(0, len(rows[row_idx]) - 2)

        if score > best_score:
            best_score = score
            best_action = {
                "type": "skill",
                "skill_id": "inlay_bar",
                "target": ((row_idx, left_idx), (row_idx, left_idx + 1)),
            }
    return best_action, best_score, False


def _never_finish_with_skill(_rows, _ai_context):
    return False


def _cross_can_finish_with_skill(rows, ai_context):
    blocked_edges = _blocked_edges_from_context(ai_context)
    remaining = active_count(rows)
    if remaining == 0:
        return False
    for row_idx, row in enumerate(rows):
        for idx, active in enumerate(row):
            if not active:
                continue
            hit_cells, _fx_cells = cross_targets(rows, row_idx, idx, blocked_edges)
            if len(hit_cells) >= remaining:
                return True
    return False


_SKILL_POLICY_BY_PROFESSION = {
    "swordsman": _best_cross_action,
    "paladin": _best_shield_action,
    "thief": _best_shadow_hand_action,
    "blacksmith": _best_inlay_bar_action,
}
_OPPONENT_FINISH_CHECKERS = {
    "swordsman": _cross_can_finish_with_skill,
}


def get_skill_policy(profession_id):
    policy = _SKILL_POLICY_BY_PROFESSION.get(profession_id)

    def _evaluate(rows, ai_context):
        if policy is None:
            return None, -10**9, False
        return policy(rows, ai_context)

    return _evaluate


def get_opponent_finish_checker(profession_id):
    return _OPPONENT_FINISH_CHECKERS.get(profession_id, _never_finish_with_skill)
