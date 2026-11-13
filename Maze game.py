import pygame
import random
import json
import os
import sys
import math
from collections import deque

pygame.init()
W, H = 960, 760
# Draw at the original logical resolution, then scale to the monitor.
SCREEN = pygame.Surface((W, H))
FULLSCREEN = True
DISPLAY = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

def display_layout():
    # Stretch the complete game canvas to the full available display area.
    # Both mouse coordinates and visuals use the same transformation.
    dw, dh = DISPLAY.get_size()
    return 0, 0, dw, dh

def logical_mouse(pos):
    ox, oy, sw, sh = display_layout()
    return (int((pos[0] - ox) * W / sw), int((pos[1] - oy) * H / sh))

def toggle_fullscreen():
    global DISPLAY, FULLSCREEN
    FULLSCREEN = not FULLSCREEN
    DISPLAY = pygame.display.set_mode((0, 0), pygame.FULLSCREEN) if FULLSCREEN else pygame.display.set_mode((W, H), pygame.RESIZABLE)

pygame.display.set_caption('LETTER MAZE')
CLOCK = pygame.time.Clock()
FPS = 60
NAVY = (9, 13, 40)
PANEL = (19, 28, 49)
PANEL2 = (27, 39, 65)
WHITE = (238, 245, 255)
MUTED = (151, 169, 195)
CYAN = (255, 255, 255)
PURPLE = (170, 115, 255)
PINK = (255, 90, 150)
GOLD = (255, 205, 94)
GREEN = (76, 232, 155)
WALL = (34, 48, 78)
FLOOR = (15, 24, 43)
MAZE_RECT = pygame.Rect(32, 116, 690, 610)
SIDE = pygame.Rect(742, 116, 186, 610)
MODES = [
    {'name': 'EXPLORER', 'cell': 14, 'enemy': False, 'bonus': 1.0},
    {'name': 'ADVENTURER', 'cell': 11, 'enemy': False, 'bonus': 1.5},
    {'name': 'MASTER', 'cell': 9, 'enemy': True, 'bonus': 2.2},
]
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'letter_maze_scores.json')
try:
    with open(SAVE_FILE, 'r', encoding='utf-8') as f:
        SCORES = json.load(f)
        if not isinstance(SCORES, dict):
            SCORES = {}
except (OSError, ValueError):
    SCORES = {}


def font(size, bold=False):
    return pygame.font.SysFont('arial', size, bold=bold)

F_TITLE = font(54, True)
F_BIG = font(38, True)
F_MED = font(24, True)
F_SMALL = font(17)
F_TINY = font(14)


def text(msg, x, y, color=WHITE, f=F_SMALL, center=False):
    img = f.render(str(msg), True, color)
    rect = img.get_rect(center=(x, y)) if center else img.get_rect(topleft=(x, y))
    SCREEN.blit(img, rect)


def panel(rect, color=PANEL, radius=16, border=None):
    pygame.draw.rect(SCREEN, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(SCREEN, border, rect, 2, border_radius=radius)


def button(rect, label, mouse, accent=CYAN):
    hovered = rect.collidepoint(mouse)
    panel(rect, PANEL2 if hovered else PANEL, 12, accent if hovered else (56, 72, 101))
    text(label, rect.centerx, rect.centery, accent if hovered else WHITE, F_MED, True)
    return hovered


def background():
    SCREEN.fill(NAVY)
    for x in range(0, W, 38):
        pygame.draw.line(SCREEN, (15, 23, 43), (x, 0), (x, H))
    for y in range(0, H, 38):
        pygame.draw.line(SCREEN, (15, 23, 43), (0, y), (W, y))


def shortest_path(maze, start, goal):
    if start == goal:
        return [start]
    q = deque([start])
    prev = {start: None}
    rows, cols = len(maze), len(maze[0])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y + dy)
            nx, ny = nxt
            if 0 <= nx < cols and 0 <= ny < rows and maze[ny][nx] == 0 and nxt not in prev:
                prev[nxt] = (x, y)
                if nxt == goal:
                    path = [goal]
                    while prev[path[-1]] is not None:
                        path.append(prev[path[-1]])
                    return path[::-1]
                q.append(nxt)
    return []


def distances(maze, start):
    q = deque([start])
    d = {start: 0}
    rows, cols = len(maze), len(maze[0])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            nxt = (nx, ny)
            if 0 <= nx < cols and 0 <= ny < rows and maze[ny][nx] == 0 and nxt not in d:
                d[nxt] = d[(x, y)] + 1
                q.append(nxt)
    return d


def make_mask(letter, cols, rows):
    surf = pygame.Surface((cols, rows), pygame.SRCALPHA)
    # Render a large, bold glyph and scale it to fit the playable grid.
    glyph_font = pygame.font.SysFont('arial', 260, bold=True)
    glyph = glyph_font.render(letter, True, WHITE)
    max_w, max_h = max(12, cols - 8), max(12, rows - 8)
    scale = min(max_w / max(1, glyph.get_width()), max_h / max(1, glyph.get_height()))
    target = (max(1, int(glyph.get_width() * scale)), max(1, int(glyph.get_height() * scale)))
    glyph = pygame.transform.smoothscale(glyph, target)
    surf.blit(glyph, glyph.get_rect(center=(cols // 2, rows // 2)))
    return [[surf.get_at((x, y)).a >= 100 for x in range(cols)] for y in range(rows)]


def components(mask):
    rows, cols = len(mask), len(mask[0])
    seen = set()
    parts = []
    for y in range(rows):
        for x in range(cols):
            if not mask[y][x] or (x, y) in seen:
                continue
            q = deque([(x, y)])
            seen.add((x, y))
            part = []
            while q:
                cx, cy = q.popleft()
                part.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < cols and 0 <= ny < rows and mask[ny][nx] and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        q.append((nx, ny))
            parts.append(part)
    return sorted(parts, key=len, reverse=True)


def build_maze(letter, cell):
    cols, rows = MAZE_RECT.width // cell, MAZE_RECT.height // cell
    mask = make_mask(letter, cols, rows)
    parts = components(mask)
    if not parts or len(parts[0]) < 30:
        raise ValueError('This character is too small for a playable maze. Try A-Z or 0-9.')
    # Use the largest connected portion of the glyph. Some characters have
    # detached dots; these remain visible as decoration but are not playable.
    allowed = set(parts[0])
    # Randomised depth-first spanning tree over adjacent mask cells.
    # This ensures every open cell is connected and the exit is reachable.
    start = random.choice(parts[0])
    visited = {start}
    stack = [start]
    maze = [[1 for _ in range(cols)] for _ in range(rows)]
    maze[start[1]][start[0]] = 0
    while stack:
        x, y = stack[-1]
        options = []
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            nx, ny = x + dx, y + dy
            middle = (x + dx // 2, y + dy // 2)
            if (nx, ny) in allowed and middle in allowed and (nx, ny) not in visited:
                options.append(((nx, ny), middle))
        if options:
            nxt, middle = random.choice(options)
            visited.add(nxt)
            maze[middle[1]][middle[0]] = 0
            maze[nxt[1]][nxt[0]] = 0
            stack.append(nxt)
        else:
            stack.pop()
    # Keep uncarved cells as WALLS: opening them all destroys the maze paths.
    # The carved spanning tree is connected, so the exit is always reachable.
    # Add a few loops to reduce dead ends, more on Explorer.
    chance = 0.09 if cell == 14 else (0.05 if cell == 11 else 0.025)
    for x, y in allowed:
        if maze[y][x] == 1 and random.random() < chance:
            horizontal = x > 0 and x < cols-1 and maze[y][x-1] == 0 and maze[y][x+1] == 0
            vertical = y > 0 and y < rows-1 and maze[y-1][x] == 0 and maze[y+1][x] == 0
            if horizontal or vertical:
                maze[y][x] = 0
    d = distances(maze, start)
    start = max(d, key=d.get)
    d = distances(maze, start)
    finish = max(d, key=d.get)
    return maze, start, finish, len(d), d[finish]


class Game:
    def __init__(self):
        self.state = 'menu'
        self.letter = 'A'
        self.mode = 0
        self.message = ''
        self.reset_values()

    def reset_values(self):
        self.maze = None
        self.player = (0, 0)
        self.finish = (0, 0)
        self.monster = None
        self.steps = 0
        self.elapsed = 0.0
        self.last_move = 0
        self.last_enemy = 0
        self.path_length = 0
        self.explored = set()
        self.result = ''
        self.score = 0
        self.best = False
        self.hint_until = 0

    def start(self):
        self.reset_values()
        try:
            mode = MODES[self.mode]
            self.maze, self.player, self.finish, self.open_count, self.path_length = build_maze(self.letter, mode['cell'])
            self.explored = {self.player}
            if mode['enemy']:
                d = distances(self.maze, self.player)
                candidates = [p for p, n in d.items() if n > self.path_length * 0.50 and p != self.finish]
                self.monster = random.choice(candidates) if candidates else self.finish
            self.state = 'playing'
            self.message = ''
        except ValueError as e:
            self.message = str(e)
            self.state = 'setup'

    def finish_game(self, victory):
        if self.state != 'playing':
            return
        self.result = 'VICTORY' if victory else 'CAUGHT'
        if victory:
            efficiency = min(1.0, self.path_length / max(1, self.steps))
            self.score = int((1200 * efficiency + 5000 / (1 + self.elapsed / 60)) * MODES[self.mode]['bonus'])
            key = f'{self.letter.upper()}:{MODES[self.mode]["name"]}'
            old = SCORES.get(key)
            self.best = old is None or self.score > old.get('score', 0)
            if self.best:
                SCORES[key] = {'score': self.score, 'time': round(self.elapsed, 1), 'steps': self.steps}
                try:
                    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(SCORES, f, indent=2)
                except OSError:
                    pass
        self.state = 'result'

    def move(self, dx, dy):
        x, y = self.player
        nx, ny = x + dx, y + dy
        if 0 <= ny < len(self.maze) and 0 <= nx < len(self.maze[0]) and self.maze[ny][nx] == 0:
            self.player = (nx, ny)
            self.steps += 1
            self.explored.add(self.player)
            if self.player == self.finish:
                self.finish_game(True)
            elif self.player == self.monster:
                self.finish_game(False)

    def update(self, dt):
        if self.state != 'playing':
            return
        self.elapsed += dt
        now = pygame.time.get_ticks()
        keys = pygame.key.get_pressed()
        if now - self.last_move >= 100:
            for key, (dx, dy) in ((pygame.K_UP, (0,-1)), (pygame.K_w, (0,-1)),
                                   (pygame.K_DOWN, (0,1)), (pygame.K_s, (0,1)),
                                   (pygame.K_LEFT, (-1,0)), (pygame.K_a, (-1,0)),
                                   (pygame.K_RIGHT, (1,0)), (pygame.K_d, (1,0))):
                if keys[key]:
                    self.move(dx, dy)
                    self.last_move = now
                    break
        if self.state != 'playing':
            return
        if self.monster is not None and now - self.last_enemy > 460:
            self.last_enemy = now
            path = shortest_path(self.maze, self.monster, self.player)
            if len(path) > 1:
                self.monster = path[1]
            if self.monster == self.player:
                self.finish_game(False)

    def draw_header(self, subtitle):
        text('LETTER MAZE', 32, 22, WHITE, F_BIG)
        text(subtitle, 34, 79, MUTED, F_SMALL)

    def draw_menu(self, mouse):
        self.draw_header('A maze adventure shaped by your own character')
        panel(pygame.Rect(150, 155, 660, 510), PANEL)
        text('FIND YOUR WAY OUT', W//2, 245, WHITE, F_TITLE, True)
        text('Choose a character. Beat the maze. Escape the hunter.', W//2, 309, MUTED, F_SMALL, True)
        if button(pygame.Rect(320, 380, 320, 68), 'PLAY GAME', mouse):
            pass
        text('WASD / ARROWS   •   P TO PAUSE   •   H FOR HINT', W//2, 502, CYAN, F_SMALL, True)
        text('Best scores are saved automatically', W//2, 547, MUTED, F_SMALL, True)

    def draw_setup(self, mouse):
        self.draw_header('Set up your next escape')
        panel(pygame.Rect(115, 150, 730, 530))
        text('CHOOSE YOUR CHARACTER', W//2, 203, WHITE, F_MED, True)
        panel(pygame.Rect(390, 233, 180, 90), PANEL2, 15, CYAN)
        text(self.letter, W//2, 275, CYAN, F_TITLE, True)
        text('Type A-Z or 0-9', W//2, 337, MUTED, F_SMALL, True)
        for i, m in enumerate(MODES):
            r = pygame.Rect(170 + i * 210, 395, 198, 70)
            panel(r, PANEL2 if i == self.mode else PANEL, 12, CYAN if i == self.mode else (63, 76, 103))
            text(m['name'], r.centerx, r.centery, CYAN if i == self.mode else WHITE, F_SMALL, True)
        button(pygame.Rect(318, 510, 324, 60), 'START ESCAPE', mouse)
        if self.message:
            text(self.message[:75], W//2, 609, PINK, F_TINY, True)
        text('ESC: Back', W//2, 649, MUTED, F_SMALL, True)

    def draw_play(self, mouse):
        self.draw_header(f'{self.letter}  /  {MODES[self.mode]["name"]}')
        panel(MAZE_RECT, FLOOR, 12, (52, 73, 108))
        panel(SIDE, PANEL, 14)
        cell = MODES[self.mode]['cell']
        ox = MAZE_RECT.x + (MAZE_RECT.width - len(self.maze[0]) * cell) // 2
        oy = MAZE_RECT.y + (MAZE_RECT.height - len(self.maze) * cell) // 2
        # Render the full letter silhouette with bright corridors and dark walls.
        letter_mask = make_mask(self.letter, len(self.maze[0]), len(self.maze))
        for y, row in enumerate(self.maze):
            for x, val in enumerate(row):
                if letter_mask[y][x]:
                    color = (40, 63, 94) if val else (102, 184, 195)
                    pygame.draw.rect(SCREEN, color, (ox+x*cell, oy+y*cell, cell, cell))
        if pygame.time.get_ticks() < self.hint_until:
            path = shortest_path(self.maze, self.player, self.finish)
            for x, y in path:
                pygame.draw.circle(SCREEN, GOLD, (ox+x*cell+cell//2, oy+y*cell+cell//2), max(2, cell//5))
        for pos, color in ((self.finish, PINK), (self.player, CYAN), (self.monster, PURPLE)):
            if pos is None:
                continue
            x, y = pos
            center = (ox + x*cell + cell//2, oy + y*cell + cell//2)
            pygame.draw.circle(SCREEN, color, center, max(3, cell//2))
            pygame.draw.circle(SCREEN, WHITE, center, max(1, cell//5))
        text('LIVE STATS', 759, 144, CYAN, F_SMALL)
        stats = [('TIME', f'{int(self.elapsed//60):02d}:{int(self.elapsed%60):02d}'),
                 ('STEPS', str(self.steps)), ('EXPLORED', str(len(self.explored))),
                 ('SHORTEST', str(self.path_length)),
                 ('TO EXIT', str(max(0, len(shortest_path(self.maze, self.player, self.finish))-1)))]
        for i, (label, value) in enumerate(stats):
            y = 195 + i * 76
            text(label, 759, y, MUTED, F_TINY)
            text(value, 759, y + 20, WHITE, F_MED)
        text('● YOU', 759, 594, CYAN, F_TINY)
        text('● EXIT', 840, 594, PINK, F_TINY)
        if self.monster:
            text('● HUNTER', 759, 616, PURPLE, F_TINY)
        text('P: PAUSE', 759, 665, MUTED, F_TINY)
        text('H: HINT (-score)', 759, 686, MUTED, F_TINY)

    def draw_pause(self, mouse):
        self.draw_play(mouse)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((4, 8, 20, 200))
        SCREEN.blit(shade, (0, 0))
        panel(pygame.Rect(240, 220, 480, 325), PANEL2, 20, CYAN)
        text('PAUSED', W//2, 286, WHITE, F_TITLE, True)
        button(pygame.Rect(315, 351, 330, 56), 'RESUME', mouse)
        button(pygame.Rect(315, 425, 330, 56), 'MAIN MENU', mouse, PINK)

    def draw_result(self, mouse):
        self.draw_header('Your escape report')
        panel(pygame.Rect(174, 136, 612, 545), PANEL, 20)
        won = self.result == 'VICTORY'
        text('ESCAPE COMPLETE!' if won else 'THE HUNTER CAUGHT YOU', W//2, 207, GREEN if won else PINK, F_BIG, True)
        if self.best:
            text('★ NEW PERSONAL BEST ★', W//2, 257, GOLD, F_MED, True)
        else:
            text('TRY AGAIN TO BEAT YOUR BEST', W//2, 257, MUTED, F_SMALL, True)
        if won:
            ratio = self.path_length / max(1, self.steps)
            stars = 3 if ratio >= .80 else 2 if ratio >= .50 else 1
        else:
            stars = 0
        text('★ ' * stars + '☆ ' * (3-stars), W//2, 306, GOLD, F_BIG, True)
        rows = [('MODE', MODES[self.mode]['name']), ('CHARACTER', self.letter),
                ('FINAL TIME', f'{int(self.elapsed//60):02d}:{int(self.elapsed%60):02d}'),
                ('TOTAL STEPS', str(self.steps)), ('SCORE', f'{self.score:,}')]
        for i, (k, v) in enumerate(rows):
            y = 358 + i * 43
            text(k, 270, y, MUTED, F_SMALL)
            text(v, 665, y, WHITE, F_MED, True)
        button(pygame.Rect(245, 595, 216, 55), 'PLAY AGAIN', mouse)
        button(pygame.Rect(493, 595, 216, 55), 'MAIN MENU', mouse, PINK)

    def handle(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if self.state == 'menu':
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.state = 'setup'
            elif self.state == 'setup':
                if event.key == pygame.K_ESCAPE:
                    self.state = 'menu'
                elif event.key == pygame.K_RETURN:
                    self.start()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.mode = event.key - pygame.K_1
                elif event.unicode and event.unicode.upper() in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
                    self.letter = event.unicode.upper()
            elif self.state == 'playing':
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.state = 'paused'
                elif event.key == pygame.K_h:
                    self.hint_until = pygame.time.get_ticks() + 1800
                    self.steps += 8  # hint penalty lowers efficiency score
                elif event.key == pygame.K_r:
                    self.start()
            elif self.state == 'paused':
                if event.key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN):
                    self.state = 'playing'
            elif self.state == 'result':
                if event.key == pygame.K_RETURN:
                    self.start()
                elif event.key == pygame.K_ESCAPE:
                    self.state = 'menu'
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = logical_mouse(event.pos)
            if self.state == 'menu' and pygame.Rect(320,380,320,68).collidepoint(mx,my):
                self.state = 'setup'
            elif self.state == 'setup':
                for i in range(3):
                    if pygame.Rect(170+i*210,395,198,70).collidepoint(mx,my):
                        self.mode = i
                if pygame.Rect(318,510,324,60).collidepoint(mx,my):
                    self.start()
            elif self.state == 'paused':
                if pygame.Rect(315,351,330,56).collidepoint(mx,my):
                    self.state = 'playing'
                elif pygame.Rect(315,425,330,56).collidepoint(mx,my):
                    self.state = 'menu'
            elif self.state == 'result':
                if pygame.Rect(245,595,216,55).collidepoint(mx,my):
                    self.start()
                elif pygame.Rect(493,595,216,55).collidepoint(mx,my):
                    self.state = 'menu'


def main():
    game = Game()
    while True:
        dt = min(CLOCK.tick(FPS) / 1000.0, 0.1)
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                toggle_fullscreen()
                continue
            game.handle(event)
        game.update(dt)
        background()
        mouse = logical_mouse(pygame.mouse.get_pos())
        if game.state == 'menu':
            game.draw_menu(mouse)
        elif game.state == 'setup':
            game.draw_setup(mouse)
        elif game.state == 'playing':
            game.draw_play(mouse)
        elif game.state == 'paused':
            game.draw_pause(mouse)
        elif game.state == 'result':
            game.draw_result(mouse)
        ox, oy, sw, sh = display_layout()
        DISPLAY.fill(NAVY)
        scaled = pygame.transform.smoothscale(SCREEN, (sw, sh))
        DISPLAY.blit(scaled, (ox, oy))
        pygame.display.flip()


if __name__ == '__main__':
    main()
