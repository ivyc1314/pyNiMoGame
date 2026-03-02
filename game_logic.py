import random

from constants import BOARD_COLS, GAP, RADIUS, ROW_SPACING, TOP_Y, WIDTH

IronBarEdge = tuple[int, int]
_NEG_INF = -10**9
_POS_INF = 10**9


def clamp(value, min_v, max_v):
    return max(min_v, min(max_v, value))


def point_in_circle(px, py, cx, cy, r):
    return (px - cx) ** 2 + (py - cy) ** 2 <= r ** 2


def get_row_centers(rows):
    centers = []
    full_width = BOARD_COLS * (RADIUS * 2 + GAP) - GAP
    start_x = (WIDTH - full_width) / 2
    for i, row in enumerate(rows):
        count = len(row)
        y = TOP_Y + i * ROW_SPACING
        row_centers = []
        for idx in range(count):
            x = start_x + idx * (RADIUS * 2 + GAP) + RADIUS
            row_centers.append((x, y))
        centers.append(row_centers)
    return centers


def find_circle(rows, pos):
    centers = get_row_centers(rows)
    for row_idx, row in enumerate(centers):
        for idx, (x, y) in enumerate(row):
            if not rows[row_idx][idx]:
                continue
            if point_in_circle(pos[0], pos[1], x, y, RADIUS):
                return row_idx, idx
    return None


def find_board_cell(rows, pos):
    centers = get_row_centers(rows)
    for row_idx, row in enumerate(centers):
        for idx, (x, y) in enumerate(row):
            if point_in_circle(pos[0], pos[1], x, y, RADIUS):
                return row_idx, idx
    return None


def _normalize_blocked_edges(blocked_edges=None):
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


def _edge_blocked(blocked_edges: set[IronBarEdge], row_idx: int, left_idx: int):
    return (row_idx, left_idx) in blocked_edges


def get_segment_bounds(rows, row_idx, index, blocked_edges=None):
    if row_idx < 0 or row_idx >= len(rows):
        return None
    if index < 0 or index >= len(rows[row_idx]):
        return None
    if not rows[row_idx][index]:
        return None
    blocked = _normalize_blocked_edges(blocked_edges)
    lo = index
    hi = index
    while lo - 1 >= 0 and rows[row_idx][lo - 1]:
        if _edge_blocked(blocked, row_idx, lo - 1):
            break
        lo -= 1
    while hi + 1 < len(rows[row_idx]) and rows[row_idx][hi + 1]:
        if _edge_blocked(blocked, row_idx, hi):
            break
        hi += 1
    return lo, hi


def get_segments(rows, blocked_edges=None):
    blocked = _normalize_blocked_edges(blocked_edges)
    segments = []
    for row_idx, row in enumerate(rows):
        start = None
        for idx, active in enumerate(row):
            if not active:
                start = None
                continue
            if start is None:
                start = idx
            if start is None:
                continue
            at_last = idx == len(row) - 1
            next_inactive = not at_last and not row[idx + 1]
            blocked_next = not at_last and _edge_blocked(blocked, row_idx, idx)
            if at_last or next_inactive or blocked_next:
                segments.append((row_idx, start, idx))
                start = None
    return segments


def segment_intersects_circle(p1, p2, cx, cy, r):
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return point_in_circle(x1, y1, cx, cy, r)
    t = ((cx - x1) * dx + (cy - y1) * dy) / (dx * dx + dy * dy)
    t = clamp(t, 0.0, 1.0)
    px = x1 + t * dx
    py = y1 + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2 <= r ** 2


def find_hit_by_segment(rows, p1, p2):
    centers = get_row_centers(rows)
    for row_idx, row in enumerate(centers):
        for idx, (x, y) in enumerate(row):
            if not rows[row_idx][idx]:
                continue
            if segment_intersects_circle(p1, p2, x, y, RADIUS):
                return row_idx, idx
    return None


def update_touched_by_segment(
    rows, row_idx, bounds, p1, p2, touched, blocked_edges=None
):
    _ = blocked_edges
    lo, hi = bounds
    centers = get_row_centers(rows)[row_idx]
    for idx in range(lo, hi + 1):
        if not rows[row_idx][idx]:
            continue
        x, y = centers[idx]
        if segment_intersects_circle(p1, p2, x, y, RADIUS):
            touched.add(idx)


def _copy_rows(rows):
    return [row[:] for row in rows]


def _normalize_cell(value):
    if (
        isinstance(value, (tuple, list))
        and len(value) == 2
        and isinstance(value[0], int)
        and isinstance(value[1], int)
    ):
        return int(value[0]), int(value[1])
    return None


def _normalize_turns_left(value):
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, int(value))
    return 0


def _empty_shield_snapshot():
    return {
        "player": {"piece": None, "turns_left": 0},
        "ai": {"piece": None, "turns_left": 0},
    }


def _shield_snapshot_from_context(ai_context):
    if not isinstance(ai_context, dict):
        return _empty_shield_snapshot()

    snapshot = _empty_shield_snapshot()
    raw_snapshot = ai_context.get("shield_state_snapshot")
    if isinstance(raw_snapshot, dict):
        for owner in ("player", "ai"):
            raw_owner = raw_snapshot.get(owner)
            if not isinstance(raw_owner, dict):
                continue
            piece = _normalize_cell(raw_owner.get("piece"))
            turns_left = _normalize_turns_left(raw_owner.get("turns_left"))
            if piece is None or turns_left <= 0:
                snapshot[owner] = {"piece": None, "turns_left": 0}
            else:
                snapshot[owner] = {"piece": piece, "turns_left": turns_left}
        return snapshot

    raw_cells = ai_context.get("shielded_cells")
    if isinstance(raw_cells, (list, tuple)):
        for idx, owner in enumerate(("player", "ai")):
            if idx >= len(raw_cells):
                break
            piece = _normalize_cell(raw_cells[idx])
            if piece is not None:
                snapshot[owner] = {"piece": piece, "turns_left": 1}
    return snapshot


def _copy_ai_context(ai_context):
    if not isinstance(ai_context, dict):
        return {"shield_state_snapshot": _empty_shield_snapshot()}
    copied = dict(ai_context)
    copied["shield_state_snapshot"] = _shield_snapshot_from_context(ai_context)
    return copied


def _consume_simulated_shield(ai_context, row_idx, idx):
    if not isinstance(ai_context, dict):
        return False
    snapshot = _shield_snapshot_from_context(ai_context)
    consumed = False
    for owner in ("player", "ai"):
        owner_snapshot = snapshot.get(owner, {})
        piece = _normalize_cell(owner_snapshot.get("piece"))
        turns_left = _normalize_turns_left(owner_snapshot.get("turns_left"))
        if piece == (row_idx, idx) and turns_left > 0:
            snapshot[owner] = {"piece": None, "turns_left": 0}
            consumed = True
    if consumed:
        ai_context["shield_state_snapshot"] = snapshot
    return consumed


def _active_count(rows):
    return sum(1 for row in rows for piece in row if piece)


def _nim_sum(rows, blocked_edges=None):
    nim_sum = 0
    for _row_idx, lo, hi in get_segments(rows, blocked_edges):
        nim_sum ^= hi - lo + 1
    return nim_sum


def _all_normal_moves(rows, blocked_edges=None):
    moves = []
    seen = set()
    for row_idx, lo, hi in get_segments(rows, blocked_edges):
        length = hi - lo + 1
        for remove in range(1, length + 1):
            candidates = [(row_idx, lo, lo + remove - 1), (row_idx, hi - remove + 1, hi)]
            for move in candidates:
                if move in seen:
                    continue
                seen.add(move)
                moves.append(move)
    return moves


def _random_normal_move(rows, blocked_edges=None):
    segments = get_segments(rows, blocked_edges)
    if not segments:
        return None
    row_idx, lo, hi = random.choice(segments)
    length = hi - lo + 1
    remove = random.randint(1, length)
    if random.random() < 0.5:
        return row_idx, lo, lo + remove - 1
    return row_idx, hi - remove + 1, hi


def _optimal_normal_move(rows, blocked_edges=None):
    moves = _all_normal_moves(rows, blocked_edges)
    if not moves:
        return None
    nim_sum = _nim_sum(rows, blocked_edges)
    if nim_sum == 0:
        return random.choice(moves)

    best = []
    move_set = set(moves)
    for row_idx, lo, hi in get_segments(rows, blocked_edges):
        length = hi - lo + 1
        target = length ^ nim_sum
        if target >= length:
            continue
        remove = length - target
        left = (row_idx, lo, lo + remove - 1)
        right = (row_idx, hi - remove + 1, hi)
        if left in move_set:
            best.append(left)
        if right in move_set:
            best.append(right)

    if best:
        return random.choice(best)
    return random.choice(moves)


def _apply_normal(rows, move):
    row_idx, start_idx, end_idx = move
    board = _copy_rows(rows)
    removed = 0
    for idx in range(min(start_idx, end_idx), max(start_idx, end_idx) + 1):
        if board[row_idx][idx]:
            board[row_idx][idx] = False
            removed += 1
    return board, removed


def _simulate_normal_with_context(rows, move, ai_context, blocked_edges=None):
    _ = blocked_edges
    row_idx, start_idx, end_idx = move
    board = _copy_rows(rows)
    simulated_context = _copy_ai_context(ai_context)
    removed = 0
    for idx in range(min(start_idx, end_idx), max(start_idx, end_idx) + 1):
        if row_idx < 0 or row_idx >= len(board):
            continue
        if idx < 0 or idx >= len(board[row_idx]):
            continue
        if not board[row_idx][idx]:
            continue
        if _consume_simulated_shield(simulated_context, row_idx, idx):
            continue
        board[row_idx][idx] = False
        removed += 1
    return board, removed, simulated_context


def _simulate_cells_remove_with_context(rows, cells, ai_context):
    board = _copy_rows(rows)
    simulated_context = _copy_ai_context(ai_context)
    removed = 0
    seen = set()
    for cell in cells:
        normalized = _normalize_cell(cell)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        row_idx, idx = normalized
        if row_idx < 0 or row_idx >= len(board):
            continue
        if idx < 0 or idx >= len(board[row_idx]):
            continue
        if not board[row_idx][idx]:
            continue
        if _consume_simulated_shield(simulated_context, row_idx, idx):
            continue
        board[row_idx][idx] = False
        removed += 1
    return board, removed, simulated_context


def _best_scored_normal(rows, legal_moves, ai_context, blocked_edges):
    if not legal_moves:
        return None
    best_move = None
    best_rows = None
    best_removed = -1
    best_context = None
    best_score = -10**9
    for move in legal_moves:
        next_rows, removed, next_context = _simulate_normal_with_context(
            rows,
            move,
            ai_context,
            blocked_edges,
        )
        score = _evaluate_result(
            rows,
            next_rows,
            removed,
            next_context,
            blocked_edges,
        )
        if score > best_score:
            best_score = score
            best_move = move
            best_rows = next_rows
            best_removed = removed
            best_context = next_context
    return best_move, best_rows, best_removed, best_context, best_score


def _opponent_can_finish_next(rows, ai_context, blocked_edges=None):
    for move in _all_normal_moves(rows, blocked_edges):
        next_rows, _removed, _next_context = _simulate_normal_with_context(
            rows,
            move,
            ai_context,
            blocked_edges,
        )
        if _active_count(next_rows) == 0:
            return True

    if not isinstance(ai_context, dict):
        return False
    if ai_context.get("opponent_skill_used", True):
        return False
    opponent_finish_checker = ai_context.get("opponent_can_finish_with_skill")
    if callable(opponent_finish_checker):
        return bool(opponent_finish_checker(rows, ai_context))
    return False


def _evaluate_result(
    rows_before, rows_after, removed_count, ai_context, blocked_edges=None
):
    remaining = _active_count(rows_after)
    if remaining == 0:
        return 100000

    score = removed_count * 5
    if _nim_sum(rows_after, blocked_edges) == 0:
        score += 35
    else:
        score -= 8

    if remaining <= 2:
        score -= 70
    elif remaining <= 4:
        score -= 20

    if _nim_sum(rows_before, blocked_edges) == 0 and _nim_sum(rows_after, blocked_edges) == 0:
        score += 10

    if _opponent_can_finish_next(rows_after, ai_context, blocked_edges):
        score -= 80
    return score


def _to_normal_action(move):
    row_idx, start_idx, end_idx = move
    return {"type": "normal", "row": row_idx, "start": start_idx, "end": end_idx}


def _rows_to_key(rows):
    return tuple(tuple(1 if cell else 0 for cell in row) for row in rows)


def _blocked_edges_to_key(blocked_edges):
    return tuple(sorted(_normalize_blocked_edges(blocked_edges)))


def _blacksmith_skill_candidates(rows, blocked_edges):
    blocked = _normalize_blocked_edges(blocked_edges)
    for row_idx, row in enumerate(rows):
        for left_idx in range(len(row) - 1):
            edge = (row_idx, left_idx)
            if edge in blocked:
                continue
            if not row[left_idx] or not row[left_idx + 1]:
                continue
            yield edge


def _blacksmith_actions(rows, blocked_edges, ai_skill_used, turn):
    actions = [("normal", move) for move in _all_normal_moves(rows, blocked_edges)]
    if turn == "ai" and not ai_skill_used:
        actions.extend(("skill", edge) for edge in _blacksmith_skill_candidates(rows, blocked_edges))
    return actions


def _blacksmith_terminal_score(turn):
    # If no active pieces at node entry, previous mover already won.
    return -800000 if turn == "ai" else 800000


def _blacksmith_heuristic(rows, blocked_edges, ai_skill_used, turn):
    remaining = _active_count(rows)
    nim = _nim_sum(rows, blocked_edges)
    ai_to_move = turn == "ai"
    if ai_to_move:
        score = 220 if nim != 0 else -220
    else:
        score = 220 if nim == 0 else -220

    # Favor converting to short, controlled endgames where a saved skill matters.
    score -= remaining * 6
    segment_count = len(get_segments(rows, blocked_edges))
    score += segment_count * 10
    if not ai_skill_used:
        score += 30 if ai_to_move else 20
    return score


def _blacksmith_quick_score(
    rows,
    blocked_edges,
    action_kind,
    payload,
    ai_skill_used,
):
    if action_kind == "normal":
        next_rows, removed = _apply_normal(rows, payload)
        score = removed * 8
        score += 25 if _nim_sum(next_rows, blocked_edges) == 0 else -10
        return score
    edge = payload
    next_blocked = set(_normalize_blocked_edges(blocked_edges))
    next_blocked.add(edge)
    score = 12
    score += 40 if _nim_sum(rows, next_blocked) == 0 else -12
    if ai_skill_used:
        score -= 300
    return score


def _ordered_blacksmith_actions(rows, blocked_edges, ai_skill_used, turn):
    actions = _blacksmith_actions(rows, blocked_edges, ai_skill_used, turn)
    reverse = turn == "ai"
    actions.sort(
        key=lambda item: _blacksmith_quick_score(
            rows,
            blocked_edges,
            item[0],
            item[1],
            ai_skill_used,
        ),
        reverse=reverse,
    )
    return actions


def _blacksmith_transition(rows, blocked_edges, ai_skill_used, turn, action_kind, payload):
    if action_kind == "normal":
        next_rows, _removed = _apply_normal(rows, payload)
        return next_rows, _normalize_blocked_edges(blocked_edges), ai_skill_used, (
            "player" if turn == "ai" else "ai"
        )

    edge = payload
    next_blocked = set(_normalize_blocked_edges(blocked_edges))
    next_blocked.add(edge)
    # Inlay bar does not consume the turn; after using skill, AI acts again.
    return _copy_rows(rows), next_blocked, True, turn


def _blacksmith_minimax(
    rows,
    blocked_edges,
    ai_skill_used,
    turn,
    depth_left,
    alpha,
    beta,
    cache,
):
    remaining = _active_count(rows)
    if remaining == 0:
        return _blacksmith_terminal_score(turn)
    if depth_left <= 0:
        return _blacksmith_heuristic(rows, blocked_edges, ai_skill_used, turn)

    cache_key = (
        _rows_to_key(rows),
        _blocked_edges_to_key(blocked_edges),
        bool(ai_skill_used),
        turn,
        int(depth_left),
    )
    if cache_key in cache:
        return cache[cache_key]

    actions = _ordered_blacksmith_actions(rows, blocked_edges, ai_skill_used, turn)
    if not actions:
        return _blacksmith_terminal_score(turn)

    if turn == "ai":
        best = _NEG_INF
        for action_kind, payload in actions:
            next_rows, next_blocked, next_ai_skill_used, next_turn = _blacksmith_transition(
                rows,
                blocked_edges,
                ai_skill_used,
                turn,
                action_kind,
                payload,
            )
            score = _blacksmith_minimax(
                next_rows,
                next_blocked,
                next_ai_skill_used,
                next_turn,
                depth_left - 1,
                alpha,
                beta,
                cache,
            )
            if score > best:
                best = score
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
    else:
        best = _POS_INF
        for action_kind, payload in actions:
            next_rows, next_blocked, next_ai_skill_used, next_turn = _blacksmith_transition(
                rows,
                blocked_edges,
                ai_skill_used,
                turn,
                action_kind,
                payload,
            )
            score = _blacksmith_minimax(
                next_rows,
                next_blocked,
                next_ai_skill_used,
                next_turn,
                depth_left - 1,
                alpha,
                beta,
                cache,
            )
            if score < best:
                best = score
            if score < beta:
                beta = score
            if alpha >= beta:
                break

    cache[cache_key] = best
    return best


def _blacksmith_optimal_action_with_lookahead(rows, ai_context, blocked_edges):
    ai_skill_used = bool(ai_context.get("ai_skill_used", True))
    remaining = _active_count(rows)
    depth = 5 if remaining <= 14 else 3
    cache = {}

    actions = _ordered_blacksmith_actions(rows, blocked_edges, ai_skill_used, "ai")
    if not actions:
        return None

    best_action = None
    best_score = _NEG_INF
    alpha = _NEG_INF
    beta = _POS_INF
    for action_kind, payload in actions:
        next_rows, next_blocked, next_ai_skill_used, next_turn = _blacksmith_transition(
            rows,
            blocked_edges,
            ai_skill_used,
            "ai",
            action_kind,
            payload,
        )
        score = _blacksmith_minimax(
            next_rows,
            next_blocked,
            next_ai_skill_used,
            next_turn,
            depth - 1,
            alpha,
            beta,
            cache,
        )
        if score > best_score:
            best_score = score
            if action_kind == "normal":
                best_action = _to_normal_action(payload)
            else:
                row_idx, left_idx = payload
                best_action = {
                    "type": "skill",
                    "skill_id": "inlay_bar",
                    "target": ((row_idx, left_idx), (row_idx, left_idx + 1)),
                }
        if score > alpha:
            alpha = score
    return best_action


def copy_rows(rows):
    return _copy_rows(rows)


def active_count(rows):
    return _active_count(rows)


def nim_sum(rows, blocked_edges=None):
    return _nim_sum(rows, blocked_edges)


def all_normal_moves(rows, blocked_edges=None):
    return _all_normal_moves(rows, blocked_edges)


def apply_normal(rows, move):
    return _apply_normal(rows, move)


def simulate_normal_with_context(rows, move, ai_context, blocked_edges=None):
    return _simulate_normal_with_context(rows, move, ai_context, blocked_edges)


def simulate_cells_remove_with_context(rows, cells, ai_context):
    return _simulate_cells_remove_with_context(rows, cells, ai_context)


def evaluate_result(rows_before, rows_after, removed_count, ai_context, blocked_edges=None):
    return _evaluate_result(
        rows_before,
        rows_after,
        removed_count,
        ai_context,
        blocked_edges,
    )


def nim_ai_move(rows, difficulty, ai_context=None):
    """
    Return AI action.

    Backward compatibility:
    - If ai_context is None, return (row_idx, start_idx, end_idx) like the old API.
    - If ai_context is provided, return an action dict with type:
      normal / skill
    """
    blocked_edges = None
    if isinstance(ai_context, dict):
        ai_context = _copy_ai_context(ai_context)
        ai_context.setdefault("difficulty", difficulty)
        blocked_edges = ai_context.get("blocked_edges")
    legal_normal_moves = _all_normal_moves(rows, blocked_edges)
    if not legal_normal_moves:
        return None

    if ai_context is None:
        if difficulty == "optimal":
            return _optimal_normal_move(rows, blocked_edges)
        if difficulty == "medium":
            return (
                _optimal_normal_move(rows, blocked_edges)
                if random.random() < 0.7
                else random.choice(legal_normal_moves)
            )
        return random.choice(legal_normal_moves)

    if (
        difficulty == "optimal"
        and ai_context.get("profession_mode")
        and ai_context.get("ai_profession") == "blacksmith"
    ):
        lookahead_action = _blacksmith_optimal_action_with_lookahead(
            rows,
            ai_context,
            blocked_edges,
        )
        if lookahead_action is not None:
            return lookahead_action

    best_scored = _best_scored_normal(rows, legal_normal_moves, ai_context, blocked_edges)
    if best_scored is None:
        fallback_move = random.choice(legal_normal_moves)
        return _to_normal_action(fallback_move)
    best_move, best_rows, best_removed, best_context, best_score = best_scored

    if difficulty == "optimal":
        normal_move = best_move
        normal_rows = best_rows
        normal_removed = best_removed
        normal_context = best_context
        normal_score = best_score
    elif difficulty == "medium":
        if random.random() < 0.7:
            normal_move = best_move
            normal_rows = best_rows
            normal_removed = best_removed
            normal_context = best_context
            normal_score = best_score
        else:
            normal_move = random.choice(legal_normal_moves)
            normal_rows, normal_removed, normal_context = _simulate_normal_with_context(
                rows,
                normal_move,
                ai_context,
                blocked_edges,
            )
            normal_score = _evaluate_result(
                rows,
                normal_rows,
                normal_removed,
                normal_context,
                blocked_edges,
            )
    else:
        normal_move = random.choice(legal_normal_moves)
        normal_rows, normal_removed, normal_context = _simulate_normal_with_context(
            rows,
            normal_move,
            ai_context,
            blocked_edges,
        )
        normal_score = _evaluate_result(
            rows,
            normal_rows,
            normal_removed,
            normal_context,
            blocked_edges,
        )

    normal_action = _to_normal_action(normal_move)

    if not ai_context.get("profession_mode"):
        return normal_action
    if ai_context.get("ai_skill_used", True):
        return normal_action

    skill_policy = ai_context.get("skill_policy")
    if not callable(skill_policy):
        return normal_action
    skill_action, skill_score, skill_immediate_win = skill_policy(rows, ai_context)

    if not skill_action:
        return normal_action
    force_use_skill = (
        isinstance(skill_action, dict) and bool(skill_action.get("force_use"))
    )
    if force_use_skill and difficulty in ("optimal", "medium"):
        return skill_action

    if difficulty == "random":
        if skill_immediate_win:
            return skill_action if random.random() < 0.85 else normal_action
        return skill_action if random.random() < 0.30 else normal_action

    if difficulty == "medium":
        if skill_immediate_win:
            return skill_action
        disadvantaged = _nim_sum(rows, blocked_edges) == 0
        if disadvantaged and skill_score >= normal_score - 12 and random.random() < 0.65:
            return skill_action
        if skill_score > normal_score + 8 and random.random() < 0.75:
            return skill_action
        return normal_action

    if skill_immediate_win:
        return skill_action
    if skill_score > normal_score + 2:
        return skill_action
    return normal_action
