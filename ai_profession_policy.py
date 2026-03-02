from game_logic import (
    active_count,
    all_normal_moves,
    copy_rows,
    evaluate_result,
    nim_sum,
    simulate_cells_remove_with_context,
    simulate_normal_with_context,
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


def _difficulty_from_context(ai_context):
    if not isinstance(ai_context, dict):
        return "medium"
    difficulty = ai_context.get("difficulty")
    if difficulty in ("random", "medium", "optimal"):
        return difficulty
    return "medium"


def _normalize_cell(value):
    if (
        isinstance(value, (tuple, list))
        and len(value) == 2
        and isinstance(value[0], int)
        and isinstance(value[1], int)
    ):
        return int(value[0]), int(value[1])
    return None


def _clone_ai_context(ai_context):
    if not isinstance(ai_context, dict):
        return {}
    copied = dict(ai_context)
    raw_snapshot = ai_context.get("shield_state_snapshot")
    if isinstance(raw_snapshot, dict):
        snapshot = {
            "player": {"piece": None, "turns_left": 0},
            "ai": {"piece": None, "turns_left": 0},
        }
        for owner in ("player", "ai"):
            raw_owner = raw_snapshot.get(owner)
            if not isinstance(raw_owner, dict):
                continue
            piece = _normalize_cell(raw_owner.get("piece"))
            turns_left = raw_owner.get("turns_left")
            if not isinstance(turns_left, int) or turns_left <= 0 or piece is None:
                snapshot[owner] = {"piece": None, "turns_left": 0}
            else:
                snapshot[owner] = {"piece": piece, "turns_left": int(turns_left)}
        copied["shield_state_snapshot"] = snapshot
    if isinstance(ai_context.get("shielded_cells"), list):
        copied["shielded_cells"] = [
            tuple(cell) if isinstance(cell, (tuple, list)) and len(cell) == 2 else None
            for cell in ai_context.get("shielded_cells", [])
        ]
    return copied


def _shielded_cells_from_context(ai_context):
    if not isinstance(ai_context, dict):
        return set()
    raw_snapshot = ai_context.get("shield_state_snapshot")
    if isinstance(raw_snapshot, dict):
        cells = set()
        for owner in ("player", "ai"):
            owner_snapshot = raw_snapshot.get(owner)
            if not isinstance(owner_snapshot, dict):
                continue
            piece = _normalize_cell(owner_snapshot.get("piece"))
            turns_left = owner_snapshot.get("turns_left")
            if piece is None:
                continue
            if isinstance(turns_left, int) and turns_left > 0:
                cells.add(piece)
        return cells
    return {
        tuple(cell)
        for cell in ai_context.get("shielded_cells", [])
        if isinstance(cell, (tuple, list)) and len(cell) == 2
    }


def _move_shield_piece_in_context(ai_context, source_cell, dest_cell, swap_back=False):
    if not isinstance(ai_context, dict):
        return
    source = _normalize_cell(source_cell)
    dest = _normalize_cell(dest_cell)
    if source is None or dest is None:
        return

    raw_snapshot = ai_context.get("shield_state_snapshot")
    if isinstance(raw_snapshot, dict):
        for owner in ("player", "ai"):
            owner_snapshot = raw_snapshot.get(owner)
            if not isinstance(owner_snapshot, dict):
                continue
            piece = _normalize_cell(owner_snapshot.get("piece"))
            turns_left = owner_snapshot.get("turns_left")
            if not isinstance(turns_left, int) or turns_left <= 0 or piece is None:
                continue
            if piece == source:
                owner_snapshot["piece"] = dest
            elif swap_back and piece == dest:
                owner_snapshot["piece"] = source

    raw_cells = ai_context.get("shielded_cells")
    if isinstance(raw_cells, list):
        for idx, piece in enumerate(raw_cells):
            normalized = _normalize_cell(piece)
            if normalized == source:
                raw_cells[idx] = dest
            elif swap_back and normalized == dest:
                raw_cells[idx] = source


def _best_normal_score(rows, ai_context, blocked_edges):
    best_score = -10**9
    for move in all_normal_moves(rows, blocked_edges):
        board, removed, next_context = simulate_normal_with_context(
            rows,
            move,
            ai_context,
            blocked_edges,
        )
        score = evaluate_result(rows, board, removed, next_context, blocked_edges)
        if score > best_score:
            best_score = score
    return best_score


def _best_followup_normal_move(rows, ai_context, blocked_edges):
    best_move = None
    best_score = -10**9
    for move in all_normal_moves(rows, blocked_edges):
        board, removed, next_context = simulate_normal_with_context(
            rows,
            move,
            ai_context,
            blocked_edges,
        )
        score = evaluate_result(rows, board, removed, next_context, blocked_edges)
        if score > best_score:
            best_score = score
            best_move = move
    return best_move, best_score


def _edge_side_segment(rows, blocked_edges, edge):
    row_idx, left_idx = edge
    if row_idx < 0 or row_idx >= len(rows):
        return 0, 0
    row = rows[row_idx]
    if left_idx < 0 or left_idx + 1 >= len(row):
        return 0, 0

    blocked = set(blocked_edges or set())

    def _walk(start_idx, step):
        if start_idx < 0 or start_idx >= len(row):
            return 0
        if not row[start_idx]:
            return 0
        idx = start_idx
        length = 0
        while 0 <= idx < len(row) and row[idx]:
            length += 1
            next_idx = idx + step
            if step < 0:
                if next_idx < 0:
                    break
                if (row_idx, next_idx) in blocked:
                    break
            else:
                if next_idx >= len(row):
                    break
                if (row_idx, idx) in blocked:
                    break
            idx = next_idx
        return length

    return _walk(left_idx, -1), _walk(left_idx + 1, 1)


def _is_same_side_followup_after_bar(followup_move, edge):
    if followup_move is None:
        return False
    row_idx, start_idx, end_idx = followup_move
    edge_row, left_idx = edge
    if row_idx != edge_row:
        return False
    lo = min(start_idx, end_idx)
    hi = max(start_idx, end_idx)
    return hi <= left_idx or lo >= left_idx + 1


def _best_cross_action(rows, ai_context):
    blocked_edges = _blocked_edges_from_context(ai_context)
    remaining = active_count(rows)
    best_action = None
    best_score = -10**9
    best_removed = -1
    best_immediate_win = False

    for row_idx, row in enumerate(rows):
        for idx, active in enumerate(row):
            if not active:
                continue
            hit_cells, _fx_cells = cross_targets(rows, row_idx, idx, blocked_edges)
            board, removed, next_context = simulate_cells_remove_with_context(
                rows,
                hit_cells,
                ai_context,
            )
            score = evaluate_result(rows, board, removed, next_context, blocked_edges)
            if score > best_score or (score == best_score and removed > best_removed):
                best_score = score
                best_removed = removed
                best_immediate_win = active_count(board) == 0 and remaining > 0
                best_action = {
                    "type": "skill",
                    "skill_id": "cross",
                    "target": (row_idx, idx),
                }

    return best_action, best_score, best_immediate_win


def _count_cell_threat(rows, target_row, target_idx, blocked_edges):
    threat = 0
    for row_idx, start_idx, end_idx in all_normal_moves(rows, blocked_edges):
        if row_idx == target_row and start_idx <= target_idx <= end_idx:
            threat += 1
    return threat


def _opponent_can_finish_by_normal(rows, blocked_edges, ai_context):
    for move in all_normal_moves(rows, blocked_edges):
        next_rows, _removed, _next_context = simulate_normal_with_context(
            rows,
            move,
            ai_context,
            blocked_edges,
        )
        if active_count(next_rows) == 0:
            return True
    return False


def _best_shield_action(rows, ai_context):
    blocked_edges = _blocked_edges_from_context(ai_context)
    shielded_cells = _shielded_cells_from_context(ai_context)
    remaining = active_count(rows)
    base_nim = nim_sum(rows, blocked_edges)
    opp_can_finish = _opponent_can_finish_by_normal(rows, blocked_edges, ai_context)
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
                    swap_back = board[target_row][target_idx]
                    board[source_row][source_idx], board[target_row][target_idx] = (
                        board[target_row][target_idx],
                        board[source_row][source_idx],
                    )
                elif (
                    0 <= target_row < len(board)
                    and target_idx == len(board[target_row])
                ):
                    swap_back = False
                    board[source_row][source_idx] = False
                    board[target_row].append(True)
                else:
                    continue
                next_context = _clone_ai_context(ai_context)
                _move_shield_piece_in_context(
                    next_context,
                    (source_row, source_idx),
                    (target_row, target_idx),
                    swap_back=swap_back,
                )
                score = evaluate_result(rows, board, 0, next_context, blocked_edges)
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
    difficulty = _difficulty_from_context(ai_context)
    remaining = active_count(rows)
    optimal_endgame_threshold = 6
    optimal_forcing_margin = 10
    candidates = []
    for row_idx, row in enumerate(rows):
        for left_idx in range(len(row) - 1):
            edge = (row_idx, left_idx)
            if edge in blocked_edges:
                continue
            # Inactive neighbors already split the segment, placing a bar is usually wasted.
            if not row[left_idx] or not row[left_idx + 1]:
                continue
            candidates.append(edge)
    if not candidates:
        return None, -10**9, False

    opp_moves_before = len(all_normal_moves(rows, blocked_edges))
    opp_finish_before = _opponent_can_finish_by_normal(rows, blocked_edges, ai_context)
    base_nim = nim_sum(rows, blocked_edges)
    base_is_losing = base_nim == 0
    normal_best_score = _best_normal_score(rows, ai_context, blocked_edges)

    best_action = None
    best_score = -10**9
    best_force_use = False
    for row_idx, left_idx in candidates:
        next_blocked_edges = set(blocked_edges)
        next_blocked_edges.add((row_idx, left_idx))

        opp_moves_after = len(all_normal_moves(rows, next_blocked_edges))
        opp_finish_after = _opponent_can_finish_by_normal(
            rows,
            next_blocked_edges,
            ai_context,
        )
        next_nim = nim_sum(rows, next_blocked_edges)
        emergency_block = opp_finish_before and not opp_finish_after
        reversal_setup = base_is_losing and next_nim == 0

        move_delta = opp_moves_before - opp_moves_after
        if move_delta <= 0 and not emergency_block and not reversal_setup:
            continue

        score = move_delta * 10
        if emergency_block:
            score += 45
        if reversal_setup:
            score += 160
        if next_nim == 0:
            score += 12
        if base_nim == 0 and next_nim != 0:
            score -= 6
        score += max(0, len(rows[row_idx]) - 3)

        left_len, right_len = _edge_side_segment(
            rows,
            next_blocked_edges,
            (row_idx, left_idx),
        )
        if left_len == 0 or right_len == 0:
            score -= 24
        else:
            score += min(left_len, right_len) * 6
            if max(left_len, right_len) >= 3:
                score += 6

        followup_move, followup_score = _best_followup_normal_move(
            rows,
            ai_context,
            next_blocked_edges,
        )
        if followup_move is not None:
            score += int(followup_score * 0.35)

        same_side_followup = _is_same_side_followup_after_bar(
            followup_move,
            (row_idx, left_idx),
        )
        if same_side_followup:
            if difficulty == "optimal" and not emergency_block and not reversal_setup:
                continue
            if difficulty == "medium" and not emergency_block and not reversal_setup:
                score -= 120
            if difficulty == "random":
                score -= 45

        forcing_advantage = (
            next_nim == 0
            and move_delta >= 1
            and followup_move is not None
            and followup_score >= normal_best_score + optimal_forcing_margin
        )
        if difficulty == "optimal" and not emergency_block and not reversal_setup:
            # Master blacksmith should keep the bar for endgame unless it creates
            # a clear forcing advantage.
            if remaining > optimal_endgame_threshold:
                continue
            if not forcing_advantage:
                continue

        if difficulty == "random" and score < normal_best_score - 16:
            continue

        candidate_force_use = reversal_setup and difficulty in ("optimal", "medium")
        if score > best_score or (score == best_score and candidate_force_use and not best_force_use):
            best_score = score
            best_force_use = candidate_force_use
            best_action = {
                "type": "skill",
                "skill_id": "inlay_bar",
                "target": ((row_idx, left_idx), (row_idx, left_idx + 1)),
            }
            if candidate_force_use:
                best_action["force_use"] = True
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
            next_rows, _removed, _next_context = simulate_cells_remove_with_context(
                rows,
                hit_cells,
                ai_context,
            )
            if active_count(next_rows) == 0:
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
