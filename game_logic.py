import random

from constants import BOARD_COLS, GAP, RADIUS, ROW_SPACING, TOP_Y, WIDTH


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


def get_segment_bounds(rows, row_idx, index):
    if not rows[row_idx][index]:
        return None
    return 0, len(rows[row_idx]) - 1


def get_segments(rows):
    segments = []
    for row_idx, row in enumerate(rows):
        start = None
        for idx, active in enumerate(row):
            if active and start is None:
                start = idx
            if (not active or idx == len(row) - 1) and start is not None:
                end = idx if active else idx - 1
                segments.append((row_idx, start, end))
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


def update_touched_by_segment(rows, row_idx, bounds, p1, p2, touched):
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


def _active_count(rows):
    return sum(1 for row in rows for piece in row if piece)


def _nim_sum(rows):
    nim_sum = 0
    for _row_idx, lo, hi in get_segments(rows):
        nim_sum ^= hi - lo + 1
    return nim_sum


def _all_normal_moves(rows):
    moves = []
    seen = set()
    for row_idx, lo, hi in get_segments(rows):
        length = hi - lo + 1
        for remove in range(1, length + 1):
            candidates = [(row_idx, lo, lo + remove - 1), (row_idx, hi - remove + 1, hi)]
            for move in candidates:
                if move in seen:
                    continue
                seen.add(move)
                moves.append(move)
    return moves


def _random_normal_move(rows):
    segments = get_segments(rows)
    if not segments:
        return None
    row_idx, lo, hi = random.choice(segments)
    length = hi - lo + 1
    remove = random.randint(1, length)
    if random.random() < 0.5:
        return row_idx, lo, lo + remove - 1
    return row_idx, hi - remove + 1, hi


def _optimal_normal_move(rows):
    moves = _all_normal_moves(rows)
    if not moves:
        return None
    nim_sum = _nim_sum(rows)
    if nim_sum == 0:
        return random.choice(moves)

    best = []
    move_set = set(moves)
    for row_idx, lo, hi in get_segments(rows):
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


def _opponent_can_finish_next(rows, ai_context):
    for move in _all_normal_moves(rows):
        next_rows, _removed = _apply_normal(rows, move)
        if _active_count(next_rows) == 0:
            return True

    if ai_context.get("opponent_skill_used", True):
        return False
    opponent_finish_checker = ai_context.get("opponent_can_finish_with_skill")
    if callable(opponent_finish_checker):
        return bool(opponent_finish_checker(rows, ai_context))
    return False


def _evaluate_result(rows_before, rows_after, removed_count, ai_context):
    remaining = _active_count(rows_after)
    if remaining == 0:
        return 100000

    score = removed_count * 5
    if _nim_sum(rows_after) == 0:
        score += 35
    else:
        score -= 8

    if remaining <= 2:
        score -= 70
    elif remaining <= 4:
        score -= 20

    if _nim_sum(rows_before) == 0 and _nim_sum(rows_after) == 0:
        score += 10

    if _opponent_can_finish_next(rows_after, ai_context):
        score -= 80
    return score


def _to_normal_action(move):
    row_idx, start_idx, end_idx = move
    return {"type": "normal", "row": row_idx, "start": start_idx, "end": end_idx}


def copy_rows(rows):
    return _copy_rows(rows)


def active_count(rows):
    return _active_count(rows)


def nim_sum(rows):
    return _nim_sum(rows)


def all_normal_moves(rows):
    return _all_normal_moves(rows)


def apply_normal(rows, move):
    return _apply_normal(rows, move)


def evaluate_result(rows_before, rows_after, removed_count, ai_context):
    return _evaluate_result(rows_before, rows_after, removed_count, ai_context)


def nim_ai_move(rows, difficulty, ai_context=None):
    """
    Return AI action.

    Backward compatibility:
    - If ai_context is None, return (row_idx, start_idx, end_idx) like the old API.
    - If ai_context is provided, return an action dict with type:
      normal / skill
    """
    legal_normal_moves = _all_normal_moves(rows)
    if not legal_normal_moves:
        return None

    if difficulty == "optimal":
        normal_move = _optimal_normal_move(rows)
    elif difficulty == "medium":
        normal_move = _optimal_normal_move(rows) if random.random() < 0.7 else random.choice(legal_normal_moves)
    else:
        normal_move = random.choice(legal_normal_moves)

    if ai_context is None:
        return normal_move

    normal_rows, normal_removed = _apply_normal(rows, normal_move)
    normal_score = _evaluate_result(rows, normal_rows, normal_removed, ai_context)
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

    if difficulty == "random":
        if skill_immediate_win:
            return skill_action if random.random() < 0.85 else normal_action
        return skill_action if random.random() < 0.30 else normal_action

    if difficulty == "medium":
        if skill_immediate_win:
            return skill_action
        disadvantaged = _nim_sum(rows) == 0
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
