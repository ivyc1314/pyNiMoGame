import math
import random
from array import array

import pygame

from constants import HEIGHT, RADIUS, SLASH_DURATION, WIDTH
from game_logic import clamp


BG_TOP = (232, 242, 252)
BG_BOTTOM = (198, 220, 238)
CLOUD_1 = (255, 231, 215, 120)
CLOUD_2 = (210, 230, 255, 130)
CLOUD_3 = (255, 255, 255, 90)
TRAIL_COLOR = (255, 205, 170)
TRAIL_GLOW = (255, 235, 210)
BTN_COLOR = (225, 230, 235)
BTN_HL = (180, 210, 240)
BTN_TEXT = (30, 40, 50)
BTN_BORDER = (175, 188, 202)
BTN_SHADOW = (0, 0, 0, 28)


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

    def draw(self, surface, font, selected=False, palette=None):
        if palette:
            base = palette["base"]
            highlight = palette["highlight"]
            text_color = palette["text"]
            border = palette["border"]
            shadow = palette["shadow"]
        else:
            base = BTN_COLOR
            highlight = BTN_HL
            text_color = BTN_TEXT
            border = BTN_BORDER
            shadow = BTN_SHADOW

        color = highlight if selected else base
        shadow_rect = self.rect.move(2, 3)
        pygame.draw.rect(surface, shadow, shadow_rect, border_radius=10)
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=10)
        label = font.render(self.text, True, text_color)
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


def draw_slash_trail(surface, points):
    if len(points) < 2:
        return
    fx = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    total = len(points) - 1
    for i in range(1, len(points)):
        t = i / max(total, 1)
        alpha = int(200 * t)
        width = int(2 + 5 * t)
        pygame.draw.line(fx, (*TRAIL_COLOR, alpha), points[i - 1], points[i], width)
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
