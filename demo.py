import pygame
import sys
import os
import textwrap
import random

try:
    from pygame._sdl2 import Window as SDL2Window, Renderer as SDL2Renderer, Texture as SDL2Texture
    SDL2_MULTI_WINDOW_AVAILABLE = True
except ImportError:
    SDL2Window = None
    SDL2Renderer = None
    SDL2Texture = None
    SDL2_MULTI_WINDOW_AVAILABLE = False

pygame.init()
clock = pygame.time.Clock()

# -----------------------------
# PYGAME SCREEN SETUP
# -----------------------------
WIDTH, HEIGHT = 640, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ARcade")

# -----------------------------
# LAYOUT / STYLE
# -----------------------------
SCREEN_CENTER_X = WIDTH // 2
SCREEN_CENTER_Y = HEIGHT // 2

CALIBRATION_DURATION_MS = 10000
COUNTDOWN_STEP_MS = 1000
DOUBLE_TAP_WINDOW_MS = 500

FAST_REFLEX_MIN_GAP_MS = 500
FAST_REFLEX_MAX_GAP_MS = 1800
FAST_REFLEX_MIN_VISIBLE_MS = 1000
FAST_REFLEX_MAX_VISIBLE_MS = 3000
FAST_REFLEX_BAD_CHANCE = 0.4
FAST_REFLEX_TOTAL_ROUNDS = 15
FAST_REFLEX_END_SCREEN_MS = 2200

PARAGRAPH_MAX_CHARS_PER_LINE = 32
PARAGRAPH_MAX_LINES_PER_PAGE = 3
LINE_SPACING = 38
TEXT_SIZE = 32

COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GREEN = (60, 200, 100)
COLOR_YELLOW = (240, 200, 50)
COLOR_RED = (220, 60, 60)
COLOR_DARK_GRAY = (40, 40, 40)
COLOR_GRAY = (120, 120, 120)

CARD_SYMBOLS = [
    "Monster1.png", "Monster2.png", "Monster3.png", "Monster4.png",
    "Monster1.png", "Monster2.png", "Monster3.png", "Monster4.png",
]

CARD_COLS = 4
CARD_ROWS = 2
CARD_W = 110
CARD_H = 110
CARD_PAD = 16
GRID_W = CARD_COLS * CARD_W + (CARD_COLS - 1) * CARD_PAD
GRID_H = CARD_ROWS * CARD_H + (CARD_ROWS - 1) * CARD_PAD
GRID_X = (WIDTH - GRID_W) // 2
GRID_Y = (HEIGHT - GRID_H) // 2 + 10

MENU_ITEMS = [
    {"label": "Matching", "state": "matching"},
    {"label": "Fast Reflexes", "state": "fast_reflexes"},
    {"label": "Second Guesser", "state": "timer_guess"},
    {"label": "DDR", "state": "ddr"},
]
MENU_COLS = 2
MENU_ROWS = 2
MENU_TILE_W = 150
MENU_TILE_H = 150
MENU_PAD_X = 20
MENU_PAD_Y = 18
MENU_GRID_W = MENU_COLS * MENU_TILE_W + (MENU_COLS - 1) * MENU_PAD_X
MENU_GRID_H = MENU_ROWS * MENU_TILE_H + (MENU_ROWS - 1) * MENU_PAD_Y
MENU_GRID_X = (WIDTH - MENU_GRID_W) // 2
MENU_GRID_Y = 58
MENU_QR_SIZE = 104
MENU_QR_FILE = "SquareQRCODE.png"

TUTORIAL_QR_FILE = "SquareQRCODE.png"

# -----------------------------
# TEXT HELPERS
# -----------------------------
def text(message, size, color, x, y):
    font = pygame.font.SysFont(None, size)
    text_surface = font.render(message, True, color)
    text_rect = text_surface.get_rect(center=(x, y))
    screen.blit(text_surface, text_rect)


def draw_multiline_text(lines, size, color, center_x, center_y, line_spacing=35):
    font = pygame.font.SysFont(None, size)
    total_height = (len(lines) - 1) * line_spacing
    first_line_y = center_y - total_height / 2

    for i, line in enumerate(lines):
        text_surface = font.render(line, True, color)
        line_y = first_line_y + i * line_spacing
        text_rect = text_surface.get_rect(center=(center_x, line_y))
        screen.blit(text_surface, text_rect)


def surface_text(surface, message, size, color, x, y):
    font = pygame.font.SysFont(None, size)
    text_surface = font.render(message, True, color)
    text_rect = text_surface.get_rect(center=(x, y))
    surface.blit(text_surface, text_rect)


def surface_multiline_text(surface, lines, size, color, center_x, center_y, line_spacing=35):
    font = pygame.font.SysFont(None, size)
    total_height = (len(lines) - 1) * line_spacing
    first_line_y = center_y - total_height / 2

    for i, line in enumerate(lines):
        text_surface = font.render(line, True, color)
        line_y = first_line_y + i * line_spacing
        text_rect = text_surface.get_rect(center=(center_x, line_y))
        surface.blit(text_surface, text_rect)


def split_paragraph_into_pages(paragraph, max_chars_per_line=32, max_lines_per_page=3):
    wrapped_lines = textwrap.wrap(
        paragraph,
        width=max_chars_per_line,
        break_long_words=False,
        break_on_hyphens=False,
    )

    if not wrapped_lines:
        return [[""]]

    pages = []
    for i in range(0, len(wrapped_lines), max_lines_per_page):
        pages.append(wrapped_lines[i:i + max_lines_per_page])

    return pages


# -----------------------------
# SPRITE HELPERS
# -----------------------------
def load_raw_sprite(filename):
    path = os.path.join("sprites", filename)
    try:
        return pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return None


def scale_to_fit(image, max_w, max_h, smooth=True):
    if image is None:
        return None
    img_w, img_h = image.get_size()
    if img_w == 0 or img_h == 0:
        return None
    scale_factor = min(max_w / img_w, max_h / img_h)
    new_size = (max(1, int(img_w * scale_factor)), max(1, int(img_h * scale_factor)))
    if smooth:
        return pygame.transform.smoothscale(image, new_size)
    return pygame.transform.scale(image, new_size)


def draw_sprite(filename, fit_to_screen=False, smooth=True, fill_screen=False):
    path = os.path.join("sprites", filename)

    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        text(f"Missing sprite: {filename}", 24, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)
        return

    if fill_screen:
        # Force sprite to occupy the full screen area for game states that need edge-to-edge visuals.
        if smooth:
            image = pygame.transform.smoothscale(image, (WIDTH, HEIGHT))
        else:
            image = pygame.transform.scale(image, (WIDTH, HEIGHT))
    elif fit_to_screen:
        img_w, img_h = image.get_size()
        scale_factor = min(WIDTH / img_w, HEIGHT / img_h)
        new_size = (int(img_w * scale_factor), int(img_h * scale_factor))
        if smooth:
            image = pygame.transform.smoothscale(image, new_size)
        else:
            image = pygame.transform.scale(image, new_size)

    rect = image.get_rect(center=(SCREEN_CENTER_X, SCREEN_CENTER_Y))
    screen.blit(image, rect)


def load_card_sprite(filename):
    path = os.path.join("sprites", filename)
    try:
        image = pygame.image.load(path).convert_alpha()
        image = pygame.transform.smoothscale(image, (CARD_W - 16, CARD_H - 16))
        return image
    except (pygame.error, FileNotFoundError):
        return None


def card_rect(index):
    col = index % CARD_COLS
    row = index // CARD_COLS
    x = GRID_X + col * (CARD_W + CARD_PAD)
    y = GRID_Y + row * (CARD_H + CARD_PAD)
    return pygame.Rect(x, y, CARD_W, CARD_H)


# -----------------------------
# SECONDARY WINDOW HELPERS
# -----------------------------

def event_window_id(event):
    if hasattr(event, "window"):
        return event.window
    if hasattr(event, "windowID"):
        return event.windowID
    event_dict = getattr(event, "dict", None)
    if isinstance(event_dict, dict):
        return event_dict.get("window") or event_dict.get("windowID")
    return None


def create_secondary_window(title, position):
    if not SDL2_MULTI_WINDOW_AVAILABLE:
        return None, None, None
    window = SDL2Window(title, size=(WIDTH, HEIGHT), position=position)
    renderer = SDL2Renderer(window)
    surface = pygame.Surface((WIDTH, HEIGHT)).convert_alpha()
    return window, renderer, surface


def destroy_secondary_window(window_name):
    global tutorial_qr_window, tutorial_qr_renderer, tutorial_qr_surface
    global menu_window, menu_renderer, menu_surface
    global matching_window, matching_renderer, matching_surface

    if window_name == "tutorial_qr":
        if tutorial_qr_renderer is not None:
            tutorial_qr_renderer = None
        if tutorial_qr_window is not None:
            try:
                tutorial_qr_window.destroy()
            except AttributeError:
                pass
            tutorial_qr_window = None
        tutorial_qr_surface = None
    elif window_name == "menu":
        if menu_renderer is not None:
            menu_renderer = None
        if menu_window is not None:
            try:
                menu_window.destroy()
            except AttributeError:
                pass
            menu_window = None
        menu_surface = None
    elif window_name == "matching":
        if matching_renderer is not None:
            matching_renderer = None
        if matching_window is not None:
            try:
                matching_window.destroy()
            except AttributeError:
                pass
            matching_window = None
        matching_surface = None


def present_surface(renderer, surface):
    if renderer is None or surface is None:
        return
    texture = SDL2Texture.from_surface(renderer, surface)
    renderer.clear()
    texture.draw()
    renderer.present()
    del texture


# -----------------------------
# MATCHING GAME
# -----------------------------
class MatchingGame:
    def __init__(self):
        self.card_back = load_card_sprite("CardBacksMonster.png")
        self.qr_card = load_card_sprite("SquareQRCODE.png")
        self.face_images = {s: load_card_sprite(s) for s in set(CARD_SYMBOLS)}
        self.reset()

    def reset(self):
        symbols = CARD_SYMBOLS[:]
        random.shuffle(symbols)
        self.symbols = symbols
        self.revealed = [False] * 8
        self.selected = None
        self.first_scanned = None
        self.matched_pairs = 0
        self.flash_card = None
        self.flash_start = None
        self.FLASH_MS = 800
        self.start_time = None
        self.end_time = None
        self.last_revealed_symbol = None
        self.pending_reveal_symbol = None
        self.pending_scan_index = None
        self.reveal_space_time = None
        self.match_feedback_until = 0
        self.match_feedback_text = ""
        self.MATCH_FEEDBACK_MS = 1000
        self.MATCH_MONSTER_PREVIEW_MS = 3000
        self.match_feedback_start = 0
        self.first_scanned_symbol = None

    @property
    def done(self):
        return self.matched_pairs == 4

    def select(self, index):
        if self.pending_reveal_symbol is not None:
            return
        if self.revealed[index]:
            return
        if index == self.selected:
            return
        self.flash_card = None
        self.pending_reveal_symbol = self.symbols[index]
        self.pending_scan_index = index
        self.last_revealed_symbol = None
        self.reveal_space_time = None
        self.selected = index

        if self.start_time is None:
            self.start_time = pygame.time.get_ticks()

    def confirm_pending_scan(self, current_time):
        if self.pending_reveal_symbol is None or self.pending_scan_index is None:
            return

        scanned_index = self.pending_scan_index
        self.last_revealed_symbol = self.pending_reveal_symbol
        self.pending_reveal_symbol = None
        self.pending_scan_index = None
        self.reveal_space_time = None
        self.selected = None

        if self.first_scanned is None:
            self.first_scanned = scanned_index
            self.first_scanned_symbol = self.symbols[scanned_index]
            return

        first = self.first_scanned
        second = scanned_index
        if self.symbols[first] == self.symbols[second] and first != second:
            self.revealed[first] = True
            self.revealed[second] = True
            self.first_scanned = None
            self.first_scanned_symbol = None
            self.matched_pairs += 1
            self.match_feedback_start = current_time + self.MATCH_MONSTER_PREVIEW_MS
            self.match_feedback_until = self.match_feedback_start + self.MATCH_FEEDBACK_MS
            self.match_feedback_text = f"{self.matched_pairs}/4 matches found"
            if self.matched_pairs == 4:
                self.end_time = pygame.time.get_ticks()
        else:
            self.flash_card = first
            self.flash_start = current_time
            self.first_scanned = second
            self.first_scanned_symbol = self.symbols[second]

    def update(self, current_time):
        if self.flash_card is not None and current_time - self.flash_start >= self.FLASH_MS:
            self.flash_card = None

    def draw(self, surface, current_time, show_revealed_faces=True, show_status_text=True, show_qr_on_reveal=False):
        self.update(current_time)

        font_label = pygame.font.SysFont(None, 26)
        font_num = pygame.font.SysFont(None, 22)

        if self.end_time is not None:
            elapsed_s = (self.end_time - self.start_time) / 1000.0
            time_str = f"Time: {elapsed_s:.2f}s"
        else:
            time_str = None

        for i in range(8):
            rect = card_rect(i)
            face_up = self.revealed[i]
            is_sel = (i == self.selected)
            is_flash = (i == self.flash_card)

            if face_up:
                continue

            qr_visible = (
                show_qr_on_reveal
                and self.pending_scan_index is not None
                and i == self.pending_scan_index
            )

            pygame.draw.rect(surface, COLOR_DARK_GRAY, rect, border_radius=10)
            num_surf = font_num.render(str(i + 1), True, COLOR_GRAY)
            surface.blit(num_surf, (rect.x + 6, rect.y + 5))

            is_first_scanned = (i == self.first_scanned)

            if qr_visible or is_first_scanned or is_sel:
                img = self.qr_card
            elif face_up or is_flash:
                if show_revealed_faces:
                    img = self.face_images.get(self.symbols[i])
                else:
                    img = self.card_back
            else:
                img = self.card_back

            if img:
                img_rect = img.get_rect(center=rect.center)
                surface.blit(img, img_rect)
            else:
                fb = font_label.render(self.symbols[i], True, COLOR_WHITE)
                surface.blit(fb, fb.get_rect(center=rect.center))

        below_y = GRID_Y + GRID_H + 24

        if show_status_text and self.done:
            congrats_surf = font_label.render("Congrats you found all the matches!", True, COLOR_WHITE)
            surface.blit(congrats_surf, congrats_surf.get_rect(center=(SCREEN_CENTER_X, below_y)))
            if time_str is not None:
                time_surf = font_label.render(time_str, True, COLOR_WHITE)
                surface.blit(time_surf, time_surf.get_rect(center=(SCREEN_CENTER_X, below_y + 26)))


matching_game = MatchingGame()
matching_intro_index = 0
matching_window = None
matching_renderer = None
matching_surface = None


MATCHING_INTRO = []

def paragraph_pages(paragraph):
    pages = split_paragraph_into_pages(
        paragraph,
        max_chars_per_line=PARAGRAPH_MAX_CHARS_PER_LINE,
        max_lines_per_page=PARAGRAPH_MAX_LINES_PER_PAGE,
    )
    return [{"type": "text", "lines": page} for page in pages]


MATCHING_INTRO += paragraph_pages("Welcome to card matching!")
MATCHING_INTRO += paragraph_pages(
    "Scan a card's QR code to reveal its icon. "
    "Then, scan another card to see if you've found the matching pair. "
    "Keep scanning and setting aside pairs until you've matched them all."
)
MATCHING_INTRO += paragraph_pages("Choose 1-8 to flip a card and scan to begin")


def open_matching_window():
    global matching_window, matching_renderer, matching_surface
    if not SDL2_MULTI_WINDOW_AVAILABLE:
        return
    if matching_window is None:
        matching_window, matching_renderer, matching_surface = create_secondary_window(
            "ARcade - Matching",
            (760, 80),
        )


def close_matching_window():
    destroy_secondary_window("matching")


def draw_matching_window(current_time):
    if matching_renderer is None or matching_surface is None:
        return
    matching_surface.fill(COLOR_BLACK)
    matching_game.draw(
        matching_surface,
        current_time,
        show_revealed_faces=False,
        show_status_text=False,
        show_qr_on_reveal=True,
    )
    present_surface(matching_renderer, matching_surface)


def is_matching_window_event(event):
    if not (SDL2_MULTI_WINDOW_AVAILABLE and matching_window is not None):
        return False
    window_id = event_window_id(event)
    if window_id is None:
        return True
    return window_id == matching_window.id


# -----------------------------
# TUTORIAL / MENU WINDOW HELPERS
# -----------------------------
tutorial_qr_window = None
tutorial_qr_renderer = None
tutorial_qr_surface = None
menu_window = None
menu_renderer = None
menu_surface = None
menu_selected_index = 0


def open_tutorial_qr_window():
    global tutorial_qr_window, tutorial_qr_renderer, tutorial_qr_surface
    if not SDL2_MULTI_WINDOW_AVAILABLE:
        return
    if tutorial_qr_window is None:
        tutorial_qr_window, tutorial_qr_renderer, tutorial_qr_surface = create_secondary_window(
            "ARcade - QR Scan",
            (760, 80),
        )


def close_tutorial_qr_window():
    destroy_secondary_window("tutorial_qr")


def draw_tutorial_qr_window():
    if tutorial_qr_renderer is None or tutorial_qr_surface is None:
        return

    tutorial_qr_surface.fill(COLOR_BLACK)
    qr_raw = load_raw_sprite(TUTORIAL_QR_FILE)
    if qr_raw is None:
        surface_text(tutorial_qr_surface, f"Missing sprite: {TUTORIAL_QR_FILE}", 24, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)
    else:
        qr_image = scale_to_fit(qr_raw, WIDTH - 40, HEIGHT - 70, smooth=True)
        if qr_image is not None:
            qr_rect = qr_image.get_rect(center=(SCREEN_CENTER_X, SCREEN_CENTER_Y - 10))
            tutorial_qr_surface.blit(qr_image, qr_rect)
    present_surface(tutorial_qr_renderer, tutorial_qr_surface)


def open_menu_window():
    global menu_window, menu_renderer, menu_surface
    if not SDL2_MULTI_WINDOW_AVAILABLE:
        return
    if menu_window is None:
        menu_window, menu_renderer, menu_surface = create_secondary_window(
            "ARcade - Select a Game",
            (760, 80),
        )


def close_menu_window():
    destroy_secondary_window("menu")


def menu_state_for_index(index):
    return [STATE_MATCHING, STATE_FAST_REFLEXES, STATE_TIMER_GUESS, STATE_DDR][index]


def draw_menu_window():
    if menu_renderer is None or menu_surface is None:
        return

    menu_surface.fill(COLOR_BLACK)
    surface_text(menu_surface, "Tap 1-4 to select a QR code to scan", 22, COLOR_WHITE, SCREEN_CENTER_X, 26)

    qr_raw = load_raw_sprite(MENU_QR_FILE)
    if qr_raw is None:
        surface_text(menu_surface, f"Missing sprite: {MENU_QR_FILE}", 24, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)
        present_surface(menu_renderer, menu_surface)
        return

    qr_image = scale_to_fit(qr_raw, MENU_QR_SIZE, MENU_QR_SIZE, smooth=True)
    label_font = pygame.font.SysFont(None, 22)
    number_font = pygame.font.SysFont(None, 24)

    for index, item in enumerate(MENU_ITEMS):
        col = index % 2
        row = index // 2
        tile_x = MENU_GRID_X + col * (MENU_TILE_W + MENU_PAD_X)
        tile_y = MENU_GRID_Y + row * (MENU_TILE_H + MENU_PAD_Y)
        tile_rect = pygame.Rect(tile_x, tile_y, MENU_TILE_W, MENU_TILE_H)
        border_color = COLOR_YELLOW if index == menu_selected_index else COLOR_GRAY
        pygame.draw.rect(menu_surface, COLOR_DARK_GRAY, tile_rect, border_radius=12)
        pygame.draw.rect(menu_surface, border_color, tile_rect, 3, border_radius=12)

        if qr_image is not None:
            qr_rect = qr_image.get_rect(center=(tile_rect.centerx, tile_rect.centery - 8))
            menu_surface.blit(qr_image, qr_rect)

        number_surf = number_font.render(str(index + 1), True, COLOR_WHITE)
        menu_surface.blit(number_surf, (tile_rect.x + 8, tile_rect.y + 6))

        label_surf = label_font.render(item["label"], True, COLOR_WHITE)
        menu_surface.blit(label_surf, label_surf.get_rect(center=(tile_rect.centerx, tile_rect.bottom - 18)))

    present_surface(menu_renderer, menu_surface)


# -----------------------------
# FAST REFLEXES STATE
# -----------------------------
fast_reflex_good_sprites = [
    "Fast_Reflexes/Fish1.png",
    "Fast_Reflexes/Fish2.png",
    "Fast_Reflexes/Fish3.png",
    "Fast_Reflexes/Fish4.png",
    "Fast_Reflexes/Fish5.png",
]
fast_reflex_bad_sprites = [
    "Fast_Reflexes/Ball1.png",
    "Fast_Reflexes/Ball2.png",
    "Fast_Reflexes/Tree.png",
    "Fast_Reflexes/Boot.png",
]
fast_reflex_next_spawn_time = 0
fast_reflex_sprite_end_time = None
fast_reflex_current_sprite = None
fast_reflex_current_is_bad = False
fast_reflex_bad_spawn_time = None
fast_reflex_rounds_completed = 0
fast_reflex_hits = 0
fast_reflex_misses = 0
fast_reflex_false_alarms = 0
fast_reflex_score = 0
fast_reflex_last_reaction_ms = None
fast_reflex_feedback = ""
fast_reflex_feedback_until = 0
fast_reflex_game_over = False
fast_reflex_waiting_to_start = True
fast_reflex_intro_sprite = None
fast_reflex_game_over_time = None


def fast_reflex_set_feedback(message, now_ms, duration_ms=1200):
    global fast_reflex_feedback, fast_reflex_feedback_until
    fast_reflex_feedback = message
    fast_reflex_feedback_until = now_ms + duration_ms


def fast_reflex_schedule_next_spawn(now_ms):
    global fast_reflex_next_spawn_time
    fast_reflex_next_spawn_time = now_ms + random.randint(FAST_REFLEX_MIN_GAP_MS, FAST_REFLEX_MAX_GAP_MS)


def reset_fast_reflexes():
    global fast_reflex_next_spawn_time, fast_reflex_sprite_end_time, fast_reflex_current_sprite
    global fast_reflex_current_is_bad, fast_reflex_bad_spawn_time, fast_reflex_rounds_completed
    global fast_reflex_hits, fast_reflex_misses, fast_reflex_false_alarms, fast_reflex_score
    global fast_reflex_last_reaction_ms, fast_reflex_feedback, fast_reflex_feedback_until, fast_reflex_game_over
    global fast_reflex_waiting_to_start, fast_reflex_intro_sprite, fast_reflex_game_over_time

    now_ms = pygame.time.get_ticks()
    fast_reflex_next_spawn_time = None
    fast_reflex_sprite_end_time = None
    fast_reflex_current_sprite = None
    fast_reflex_current_is_bad = False
    fast_reflex_bad_spawn_time = None
    fast_reflex_rounds_completed = 0
    fast_reflex_hits = 0
    fast_reflex_misses = 0
    fast_reflex_false_alarms = 0
    fast_reflex_score = 0
    fast_reflex_last_reaction_ms = None
    fast_reflex_feedback = ""
    fast_reflex_feedback_until = now_ms
    fast_reflex_game_over = False
    fast_reflex_waiting_to_start = True
    fast_reflex_intro_sprite = None
    fast_reflex_game_over_time = None


# -----------------------------
# TUTORIAL / TIMER / DDR SEQUENCES
# -----------------------------
tutorial_sequence = []
tutorial_sequence += paragraph_pages("Tap the side of your glasses once to continue reading.")
tutorial_sequence += paragraph_pages("Perfect!")
tutorial_sequence += paragraph_pages("Now you can tap the side of your glasses to advance through the tutorial.")
tutorial_sequence += paragraph_pages("Lets display a sprite!")
tutorial_sequence.append({"type": "sprite", "filename": "hotdog_4bit.png"})
tutorial_sequence += paragraph_pages("Double tap the side of your glasses to scan a QR code")
tutorial_sequence.append({"type": "qr"})
tutorial_sequence.append({"type": "sprite", "filename": "check.png"})
tutorial_sequence += paragraph_pages("Now lets test your timing. Tap when you think 2 seconds have passed")
tutorial_sequence.append({"type": "countdown"})
tutorial_sequence.append({"type": "timing"})
tutorial_sequence.append({"type": "result"})
tutorial_sequence += paragraph_pages("This concludes the demo!")
tutorial_sequence += paragraph_pages("You're now ready to explore the Digital Arcade.")


def create_timer_guess_sequence(target_seconds):
    sequence = []
    sequence += paragraph_pages(
        "Welcome to Second Guesser! You will be shown a number, once it disappears, try to tap exactly that many seconds later. The closer you are to the target time, the better your score. Ready to test your timing?"
    )
    sequence.append({"type": "timer_number", "number": target_seconds})
    sequence.append({"type": "timer_blank"})
    sequence.append({"type": "timer_result"})
    return sequence


def create_ddr_sequence():
    sequence = []
    sequence += paragraph_pages("Welcome to DDR!")
    sequence += paragraph_pages("Use 2 fingers to swipe on the touchpad in the direction that matches the arrow on screen!")
    sequence += paragraph_pages("You have 10 arrows. Good luck!")
    sequence.append({"type": "ddr_game"})
    sequence.append({"type": "ddr_result"})
    return sequence


# -----------------------------
# STATE
# -----------------------------
STATE_CALIBRATING = "calibrating"
STATE_TUTORIAL = "tutorial"
STATE_BETWEEN_GAMES = "between_games"
STATE_MATCHING = "matching"
STATE_FAST_REFLEXES = "fast_reflexes"
STATE_TIMER_GUESS = "timer_guess"
STATE_DDR = "ddr"

state = STATE_CALIBRATING
state_start_time = pygame.time.get_ticks()

current_page_index = 0
timer_guess_page_index = 0
timer_guess_sequence = []
timer_guess_target = None
timer_guess_start_time = None
measured_time_seconds = None

countdown_start_time = None
timing_start_time = None
last_space_time = None

# DDR state variables
ddr_current_arrow = None
ddr_feedback = None
ddr_feedback_time = None
DDR_FEEDBACK_DURATION_MS = 600
DDR_ARROWS = ["up", "down", "left", "right"]
ddr_current_sprite = None
ddr_moves_completed = 0
DDR_MAX_MOVES = 10
ddr_sequence = []
ddr_page_index = 0
ddr_score = 0
ddr_game_start_time = None
ddr_total_time = None
swipe_start_x = None
swipe_start_y = None
SWIPE_MIN_DISTANCE = 50


# -----------------------------
# STATE HELPERS
# -----------------------------
def set_state(new_state):
    global state, state_start_time, timer_guess_sequence, timer_guess_page_index, timer_guess_target
    global menu_selected_index, last_space_time, matching_intro_index
    state = new_state
    state_start_time = pygame.time.get_ticks()
    last_space_time = None

    if new_state != STATE_TUTORIAL:
        close_tutorial_qr_window()
    if new_state != STATE_BETWEEN_GAMES:
        close_menu_window()
    if new_state != STATE_MATCHING:
        close_matching_window()

    if new_state == STATE_MATCHING:
        matching_game.reset()
        matching_intro_index = 0
        open_matching_window()
    elif new_state == STATE_BETWEEN_GAMES:
        menu_selected_index = 0
        open_menu_window()
    elif new_state == STATE_TIMER_GUESS:
        timer_guess_target = random.randint(2, 8)
        timer_guess_sequence = create_timer_guess_sequence(timer_guess_target)
        timer_guess_page_index = 0
    elif new_state == STATE_FAST_REFLEXES:
        reset_fast_reflexes()
    elif new_state == STATE_DDR:
        global ddr_feedback, ddr_feedback_time, ddr_moves_completed, ddr_sequence, ddr_page_index, ddr_score, ddr_game_start_time, ddr_total_time
        ddr_sequence = create_ddr_sequence()
        ddr_page_index = 0
        ddr_feedback = None
        ddr_feedback_time = None
        ddr_moves_completed = 0
        ddr_score = 0
        ddr_game_start_time = None
        ddr_total_time = None
        new_ddr_arrow()


def current_page():
    return tutorial_sequence[current_page_index]


def advance_tutorial():
    global current_page_index
    if current_page_index < len(tutorial_sequence) - 1:
        current_page_index += 1
    else:
        set_state(STATE_BETWEEN_GAMES)


def timer_guess_current_page():
    return timer_guess_sequence[timer_guess_page_index]


def advance_timer_guess():
    global timer_guess_page_index
    if timer_guess_page_index < len(timer_guess_sequence) - 1:
        timer_guess_page_index += 1
    else:
        set_state(STATE_BETWEEN_GAMES)


def ddr_current_page():
    return ddr_sequence[ddr_page_index]


def advance_ddr():
    global ddr_page_index
    if ddr_page_index < len(ddr_sequence) - 1:
        ddr_page_index += 1
        if ddr_sequence[ddr_page_index]["type"] == "ddr_game":
            new_ddr_arrow()
    else:
        set_state(STATE_BETWEEN_GAMES)


def new_ddr_arrow():
    global ddr_current_arrow, ddr_current_sprite
    ddr_current_arrow = random.choice(DDR_ARROWS)
    folder = os.path.join("sprites", "ddr", ddr_current_arrow)
    options = os.listdir(folder)
    chosen_file = random.choice(options)
    ddr_current_sprite = os.path.join("ddr", ddr_current_arrow, chosen_file)


# -----------------------------
# MAIN LOOP
# -----------------------------
running = True
while running:
    current_time = pygame.time.get_ticks()
    elapsed = current_time - state_start_time

    # keep secondary windows synchronized with the current state
    if state == STATE_TUTORIAL and current_page()["type"] == "qr":
        open_tutorial_qr_window()
    else:
        close_tutorial_qr_window()

    if state == STATE_BETWEEN_GAMES:
        open_menu_window()
    else:
        close_menu_window()

    if state == STATE_MATCHING and not matching_game.done:
        open_matching_window()
    elif state != STATE_MATCHING:
        close_matching_window()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                set_state(STATE_BETWEEN_GAMES)

            if state == STATE_MATCHING and SDL2_MULTI_WINDOW_AVAILABLE and matching_window is not None:
                if matching_intro_index < len(MATCHING_INTRO):
                    if event.key == pygame.K_SPACE:
                        matching_intro_index += 1
                    continue

                if event.key == pygame.K_SPACE and matching_game.done:
                    set_state(STATE_BETWEEN_GAMES)
                    continue

                if event.key == pygame.K_SPACE and matching_game.pending_reveal_symbol is not None:
                    if matching_game.reveal_space_time is not None and (current_time - matching_game.reveal_space_time) <= DOUBLE_TAP_WINDOW_MS:
                        matching_game.confirm_pending_scan(current_time)
                    else:
                        matching_game.reveal_space_time = current_time
                    continue

                card_key_map = {
                    pygame.K_1: 0,
                    pygame.K_2: 1,
                    pygame.K_3: 2,
                    pygame.K_4: 3,
                    pygame.K_5: 4,
                    pygame.K_6: 5,
                    pygame.K_7: 6,
                    pygame.K_8: 7,
                }
                selected_index = card_key_map.get(event.key)
                if selected_index is not None:
                    matching_game.select(selected_index)
                continue

            elif state == STATE_MATCHING:
                if event.key == pygame.K_SPACE and matching_game.done:
                    set_state(STATE_BETWEEN_GAMES)
                elif event.key == pygame.K_SPACE and matching_game.pending_reveal_symbol is not None:
                    if matching_game.reveal_space_time is not None and (current_time - matching_game.reveal_space_time) <= DOUBLE_TAP_WINDOW_MS:
                        matching_game.confirm_pending_scan(current_time)
                    else:
                        matching_game.reveal_space_time = current_time
                elif pygame.K_1 <= event.key <= pygame.K_8:
                    matching_game.select(event.key - pygame.K_1)
                continue

            if state == STATE_TUTORIAL:
                page = current_page()
                page_type = page["type"]

                if event.key == pygame.K_SPACE:
                    if page_type == "text":
                        advance_tutorial()
                    elif page_type == "sprite":
                        advance_tutorial()
                    elif page_type == "qr":
                        if last_space_time is not None and (current_time - last_space_time) <= DOUBLE_TAP_WINDOW_MS:
                            advance_tutorial()
                        else:
                            last_space_time = current_time
                    elif page_type == "countdown":
                        pass
                    elif page_type == "timing":
                        if timing_start_time is not None:
                            measured_time_seconds = (current_time - timing_start_time) / 1000.0
                            advance_tutorial()
                    elif page_type == "result":
                        advance_tutorial()

            elif state == STATE_BETWEEN_GAMES:
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    global_index = event.key - pygame.K_1
                    menu_selected_index = global_index
                    last_space_time = None
                elif event.key == pygame.K_SPACE:
                    if last_space_time is not None and (current_time - last_space_time) <= DOUBLE_TAP_WINDOW_MS:
                        set_state(menu_state_for_index(menu_selected_index))
                    else:
                        last_space_time = current_time

            elif state == STATE_TIMER_GUESS:
                page = timer_guess_current_page()
                page_type = page["type"]
                if event.key == pygame.K_SPACE:
                    if page_type == "text":
                        advance_timer_guess()
                    elif page_type == "timer_number":
                        advance_timer_guess()
                    elif page_type == "timer_blank":
                        if timer_guess_start_time is not None:
                            measured_time_seconds = (current_time - timer_guess_start_time) / 1000.0
                            advance_timer_guess()
                    elif page_type == "timer_result":
                        advance_timer_guess()

            elif state == STATE_FAST_REFLEXES:
                if event.key == pygame.K_SPACE:
                    if fast_reflex_waiting_to_start:
                        fast_reflex_waiting_to_start = False
                        fast_reflex_intro_sprite = None
                        fast_reflex_schedule_next_spawn(current_time)
                    elif fast_reflex_game_over:
                        pass
                    elif fast_reflex_current_sprite is None:
                        fast_reflex_false_alarms += 1
                        fast_reflex_score = max(0, fast_reflex_score - 60)
                        fast_reflex_set_feedback("Too early! No sprite on screen.", current_time)
                    elif fast_reflex_current_is_bad:
                        reaction_ms = current_time - fast_reflex_bad_spawn_time
                        points = max(100, 1300 - reaction_ms)
                        fast_reflex_hits += 1
                        fast_reflex_score += points
                        fast_reflex_last_reaction_ms = reaction_ms
                        fast_reflex_rounds_completed += 1
                        fast_reflex_set_feedback(f"Caught an object in {reaction_ms}ms (+{points})", current_time)
                        fast_reflex_current_sprite = None
                        fast_reflex_bad_spawn_time = None
                        fast_reflex_sprite_end_time = None

                        if fast_reflex_rounds_completed >= FAST_REFLEX_TOTAL_ROUNDS:
                            fast_reflex_game_over = True
                            fast_reflex_game_over_time = current_time
                        else:
                            fast_reflex_schedule_next_spawn(current_time)
                    else:
                        fast_reflex_false_alarms += 1
                        fast_reflex_score = max(0, fast_reflex_score - 80)
                        fast_reflex_rounds_completed += 1
                        fast_reflex_set_feedback("You caught a fish on accident!", current_time)
                        fast_reflex_current_sprite = None
                        fast_reflex_bad_spawn_time = None
                        fast_reflex_sprite_end_time = None

                        if fast_reflex_rounds_completed >= FAST_REFLEX_TOTAL_ROUNDS:
                            fast_reflex_game_over = True
                            fast_reflex_game_over_time = current_time
                        else:
                            fast_reflex_schedule_next_spawn(current_time)

            elif state == STATE_DDR:
                page = ddr_current_page()
                if page["type"] == "text":
                    if event.key == pygame.K_SPACE:
                        advance_ddr()
                elif page["type"] == "ddr_result":
                    if event.key == pygame.K_SPACE:
                        advance_ddr()

        elif event.type == pygame.MOUSEWHEEL:
            if state == STATE_DDR:
                page = ddr_current_page()
                if page["type"] == "ddr_game":
                    if abs(event.x) > abs(event.y):
                        direction = "right" if event.x < 0 else "left"
                    else:
                        direction = "up" if event.y < 0 else "down"

                    if direction == ddr_current_arrow:
                        ddr_feedback = "hit"
                    else:
                        ddr_feedback = "miss"
                    ddr_feedback_time = current_time

    # -----------------------------
    # LOGIC
    # -----------------------------
    if state == STATE_CALIBRATING:
        if elapsed >= CALIBRATION_DURATION_MS:
            set_state(STATE_TUTORIAL)

    elif state == STATE_TUTORIAL:
        page = current_page()
        page_type = page["type"]

        if page_type == "countdown":
            if countdown_start_time is None:
                countdown_start_time = current_time

            countdown_elapsed = current_time - countdown_start_time
            if countdown_elapsed >= 4 * COUNTDOWN_STEP_MS:
                advance_tutorial()
                timing_start_time = pygame.time.get_ticks()
                countdown_start_time = None
        else:
            countdown_start_time = None

    elif state == STATE_TIMER_GUESS:
        page = timer_guess_current_page()
        page_type = page["type"]
        if page_type == "timer_number":
            pass
        elif page_type == "timer_blank":
            if timer_guess_start_time is None:
                timer_guess_start_time = current_time
        else:
            timer_guess_start_time = None

    elif state == STATE_FAST_REFLEXES:
        if fast_reflex_waiting_to_start:
            pass
        elif not fast_reflex_game_over:
            if fast_reflex_current_sprite is None and fast_reflex_next_spawn_time is not None and current_time >= fast_reflex_next_spawn_time:
                show_bad_sprite = random.random() < FAST_REFLEX_BAD_CHANCE
                if show_bad_sprite:
                    fast_reflex_current_sprite = random.choice(fast_reflex_bad_sprites)
                    fast_reflex_current_is_bad = True
                    fast_reflex_bad_spawn_time = current_time
                else:
                    fast_reflex_current_sprite = random.choice(fast_reflex_good_sprites)
                    fast_reflex_current_is_bad = False
                    fast_reflex_bad_spawn_time = None

                visible_ms = random.randint(FAST_REFLEX_MIN_VISIBLE_MS, FAST_REFLEX_MAX_VISIBLE_MS)
                fast_reflex_sprite_end_time = current_time + visible_ms

            elif fast_reflex_current_sprite is not None and current_time >= fast_reflex_sprite_end_time:
                if fast_reflex_current_is_bad:
                    fast_reflex_misses += 1
                    fast_reflex_score = max(0, fast_reflex_score - 120)
                    fast_reflex_set_feedback("You missed an object!", current_time)

                fast_reflex_rounds_completed += 1
                fast_reflex_current_sprite = None
                fast_reflex_current_is_bad = False
                fast_reflex_bad_spawn_time = None
                fast_reflex_sprite_end_time = None

                if fast_reflex_rounds_completed >= FAST_REFLEX_TOTAL_ROUNDS:
                    fast_reflex_game_over = True
                    fast_reflex_game_over_time = current_time
                else:
                    fast_reflex_schedule_next_spawn(current_time)
        elif fast_reflex_game_over_time is not None and (current_time - fast_reflex_game_over_time) >= FAST_REFLEX_END_SCREEN_MS:
            set_state(STATE_BETWEEN_GAMES)

    elif state == STATE_DDR:
        page = ddr_current_page()
        if page["type"] == "ddr_game":
            if ddr_game_start_time is None:
                ddr_game_start_time = current_time

            if ddr_feedback is not None:
                if current_time - ddr_feedback_time >= DDR_FEEDBACK_DURATION_MS:
                    if ddr_feedback == "hit":
                        ddr_score += 1
                    ddr_moves_completed += 1
                    if ddr_moves_completed >= DDR_MAX_MOVES:
                        ddr_total_time = (current_time - ddr_game_start_time) / 1000.0
                        advance_ddr()
                    else:
                        new_ddr_arrow()
                        ddr_feedback = None

    elif state == STATE_MATCHING:
        if matching_game.done and matching_window is not None:
            close_matching_window()

    # -----------------------------
    # DRAW
    # -----------------------------
    screen.fill(COLOR_BLACK)

    if state == STATE_CALIBRATING:
        text("Calibrating...", TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)

    elif state == STATE_TUTORIAL:
        page = current_page()
        page_type = page["type"]

        if page_type == "text":
            draw_multiline_text(page["lines"], TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y, line_spacing=LINE_SPACING)
        elif page_type == "sprite":
            draw_sprite(page["filename"])
        elif page_type == "qr":
            pass
        elif page_type == "countdown":
            countdown_elapsed = current_time - countdown_start_time if countdown_start_time is not None else 0
            if countdown_elapsed < 1000:
                countdown_text = "3"
            elif countdown_elapsed < 2000:
                countdown_text = "2"
            elif countdown_elapsed < 3000:
                countdown_text = "1"
            else:
                countdown_text = "GO!"
            text(countdown_text, 72, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)
        elif page_type == "timing":
            text("", 48, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y - 20)
        elif page_type == "result":
            result_message = f"Your time was {measured_time_seconds:.2f} seconds"
            result_lines = split_paragraph_into_pages(
                result_message,
                max_chars_per_line=PARAGRAPH_MAX_CHARS_PER_LINE,
                max_lines_per_page=PARAGRAPH_MAX_LINES_PER_PAGE,
            )[0]
            draw_multiline_text(result_lines, TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y, line_spacing=LINE_SPACING)

    elif state == STATE_BETWEEN_GAMES:
        pass

    elif state == STATE_MATCHING:
        if matching_intro_index < len(MATCHING_INTRO):
            page = MATCHING_INTRO[matching_intro_index]
            draw_multiline_text(page["lines"], TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y, line_spacing=LINE_SPACING)
        elif current_time <= matching_game.match_feedback_until:
            text("Match found!", 48, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y - 24)
            text(matching_game.match_feedback_text, 36, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y + 20)
        elif matching_game.done and matching_game.start_time is not None and matching_game.end_time is not None:
            elapsed_s = (matching_game.end_time - matching_game.start_time) / 1000.0
            text(f"Time: {elapsed_s:.2f}s", 48, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y - 10)
        elif SDL2_MULTI_WINDOW_AVAILABLE and matching_renderer is not None:
            if matching_game.first_scanned_symbol is not None:
                draw_sprite(matching_game.first_scanned_symbol, fit_to_screen=True)
        else:
            text("Second window unavailable;", 28, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y - 20)
            text("showing matching game here.", 28, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y + 10)
            matching_game.draw(screen, current_time)

    elif state == STATE_FAST_REFLEXES:
        if fast_reflex_waiting_to_start:
            instruction_lines = split_paragraph_into_pages(
                "Catch anything that is not a fish. Press SPACE to begin.",
                max_chars_per_line=PARAGRAPH_MAX_CHARS_PER_LINE,
                max_lines_per_page=PARAGRAPH_MAX_LINES_PER_PAGE,
            )[0]
            draw_multiline_text(
                instruction_lines,
                TEXT_SIZE,
                COLOR_WHITE,
                SCREEN_CENTER_X,
                SCREEN_CENTER_Y,
                line_spacing=LINE_SPACING,
            )
        elif fast_reflex_game_over:
            text(f"Score: {fast_reflex_score}", 54, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)
        elif fast_reflex_current_sprite is not None:
            draw_sprite(fast_reflex_current_sprite, fill_screen=True, smooth=False)

    elif state == STATE_TIMER_GUESS:
        page = timer_guess_current_page()
        page_type = page["type"]

        if page_type == "text":
            draw_multiline_text(page["lines"], TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y, line_spacing=LINE_SPACING)
        elif page_type == "timer_number":
            text(str(page["number"]), 96, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)
        elif page_type == "timer_blank":
            text("", 48, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y - 20)
        elif page_type == "timer_result":
            accuracy = abs(measured_time_seconds - timer_guess_target)
            result_message = f"Target: {timer_guess_target}s Your time: {measured_time_seconds:.2f}s Difference: {accuracy:.2f}s"
            result_lines = split_paragraph_into_pages(
                result_message,
                max_chars_per_line=PARAGRAPH_MAX_CHARS_PER_LINE,
                max_lines_per_page=PARAGRAPH_MAX_LINES_PER_PAGE,
            )[0]
            draw_multiline_text(result_lines, TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y, line_spacing=LINE_SPACING)

    elif state == STATE_DDR:
        page = ddr_current_page()
        if page["type"] == "text":
            draw_multiline_text(page["lines"], TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y, line_spacing=LINE_SPACING)
        elif page["type"] == "ddr_game":
            if ddr_feedback == "hit":
                draw_sprite("check.png")
            elif ddr_feedback == "miss":
                draw_sprite("x.png", fit_to_screen=True, smooth=False)
            else:
                draw_sprite(ddr_current_sprite, fit_to_screen=True, smooth=False)
        elif page["type"] == "ddr_result":
            result_message = f"Score: {ddr_score}/10  Time: {ddr_total_time:.1f}s"
            result_lines = split_paragraph_into_pages(
                result_message,
                max_chars_per_line=PARAGRAPH_MAX_CHARS_PER_LINE,
                max_lines_per_page=PARAGRAPH_MAX_LINES_PER_PAGE,
            )[0]
            draw_multiline_text(result_lines, TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y, line_spacing=LINE_SPACING)

    pygame.display.flip()

    if state == STATE_TUTORIAL and current_page()["type"] == "qr":
        draw_tutorial_qr_window()
    if state == STATE_BETWEEN_GAMES:
        draw_menu_window()
    if state == STATE_MATCHING:
        draw_matching_window(current_time)

    clock.tick(60)

close_tutorial_qr_window()
close_menu_window()
close_matching_window()
pygame.quit()
sys.exit()
