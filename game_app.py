import glob
import os
import random
import math

import pygame

from ai_profession_policy import get_opponent_finish_checker, get_skill_policy
from constants import BOARD_COLS, GAP, HEIGHT, RADIUS, WIDTH
from game_logic import (
    find_board_cell,
    find_circle,
    find_hit_by_segment,
    get_row_centers,
    get_segment_bounds,
    nim_ai_move,
    update_touched_by_segment,
)
from profession_registry import (
    get_default_profession,
    get_profession_icon_stem,
    get_profession_ids,
    get_profession_intro_lines,
    get_profession_label,
    get_profession_skill_id,
)
from skill_system import (
    SkillUseContext,
    consume_shield as consume_shield_state,
    execute_skill,
    get_skill_mode,
    get_skill_name,
    reset_shield as reset_shield_state,
    shadow_hand_destinations,
    shield_turns_for_cell as shield_turns_for_cell_state,
    update_shield_states_after_action as update_shield_states_after_action_state,
)
from ui_components import (
    Button,
    SlashEffect,
    build_background,
    draw_slash_trail,
    generate_button_click_sound,
    generate_slash_sound,
)


FPS = 60

CIRCLE_COLOR = (60, 90, 120)
CIRCLE_HL = (186, 152, 96)
SELECT_GLOW_COLOR = (255, 214, 140)
SELECT_GLOW_ALPHA = 96
SELECT_GLOW_EXPAND = 3
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
MENU_TITLE_TEXT = (255, 255, 255)
MENU_LABEL_COLOR = (246, 232, 202)
MENU_LABEL_SHADOW = (22, 12, 8)
MENU_BUTTON_PALETTE = {
    "base": (108, 73, 42),
    "highlight": (136, 94, 56),
    "text": (255, 255, 255),
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
PROFESSION_ORDER = get_profession_ids()
SHIELD_FILL_COLOR = (216, 170, 74)
SHIELD_INNER_COLOR = (236, 197, 108)
SHIELD_EDGE_COLOR = (255, 233, 176)
SHIELD_HILITE_COLOR = (255, 247, 220)
SHIELD_CROSS_COLOR = (170, 118, 44)
CROSS_FX_OFFSET_X = -4
CROSS_FX_OFFSET_Y = -3
PIECE_MARKER_LEFT_SHIFT_RATIO = 0.20
SKILL_MODE_HINTS = {
    "shield": "圣盾模式：点击一个完整棋子施加护盾",
    "cross": "十字斩模式：点击中心棋子释放技能",
}
SKILL_MODE_HINTS["shadow_hand"] = (
    "\u6697\u624b\u6a21\u5f0f\uff1a\u5148\u70b9\u4e00\u4e2a\u5b58\u5728\u7684\u68cb\u5b50\uff0c"
    "\u518d\u70b9\u4efb\u610f\u76ee\u6807\u4ea4\u6362\uff08\u542b\u7834\u788e\u4f4d\uff09\uff0c"
    "\u884c\u5c3e\u53ef\u65b0\u589e\u69fd\u4f4d"
)
PROFESSION_BUTTON_ICON_HEIGHT = 24
PROFESSION_HEADER_ICON_HEIGHT = 22
PROFESSION_BATTLE_ICON_HEIGHT = 20
PROFESSION_ICON_TEXT_GAP = 8
PROFESSION_ICON_SCALE = {"thief": 1.18}

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

    bg_surface = None
    bg_clouds = None
    menu_bg = None
    menu_states = {"main_menu", "single_menu", "quick_menu", "custom_menu", "rules"}
    picture_dir = os.path.join(os.path.dirname(__file__), "picture")
    music_dir = os.path.join(os.path.dirname(__file__), "music")
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

    loading_font = pick_font(38)

    def draw_loading_screen(message="\u52a0\u8f7d\u4e2d..."):
        if menu_bg is not None:
            screen.blit(menu_bg, (0, 0))
        elif bg_surface is not None and bg_clouds is not None:
            screen.blit(bg_surface, (0, 0))
            screen.blit(bg_clouds, (0, 0))
        else:
            screen.fill((24, 18, 12))
        loading_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        loading_overlay.fill((8, 6, 4, 64))
        screen.blit(loading_overlay, (0, 0))
        shadow = loading_font.render(message, True, (26, 16, 10))
        label = loading_font.render(message, True, (246, 231, 197))
        center = (WIDTH // 2, HEIGHT // 2)
        screen.blit(shadow, shadow.get_rect(center=(center[0] + 2, center[1] + 2)))
        screen.blit(label, label.get_rect(center=center))
        pygame.display.flip()
        pygame.event.pump()

    draw_loading_screen()
    bg_surface, bg_clouds = build_background()
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

    def load_icon_asset(path, target_h=48, min_width=38):
        try:
            icon = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None

        trim = icon.get_bounding_rect(min_alpha=8)
        if trim.w <= 0 or trim.h <= 0:
            return None

        icon = icon.subsurface(trim).copy()
        target_w = max(min_width, int(icon.get_width() * (target_h / icon.get_height())))
        return pygame.transform.smoothscale(icon, (target_w, target_h))

    def find_asset_path(stem):
        for ext in ("png", "jpg", "jpeg", "bmp", "webp"):
            path = os.path.join(picture_dir, f"{stem}.{ext}")
            if os.path.exists(path):
                return path
        return None

    png_images = sorted(glob.glob(os.path.join(picture_dir, "*.png")))
    table_path = find_asset_path("\u684c\u5b50")
    if not table_path:
        table_candidates = [
            p for p in png_images if "\u684c" in os.path.splitext(os.path.basename(p))[0]
        ]
        if table_candidates:
            table_path = min(table_candidates, key=os.path.getsize)
        elif png_images:
            table_path = min(png_images, key=os.path.getsize)
    if table_path:
        try:
            battle_bg = pygame.image.load(table_path).convert()
            battle_bg = pygame.transform.smoothscale(battle_bg, (WIDTH, HEIGHT))
        except pygame.error:
            battle_bg = None

    piece_stems = [
        "\u68cb\u5b501",
        "\u68cb\u5b502",
        "\u68cb\u5b503",
    ]
    for stem in piece_stems:
        piece_path = find_asset_path(stem)
        if not piece_path:
            continue
        icon = load_icon_asset(piece_path, target_h=58)
        if icon is not None:
            battle_piece_icons.append(icon)

    broken_asset_candidates = ["\u7834\u788e\u7684\u68cb\u5b50", "\u7834\u788e\u68cb\u5b50"]
    for stem in broken_asset_candidates:
        broken_path = find_asset_path(stem)
        if not broken_path:
            continue
        base = load_icon_asset(broken_path, target_h=62)
        if base is None:
            continue
        broken_piece_icons = [
            pygame.transform.rotozoom(base, -8, 0.97),
            base,
            pygame.transform.rotozoom(base, 7, 1.02),
        ]
        break

    profession_icons_menu = {}
    profession_icons_header = {}
    profession_icons_battle = {}
    for profession_id in PROFESSION_ORDER:
        icon_stem = get_profession_icon_stem(profession_id)
        icon_path = find_asset_path(icon_stem)
        if not icon_path:
            continue
        icon_scale = PROFESSION_ICON_SCALE.get(profession_id, 1.0)
        menu_h = max(1, int(PROFESSION_BUTTON_ICON_HEIGHT * icon_scale))
        header_h = max(1, int(PROFESSION_HEADER_ICON_HEIGHT * icon_scale))
        battle_h = max(1, int(PROFESSION_BATTLE_ICON_HEIGHT * icon_scale))
        menu_icon = load_icon_asset(
            icon_path,
            target_h=menu_h,
            min_width=0,
        )
        if menu_icon is not None:
            profession_icons_menu[profession_id] = menu_icon
        header_icon = load_icon_asset(
            icon_path,
            target_h=header_h,
            min_width=0,
        )
        if header_icon is not None:
            profession_icons_header[profession_id] = header_icon
        battle_icon = load_icon_asset(
            icon_path,
            target_h=battle_h,
            min_width=0,
        )
        if battle_icon is not None:
            profession_icons_battle[profession_id] = battle_icon

    slash_sound = None
    button_click_sound = None
    mixer_ready = False
    music_tracks = []
    music_lengths = []
    music_index = -1
    current_track = None
    music_transitioning = False
    music_next_switch_at = 0
    music_started_at = 0
    MUSIC_FADE_MS = 2000
    MUSIC_VOLUME = 0.55
    TRACK_END_GUARD_S = 2.2
    PREFERRED_MUSIC_TRACKS = [
        "delosound-medieval-background-351307.mp3",
        "deuslower-dark-fantasy-ambient-dungeon-synthpiano-verse-248214.mp3",
        "montogoronto-ominousdark-medievalfantasy-song-309510.mp3",
        "syouki_takahashi-midnight-forest-184304.mp3",
    ]

    def discover_music_tracks():
        tracks = []
        for name in PREFERRED_MUSIC_TRACKS:
            track_path = os.path.join(music_dir, name)
            if os.path.isfile(track_path):
                tracks.append(track_path)
        if tracks:
            return tracks

        fallback_tracks = []
        for ext in ("*.mp3", "*.ogg", "*.wav"):
            fallback_tracks.extend(sorted(glob.glob(os.path.join(music_dir, ext))))
        return fallback_tracks

    def start_music_track(track_idx, fade_ms=MUSIC_FADE_MS):
        nonlocal music_index, current_track, music_transitioning
        nonlocal music_next_switch_at, music_started_at
        if not mixer_ready or not music_tracks:
            return False
        track_idx %= len(music_tracks)
        track_path = music_tracks[track_idx]
        try:
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play(loops=0, fade_ms=fade_ms)
        except pygame.error:
            return False
        music_index = track_idx
        current_track = track_path
        music_started_at = pygame.time.get_ticks()
        music_transitioning = False
        music_next_switch_at = 0
        return True

    def schedule_music_transition():
        nonlocal music_transitioning, music_next_switch_at
        if not mixer_ready or not music_tracks or music_transitioning:
            return
        try:
            pygame.mixer.music.fadeout(MUSIC_FADE_MS)
        except pygame.error:
            return
        music_transitioning = True
        music_next_switch_at = pygame.time.get_ticks() + MUSIC_FADE_MS

    def update_music():
        nonlocal music_transitioning
        if not mixer_ready or not music_tracks:
            return
        now = pygame.time.get_ticks()
        if music_transitioning:
            if now >= music_next_switch_at:
                start_music_track(music_index + 1, fade_ms=MUSIC_FADE_MS)
            return

        if not pygame.mixer.music.get_busy():
            start_music_track(music_index + 1, fade_ms=MUSIC_FADE_MS)
            return

        track_len = 0.0
        if 0 <= music_index < len(music_lengths):
            track_len = music_lengths[music_index]
        if track_len <= TRACK_END_GUARD_S:
            return

        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms >= 0:
            elapsed = pos_ms / 1000.0
        else:
            elapsed = max(0.0, (now - music_started_at) / 1000.0)
        remaining = track_len - elapsed
        if remaining <= TRACK_END_GUARD_S:
            schedule_music_transition()

    try:
        pygame.mixer.init()
        mixer_ready = True
    except pygame.error:
        mixer_ready = False

    if mixer_ready:
        try:
            slash_sound = generate_slash_sound()
        except pygame.error:
            slash_sound = None
        try:
            button_click_sound = generate_button_click_sound()
            button_click_sound.set_volume(0.45)
        except pygame.error:
            button_click_sound = None

        music_tracks = discover_music_tracks()
        for track_path in music_tracks:
            try:
                music_lengths.append(pygame.mixer.Sound(track_path).get_length())
            except pygame.error:
                music_lengths.append(0.0)
        if music_tracks:
            start_music_track(0, fade_ms=MUSIC_FADE_MS)

    difficulty = "optimal"
    first_player = "player"
    match_mode = "single"
    quick_mode = False
    single_mode = "classic"
    selected_profession = get_default_profession()
    ai_profession = get_default_profession()
    auto_random_ai_profession = False
    game_number = 1
    match_wins = {"player": 0, "ai": 0}
    match_removed = {"player": 0, "ai": 0}
    game1_first = None
    game2_first = None
    current_player = "player"
    skill_used_by = {"player": False, "ai": False}
    skill_mode = None
    skill_source_cell = None
    shadow_empty_cells = set()
    shield_states = {
        "player": {"piece": None, "turns_left": 0, "action_count": 0},
        "ai": {"piece": None, "turns_left": 0, "action_count": 0},
    }

    game_state = "main_menu"
    rows = [[True for _ in range(count)] for count in ROW_INIT]
    piece_icon_map = []
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
    pressed_button = None
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
    skill_button = Button((30, 70, 132, 40), "")

    main_buttons = [
        Button((main_btn_x, main_btn_y, main_btn_w, main_btn_h), "单人游戏"),
        Button(
            (main_btn_x, main_btn_y + main_btn_h + main_btn_gap, main_btn_w, main_btn_h),
            "规则",
        ),
    ]
    single_buttons = [
        Button((main_btn_x, main_btn_y, main_btn_w, main_btn_h), "经典模式"),
        Button(
            (main_btn_x, main_btn_y + main_btn_h + main_btn_gap, main_btn_w, main_btn_h),
            "职业模式",
        ),
        Button(
            (
                main_btn_x,
                main_btn_y + (main_btn_h + main_btn_gap) * 2,
                main_btn_w,
                main_btn_h,
            ),
            "自定义游戏",
        ),
    ]
    difficulty_buttons = [
        Button((left_x, buttons_y + i * (btn_h + btn_gap), btn_w, btn_h), label)
        for i, label in enumerate(["新手", "职业", "大师"])
    ]
    profession_label_y = buttons_y + (btn_h + btn_gap) * 3 + 6
    profession_buttons_y = profession_label_y + label_font.get_height() + 8
    profession_btn_gap = 6
    profession_row_w = btn_w + 24
    profession_row_offset = (profession_row_w - btn_w) // 2
    profession_count = max(1, len(PROFESSION_ORDER))
    profession_btn_w = (
        profession_row_w - profession_btn_gap * (profession_count - 1)
    ) // profession_count

    def profession_btn_x(base_x, idx):
        return base_x - profession_row_offset + idx * (
            profession_btn_w + profession_btn_gap
        )

    mode_option_count = 2
    mode_btn_gap = 8
    mode_btn_w = (btn_w - mode_btn_gap * (mode_option_count - 1)) // mode_option_count

    def mode_btn_x(base_x, idx):
        return base_x + idx * (mode_btn_w + mode_btn_gap)

    profession_buttons = [
        Button(
            (
                profession_btn_x(left_x, i),
                profession_buttons_y,
                profession_btn_w,
                btn_h,
            ),
            get_profession_label(key),
        )
        for i, key in enumerate(PROFESSION_ORDER)
    ]
    custom_menu_btn_gap = 10
    custom_difficulty_label_y = label_y
    custom_difficulty_buttons_y = custom_difficulty_label_y + label_font.get_height() + 6
    custom_difficulty_buttons = [
        Button(
            (
                left_x,
                custom_difficulty_buttons_y + i * (btn_h + custom_menu_btn_gap),
                btn_w,
                btn_h,
            ),
            label,
        )
        for i, label in enumerate(["新手", "职业", "大师"])
    ]
    custom_mode_label_y = custom_difficulty_buttons_y + btn_h * 3 + custom_menu_btn_gap * 2 + 8
    custom_mode_buttons_y = custom_mode_label_y + label_font.get_height() + 6
    custom_mode_buttons = [
        Button(
            (
                mode_btn_x(left_x, i),
                custom_mode_buttons_y,
                mode_btn_w,
                btn_h,
            ),
            label,
        )
        for i, label in enumerate(["经典", "职业"])
    ]
    custom_ai_prof_label_y = custom_mode_buttons_y + btn_h + 8
    custom_ai_prof_buttons_y = custom_ai_prof_label_y + label_font.get_height() + 6
    ai_profession_buttons = [
        Button(
            (
                profession_btn_x(left_x, i),
                custom_ai_prof_buttons_y,
                profession_btn_w,
                btn_h,
            ),
            get_profession_label(key),
        )
        for i, key in enumerate(PROFESSION_ORDER)
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
    custom_prof_label_y = match_buttons_y + btn_h + 12
    custom_prof_buttons_y = custom_prof_label_y + label_font.get_height() + 8
    if custom_prof_buttons_y + btn_h > start_btn_y - 8:
        custom_prof_buttons_y = start_btn_y - btn_h - 8
        custom_prof_label_y = custom_prof_buttons_y - label_font.get_height() - 8
    custom_profession_buttons = [
        Button(
            (
                profession_btn_x(right_x, i),
                custom_prof_buttons_y,
                profession_btn_w,
                btn_h,
            ),
            get_profession_label(key),
        )
        for i, key in enumerate(PROFESSION_ORDER)
    ]
    custom_menu_raise = 40
    custom_difficulty_label_y -= custom_menu_raise
    custom_mode_label_y -= custom_menu_raise
    custom_ai_prof_label_y -= custom_menu_raise
    custom_prof_label_y -= custom_menu_raise
    custom_first_label_y = label_y - custom_menu_raise
    custom_match_label_y = match_label_y - custom_menu_raise
    for btn in (
        custom_difficulty_buttons
        + custom_mode_buttons
        + ai_profession_buttons
        + first_buttons
        + match_buttons
        + custom_profession_buttons
    ):
        btn.rect.y -= custom_menu_raise
    start_button = Button((panel_rect.centerx - 120, start_btn_y, 240, 56), "开始游戏")
    back_button = Button((panel_rect.x + 24, panel_rect.bottom - 64, 160, 44), "返回")
    next_button = Button((WIDTH // 2 - 110, HEIGHT // 2 + 40, 220, 55), "下一局")
    restart_button = Button((WIDTH // 2 - 110, HEIGHT // 2 + 40, 220, 55), "再开一局")
    menu_button = Button((WIDTH // 2 - 110, HEIGHT // 2 + 110, 220, 55), "返回赌桌厅")

    def difficulty_text():
        if difficulty == "random":
            return "新手"
        if difficulty == "medium":
            return "职业"
        return "大师"

    def get_actor_profession(actor="player"):
        return selected_profession if actor == "player" else ai_profession

    def profession_text(actor="player"):
        profession = get_actor_profession(actor)
        return get_profession_label(profession)

    def get_profession_icon(profession_id, style="menu"):
        if style == "battle":
            icon_map = profession_icons_battle
        elif style == "header":
            icon_map = profession_icons_header
        else:
            icon_map = profession_icons_menu
        return icon_map.get(profession_id)

    def get_actor_profession_icon(actor="player", style="menu"):
        return get_profession_icon(get_actor_profession(actor), style=style)

    def profession_mode_enabled():
        return single_mode == "profession"

    def current_skill_id(actor="player"):
        profession = get_actor_profession(actor)
        return get_profession_skill_id(profession)

    def skill_name(actor="player"):
        return get_skill_name(current_skill_id(actor))

    def skill_button_text():
        if skill_mode is not None:
            return f"取消{skill_name()}"
        if skill_used_by["player"]:
            return f"{skill_name()}(已用)"
        return skill_name()

    def build_skill_context(actor):
        return SkillUseContext(rows=rows, actor=actor, shield_states=shield_states)

    def reset_shield(owner=None):
        reset_shield_state(shield_states, owner)

    def shield_turns_for_cell(row_idx, idx):
        return shield_turns_for_cell_state(shield_states, row_idx, idx)

    def consume_shield(row_idx, idx):
        return consume_shield_state(shield_states, row_idx, idx)

    def update_shield_states_after_action():
        update_shield_states_after_action_state(shield_states, rows)

    def _is_cell(value):
        return (
            isinstance(value, (tuple, list))
            and len(value) == 2
            and isinstance(value[0], int)
            and isinstance(value[1], int)
        )

    def parse_skill_target(skill_id, raw_target):
        if skill_id == "shadow_hand":
            if not isinstance(raw_target, (tuple, list)) or len(raw_target) != 2:
                return None
            source_cell = raw_target[0]
            dest_cell = raw_target[1]
            if not _is_cell(source_cell) or not _is_cell(dest_cell):
                return None
            return (
                (int(source_cell[0]), int(source_cell[1])),
                (int(dest_cell[0]), int(dest_cell[1])),
            )
        if not _is_cell(raw_target):
            return None
        return (int(raw_target[0]), int(raw_target[1]))

    def move_shield_piece(source_cell, dest_cell, swap_back=False):
        for owner in ("player", "ai"):
            piece = shield_states[owner]["piece"]
            if piece == source_cell:
                shield_states[owner]["piece"] = dest_cell
            elif swap_back and piece == dest_cell:
                shield_states[owner]["piece"] = source_cell

    def _shadow_virtual_targets():
        centers = get_row_centers(rows)
        targets = []
        step = RADIUS * 2 + GAP
        for row_idx, row in enumerate(centers):
            if row_idx >= len(rows):
                continue
            if len(rows[row_idx]) >= BOARD_COLS:
                continue
            if not row:
                continue
            x = row[-1][0] + step
            y = row[-1][1]
            targets.append((row_idx, len(rows[row_idx]), x, y))
        return targets

    def _find_shadow_hand_target(pos):
        hit = find_board_cell(rows, pos)
        if hit:
            return hit
        for row_idx, idx, x, y in _shadow_virtual_targets():
            dx = pos[0] - x
            dy = pos[1] - y
            if dx * dx + dy * dy <= RADIUS * RADIUS:
                return row_idx, idx
        return None

    def apply_board_updates(board_updates):
        for cell, active in board_updates:
            if not _is_cell(cell):
                continue
            row_idx, idx = int(cell[0]), int(cell[1])
            if row_idx < 0 or row_idx >= len(rows):
                continue
            if idx == len(rows[row_idx]) and bool(active) and len(rows[row_idx]) < BOARD_COLS:
                rows[row_idx].append(True)
                shadow_empty_cells.discard((row_idx, idx))
                continue
            if idx < 0 or idx >= len(rows[row_idx]):
                continue
            rows[row_idx][idx] = bool(active)
            if rows[row_idx][idx]:
                shadow_empty_cells.discard((row_idx, idx))

    def switch_turn(actor):
        nonlocal current_player, ai_timer
        current_player = "ai" if actor == "player" else "player"
        ai_timer = AI_DELAY if current_player == "ai" else 0.0

    def apply_instant_skill_effect(execution, skill_id, actor):
        nonlocal game_state, winner
        if skill_id == "shadow_hand":
            source_cell, dest_cell = execution.shadow_move or (None, None)
            swap_back = False
            dest_was_existing_empty = False
            if source_cell is not None and dest_cell is not None:
                dest_row, dest_idx = dest_cell
                if (
                    0 <= dest_row < len(rows)
                    and 0 <= dest_idx < len(rows[dest_row])
                ):
                    if rows[dest_row][dest_idx]:
                        swap_back = True
                    else:
                        dest_was_existing_empty = True
            if execution.board_updates:
                apply_board_updates(execution.board_updates)
            if source_cell is not None:
                source_row, source_idx = source_cell
                if (
                    0 <= source_row < len(rows)
                    and 0 <= source_idx < len(rows[source_row])
                    and not rows[source_row][source_idx]
                ):
                    if dest_was_existing_empty:
                        shadow_empty_cells.discard(source_cell)
                    else:
                        shadow_empty_cells.add(source_cell)
                else:
                    shadow_empty_cells.discard(source_cell)
            if dest_cell is not None:
                dest_row, dest_idx = dest_cell
                if (
                    0 <= dest_row < len(rows)
                    and 0 <= dest_idx < len(rows[dest_row])
                    and rows[dest_row][dest_idx]
                ):
                    shadow_empty_cells.discard(dest_cell)
            if source_cell is not None and dest_cell is not None:
                move_shield_piece(source_cell, dest_cell, swap_back=swap_back)
            update_shield_states_after_action()
            if all(not piece for row in rows for piece in row):
                winner = actor
                if match_mode == "best3" or quick_mode:
                    match_wins[winner] += 1
                game_state = "gameover"
                return
            switch_turn(actor)
            return

        if execution.board_updates:
            apply_board_updates(execution.board_updates)

    def clear_player_selection():
        nonlocal selecting, select_row, select_start, select_end
        nonlocal select_bounds, select_touched, slash_points, last_pos, cancel_hover
        selecting = False
        select_row = None
        select_start = None
        select_end = None
        select_bounds = None
        select_touched = set()
        slash_points = []
        last_pos = None
        cancel_hover = False

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

    def reset_piece_icon_map():
        nonlocal piece_icon_map
        if not battle_piece_icons:
            piece_icon_map = []
            return
        piece_icon_map = [
            [random.randrange(len(battle_piece_icons)) for _ in row] for row in rows
        ]

    def clear_round_state():
        nonlocal winner, slash_effect, pending_remove, skill_mode, skill_source_cell
        winner = None
        clear_player_selection()
        slash_effect = None
        pending_remove = None
        skill_mode = None
        skill_source_cell = None
        shadow_empty_cells.clear()
        reset_shield()

    def begin_game(first):
        nonlocal rows, current_player, game_state, ai_timer, intro_timer, skill_mode
        nonlocal skill_source_cell
        if match_mode == "best3" or quick_mode:
            rows = [[True for _ in range(c)] for c in generate_rows()]
        else:
            rows = [[True for _ in range(c)] for c in ROW_INIT]
        reset_piece_icon_map()
        clear_round_state()
        skill_used_by["player"] = False
        skill_used_by["ai"] = False
        skill_mode = None
        skill_source_cell = None
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
        nonlocal game1_first, game2_first, ai_profession
        match_mode = mode
        quick_mode = quick
        game_number = 1
        match_wins = {"player": 0, "ai": 0}
        match_removed = {"player": 0, "ai": 0}
        game1_first = None
        game2_first = None
        if profession_mode_enabled() and auto_random_ai_profession:
            ai_profession = random.choice(PROFESSION_ORDER)
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
        nonlocal game1_first, game2_first, ai_timer, intro_timer, pressed_button
        nonlocal skill_mode, skill_source_cell, auto_random_ai_profession
        clear_round_state()
        quick_mode = False
        auto_random_ai_profession = False
        game_number = 1
        match_wins = {"player": 0, "ai": 0}
        match_removed = {"player": 0, "ai": 0}
        game1_first = None
        game2_first = None
        ai_timer = 0.0
        intro_timer = 0.0
        pressed_button = None
        skill_used_by["player"] = False
        skill_used_by["ai"] = False
        reset_shield()
        skill_mode = None
        skill_source_cell = None
        game_state = "main_menu"

    def find_button_at(pos):
        if game_state == "main_menu":
            for btn in main_buttons:
                if btn.hit(pos):
                    return btn
        elif game_state == "single_menu":
            for btn in single_buttons:
                if btn.hit(pos):
                    return btn
            if back_button.hit(pos):
                return back_button
        elif game_state == "quick_menu":
            for btn in difficulty_buttons:
                if btn.hit(pos):
                    return btn
            if profession_mode_enabled():
                for btn in profession_buttons:
                    if btn.hit(pos):
                        return btn
            if start_button.hit(pos):
                return start_button
            if back_button.hit(pos):
                return back_button
        elif game_state == "custom_menu":
            for btn in custom_difficulty_buttons:
                if btn.hit(pos):
                    return btn
            for btn in custom_mode_buttons:
                if btn.hit(pos):
                    return btn
            if profession_mode_enabled():
                for btn in custom_profession_buttons:
                    if btn.hit(pos):
                        return btn
                for btn in ai_profession_buttons:
                    if btn.hit(pos):
                        return btn
            for btn in first_buttons:
                if btn.hit(pos):
                    return btn
            for btn in match_buttons:
                if btn.hit(pos):
                    return btn
            if start_button.hit(pos):
                return start_button
            if back_button.hit(pos):
                return back_button
        elif game_state == "rules":
            if back_button.hit(pos):
                return back_button
        elif game_state in ("playing", "round_intro"):
            if (
                game_state == "playing"
                and profession_mode_enabled()
                and current_player == "player"
                and not slash_effect
                and skill_button.hit(pos)
            ):
                return skill_button
            if exit_button.hit(pos):
                return exit_button
        elif game_state == "gameover":
            if match_complete():
                if menu_button.hit(pos):
                    return menu_button
                if restart_button.hit(pos):
                    return restart_button
            elif next_button.hit(pos):
                return next_button
        return None

    def handle_button_click(btn):
        nonlocal game_state, difficulty, first_player, match_mode
        nonlocal selected_profession, ai_profession, skill_mode, skill_source_cell, single_mode
        nonlocal auto_random_ai_profession
        if game_state == "main_menu":
            if btn is main_buttons[0]:
                game_state = "single_menu"
            elif btn is main_buttons[1]:
                game_state = "rules"
            return
        if game_state == "single_menu":
            if btn is single_buttons[0]:
                single_mode = "classic"
                auto_random_ai_profession = False
                game_state = "quick_menu"
            elif btn is single_buttons[1]:
                single_mode = "profession"
                auto_random_ai_profession = True
                game_state = "quick_menu"
            elif btn is single_buttons[2]:
                single_mode = "classic"
                auto_random_ai_profession = False
                game_state = "custom_menu"
            elif btn is back_button:
                game_state = "main_menu"
            return
        if game_state == "quick_menu":
            for idx, opt_btn in enumerate(difficulty_buttons):
                if btn is opt_btn:
                    difficulty = ["random", "medium", "optimal"][idx]
                    return
            if profession_mode_enabled():
                for idx, opt_btn in enumerate(profession_buttons):
                    if btn is opt_btn:
                        selected_profession = PROFESSION_ORDER[idx]
                        return
            if btn is start_button:
                first_player = "player"
                auto_random_ai_profession = profession_mode_enabled()
                start_match("best3", quick=False)
            elif btn is back_button:
                game_state = "single_menu"
            return
        if game_state == "custom_menu":
            for idx, opt_btn in enumerate(custom_difficulty_buttons):
                if btn is opt_btn:
                    difficulty = ["random", "medium", "optimal"][idx]
                    return
            for idx, opt_btn in enumerate(custom_mode_buttons):
                if btn is opt_btn:
                    single_mode = ["classic", "profession"][idx]
                    skill_mode = None
                    skill_source_cell = None
                    return
            if profession_mode_enabled():
                for idx, opt_btn in enumerate(custom_profession_buttons):
                    if btn is opt_btn:
                        selected_profession = PROFESSION_ORDER[idx]
                        return
                for idx, opt_btn in enumerate(ai_profession_buttons):
                    if btn is opt_btn:
                        ai_profession = PROFESSION_ORDER[idx]
                        return
            for idx, opt_btn in enumerate(first_buttons):
                if btn is opt_btn:
                    first_player = ["player", "ai"][idx]
                    return
            for idx, opt_btn in enumerate(match_buttons):
                if btn is opt_btn:
                    match_mode = ["single", "best3"][idx]
                    return
            if btn is start_button:
                auto_random_ai_profession = False
                start_match(match_mode, quick=False)
            elif btn is back_button:
                game_state = "single_menu"
            return
        if game_state == "rules":
            if btn is back_button:
                game_state = "main_menu"
            return
        if game_state in ("playing", "round_intro"):
            if btn is skill_button and game_state == "playing":
                if not profession_mode_enabled():
                    return
                if current_player != "player" or slash_effect:
                    return
                if skill_mode is not None:
                    skill_mode = None
                    skill_source_cell = None
                    clear_player_selection()
                    return
                if skill_used_by["player"]:
                    return
                skill_mode = get_skill_mode(current_skill_id("player"))
                skill_source_cell = None
                clear_player_selection()
                return
            if btn is exit_button:
                return_to_menu()
            return
        if game_state == "gameover":
            if match_complete():
                if btn is menu_button:
                    return_to_menu()
                elif btn is restart_button:
                    if quick_mode:
                        start_match("best3", quick=True)
                    elif match_mode == "best3":
                        start_match("best3", quick=False)
                    else:
                        begin_game(first_player)
            elif btn is next_button:
                start_next_game()

    def is_button_pressed(btn):
        if pressed_button is not btn:
            return False
        if not pygame.mouse.get_pressed()[0]:
            return False
        return btn.hit(pygame.mouse.get_pos())

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

    def draw_menu_text_with_icon(text, text_font, pos, icon):
        text_x, text_y = pos
        if icon is not None:
            icon_y = text_y + max(0, (text_font.get_height() - icon.get_height()) // 2)
            screen.blit(icon, (text_x, icon_y))
            text_x += icon.get_width() + PROFESSION_ICON_TEXT_GAP
        draw_menu_text(text, text_font, (text_x, text_y))

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

    def draw_battle_text_with_icon(
        text,
        text_font,
        pos,
        icon,
        color=BATTLE_SUBTEXT_MAIN,
        shadow=BATTLE_SUBTEXT_SHADOW,
    ):
        text_x, text_y = pos
        if icon is not None:
            icon_y = text_y + max(0, (text_font.get_height() - icon.get_height()) // 2)
            screen.blit(icon, (text_x, icon_y))
            text_x += icon.get_width() + PROFESSION_ICON_TEXT_GAP
        draw_battle_text(
            text,
            text_font,
            (text_x, text_y),
            color=color,
            shadow=shadow,
        )

    def draw_selection_glow(center, glow_r):
        outer_r = glow_r + SELECT_GLOW_EXPAND
        fx_size = outer_r * 2
        fx = pygame.Surface((fx_size, fx_size), pygame.SRCALPHA)
        c = outer_r
        pygame.draw.circle(
            fx, (*SELECT_GLOW_COLOR, max(32, SELECT_GLOW_ALPHA // 2)), (c, c), outer_r
        )
        pygame.draw.circle(fx, (*SELECT_GLOW_COLOR, SELECT_GLOW_ALPHA), (c, c), glow_r)
        screen.blit(fx, (center[0] - c, center[1] - c))

    def draw_shield_marker(center, piece_r, turns_left):
        if turns_left <= 0:
            return
        cx, cy = center
        shield_r = max(16, int(piece_r * 1.12))
        pad = 4
        surf_w = (shield_r + pad) * 2
        surf_h = (shield_r + pad) * 2
        fx = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        marker_alpha = 255 if turns_left >= 2 else 140

        sx = surf_w // 2
        sy = surf_h // 2
        pygame.draw.circle(fx, (*SHIELD_FILL_COLOR, 222), (sx, sy), shield_r)
        pygame.draw.circle(
            fx,
            (*SHIELD_INNER_COLOR, 205),
            (sx, sy),
            max(8, shield_r - 4),
        )
        pygame.draw.circle(fx, SHIELD_EDGE_COLOR, (sx, sy), shield_r, 3)
        pygame.draw.circle(fx, SHIELD_HILITE_COLOR, (sx, sy), max(7, shield_r - 7), 1)

        glint_r = max(2, shield_r // 5)
        pygame.draw.circle(
            fx,
            (*SHIELD_HILITE_COLOR, 210),
            (sx - max(3, shield_r // 3), sy - max(3, shield_r // 3)),
            glint_r,
        )

        cross_len = max(9, int(shield_r * 0.95))
        cross_half = cross_len // 2
        cross_thick = max(2, int(shield_r * 0.24))
        pygame.draw.line(
            fx,
            SHIELD_CROSS_COLOR,
            (sx, sy - cross_half),
            (sx, sy + cross_half),
            cross_thick,
        )
        pygame.draw.line(
            fx,
            SHIELD_CROSS_COLOR,
            (sx - cross_half, sy),
            (sx + cross_half, sy),
            cross_thick,
        )
        fx.set_alpha(marker_alpha)
        shield_stretch_y = 1.12
        stretched_h = int(surf_h * shield_stretch_y)
        fx = pygame.transform.smoothscale(fx, (surf_w, stretched_h))
        screen.blit(fx, (cx - surf_w // 2, cy - stretched_h // 2))

        turn_text = str(turns_left)
        num_y = cy - shield_r - small_font.get_height() // 2 - 3
        shadow = small_font.render(turn_text, True, (18, 12, 8))
        label = small_font.render(turn_text, True, (255, 245, 216))
        shadow.set_alpha(marker_alpha)
        label.set_alpha(marker_alpha)
        screen.blit(shadow, shadow.get_rect(center=(cx + 1, num_y + 1)))
        screen.blit(label, label.get_rect(center=(cx, num_y)))

    def start_slash(row_idx, start_idx, end_idx, actor):
        nonlocal slash_effect, pending_remove
        centers = get_row_centers(rows)
        if row_idx < 0 or row_idx >= len(centers):
            return
        lo = min(start_idx, end_idx)
        hi = max(start_idx, end_idx)
        positions = centers[row_idx][lo : hi + 1]
        slash_effect = SlashEffect(positions)
        pending_remove = {
            "actor": actor,
            "cells": [(row_idx, idx) for idx in range(lo, hi + 1)],
        }
        if slash_sound:
            slash_sound.play()

    def start_skill_slash(hit_cells, fx_cells, actor):
        nonlocal slash_effect, pending_remove
        if not fx_cells:
            return False
        centers = get_row_centers(rows)
        fx_positions = [
            (
                centers[row_idx][idx][0] + CROSS_FX_OFFSET_X,
                centers[row_idx][idx][1] + CROSS_FX_OFFSET_Y,
            )
            for row_idx, idx in fx_cells
            if 0 <= row_idx < len(centers) and 0 <= idx < len(centers[row_idx])
        ]
        if not fx_positions:
            return False
        slash_effect = SlashEffect(fx_positions, style="cross")
        pending_remove = {"actor": actor, "cells": hit_cells}
        if slash_sound:
            slash_sound.play()
        return True

    def apply_pending():
        nonlocal pending_remove, slash_effect, current_player, game_state, winner, ai_timer
        if not pending_remove:
            return
        actor = pending_remove["actor"]
        removed_count = 0
        for row_idx, idx in pending_remove["cells"]:
            if row_idx < 0 or row_idx >= len(rows):
                continue
            if idx < 0 or idx >= len(rows[row_idx]):
                continue
            if not rows[row_idx][idx]:
                continue
            if consume_shield(row_idx, idx):
                continue
            rows[row_idx][idx] = False
            removed_count += 1
        update_shield_states_after_action()
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
        switch_turn(actor)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        update_music()
        menu_fx_time += dt
        if pressed_button and not pygame.mouse.get_pressed()[0]:
            pressed_button = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                btn = find_button_at(event.pos)
                if btn is not None:
                    pressed_button = btn
                    continue

            if (
                event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
                and pressed_button is not None
            ):
                if pressed_button.hit(event.pos) and find_button_at(event.pos) is pressed_button:
                    if button_click_sound:
                        button_click_sound.play()
                    handle_button_click(pressed_button)
                pressed_button = None
                continue

            if game_state == "playing":
                if current_player == "player" and not slash_effect:
                    if skill_mode is not None:
                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            player_skill_id = current_skill_id("player")
                            skill_target = None
                            if skill_mode == "shadow_hand":
                                if skill_source_cell is None:
                                    source_hit = find_circle(rows, event.pos)
                                    if not source_hit:
                                        continue
                                    if not shadow_hand_destinations(rows, source_hit):
                                        continue
                                    skill_source_cell = source_hit
                                    continue
                                target_hit = _find_shadow_hand_target(event.pos)
                                if not target_hit:
                                    continue
                                skill_target = (skill_source_cell, target_hit)
                            else:
                                hit = find_circle(rows, event.pos)
                                if not hit:
                                    continue
                                skill_target = hit
                            execution = execute_skill(
                                build_skill_context("player"),
                                player_skill_id,
                                skill_target,
                            )
                            if not execution.consume_skill:
                                continue
                            if execution.start_animation:
                                if not start_skill_slash(
                                    execution.pending_remove_cells,
                                    execution.fx_cells,
                                    "player",
                                ):
                                    continue
                            else:
                                apply_instant_skill_effect(
                                    execution,
                                    player_skill_id,
                                    "player",
                                )
                            skill_used_by["player"] = True
                            skill_mode = None
                            skill_source_cell = None
                    else:
                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
                                select_bounds = get_segment_bounds(
                                    rows, select_row, select_start
                                )
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
                        elif (
                            event.type == pygame.MOUSEBUTTONUP
                            and event.button == 1
                            and selecting
                        ):
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
                    ai_action = nim_ai_move(
                        rows,
                        difficulty,
                        ai_context={
                            "profession_mode": profession_mode_enabled(),
                            "ai_profession": ai_profession,
                            "ai_skill_used": skill_used_by["ai"],
                            "opponent_profession": selected_profession,
                            "opponent_skill_used": skill_used_by["player"],
                            "skill_policy": get_skill_policy(ai_profession),
                            "opponent_can_finish_with_skill": get_opponent_finish_checker(
                                selected_profession
                            ),
                            "shielded_cells": [
                                shield_states["player"]["piece"],
                                shield_states["ai"]["piece"],
                            ],
                        },
                    )
                    executed = False
                    if isinstance(ai_action, dict):
                        action_type = ai_action.get("type")
                        if action_type == "skill":
                            skill_id = ai_action.get("skill_id")
                            target = ai_action.get("target")
                            if isinstance(skill_id, str):
                                parsed_target = parse_skill_target(skill_id, target)
                                if parsed_target is not None:
                                    execution = execute_skill(
                                        build_skill_context("ai"),
                                        skill_id,
                                        parsed_target,
                                    )
                                    if execution.consume_skill:
                                        if execution.start_animation:
                                            if start_skill_slash(
                                                execution.pending_remove_cells,
                                                execution.fx_cells,
                                                "ai",
                                            ):
                                                skill_used_by["ai"] = True
                                                executed = True
                                        else:
                                            apply_instant_skill_effect(
                                                execution,
                                                skill_id,
                                                "ai",
                                            )
                                            skill_used_by["ai"] = True
                                            if skill_id != "shadow_hand":
                                                ai_timer = AI_DELAY
                                            executed = True
                        elif action_type == "normal":
                            row_idx = ai_action.get("row", -1)
                            start_idx = ai_action.get("start", -1)
                            end_idx = ai_action.get("end", -1)
                            if 0 <= row_idx < len(rows):
                                start_slash(row_idx, start_idx, end_idx, "ai")
                                executed = True
                    elif ai_action:
                        row_idx, start_idx, end_idx = ai_action
                        start_slash(row_idx, start_idx, end_idx, "ai")
                        executed = True

                    if not executed:
                        fallback_move = nim_ai_move(rows, difficulty)
                        if fallback_move:
                            row_idx, start_idx, end_idx = fallback_move
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
            valid_shadow_empty_cells = {
                (row_idx, idx)
                for row_idx, row in enumerate(rows)
                for idx, active in enumerate(row)
                if not active
            }
            shadow_empty_cells.intersection_update(valid_shadow_empty_cells)
            shadow_hand_targets = set()
            shadow_virtual_positions = {}
            if skill_mode == "shadow_hand" and skill_source_cell is not None:
                shadow_hand_targets = set(
                    shadow_hand_destinations(rows, skill_source_cell)
                )
                for row_idx, idx, x, y in _shadow_virtual_targets():
                    if (row_idx, idx) in shadow_hand_targets:
                        shadow_virtual_positions[(row_idx, idx)] = (x, y)
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
                    if (
                        skill_mode == "shadow_hand"
                        and skill_source_cell == (row_idx, idx)
                    ):
                        selected = True
                    target_highlight = (row_idx, idx) in shadow_hand_targets
                    if target_highlight:
                        draw_selection_glow((int(x), int(y)), RADIUS)

                    if rows[row_idx][idx]:
                        piece_r = RADIUS
                        if battle_piece_icons:
                            icon_idx = (row_idx * len(row) + idx) % len(
                                battle_piece_icons
                            )
                            if (
                                row_idx < len(piece_icon_map)
                                and idx < len(piece_icon_map[row_idx])
                            ):
                                icon_idx = piece_icon_map[row_idx][idx] % len(
                                    battle_piece_icons
                                )
                            icon = battle_piece_icons[icon_idx]
                            piece_r = min(icon.get_width(), icon.get_height()) // 2
                            if selected:
                                glow_r = max(RADIUS, piece_r - 1)
                                glow_r = min(glow_r, RADIUS + 5)
                                left_shift = int(glow_r * PIECE_MARKER_LEFT_SHIFT_RATIO)
                                ring_center = (int(x) - left_shift, int(y))
                                draw_selection_glow(ring_center, glow_r)
                            icon_rect = icon.get_rect(center=(int(x), int(y)))
                            screen.blit(icon, icon_rect)
                        else:
                            color = CIRCLE_HL if selected else CIRCLE_COLOR
                            pygame.draw.circle(screen, color, (int(x), int(y)), RADIUS)
                        shield_turns = shield_turns_for_cell(row_idx, idx)
                        if shield_turns > 0:
                            shield_center = (int(x), int(y))
                            if battle_piece_icons:
                                # Keep the shield marker aligned with the same perspective offset as selection glow.
                                align_r = max(RADIUS, piece_r - 1)
                                align_r = min(align_r, RADIUS + 5)
                                left_shift = int(
                                    align_r * PIECE_MARKER_LEFT_SHIFT_RATIO
                                )
                                shield_center = (int(x) - left_shift, int(y))
                            draw_shield_marker(shield_center, piece_r, shield_turns)
                    else:
                        if (row_idx, idx) in shadow_empty_cells:
                            continue
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
            for _target_cell, (x, y) in shadow_virtual_positions.items():
                draw_selection_glow((int(x), int(y)), RADIUS)
                pygame.draw.circle(screen, CIRCLE_HL, (int(x), int(y)), RADIUS, 2)

            if game_state == "playing":
                if profession_mode_enabled():
                    skill_button.text = skill_button_text()
                    skill_button.draw(
                        screen,
                        button_font,
                        selected=skill_mode is not None,
                        palette=BATTLE_BUTTON_PALETTE,
                        pressed=is_button_pressed(skill_button),
                    )
                exit_button.draw(
                    screen,
                    button_font,
                    selected=False,
                    palette=BATTLE_BUTTON_PALETTE,
                    pressed=is_button_pressed(exit_button),
                )

            info_rect = pygame.Rect(160, 18, WIDTH - 390, 198)
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
            round_text = f"第{game_number}局" if quick_mode or match_mode == "best3" else "单盘"
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
            if profession_mode_enabled():
                player_line = f"玩家职业：{profession_text('player')}"
                ai_line = f"AI职业：{profession_text('ai')}"
                draw_battle_text_with_icon(
                    player_line,
                    small_font,
                    (info_rect.x + 20, y),
                    get_actor_profession_icon("player", style="battle"),
                )
                draw_battle_text_with_icon(
                    ai_line,
                    small_font,
                    (info_rect.centerx + 10, y),
                    get_actor_profession_icon("ai", style="battle"),
                )
                y += small_font.get_height() + 4

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

            if score_line:
                score_w, _ = small_font.size(score_line)
                draw_battle_text(
                    score_line,
                    small_font,
                    (right_anchor - score_w, y),
                    color=BATTLE_SUBTEXT_MAIN,
                    shadow=BATTLE_SUBTEXT_SHADOW,
                )
            y += small_font.get_height() + gap

            if game_state == "playing" and current_player == "player":
                if not profession_mode_enabled():
                    hint_text = "经典模式：沿同一排连续划棋子，可一次收走连续区间"
                elif skill_mode is not None:
                    hint_text = SKILL_MODE_HINTS.get(
                        skill_mode,
                        "技能模式：点击棋子释放技能",
                    )
                elif current_player == "player" and not skill_used_by["player"]:
                    hint_text = f"可用技能：{skill_name()}"
                else:
                    hint_text = "沿同一排连续划棋子，可一次收走连续区间"
                if skill_mode == "shadow_hand":
                    if skill_source_cell is None:
                        hint_text = (
                            "\u6697\u624b\u6a21\u5f0f\uff1a\u5148\u9009\u62e9\u4e00\u4e2a"
                            "\u4ecd\u5b58\u5728\u7684\u68cb\u5b50"
                        )
                    else:
                        hint_text = (
                            "\u6697\u624b\u6a21\u5f0f\uff1a\u518d\u70b9\u4efb\u610f"
                            "\u68cb\u4f4d\u4ea4\u6362\uff0c\u6216\u70b9\u9ad8\u4eae\u7684"
                            "\u65b0\u589e\u69fd\u4f4d"
                        )
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
                btn.draw(
                    screen,
                    button_font,
                    palette=MENU_BUTTON_PALETTE,
                    pressed=is_button_pressed(btn),
                )

        if game_state == "single_menu":
            draw_panel("单人游戏")
            for btn in single_buttons:
                btn.draw(
                    screen,
                    button_font,
                    palette=MENU_BUTTON_PALETTE,
                    pressed=is_button_pressed(btn),
                )
            back_button.draw(
                screen,
                button_font,
                palette=MENU_BUTTON_PALETTE,
                pressed=is_button_pressed(back_button),
            )

        if game_state == "quick_menu":
            draw_panel("职业模式" if profession_mode_enabled() else "经典模式")
            draw_menu_text("AI难度", label_font, (left_x, label_y))
            for idx, btn in enumerate(difficulty_buttons):
                selected = difficulty == ["random", "medium", "optimal"][idx]
                btn.draw(
                    screen,
                    button_font,
                    selected=selected,
                    palette=MENU_BUTTON_PALETTE,
                    pressed=is_button_pressed(btn),
                )
            if profession_mode_enabled():
                draw_menu_text("职业", label_font, (left_x, profession_label_y))
                for idx, btn in enumerate(profession_buttons):
                    selected = selected_profession == PROFESSION_ORDER[idx]
                    btn.draw(
                        screen,
                        button_font,
                        selected=selected,
                        palette=MENU_BUTTON_PALETTE,
                        pressed=is_button_pressed(btn),
                    )
            quick_y = label_y
            if profession_mode_enabled():
                draw_menu_text_with_icon(
                    f"{profession_text('player')}介绍",
                    label_font,
                    (right_x, quick_y),
                    get_actor_profession_icon("player", style="header"),
                )
                quick_y += label_font.get_height() + 6
                for line in get_profession_intro_lines(selected_profession):
                    draw_menu_text(line, small_font, (right_x, quick_y))
                    quick_y += 28
                quick_y += 8
            quick_lines = ["默认：三局两胜", "默认：玩家先手", "更多设置请进入“自定义游戏”"]
            for line in quick_lines:
                draw_menu_text(line, small_font, (right_x, quick_y))
                quick_y += 26
            start_button.draw(
                screen,
                button_font,
                selected=False,
                palette=MENU_BUTTON_PALETTE,
                pressed=is_button_pressed(start_button),
            )
            back_button.draw(
                screen,
                button_font,
                palette=MENU_BUTTON_PALETTE,
                pressed=is_button_pressed(back_button),
            )

        if game_state == "custom_menu":
            draw_panel("自定义游戏")
            draw_menu_text("选择难度", label_font, (left_x, custom_difficulty_label_y))
            for idx, btn in enumerate(custom_difficulty_buttons):
                selected = difficulty == ["random", "medium", "optimal"][idx]
                btn.draw(
                    screen,
                    button_font,
                    selected=selected,
                    palette=MENU_BUTTON_PALETTE,
                    pressed=is_button_pressed(btn),
                )
            draw_menu_text("玩法", label_font, (left_x, custom_mode_label_y))
            for idx, btn in enumerate(custom_mode_buttons):
                selected = single_mode == ["classic", "profession"][idx]
                btn.draw(
                    screen,
                    button_font,
                    selected=selected,
                    palette=MENU_BUTTON_PALETTE,
                    pressed=is_button_pressed(btn),
                )
            if profession_mode_enabled():
                draw_menu_text("AI职业", label_font, (left_x, custom_ai_prof_label_y))
                for idx, btn in enumerate(ai_profession_buttons):
                    selected = ai_profession == PROFESSION_ORDER[idx]
                    btn.draw(
                        screen,
                        button_font,
                        selected=selected,
                        palette=MENU_BUTTON_PALETTE,
                        pressed=is_button_pressed(btn),
                    )
                draw_menu_text("玩家职业", label_font, (right_x, custom_prof_label_y))
                for idx, btn in enumerate(custom_profession_buttons):
                    selected = selected_profession == PROFESSION_ORDER[idx]
                    btn.draw(
                        screen,
                        button_font,
                        selected=selected,
                        palette=MENU_BUTTON_PALETTE,
                        pressed=is_button_pressed(btn),
                    )

            draw_menu_text("先手", label_font, (right_x, custom_first_label_y))
            for idx, btn in enumerate(first_buttons):
                selected = first_player == ["player", "ai"][idx]
                btn.draw(
                    screen,
                    button_font,
                    selected=selected,
                    palette=MENU_BUTTON_PALETTE,
                    pressed=is_button_pressed(btn),
                )

            draw_menu_text("对局模式", label_font, (right_x, custom_match_label_y))
            for idx, btn in enumerate(match_buttons):
                selected = match_mode == ["single", "best3"][idx]
                btn.draw(
                    screen,
                    button_font,
                    selected=selected,
                    palette=MENU_BUTTON_PALETTE,
                    pressed=is_button_pressed(btn),
                )

            start_button.draw(
                screen,
                button_font,
                selected=False,
                palette=MENU_BUTTON_PALETTE,
                pressed=is_button_pressed(start_button),
            )
            back_button.draw(
                screen,
                button_font,
                palette=MENU_BUTTON_PALETTE,
                pressed=is_button_pressed(back_button),
            )

        if game_state == "rules":
            draw_panel("规则")
            rules_lines = [
                "1. 同一横排连续划过即可移除。",
                "2. 空位不会阻挡，可连续划过。",
                "3. 单人游戏包含：经典模式、职业模式、自定义游戏。",
                "4. 经典/职业默认三局两胜，默认玩家先手。",
                "5. 职业模式中玩家与AI每局各可使用1次技能。",
                "6. 自定义游戏可选玩法、先手、局制与职业。",
            ]
            rule_y = panel_rect.y + 140
            for line in rules_lines:
                draw_menu_text(line, small_font, (panel_rect.x + 40, rule_y))
                rule_y += 28
            back_button.draw(
                screen,
                button_font,
                palette=MENU_BUTTON_PALETTE,
                pressed=is_button_pressed(back_button),
            )

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
                    f"赌局已定：{overall_winner}胜出",
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
                restart_button.draw(
                    screen,
                    button_font,
                    palette=BATTLE_BUTTON_PALETTE,
                    pressed=is_button_pressed(restart_button),
                )
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
                    next_button.draw(
                        screen,
                        button_font,
                        palette=BATTLE_BUTTON_PALETTE,
                        pressed=is_button_pressed(next_button),
                    )
                else:
                    restart_button.text = "再开一局"
                    restart_button.draw(
                        screen,
                        button_font,
                        palette=BATTLE_BUTTON_PALETTE,
                        pressed=is_button_pressed(restart_button),
                    )
            if match_complete():
                menu_button.draw(
                    screen,
                    button_font,
                    palette=BATTLE_BUTTON_PALETTE,
                    pressed=is_button_pressed(menu_button),
                )

        pygame.display.flip()

    if mixer_ready:
        pygame.mixer.music.stop()
    pygame.quit()
