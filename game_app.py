import glob
import os
import random
import math

import pygame

from constants import HEIGHT, RADIUS, WIDTH
from game_logic import (
    find_circle,
    find_hit_by_segment,
    get_row_centers,
    get_segment_bounds,
    nim_ai_move,
    update_touched_by_segment,
)
from ui_components import (
    Button,
    SlashEffect,
    build_background,
    draw_slash_trail,
    generate_slash_sound,
)


FPS = 60

CIRCLE_COLOR = (60, 90, 120)
CIRCLE_HL = (240, 100, 80)
BROKEN_COLOR = (170, 178, 188)
BROKEN_EDGE = (120, 128, 140)
TEXT_COLOR = (30, 40, 50)
TITLE_COLOR = (24, 44, 66)
SUBTEXT_COLOR = (60, 70, 85)
CANCEL_BG = (122, 88, 54)
CANCEL_HL = (150, 109, 69)
CANCEL_TEXT = (246, 229, 192)
CANCEL_BORDER = (196, 154, 82)
PANEL_BG = (247, 250, 252, 235)
PANEL_BORDER = (178, 192, 206)
INFO_BG = (255, 255, 255, 210)
OVERLAY_BG = (0, 0, 0, 120)
MENU_PANEL_BG = (217, 191, 144, 55)
MENU_PANEL_EDGE_DARK = (86, 58, 33)
MENU_PANEL_EDGE_GOLD = (191, 149, 72)
MENU_TITLE_GLOW = (224, 178, 88)
MENU_TITLE_TEXT = (250, 233, 195)
MENU_LABEL_COLOR = (246, 232, 202)
MENU_LABEL_SHADOW = (22, 12, 8)
MENU_BUTTON_PALETTE = {
    "base": (108, 73, 42),
    "highlight": (136, 94, 56),
    "text": (248, 226, 186),
    "border": (194, 155, 80),
    "shadow": (0, 0, 0, 80),
}
BATTLE_PANEL_BG = (117, 86, 52, 214)
BATTLE_PANEL_BORDER_DARK = (66, 45, 27)
BATTLE_PANEL_BORDER_GOLD = (190, 151, 78)
BATTLE_TEXT_MAIN = (245, 232, 198)
BATTLE_TEXT_SHADOW = (24, 15, 9)
BATTLE_SUBTEXT_MAIN = (228, 205, 162)
BATTLE_SUBTEXT_SHADOW = (20, 12, 7)
BATTLE_OVERLAY_BG = (13, 9, 6, 170)
BATTLE_BUTTON_PALETTE = {
    "base": (96, 67, 40),
    "highlight": (126, 90, 56),
    "text": (248, 228, 190),
    "border": (196, 156, 84),
    "shadow": (0, 0, 0, 92),
}
ROLE_LABELS = {"player": "玩家", "ai": "AI赌徒"}

ROW_INIT = [3, 4, 5]
AI_DELAY = 0.4


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
    menu_bg = None
    menu_states = {"main_menu", "single_menu", "quick_menu", "custom_menu", "rules"}
    picture_dir = os.path.join(os.path.dirname(__file__), "picture")
    menu_bg_candidates = []
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.webp"):
        menu_bg_candidates.extend(sorted(glob.glob(os.path.join(picture_dir, ext))))
    menu_bg_candidates.sort(
        key=lambda p: (
            0
            if ("棋桌" in os.path.basename(p) and "棋子" in os.path.basename(p))
            else 1,
            -os.path.getsize(p),
            p,
        )
    )
    if menu_bg_candidates:
        try:
            menu_bg = pygame.image.load(menu_bg_candidates[0]).convert()
            menu_bg = pygame.transform.smoothscale(menu_bg, (WIDTH, HEIGHT))
        except pygame.error:
            menu_bg = None
    menu_tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    menu_tint.fill((20, 12, 6, 28))
    for y in range(HEIGHT):
        alpha = int(4 + 10 * (y / max(HEIGHT - 1, 1)))
        pygame.draw.line(menu_tint, (48, 24, 10, alpha), (0, y), (WIDTH, y))
    pygame.draw.ellipse(menu_tint, (255, 215, 132, 28), (-120, -120, 430, 280))
    pygame.draw.ellipse(menu_tint, (255, 210, 120, 20), (WIDTH - 360, -80, 420, 260))
    menu_sparks = [
        (
            random.randint(40, WIDTH - 40),
            random.randint(30, HEIGHT - 30),
            random.uniform(0.0, math.tau),
            random.uniform(0.7, 1.5),
        )
        for _ in range(22)
    ]
    menu_fx_time = 0.0
    battle_bg = None
    battle_piece_icons = []
    broken_piece_icons = []

    def cutout_checkerboard(src_surface):
        w, h = src_surface.get_size()
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            for x in range(w):
                r, g, b, _ = src_surface.get_at((x, y))
                diff = max(abs(r - g), abs(g - b), abs(r - b))
                lum = (r + g + b) // 3
                if diff <= 10 and 40 <= lum <= 220:
                    continue
                if diff <= 16 and 40 <= lum <= 220:
                    alpha = int(255 * (diff - 10) / 6)
                    alpha = max(0, min(255, alpha))
                else:
                    alpha = 255
                out.set_at((x, y), (r, g, b, alpha))
        return out

    def extract_icons_from_sheet(path, target_h=48, split_components=True):
        icons = []
        try:
            sheet = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return icons

        cutout = cutout_checkerboard(sheet)
        if split_components:
            mask = pygame.mask.from_surface(cutout, 10)
            rects = [r for r in mask.get_bounding_rects() if r.w > 40 and r.h > 40]
            rects.sort(key=lambda r: (r.y, r.x))
        else:
            whole = cutout.get_bounding_rect(min_alpha=8)
            rects = [whole] if whole.w > 0 and whole.h > 0 else []

        for rect in rects:
            icon = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            icon.blit(cutout, (0, 0), rect)
            trim = icon.get_bounding_rect(min_alpha=8)
            if trim.w <= 0 or trim.h <= 0:
                continue
            icon = icon.subsurface(trim).copy()
            target_w = max(38, int(icon.get_width() * (target_h / icon.get_height())))
            icon = pygame.transform.smoothscale(icon, (target_w, target_h))
            icons.append(icon)
        return icons

    png_images = sorted(glob.glob(os.path.join(picture_dir, "*.png")))
    jpg_images = sorted(glob.glob(os.path.join(picture_dir, "*.jpg")))
    jpg_images += sorted(glob.glob(os.path.join(picture_dir, "*.jpeg")))

    table_path = min(png_images, key=os.path.getsize) if png_images else None
    if table_path:
        try:
            battle_bg = pygame.image.load(table_path).convert()
            battle_bg = pygame.transform.smoothscale(battle_bg, (WIDTH, HEIGHT))
        except pygame.error:
            battle_bg = None

    piece_sheet_path = max(jpg_images, key=os.path.getsize) if jpg_images else None
    if not piece_sheet_path and png_images:
        piece_sheet_path = max(png_images, key=os.path.getsize)
    if piece_sheet_path:
        battle_piece_icons = extract_icons_from_sheet(
            piece_sheet_path, target_h=58, split_components=True
        )

    broken_sheet_path = None
    if len(png_images) >= 2:
        non_table_pngs = [p for p in png_images if p != table_path]
        if non_table_pngs:
            broken_sheet_path = max(non_table_pngs, key=os.path.getsize)
    if broken_sheet_path:
        broken_piece_icons = extract_icons_from_sheet(
            broken_sheet_path, target_h=62, split_components=False
        )
        if broken_piece_icons:
            base = broken_piece_icons[0]
            broken_piece_icons = [
                pygame.transform.rotozoom(base, -8, 0.97),
                base,
                pygame.transform.rotozoom(base, 7, 1.02),
            ]

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
    exit_button = Button((30, 18, 108, 40), "离席")

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
        for i, label in enumerate(["新手", "职业", "大师"])
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
    next_button = Button((WIDTH // 2 - 110, HEIGHT // 2 + 40, 220, 55), "下一盘")
    restart_button = Button((WIDTH // 2 - 110, HEIGHT // 2 + 40, 220, 55), "再开一盘")
    menu_button = Button((WIDTH // 2 - 110, HEIGHT // 2 + 110, 220, 55), "返回赌桌厅")

    def difficulty_text():
        if difficulty == "random":
            return "新手"
        if difficulty == "medium":
            return "职业"
        return "大师"

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
            panel_surface, MENU_PANEL_BG, panel_surface.get_rect(), border_radius=22
        )
        pygame.draw.rect(
            panel_surface,
            MENU_PANEL_EDGE_DARK,
            panel_surface.get_rect(),
            3,
            border_radius=22,
        )
        pygame.draw.rect(
            panel_surface,
            MENU_PANEL_EDGE_GOLD,
            panel_surface.get_rect().inflate(-10, -10),
            2,
            border_radius=18,
        )
        for ox, oy in ((16, 16), (16, panel_rect.height - 16), (panel_rect.width - 16, 16), (panel_rect.width - 16, panel_rect.height - 16)):
            pygame.draw.circle(panel_surface, MENU_PANEL_EDGE_GOLD, (ox, oy), 4)
        for x in (70, panel_rect.width - 70):
            pygame.draw.line(
                panel_surface,
                MENU_PANEL_EDGE_GOLD,
                (x, 24),
                (panel_rect.width - x, 24),
                2,
            )
            pygame.draw.line(
                panel_surface,
                MENU_PANEL_EDGE_GOLD,
                (x, panel_rect.height - 24),
                (panel_rect.width - x, panel_rect.height - 24),
                2,
            )
        screen.blit(panel_surface, panel_rect.topleft)
        title_shadow = big_font.render(title, True, (56, 32, 18))
        screen.blit(
            title_shadow,
            title_shadow.get_rect(center=(WIDTH // 2 + 2, title_y + 2)),
        )
        glow = big_font.render(title, True, MENU_TITLE_GLOW)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            screen.blit(glow, glow.get_rect(center=(WIDTH // 2 + dx, title_y + dy)))
        title_label = big_font.render(title, True, MENU_TITLE_TEXT)
        screen.blit(title_label, title_label.get_rect(center=(WIDTH // 2, title_y)))

    def draw_menu_magic():
        screen.blit(menu_tint, (0, 0))
        for x, y, phase, speed in menu_sparks:
            t = menu_fx_time * speed + phase
            alpha = int(52 + 58 * (0.5 + 0.5 * math.sin(t)))
            radius = 1 + int(2 * (0.5 + 0.5 * math.sin(t * 1.7)))
            fx = pygame.Surface((radius * 8, radius * 8), pygame.SRCALPHA)
            c = radius * 4
            pygame.draw.circle(fx, (255, 220, 150, alpha), (c, c), radius + 1)
            pygame.draw.circle(fx, (255, 248, 214, min(210, alpha + 80)), (c, c), radius)
            screen.blit(fx, (x - c, y - c))

    def draw_menu_text(text, text_font, pos):
        shadow = text_font.render(text, True, MENU_LABEL_SHADOW)
        screen.blit(shadow, (pos[0] + 1, pos[1] + 2))
        label = text_font.render(text, True, MENU_LABEL_COLOR)
        screen.blit(label, pos)

    def draw_battle_text(
        text,
        text_font,
        pos,
        color=BATTLE_TEXT_MAIN,
        shadow=BATTLE_TEXT_SHADOW,
        center=False,
    ):
        shadow_label = text_font.render(text, True, shadow)
        label = text_font.render(text, True, color)
        if center:
            screen.blit(
                shadow_label, shadow_label.get_rect(center=(pos[0] + 1, pos[1] + 2))
            )
            screen.blit(label, label.get_rect(center=pos))
        else:
            screen.blit(shadow_label, (pos[0] + 1, pos[1] + 2))
            screen.blit(label, pos)
        return label

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
        menu_fx_time += dt
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
                            difficulty = ["random", "medium", "optimal"][idx]
                    if start_button.hit(event.pos):
                        start_match("best3", quick=True)
                    elif back_button.hit(event.pos):
                        game_state = "single_menu"
                elif game_state == "custom_menu":
                    for idx, btn in enumerate(difficulty_buttons):
                        if btn.hit(event.pos):
                            difficulty = ["random", "medium", "optimal"][idx]
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

        if game_state in menu_states:
            if menu_bg is not None:
                screen.blit(menu_bg, (0, 0))
            else:
                screen.blit(bg_surface, (0, 0))
                screen.blit(bg_clouds, (0, 0))
            draw_menu_magic()
        elif game_state in ("playing", "gameover", "round_intro") and battle_bg is not None:
            screen.blit(battle_bg, (0, 0))
        else:
            screen.blit(bg_surface, (0, 0))
            screen.blit(bg_clouds, (0, 0))

        if game_state in ("playing", "gameover"):
            centers = get_row_centers(rows)
            for row_idx, row in enumerate(centers):
                for idx, (x, y) in enumerate(row):
                    selected = False
                    if (
                        selecting
                        and row_idx == select_row
                        and select_start is not None
                        and select_end is not None
                    ):
                        lo = min(select_start, select_end)
                        hi = max(select_start, select_end)
                        selected = lo <= idx <= hi

                    if rows[row_idx][idx]:
                        if battle_piece_icons:
                            icon = battle_piece_icons[
                                (row_idx * len(row) + idx) % len(battle_piece_icons)
                            ]
                            if selected:
                                glow_r = max(RADIUS + 7, icon.get_width() // 2 + 6)
                                pygame.draw.circle(
                                    screen, CIRCLE_HL, (int(x), int(y)), glow_r
                                )
                            icon_rect = icon.get_rect(center=(int(x), int(y)))
                            screen.blit(icon, icon_rect)
                        else:
                            color = CIRCLE_HL if selected else CIRCLE_COLOR
                            pygame.draw.circle(screen, color, (int(x), int(y)), RADIUS)
                    else:
                        if broken_piece_icons:
                            icon = broken_piece_icons[
                                (row_idx * len(row) + idx) % len(broken_piece_icons)
                            ]
                            icon_rect = icon.get_rect(center=(int(x), int(y)))
                            screen.blit(icon, icon_rect)
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
                exit_button.draw(
                    screen,
                    button_font,
                    selected=False,
                    palette=BATTLE_BUTTON_PALETTE,
                )

            info_rect = pygame.Rect(130, 18, WIDTH - 360, 198)
            info_shadow = info_rect.move(3, 4)
            pygame.draw.rect(screen, (0, 0, 0, 92), info_shadow, border_radius=18)
            info_surface = pygame.Surface(info_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                info_surface, BATTLE_PANEL_BG, info_surface.get_rect(), border_radius=16
            )
            pygame.draw.rect(
                info_surface,
                BATTLE_PANEL_BORDER_DARK,
                info_surface.get_rect(),
                3,
                border_radius=16,
            )
            pygame.draw.rect(
                info_surface,
                BATTLE_PANEL_BORDER_GOLD,
                info_surface.get_rect().inflate(-10, -10),
                2,
                border_radius=12,
            )
            screen.blit(info_surface, info_rect.topleft)

            pad = 12
            gap = 6
            right_anchor = info_rect.right - 20
            y = info_rect.y + pad
            turn_text = f"当前回合：{ROLE_LABELS[current_player]}"
            info = draw_battle_text(turn_text, font, (info_rect.x + 20, y))
            round_text = (
                f"第{game_number}局"
                if quick_mode or match_mode == "best3"
                else "单盘"
            )
            round_w, _ = small_font.size(round_text)
            round_y = info_rect.bottom - pad - small_font.get_height()
            draw_battle_text(
                round_text,
                small_font,
                (right_anchor - round_w, round_y),
                color=BATTLE_SUBTEXT_MAIN,
                shadow=BATTLE_SUBTEXT_SHADOW,
            )
            y += font.get_height() + gap

            diff_text = f"难度：{difficulty_text()}"
            draw_battle_text(diff_text, font, (info_rect.x + 20, y))
            if quick_mode:
                removed_line = f"碎子数：玩家{match_removed['player']} - AI赌徒{match_removed['ai']}"
                removed_w, removed_h = small_font.size(removed_line)
                removed_x = right_anchor - removed_w
                removed_y = y + (font.get_height() - removed_h) // 2
                draw_battle_text(
                    removed_line,
                    small_font,
                    (removed_x, removed_y),
                    color=BATTLE_SUBTEXT_MAIN,
                    shadow=BATTLE_SUBTEXT_SHADOW,
                )
            y += font.get_height() + gap

            if quick_mode:
                mode_line = "三局两胜"
                score_line = f"赌分：玩家{match_wins['player']} - AI赌徒{match_wins['ai']}"
            elif match_mode == "best3":
                mode_line = "三局两胜"
                score_line = f"赌分：玩家{match_wins['player']} - AI赌徒{match_wins['ai']}"
            else:
                mode_line = "赌局：单盘"
                score_line = ""

            draw_battle_text(
                mode_line,
                small_font,
                (info_rect.x + 20, y),
                color=BATTLE_SUBTEXT_MAIN,
                shadow=BATTLE_SUBTEXT_SHADOW,
            )
            y += small_font.get_height() + gap

            if score_line:
                draw_battle_text(
                    score_line,
                    small_font,
                    (info_rect.x + 20, y),
                    color=BATTLE_SUBTEXT_MAIN,
                    shadow=BATTLE_SUBTEXT_SHADOW,
                )
                y += small_font.get_height() + gap

            if game_state == "playing":
                hint_text = "沿同一排连划木筹，可一次收走"
                hint_w, hint_h = small_font.size(hint_text)
                hint_x = right_anchor - hint_w
                hint_y = info_rect.y + pad + (font.get_height() - hint_h) // 2
                if hint_x < info_rect.x + 20 + info.get_width() + 12:
                    hint_y = info_rect.y + pad + font.get_height() + gap
                    hint_x = right_anchor - hint_w
                draw_battle_text(
                    hint_text,
                    small_font,
                    (hint_x, hint_y),
                    color=BATTLE_SUBTEXT_MAIN,
                    shadow=BATTLE_SUBTEXT_SHADOW,
                )

            if slash_effect:
                slash_effect.draw(screen)
            if selecting and slash_points:
                draw_slash_trail(screen, slash_points)
            if selecting and select_row is not None:
                cancel_color = CANCEL_HL if cancel_hover else CANCEL_BG
                pygame.draw.rect(screen, cancel_color, cancel_rect, border_radius=10)
                pygame.draw.rect(screen, CANCEL_BORDER, cancel_rect, 2, border_radius=10)
                draw_battle_text(
                    "收手",
                    small_font,
                    cancel_rect.center,
                    color=CANCEL_TEXT,
                    shadow=BATTLE_TEXT_SHADOW,
                    center=True,
                )

        if game_state == "main_menu":
            draw_panel("尼莫游戏")
            for btn in main_buttons:
                btn.draw(screen, button_font, palette=MENU_BUTTON_PALETTE)

        if game_state == "single_menu":
            draw_panel("单人游戏")
            for btn in single_buttons:
                btn.draw(screen, button_font, palette=MENU_BUTTON_PALETTE)
            back_button.draw(screen, button_font, palette=MENU_BUTTON_PALETTE)

        if game_state == "quick_menu":
            draw_panel("快速游戏")
            draw_menu_text("AI难度", label_font, (left_x, label_y))
            for idx, btn in enumerate(difficulty_buttons):
                selected = difficulty == ["random", "medium", "optimal"][idx]
                btn.draw(
                    screen,
                    button_font,
                    selected=selected,
                    palette=MENU_BUTTON_PALETTE,
                )
            quick_lines = [
                "三局两胜",
                "第1局先手随机",
                "第2局先手交换",
                "第3局先手：前两局总删除数更少者",
                "平局：第2局后手先",
            ]
            quick_y = label_y
            for line in quick_lines:
                draw_menu_text(line, small_font, (right_x, quick_y))
                quick_y += 26
            start_button.draw(
                screen,
                button_font,
                selected=False,
                palette=MENU_BUTTON_PALETTE,
            )
            back_button.draw(screen, button_font, palette=MENU_BUTTON_PALETTE)

        if game_state == "custom_menu":
            draw_panel("自定义对局")
            draw_menu_text("选择难度", label_font, (left_x, label_y))
            for idx, btn in enumerate(difficulty_buttons):
                selected = difficulty == ["random", "medium", "optimal"][idx]
                btn.draw(
                    screen,
                    button_font,
                    selected=selected,
                    palette=MENU_BUTTON_PALETTE,
                )

            draw_menu_text("先手", label_font, (right_x, label_y))
            for idx, btn in enumerate(first_buttons):
                selected = first_player == ["player", "ai"][idx]
                btn.draw(
                    screen,
                    button_font,
                    selected=selected,
                    palette=MENU_BUTTON_PALETTE,
                )

            draw_menu_text("对局模式", label_font, (right_x, match_label_y))
            for idx, btn in enumerate(match_buttons):
                selected = match_mode == ["single", "best3"][idx]
                btn.draw(
                    screen,
                    button_font,
                    selected=selected,
                    palette=MENU_BUTTON_PALETTE,
                )

            start_button.draw(
                screen,
                button_font,
                selected=False,
                palette=MENU_BUTTON_PALETTE,
            )
            back_button.draw(screen, button_font, palette=MENU_BUTTON_PALETTE)

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
                draw_menu_text(line, small_font, (panel_rect.x + 40, rule_y))
                rule_y += 28
            back_button.draw(screen, button_font, palette=MENU_BUTTON_PALETTE)

        if game_state == "round_intro":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill(BATTLE_OVERLAY_BG)
            screen.blit(overlay, (0, 0))
            mode_name = "三局两胜" if (quick_mode or match_mode == "best3") else "单盘"
            draw_battle_text(
                f"{mode_name} · 第{game_number}局",
                big_font,
                (WIDTH // 2, HEIGHT // 2 - 30),
                color=BATTLE_TEXT_MAIN,
                shadow=BATTLE_TEXT_SHADOW,
                center=True,
            )
            draw_battle_text(
                f"当前赌分 玩家{match_wins['player']} - AI赌徒{match_wins['ai']}",
                small_font,
                (WIDTH // 2, HEIGHT // 2 + 10),
                color=BATTLE_SUBTEXT_MAIN,
                shadow=BATTLE_SUBTEXT_SHADOW,
                center=True,
            )
            draw_battle_text(
                f"先执：{ROLE_LABELS[current_player]}",
                small_font,
                (WIDTH // 2, HEIGHT // 2 + 38),
                color=BATTLE_SUBTEXT_MAIN,
                shadow=BATTLE_SUBTEXT_SHADOW,
                center=True,
            )

        if game_state == "gameover":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill(BATTLE_OVERLAY_BG)
            screen.blit(overlay, (0, 0))
            if match_complete() and (match_mode == "best3" or quick_mode):
                overall_winner = (
                    ROLE_LABELS["player"]
                    if match_wins["player"] > match_wins["ai"]
                    else ROLE_LABELS["ai"]
                )
                draw_battle_text(
                    f"赌局已定：{overall_winner}胜出！",
                    big_font,
                    (WIDTH // 2, HEIGHT // 2 - 30),
                    color=BATTLE_TEXT_MAIN,
                    shadow=BATTLE_TEXT_SHADOW,
                    center=True,
                )
                draw_battle_text(
                    f"赌分 玩家{match_wins['player']} - AI赌徒{match_wins['ai']}",
                    small_font,
                    (WIDTH // 2, HEIGHT // 2 + 8),
                    color=BATTLE_SUBTEXT_MAIN,
                    shadow=BATTLE_SUBTEXT_SHADOW,
                    center=True,
                )
                restart_button.text = "再开一组赌局"
                restart_button.draw(screen, button_font, palette=BATTLE_BUTTON_PALETTE)
            else:
                draw_battle_text(
                    f"本盘胜者：{ROLE_LABELS[winner]}",
                    big_font,
                    (WIDTH // 2, HEIGHT // 2 - 20),
                    color=BATTLE_TEXT_MAIN,
                    shadow=BATTLE_TEXT_SHADOW,
                    center=True,
                )
                if match_mode == "best3" or quick_mode:
                    next_button.draw(screen, button_font, palette=BATTLE_BUTTON_PALETTE)
                else:
                    restart_button.text = "再开一盘"
                    restart_button.draw(
                        screen, button_font, palette=BATTLE_BUTTON_PALETTE
                    )
            if match_complete():
                menu_button.draw(screen, button_font, palette=BATTLE_BUTTON_PALETTE)

        pygame.display.flip()

    pygame.quit()

