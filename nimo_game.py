import math
import os
import random
import time
from array import array

import pygame


WIDTH, HEIGHT = 900, 600
FPS = 60

BG_COLOR = (242, 245, 248)
CIRCLE_COLOR = (60, 90, 120)
CIRCLE_HL = (240, 100, 80)
TEXT_COLOR = (30, 40, 50)
BTN_COLOR = (225, 230, 235)
BTN_HL = (180, 210, 240)
BTN_TEXT = (30, 40, 50)
OVERLAY_BG = (0, 0, 0, 120)

RADIUS = 22
GAP = 16
ROW_SPACING = 120
TOP_Y = 170

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
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (180, 190, 200), self.rect, 2, border_radius=8)
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
    for i, count in enumerate(rows):
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
            if point_in_circle(pos[0], pos[1], x, y, RADIUS):
                return row_idx, idx
    return None


def x_to_index(rows, row_idx, x):
    count = rows[row_idx]
    row_width = count * (RADIUS * 2 + GAP) - GAP
    start_x = (WIDTH - row_width) / 2
    rel = (x - start_x - RADIUS) / (RADIUS * 2 + GAP)
    idx = int(round(rel))
    return clamp(idx, 0, count - 1)


def nim_ai_move(rows, difficulty):
    available = [i for i, c in enumerate(rows) if c > 0]
    if not available:
        return None

    def random_move():
        row = random.choice(available)
        remove = random.randint(1, rows[row])
        return row, remove

    use_optimal = difficulty == "optimal"
    if difficulty == "medium":
        use_optimal = random.random() < 0.7

    if not use_optimal:
        return random_move()

    nim_sum = 0
    for c in rows:
        nim_sum ^= c
    if nim_sum == 0:
        return random_move()

    for i, c in enumerate(rows):
        target = c ^ nim_sum
        if target < c:
            remove = c - target
            return i, remove
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

    font = pick_font(32)
    big_font = pick_font(48)

    slash_sound = None
    try:
        pygame.mixer.init()
        slash_sound = generate_slash_sound()
    except pygame.error:
        slash_sound = None

    difficulty = "optimal"
    first_player = "player"
    current_player = "player"

    game_state = "menu"
    rows = ROW_INIT[:]
    winner = None

    selecting = False
    select_row = None
    select_start = None
    select_end = None

    slash_effect = None
    pending_remove = None
    ai_timer = 0.0

    menu_buttons = [
        Button((120, 120, 170, 46), "最优"),
        Button((120, 180, 170, 46), "中等"),
        Button((120, 240, 170, 46), "随机"),
    ]
    first_buttons = [
        Button((360, 120, 170, 46), "玩家先手"),
        Button((360, 180, 170, 46), "AI先手"),
    ]
    start_button = Button((620, 200, 200, 60), "开始游戏")
    restart_button = Button((WIDTH // 2 - 100, HEIGHT // 2 + 60, 200, 55), "再来一局")

    def reset_game():
        nonlocal rows, current_player, game_state, winner, selecting, select_row, select_start, select_end
        nonlocal slash_effect, pending_remove, ai_timer
        rows = ROW_INIT[:]
        winner = None
        selecting = False
        select_row = None
        select_start = None
        select_end = None
        slash_effect = None
        pending_remove = None
        current_player = first_player
        game_state = "playing"
        ai_timer = AI_DELAY if current_player == "ai" else 0.0

    def start_slash(row_idx, start_idx, end_idx, actor):
        nonlocal slash_effect, pending_remove
        centers = get_row_centers(rows)
        if row_idx < 0 or row_idx >= len(centers):
            return
        lo = min(start_idx, end_idx)
        hi = max(start_idx, end_idx)
        positions = centers[row_idx][lo : hi + 1]
        slash_effect = SlashEffect(positions)
        pending_remove = (row_idx, hi - lo + 1, actor)
        if slash_sound:
            slash_sound.play()

    def apply_pending():
        nonlocal pending_remove, slash_effect, current_player, game_state, winner, ai_timer
        if not pending_remove:
            return
        row_idx, remove_count, actor = pending_remove
        rows[row_idx] = max(0, rows[row_idx] - remove_count)
        pending_remove = None
        slash_effect = None
        if all(c == 0 for c in rows):
            winner = actor
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

            if game_state == "menu" and event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                for idx, btn in enumerate(menu_buttons):
                    if btn.hit(pos):
                        difficulty = ["optimal", "medium", "random"][idx]
                for idx, btn in enumerate(first_buttons):
                    if btn.hit(pos):
                        first_player = ["player", "ai"][idx]
                if start_button.hit(pos):
                    reset_game()

            if game_state == "playing":
                if current_player == "player" and not slash_effect:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        hit = find_circle(rows, event.pos)
                        if hit:
                            selecting = True
                            select_row, select_start = hit
                            select_end = select_start
                    elif event.type == pygame.MOUSEMOTION and selecting:
                        if select_row is not None:
                            select_end = x_to_index(rows, select_row, event.pos[0])
                    elif event.type == pygame.MOUSEBUTTONUP and selecting:
                        selecting = False
                        if select_row is not None and select_start is not None:
                            start_slash(select_row, select_start, select_end, "player")
                            select_row = None
                            select_start = None
                            select_end = None

            if game_state == "gameover" and event.type == pygame.MOUSEBUTTONDOWN:
                if restart_button.hit(event.pos):
                    reset_game()

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
                        row_idx, remove_count = move
                        start_idx = rows[row_idx] - remove_count
                        end_idx = rows[row_idx] - 1
                        start_slash(row_idx, start_idx, end_idx, "ai")

        screen.fill(BG_COLOR)

        if game_state in ("playing", "gameover"):
            centers = get_row_centers(rows)
            for row_idx, row in enumerate(centers):
                for idx, (x, y) in enumerate(row):
                    color = CIRCLE_COLOR
                    if selecting and row_idx == select_row:
                        lo = min(select_start, select_end)
                        hi = max(select_start, select_end)
                        if lo <= idx <= hi:
                            color = CIRCLE_HL
                    pygame.draw.circle(screen, color, (int(x), int(y)), RADIUS)

            turn_text = f"轮到：{'玩家' if current_player == 'player' else 'AI'}"
            info = font.render(turn_text, True, TEXT_COLOR)
            screen.blit(info, (40, 30))
            diff_text = f"难度：{'最优' if difficulty == 'optimal' else '中等' if difficulty == 'medium' else '随机'}"
            info2 = font.render(diff_text, True, TEXT_COLOR)
            screen.blit(info2, (40, 65))
            hint = font.render("拖拽同一行连续划圆", True, TEXT_COLOR)
            screen.blit(hint, (40, 100))

            if slash_effect:
                slash_effect.draw(screen)

        if game_state == "menu":
            title = big_font.render("尼莫游戏", True, TEXT_COLOR)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 50)))

            label1 = font.render("选择难度", True, TEXT_COLOR)
            screen.blit(label1, (120, 90))
            for idx, btn in enumerate(menu_buttons):
                selected = difficulty == ["optimal", "medium", "random"][idx]
                btn.draw(screen, font, selected=selected)

            label2 = font.render("先手", True, TEXT_COLOR)
            screen.blit(label2, (360, 90))
            for idx, btn in enumerate(first_buttons):
                selected = first_player == ["player", "ai"][idx]
                btn.draw(screen, font, selected=selected)

            start_button.draw(screen, font, selected=False)

        if game_state == "gameover":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill(OVERLAY_BG)
            screen.blit(overlay, (0, 0))
            msg = f"{'玩家' if winner == 'player' else 'AI'} 获胜！"
            label = big_font.render(msg, True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            restart_button.draw(screen, font)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
