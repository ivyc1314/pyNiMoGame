import math
import os
import random
import time
from array import array

import pygame


WIDTH, HEIGHT = 1080, 720
FPS = 60

BG_COLOR = (242, 245, 248)
BG_TOP = (232, 242, 252)
BG_BOTTOM = (198, 220, 238)
CLOUD_1 = (255, 231, 215, 120)
CLOUD_2 = (210, 230, 255, 130)
CLOUD_3 = (255, 255, 255, 90)
CIRCLE_COLOR = (60, 90, 120)
CIRCLE_HL = (240, 100, 80)
BROKEN_COLOR = (170, 178, 188)
BROKEN_EDGE = (120, 128, 140)
TEXT_COLOR = (30, 40, 50)
TITLE_COLOR = (24, 44, 66)
SUBTEXT_COLOR = (60, 70, 85)
TRAIL_COLOR = (255, 205, 170)
TRAIL_GLOW = (255, 235, 210)
CANCEL_BG = (240, 118, 96)
CANCEL_HL = (255, 150, 130)
CANCEL_TEXT = (255, 255, 255)
CANCEL_BORDER = (182, 78, 64)
BTN_COLOR = (225, 230, 235)
BTN_HL = (180, 210, 240)
BTN_TEXT = (30, 40, 50)
BTN_BORDER = (175, 188, 202)
BTN_SHADOW = (0, 0, 0, 28)
PANEL_BG = (247, 250, 252, 235)
PANEL_BORDER = (178, 192, 206)
INFO_BG = (255, 255, 255, 210)
OVERLAY_BG = (0, 0, 0, 120)

RADIUS = 22
GAP = 16
ROW_SPACING = 140
TOP_Y = 260

ROW_INIT = [3, 4, 5]
AI_DELAY = 0.4
SLASH_DURATION = 0.3


def clamp(value, min_v, max_v):
    return max(min_v, min(max_v, value))


def point_in_circle(px, py, cx, cy, r):
    return (px - cx) ** 2 + (py - cy) ** 2 <= r ** 2


def generate_slash_sound():
    sample_rate = 22050
    duration = 0.12
    total = int(sample_rate * duration)
    data = array("h")
    for i in range(total):
        t = i / total
        amp = (1.0 - t) ** 2
        noise = (random.random() * 2.0 - 1.0) * 12000
        tone = math.sin(2 * math.pi * 320 * t) * 4000
        value = int(amp * (noise + tone))
        data.append(clamp(value, -32768, 32767))
    return pygame.mixer.Sound(buffer=data.tobytes())


class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text

    def draw(self, surface, font, selected=False):
        color = BTN_HL if selected else BTN_COLOR
        shadow_rect = self.rect.move(2, 3)
        pygame.draw.rect(surface, BTN_SHADOW, shadow_rect, border_radius=10)
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, BTN_BORDER, self.rect, 2, border_radius=10)
        label = font.render(self.text, True, BTN_TEXT)
        surface.blit(label, label.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.rect.collidepoint(pos)


class SlashEffect:
    def __init__(self, positions, duration=SLASH_DURATION):
        self.positions = positions
        self.duration = duration
        self.elapsed = 0.0
        self.particles = []
        for (x, y) in positions:
            for _ in range(5):
                angle = random.uniform(-math.pi / 2, math.pi / 2)
                speed = random.uniform(80, 180)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed - 40
                self.particles.append([x, y, vx, vy, random.uniform(0.2, 0.35)])

    def update(self, dt):
        self.elapsed += dt
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.94
            p[3] = p[3] * 0.94 + 120 * dt
            p[4] -= dt

    def finished(self):
        return self.elapsed >= self.duration

    def draw(self, surface):
        if not self.positions:
            return
        progress = clamp(self.elapsed / self.duration, 0.0, 1.0)
        alpha = int(255 * (1.0 - progress))
        fx = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        first = self.positions[0]
        last = self.positions[-1]
        start = (first[0] - RADIUS * 0.6, first[1] - RADIUS * 0.4)
        end = (last[0] + RADIUS * 0.6, last[1] + RADIUS * 0.4)
        pygame.draw.line(fx, (255, 230, 210, alpha), start, end, 5)
        pygame.draw.line(
            fx,
            (255, 200, 170, int(alpha * 0.7)),
            (start[0] + 4, start[1] - 2),
            (end[0] + 4, end[1] - 2),
            2,
        )

        for x, y, _, _, life in self.particles:
            if life <= 0:
                continue
            a = int(255 * clamp(life / 0.35, 0.0, 1.0))
            pygame.draw.circle(fx, (255, 220, 200, a), (int(x), int(y)), 3)

        surface.blit(fx, (0, 0))


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


def x_to_index(rows, row_idx, x):
    count = len(rows[row_idx])
    row_width = count * (RADIUS * 2 + GAP) - GAP
    start_x = (WIDTH - row_width) / 2
    rel = (x - start_x - RADIUS) / (RADIUS * 2 + GAP)
    idx = int(round(rel))
    return clamp(idx, 0, count - 1)


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


def draw_slash_trail(surface, points):
    if len(points) < 2:
        return
    fx = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    total = len(points) - 1
    for i in range(1, len(points)):
        t = i / max(total, 1)
        alpha = int(200 * t)
        width = int(2 + 5 * t)
        pygame.draw.line(
            fx, (*TRAIL_COLOR, alpha), points[i - 1], points[i], width
        )
    head = points[-1]
    pygame.draw.circle(fx, (*TRAIL_GLOW, 180), head, 10)
    surface.blit(fx, (0, 0))


def build_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / max(HEIGHT - 1, 1)
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        pygame.draw.line(bg, (r, g, b), (0, y), (WIDTH, y))

    clouds = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(clouds, CLOUD_1, (140, 120), 110)
    pygame.draw.circle(clouds, CLOUD_2, (720, 140), 140)
    pygame.draw.circle(clouds, CLOUD_3, (780, 440), 180)
    pygame.draw.circle(clouds, CLOUD_2, (250, 480), 150)
    return bg, clouds


def nim_ai_move(rows, difficulty):
    segments = get_segments(rows)
    if not segments:
        return None

    def random_move():
        row_idx, lo, hi = random.choice(segments)
        length = hi - lo + 1
        remove = random.randint(1, length)
        start = hi - remove + 1
        end = hi
        return row_idx, start, end

    use_optimal = difficulty == "optimal"
    if difficulty == "medium":
        use_optimal = random.random() < 0.7

    if not use_optimal:
        return random_move()

    nim_sum = 0
    for row_idx, lo, hi in segments:
        nim_sum ^= (hi - lo + 1)
    if nim_sum == 0:
        return random_move()

    for row_idx, lo, hi in segments:
        length = hi - lo + 1
        target = length ^ nim_sum
        if target < length:
            remove = length - target
            start = hi - remove + 1
            end = hi
            return row_idx, start, end
    return random_move()


def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("尼莫游戏")
    clock = pygame.time.Clock()
    def pick_font(size):
        candidates = [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\msyh.ttf",
            r"C:\Windows\Fonts\msyhbd.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\simkai.ttf",
            r"C:\Windows\Fonts\msjh.ttc",
            r"C:\Windows\Fonts\arialuni.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                return pygame.font.Font(path, size)
        return pygame.font.Font(None, size)

    font = pick_font(28)
    big_font = pick_font(52)
    label_font = pick_font(24)
    small_font = pick_font(22)
    button_font = pick_font(26)

    bg_surface, bg_clouds = build_background()

    slash_sound = None
    try:
        pygame.mixer.init()
        slash_sound = generate_slash_sound()
    except pygame.error:
        slash_sound = None

    difficulty = "optimal"
    first_player = "player"
    match_mode = "single"
    quick_mode = False
    game_number = 1
    match_wins = {"player": 0, "ai": 0}
    match_removed = {"player": 0, "ai": 0}
    game1_first = None
    game2_first = None
    current_player = "player"

    game_state = "main_menu"
    rows = [[True for _ in range(count)] for count in ROW_INIT]
    winner = None

    selecting = False
    select_row = None
    select_start = None
    select_end = None
    select_bounds = None
    select_touched = set()
    slash_points = []
    last_pos = None
    cancel_hover = False
    intro_timer = 0.0

    slash_effect = None
    pending_remove = None
    ai_timer = 0.0

    panel_rect = pygame.Rect(90, 70, WIDTH - 180, HEIGHT - 140)
    title_y = panel_rect.y + 54
    section_y = title_y + big_font.get_height() + 26
    label_y = section_y
    buttons_y = label_y + label_font.get_height() + 12
    left_x = panel_rect.x + 60
    right_x = panel_rect.centerx + 20
    btn_w = 220
    btn_h = 48
    btn_gap = 16
    main_btn_w = 260
    main_btn_h = 56
    main_btn_x = panel_rect.centerx - main_btn_w // 2
    main_btn_y = panel_rect.y + 170
    main_btn_gap = 22
    start_btn_y = panel_rect.bottom - 70
    cancel_rect = pygame.Rect(WIDTH - 170, 30, 140, 36)
    exit_button = Button((30, 18, 96, 36), "退出")

    main_buttons = [
        Button((main_btn_x, main_btn_y, main_btn_w, main_btn_h), "单人游戏"),
        Button(
            (main_btn_x, main_btn_y + main_btn_h + main_btn_gap, main_btn_w, main_btn_h),
            "规则",
        ),
    ]
    single_buttons = [
        Button((main_btn_x, main_btn_y, main_btn_w, main_btn_h), "快速游戏"),
        Button(
            (main_btn_x, main_btn_y + main_btn_h + main_btn_gap, main_btn_w, main_btn_h),
            "自定义对局",
        ),
    ]
    difficulty_buttons = [
        Button((left_x, buttons_y + i * (btn_h + btn_gap), btn_w, btn_h), label)
        for i, label in enumerate(["最优", "中等", "随机"])
    ]
    first_buttons = [
        Button((right_x, buttons_y + i * (btn_h + btn_gap), btn_w, btn_h), label)
        for i, label in enumerate(["玩家先手", "AI先手"])
    ]
    match_label_y = buttons_y + (btn_h + btn_gap) * 2 + 6
    match_buttons_y = match_label_y + label_font.get_height() + 10
    min_gap = 20
    max_match_y = start_btn_y - btn_h - min_gap
    if match_buttons_y > max_match_y:
        match_buttons_y = max_match_y
        match_label_y = match_buttons_y - label_font.get_height() - 8
    match_btn_w = (btn_w - 12) // 2
    match_buttons = [
        Button((right_x, match_buttons_y, match_btn_w, btn_h), "单局"),
        Button(
            (right_x + match_btn_w + 12, match_buttons_y, match_btn_w, btn_h),
            "三局两胜",
        ),
    ]
    start_button = Button(
        (panel_rect.centerx - 120, start_btn_y, 240, 56), "开始游戏"
    )
    back_button = Button((panel_rect.x + 24, panel_rect.bottom - 64, 160, 44), "返回")
    next_button = Button((WIDTH // 2 - 100, HEIGHT // 2 + 40, 200, 55), "下一局")
    restart_button = Button((WIDTH // 2 - 100, HEIGHT // 2 + 40, 200, 55), "再来一局")
    menu_button = Button((WIDTH // 2 - 100, HEIGHT // 2 + 110, 200, 55), "返回主菜单")

    def difficulty_text():
        if difficulty == "optimal":
            return "最优"
        if difficulty == "medium":
            return "中等"
        return "随机"

    def generate_rows():
        while True:
            rows = [random.randint(2, 6) for _ in range(3)]
            if sum(rows) <= 8:
                continue
            nim_sum = 0
            for c in rows:
                nim_sum ^= c
            if nim_sum != 0:
                return rows

    def clear_round_state():
        nonlocal winner, selecting, select_row, select_start, select_end
        nonlocal select_bounds, select_touched, slash_points, last_pos, cancel_hover
        nonlocal slash_effect, pending_remove
        winner = None
        selecting = False
        select_row = None
        select_start = None
        select_end = None
        select_bounds = None
        select_touched = set()
        slash_points = []
        last_pos = None
        cancel_hover = False
        slash_effect = None
        pending_remove = None

    def begin_game(first):
        nonlocal rows, current_player, game_state, ai_timer, intro_timer
        if match_mode == "best3" or quick_mode:
            rows = [[True for _ in range(c)] for c in generate_rows()]
        else:
            rows = [[True for _ in range(c)] for c in ROW_INIT]
        clear_round_state()
        current_player = first
        if match_mode == "best3" or quick_mode:
            intro_timer = 1.6
            game_state = "round_intro"
        else:
            game_state = "playing"
        ai_timer = AI_DELAY if current_player == "ai" else 0.0

    def determine_first(game_index):
        if quick_mode:
            if game_index == 1:
                return random.choice(["player", "ai"])
            if game_index == 2:
                return "ai" if game1_first == "player" else "player"
            if game_index == 3:
                if match_removed["player"] < match_removed["ai"]:
                    return "player"
                if match_removed["ai"] < match_removed["player"]:
                    return "ai"
                return "ai" if game2_first == "player" else "player"
        if match_mode == "single":
            return first_player
        return (
            first_player
            if game_index % 2 == 1
            else ("ai" if first_player == "player" else "player")
        )

    def start_match(mode, quick=False):
        nonlocal match_mode, quick_mode, game_number, match_wins, match_removed
        nonlocal game1_first, game2_first
        match_mode = mode
        quick_mode = quick
        game_number = 1
        match_wins = {"player": 0, "ai": 0}
        match_removed = {"player": 0, "ai": 0}
        game1_first = None
        game2_first = None
        first = determine_first(1)
        if quick_mode:
            game1_first = first
        begin_game(first)

    def start_next_game():
        nonlocal game_number, game2_first
        game_number += 1
        first = determine_first(game_number)
        if quick_mode and game_number == 2:
            game2_first = first
        begin_game(first)

    def match_complete():
        if match_mode == "single" and not quick_mode:
            return True
        return (
            match_wins["player"] >= 2
            or match_wins["ai"] >= 2
            or game_number >= 3
        )

    def return_to_menu():
        nonlocal game_state, quick_mode, game_number, match_wins, match_removed
        nonlocal game1_first, game2_first, ai_timer, intro_timer
        clear_round_state()
        quick_mode = False
        game_number = 1
        match_wins = {"player": 0, "ai": 0}
        match_removed = {"player": 0, "ai": 0}
        game1_first = None
        game2_first = None
        ai_timer = 0.0
        intro_timer = 0.0
        game_state = "main_menu"

    def draw_panel(title):
        panel_surface = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            panel_surface, PANEL_BG, panel_surface.get_rect(), border_radius=20
        )
        pygame.draw.rect(
            panel_surface, PANEL_BORDER, panel_surface.get_rect(), 2, border_radius=20
        )
        screen.blit(panel_surface, panel_rect.topleft)
        title_label = big_font.render(title, True, TITLE_COLOR)
        screen.blit(title_label, title_label.get_rect(center=(WIDTH // 2, title_y)))

    def start_slash(row_idx, start_idx, end_idx, actor):
        nonlocal slash_effect, pending_remove
        centers = get_row_centers(rows)
        if row_idx < 0 or row_idx >= len(centers):
            return
        lo = min(start_idx, end_idx)
        hi = max(start_idx, end_idx)
        positions = centers[row_idx][lo : hi + 1]
        slash_effect = SlashEffect(positions)
        pending_remove = (row_idx, lo, hi, actor)
        if slash_sound:
            slash_sound.play()

    def apply_pending():
        nonlocal pending_remove, slash_effect, current_player, game_state, winner, ai_timer
        if not pending_remove:
            return
        row_idx, lo, hi, actor = pending_remove
        removed_count = hi - lo + 1
        for idx in range(lo, hi + 1):
            rows[row_idx][idx] = False
        if quick_mode and game_number <= 2:
            match_removed[actor] += removed_count
        pending_remove = None
        slash_effect = None
        if all(not piece for row in rows for piece in row):
            winner = actor
            if match_mode == "best3" or quick_mode:
                match_wins[winner] += 1
            game_state = "gameover"
            return
        current_player = "ai" if actor == "player" else "player"
        if current_player == "ai":
            ai_timer = AI_DELAY

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_state == "main_menu":
                    if main_buttons[0].hit(event.pos):
                        game_state = "single_menu"
                    elif main_buttons[1].hit(event.pos):
                        game_state = "rules"
                elif game_state == "single_menu":
                    if single_buttons[0].hit(event.pos):
                        game_state = "quick_menu"
                    elif single_buttons[1].hit(event.pos):
                        game_state = "custom_menu"
                    elif back_button.hit(event.pos):
                        game_state = "main_menu"
                elif game_state == "quick_menu":
                    for idx, btn in enumerate(difficulty_buttons):
                        if btn.hit(event.pos):
                            difficulty = ["optimal", "medium", "random"][idx]
                    if start_button.hit(event.pos):
                        start_match("best3", quick=True)
                    elif back_button.hit(event.pos):
                        game_state = "single_menu"
                elif game_state == "custom_menu":
                    for idx, btn in enumerate(difficulty_buttons):
                        if btn.hit(event.pos):
                            difficulty = ["optimal", "medium", "random"][idx]
                    for idx, btn in enumerate(first_buttons):
                        if btn.hit(event.pos):
                            first_player = ["player", "ai"][idx]
                    for idx, btn in enumerate(match_buttons):
                        if btn.hit(event.pos):
                            match_mode = ["single", "best3"][idx]
                    if start_button.hit(event.pos):
                        start_match(match_mode, quick=False)
                    elif back_button.hit(event.pos):
                        game_state = "single_menu"
                elif game_state == "rules":
                    if back_button.hit(event.pos):
                        game_state = "main_menu"

            if game_state == "playing":
                if current_player == "player" and not slash_effect:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        selecting = True
                        select_row = None
                        select_start = None
                        select_end = None
                        select_bounds = None
                        select_touched = set()
                        slash_points = [event.pos]
                        last_pos = event.pos
                        cancel_hover = False

                        hit = find_circle(rows, event.pos)
                        if hit:
                            select_row, select_start = hit
                            select_bounds = get_segment_bounds(rows, select_row, select_start)
                            if select_bounds:
                                select_touched.add(select_start)
                                select_end = select_start
                    elif event.type == pygame.MOUSEMOTION and selecting:
                        if last_pos is None:
                            last_pos = event.pos
                        slash_points.append(event.pos)
                        if len(slash_points) > 14:
                            slash_points.pop(0)

                        if select_row is not None:
                            cancel_hover = cancel_rect.collidepoint(event.pos)
                        else:
                            cancel_hover = False

                        if select_row is None:
                            hit = find_hit_by_segment(rows, last_pos, event.pos)
                            if hit:
                                select_row, select_start = hit
                                select_bounds = get_segment_bounds(
                                    rows, select_row, select_start
                                )
                                if select_bounds:
                                    select_touched.add(select_start)
                                    select_end = select_start
                        if select_row is not None and select_bounds is not None:
                            update_touched_by_segment(
                                rows,
                                select_row,
                                select_bounds,
                                last_pos,
                                event.pos,
                                select_touched,
                            )
                            if select_touched:
                                select_start = min(select_touched)
                                select_end = max(select_touched)
                        last_pos = event.pos
                    elif event.type == pygame.MOUSEBUTTONUP and selecting:
                        selecting = False
                        last_pos = None
                        slash_points = []
                        if cancel_hover:
                            select_row = None
                            select_start = None
                            select_end = None
                            select_bounds = None
                            select_touched = set()
                            cancel_hover = False
                        elif select_row is not None and select_start is not None:
                            start_slash(select_row, select_start, select_end, "player")
                            select_row = None
                            select_start = None
                            select_end = None
                            select_bounds = None
                            select_touched = set()
                            cancel_hover = False

            if event.type == pygame.MOUSEBUTTONDOWN and game_state in ("playing", "round_intro"):
                if exit_button.hit(event.pos):
                    return_to_menu()

            if game_state == "gameover" and event.type == pygame.MOUSEBUTTONDOWN:
                if match_complete() and menu_button.hit(event.pos):
                    return_to_menu()
                elif match_complete():
                    if restart_button.hit(event.pos):
                        if quick_mode:
                            start_match("best3", quick=True)
                        elif match_mode == "best3":
                            start_match("best3", quick=False)
                        else:
                            begin_game(first_player)
                elif next_button.hit(event.pos):
                    start_next_game()

        if game_state == "round_intro":
            intro_timer -= dt
            if intro_timer <= 0:
                game_state = "playing"

        if game_state == "playing":
            if slash_effect:
                slash_effect.update(dt)
                if slash_effect.finished():
                    apply_pending()
            elif current_player == "ai":
                ai_timer -= dt
                if ai_timer <= 0:
                    move = nim_ai_move(rows, difficulty)
                    if move:
                        row_idx, start_idx, end_idx = move
                        start_slash(row_idx, start_idx, end_idx, "ai")

        screen.blit(bg_surface, (0, 0))
        screen.blit(bg_clouds, (0, 0))

        if game_state in ("playing", "gameover"):
            centers = get_row_centers(rows)
            for row_idx, row in enumerate(centers):
                for idx, (x, y) in enumerate(row):
                    if rows[row_idx][idx]:
                        color = CIRCLE_COLOR
                        if selecting and row_idx == select_row:
                            lo = min(select_start, select_end)
                            hi = max(select_start, select_end)
                            if lo <= idx <= hi:
                                color = CIRCLE_HL
                        pygame.draw.circle(screen, color, (int(x), int(y)), RADIUS)
                    else:
                        pygame.draw.circle(
                            screen, BROKEN_COLOR, (int(x), int(y)), RADIUS
                        )
                        pygame.draw.circle(
                            screen, BROKEN_EDGE, (int(x), int(y)), RADIUS, 2
                        )
                        pygame.draw.line(
                            screen,
                            BROKEN_EDGE,
                            (int(x - RADIUS * 0.5), int(y - 2)),
                            (int(x + RADIUS * 0.4), int(y + 6)),
                            2,
                        )
                        pygame.draw.line(
                            screen,
                            BROKEN_EDGE,
                            (int(x - RADIUS * 0.1), int(y + 8)),
                            (int(x + RADIUS * 0.5), int(y - 6)),
                            2,
                        )

            if game_state == "playing":
                exit_button.draw(screen, button_font, selected=False)

            info_rect = pygame.Rect(140, 18, WIDTH - 420, 190)
            info_surface = pygame.Surface(info_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                info_surface, INFO_BG, info_surface.get_rect(), border_radius=16
            )
            pygame.draw.rect(
                info_surface,
                PANEL_BORDER,
                info_surface.get_rect(),
                2,
                border_radius=16,
            )
            screen.blit(info_surface, info_rect.topleft)

            pad = 12
            gap = 6
            y = info_rect.y + pad
            turn_text = f"当前回合：{'玩家' if current_player == 'player' else 'AI'}"
            info = font.render(turn_text, True, TEXT_COLOR)
            screen.blit(info, (info_rect.x + 20, y))
            y += font.get_height() + gap

            diff_text = f"难度：{difficulty_text()}"
            info2 = font.render(diff_text, True, TEXT_COLOR)
            screen.blit(info2, (info_rect.x + 20, y))
            if quick_mode:
                removed_line = (
                    f"前两局已删除：玩家{match_removed['player']} - AI{match_removed['ai']}"
                )
                removed_label = small_font.render(removed_line, True, SUBTEXT_COLOR)
                removed_x = info_rect.x + 20 + info2.get_width() + 16
                removed_y = y + (font.get_height() - removed_label.get_height()) // 2
                if removed_x + removed_label.get_width() > info_rect.right - 20:
                    y += font.get_height() + gap
                    removed_x = info_rect.x + 20
                    removed_y = y
                screen.blit(removed_label, (removed_x, removed_y))
            y += font.get_height() + gap

            if quick_mode:
                mode_line = f"快速赛 第{game_number}局/3"
                score_line = f"比分：玩家{match_wins['player']} - AI{match_wins['ai']}"
            elif match_mode == "best3":
                mode_line = f"三局两胜 第{game_number}局/3"
                score_line = f"比分：玩家{match_wins['player']} - AI{match_wins['ai']}"
            else:
                mode_line = "模式：单局"
                score_line = ""

            mode_label = small_font.render(mode_line, True, SUBTEXT_COLOR)
            screen.blit(mode_label, (info_rect.x + 20, y))
            y += small_font.get_height() + gap

            if score_line:
                score_label = small_font.render(score_line, True, SUBTEXT_COLOR)
                screen.blit(score_label, (info_rect.x + 20, y))
                y += small_font.get_height() + gap

            if game_state == "playing":
                hint = small_font.render("拖拽同一行连续划过即可取子", True, SUBTEXT_COLOR)
                hint_x = info_rect.right - 20 - hint.get_width()
                hint_y = info_rect.y + pad + (font.get_height() - hint.get_height()) // 2
                if hint_x < info_rect.x + 20 + info.get_width() + 12:
                    hint_y = info_rect.y + pad + font.get_height() + gap
                    hint_x = info_rect.right - 20 - hint.get_width()
                screen.blit(hint, (hint_x, hint_y))

            if slash_effect:
                slash_effect.draw(screen)
            if selecting and slash_points:
                draw_slash_trail(screen, slash_points)
            if selecting and select_row is not None:
                cancel_color = CANCEL_HL if cancel_hover else CANCEL_BG
                pygame.draw.rect(screen, cancel_color, cancel_rect, border_radius=10)
                pygame.draw.rect(screen, CANCEL_BORDER, cancel_rect, 2, border_radius=10)
                cancel_label = small_font.render("取消", True, CANCEL_TEXT)
                screen.blit(
                    cancel_label, cancel_label.get_rect(center=cancel_rect.center)
                )

        if game_state == "main_menu":
            draw_panel("尼莫游戏")
            for btn in main_buttons:
                btn.draw(screen, button_font)

        if game_state == "single_menu":
            draw_panel("单人游戏")
            for btn in single_buttons:
                btn.draw(screen, button_font)
            back_button.draw(screen, button_font)

        if game_state == "quick_menu":
            draw_panel("快速游戏")
            label1 = label_font.render("AI难度", True, SUBTEXT_COLOR)
            screen.blit(label1, (left_x, label_y))
            for idx, btn in enumerate(difficulty_buttons):
                selected = difficulty == ["optimal", "medium", "random"][idx]
                btn.draw(screen, button_font, selected=selected)
            quick_lines = [
                "三局两胜",
                "第1局先手随机",
                "第2局先手交换",
                "第3局先手：前两局总删除数更少者",
                "平局：第2局后手先",
            ]
            quick_y = label_y
            for line in quick_lines:
                quick_label = small_font.render(line, True, SUBTEXT_COLOR)
                screen.blit(quick_label, (right_x, quick_y))
                quick_y += 26
            start_button.draw(screen, button_font, selected=False)
            back_button.draw(screen, button_font)

        if game_state == "custom_menu":
            draw_panel("自定义对局")
            label1 = label_font.render("选择难度", True, SUBTEXT_COLOR)
            screen.blit(label1, (left_x, label_y))
            for idx, btn in enumerate(difficulty_buttons):
                selected = difficulty == ["optimal", "medium", "random"][idx]
                btn.draw(screen, button_font, selected=selected)

            label2 = label_font.render("先手", True, SUBTEXT_COLOR)
            screen.blit(label2, (right_x, label_y))
            for idx, btn in enumerate(first_buttons):
                selected = first_player == ["player", "ai"][idx]
                btn.draw(screen, button_font, selected=selected)

            label3 = label_font.render("对局模式", True, SUBTEXT_COLOR)
            screen.blit(label3, (right_x, match_label_y))
            for idx, btn in enumerate(match_buttons):
                selected = match_mode == ["single", "best3"][idx]
                btn.draw(screen, button_font, selected=selected)

            start_button.draw(screen, button_font, selected=False)
            back_button.draw(screen, button_font)

        if game_state == "rules":
            draw_panel("规则")
            rules_lines = [
                "1. 同一横排连续划过即可移除。",
                "2. 碎裂棋子会阻挡，不能跨越。",
                "3. 单人模式对AI。",
                "4. 快速游戏为三局两胜。",
                "5. 第1局先手随机，第2局先手交换。",
                "6. 第3局先手：前两局总删除数更少者。",
                "7. 平局：第2局后手先。",
            ]
            rule_y = panel_rect.y + 140
            for line in rules_lines:
                rule_label = small_font.render(line, True, SUBTEXT_COLOR)
                screen.blit(rule_label, (panel_rect.x + 40, rule_y))
                rule_y += 28
            back_button.draw(screen, button_font)

        if game_state == "round_intro":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill(OVERLAY_BG)
            screen.blit(overlay, (0, 0))
            mode_name = "快速赛" if quick_mode else "三局两胜"
            title = big_font.render(f"{mode_name} 第{game_number}局", True, (255, 255, 255))
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30)))
            score_text = f"当前比分 玩家{match_wins['player']} - AI{match_wins['ai']}"
            score_label = small_font.render(score_text, True, (255, 255, 255))
            screen.blit(
                score_label, score_label.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
            )
            first_text = f"先手：{'玩家' if current_player == 'player' else 'AI'}"
            first_label = small_font.render(first_text, True, (255, 255, 255))
            screen.blit(
                first_label, first_label.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 38))
            )

        if game_state == "gameover":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill(OVERLAY_BG)
            screen.blit(overlay, (0, 0))
            if match_complete() and (match_mode == "best3" or quick_mode):
                overall_winner = (
                    "玩家" if match_wins["player"] > match_wins["ai"] else "AI"
                )
                msg = f"比赛结束：{overall_winner}获胜！"
                label = big_font.render(msg, True, (255, 255, 255))
                screen.blit(
                    label, label.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
                )
                score_text = f"比分 玩家{match_wins['player']} - AI{match_wins['ai']}"
                score_label = small_font.render(score_text, True, (255, 255, 255))
                screen.blit(
                    score_label, score_label.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 8))
                )
                restart_button.text = "再来一组"
                restart_button.draw(screen, button_font)
            else:
                msg = f"{'玩家' if winner == 'player' else 'AI'} 获胜！"
                label = big_font.render(msg, True, (255, 255, 255))
                screen.blit(
                    label, label.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20))
                )
                if match_mode == "best3" or quick_mode:
                    next_button.draw(screen, button_font)
                else:
                    restart_button.text = "再来一局"
                    restart_button.draw(screen, button_font)
            if match_complete():
                menu_button.draw(screen, button_font)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
