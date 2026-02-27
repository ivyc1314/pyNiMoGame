import random
from constants import GAP, RADIUS, ROW_SPACING, TOP_Y, WIDTH


def clamp(value, min_v, max_v):
    return max(min_v, min(max_v, value))


def point_in_circle(px, py, cx, cy, r):
    return (px - cx) ** 2 + (py - cy) ** 2 <= r ** 2


def get_row_centers(rows):
    centers = []
    for i, row in enumerate(rows):
        count = len(row)
        row_width = count * (RADIUS * 2 + GAP) - GAP
        start_x = (WIDTH - row_width) / 2
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


def get_segment_bounds(rows, row_idx, index):
    if not rows[row_idx][index]:
        return None
    lo = index
    while lo - 1 >= 0 and rows[row_idx][lo - 1]:
        lo -= 1
    hi = index
    max_idx = len(rows[row_idx]) - 1
    while hi + 1 <= max_idx and rows[row_idx][hi + 1]:
        hi += 1
    return lo, hi


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


def nim_ai_move(rows, difficulty):
    segments = get_segments(rows)
    if not segments:
        return None

    def edge_move(lo, hi, remove):
        if random.random() < 0.5:
            start = lo
            end = lo + remove - 1
        else:
            start = hi - remove + 1
            end = hi
        return start, end

    def random_move():
        row_idx, lo, hi = random.choice(segments)
        length = hi - lo + 1
        remove = random.randint(1, length)
        start, end = edge_move(lo, hi, remove)
        return row_idx, start, end

    use_optimal = difficulty == "optimal"
    if difficulty == "medium":
        use_optimal = random.random() < 0.7

    if not use_optimal:
        return random_move()

    nim_sum = 0
    for row_idx, lo, hi in segments:
        nim_sum ^= hi - lo + 1
    if nim_sum == 0:
        return random_move()

    for row_idx, lo, hi in segments:
        length = hi - lo + 1
        target = length ^ nim_sum
        if target < length:
            remove = length - target
            start, end = edge_move(lo, hi, remove)
            return row_idx, start, end
    return random_move()
