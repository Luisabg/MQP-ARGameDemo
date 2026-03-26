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

CARD_SYMBOLS = ["Monster1.png", "Monster2.png", "Monster3.png", "Monster4.png",
                "Monster1.png", "Monster2.png", "Monster3.png", "Monster4.png"]

CARD_COLS = 4
CARD_ROWS = 2
CARD_W = 110
CARD_H = 110
CARD_PAD = 16
GRID_W = CARD_COLS * CARD_W + (CARD_COLS - 1) * CARD_PAD
GRID_H = CARD_ROWS * CARD_H + (CARD_ROWS - 1) * CARD_PAD
GRID_X = (WIDTH - GRID_W) // 2
GRID_Y = (HEIGHT - GRID_H) // 2 + 10


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

def split_paragraph_into_pages(paragraph, max_chars_per_line=32, max_lines_per_page=3):
    wrapped_lines = textwrap.wrap(
        paragraph,
        width=max_chars_per_line,
        break_long_words=False,
        break_on_hyphens=False
    )

    if not wrapped_lines:
        return [[""]]

    pages = []
    for i in range(0, len(wrapped_lines), max_lines_per_page):
        pages.append(wrapped_lines[i:i + max_lines_per_page])

    return pages

# -----------------------------
# SPRITE HELPER
# -----------------------------
def draw_sprite(filename, fit_to_screen=False, smooth=True):
    path = os.path.join("sprites", filename)

    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        text(f"Missing sprite: {filename}", 24, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)
        return

    if fit_to_screen:
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

        # Start timer on first card pick
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
            # Stop timer on final pair
            if self.matched_pairs == 4:
                self.end_time = pygame.time.get_ticks()
        else:
            self.flash_card = first
            self.flash_start = current_time
            self.first_scanned = second
            self.first_scanned_symbol = self.symbols[second]

    def update(self, current_time):
        if self.flash_card is not None:
            if current_time - self.flash_start >= self.FLASH_MS:
                self.flash_card = None

    def draw(self, screen, current_time, show_revealed_faces=True, show_status_text=True, show_qr_on_reveal=False):
        self.update(current_time)

        font_label = pygame.font.SysFont(None, 26)
        font_num = pygame.font.SysFont(None, 22)

        # Timer
        if self.end_time is not None:
            elapsed_s = (self.end_time - self.start_time) / 1000.0
            time_str = f"Time: {elapsed_s:.2f}s"
        else:
            time_str = None

        # --- Cards ---
        for i in range(8):
            rect = card_rect(i)
            face_up = self.revealed[i]
            is_sel = (i == self.selected)
            is_flash = (i == self.flash_card)

            # Hide matched cards entirely
            if face_up:
                continue

            qr_visible = (
                show_qr_on_reveal
                and self.pending_scan_index is not None
                and i == self.pending_scan_index
            )

            # Draw card without border outline
            pygame.draw.rect(screen, COLOR_DARK_GRAY, rect, border_radius=10)

            # Card number
            num_surf = font_num.render(str(i + 1), True, COLOR_GRAY)
            screen.blit(num_surf, (rect.x + 6, rect.y + 5))

            # Sprite
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
                screen.blit(img, img_rect)
            else:
                # Fallback if sprite is  missing
                fb = font_label.render(self.symbols[i], True, COLOR_WHITE)
                screen.blit(fb, fb.get_rect(center=rect.center))

        below_y = GRID_Y + GRID_H + 24

        if show_status_text and self.done:
            congrats_surf = font_label.render("Congrats you found all the matches!", True, COLOR_WHITE)
            screen.blit(congrats_surf, congrats_surf.get_rect(center=(SCREEN_CENTER_X, below_y)))

            if time_str is not None:
                time_surf = font_label.render(time_str, True, COLOR_WHITE)
                screen.blit(time_surf, time_surf.get_rect(center=(SCREEN_CENTER_X, below_y + 26)))
       


matching_game = MatchingGame()

matching_intro_index = 0
matching_window = None
matching_renderer = None
matching_surface = None


def open_matching_window():
    global matching_window, matching_renderer, matching_surface
    if not SDL2_MULTI_WINDOW_AVAILABLE:
        return
    if matching_window is None:
        matching_window = SDL2Window("ARcade - Matching", size=(WIDTH, HEIGHT), position=(760, 80))
        matching_renderer = SDL2Renderer(matching_window)
        matching_surface = pygame.Surface((WIDTH, HEIGHT)).convert_alpha()


def close_matching_window():
    global matching_window, matching_renderer, matching_surface
    # Renderer/Texture objects in pygame._sdl2 are released by GC in pygame 2.6.x.
    # Calling unsupported destroy() methods raises AttributeError in some builds.
    if matching_renderer is not None:
        matching_renderer = None
    if matching_window is not None:
        matching_window.destroy()
        matching_window = None
    matching_surface = None


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
    matching_texture = SDL2Texture.from_surface(matching_renderer, matching_surface)
    matching_renderer.clear()
    matching_texture.draw()
    matching_renderer.present()
    # Explicit delete releases the temporary texture without calling unsupported APIs.
    del matching_texture


def event_window_id(event):
    """Best-effort extraction of source window id for SDL2-backed pygame events."""
    if hasattr(event, "window"):
        return event.window
    if hasattr(event, "windowID"):
        return event.windowID
    event_dict = getattr(event, "dict", None)
    if isinstance(event_dict, dict):
        return event_dict.get("window") or event_dict.get("windowID")
    return None


def is_matching_window_event(event):
    if not (SDL2_MULTI_WINDOW_AVAILABLE and matching_window is not None):
        return False
    window_id = event_window_id(event)
    # Some pygame backends omit window id metadata on KEYDOWN events.
    # Treat unscoped key events as matching-window input so controls still work.
    if window_id is None:
        return True
    return window_id == matching_window.id

# -----------------------------
# BUILD TUTORIAL PAGES
# -----------------------------
def paragraph_pages(paragraph):
    pages = split_paragraph_into_pages(
        paragraph,
        max_chars_per_line=PARAGRAPH_MAX_CHARS_PER_LINE,
        max_lines_per_page=PARAGRAPH_MAX_LINES_PER_PAGE
    )
    return [{"type": "text", "lines": page} for page in pages]

MATCHING_INTRO = []
MATCHING_INTRO += paragraph_pages("Welcome to card matching!")
MATCHING_INTRO += paragraph_pages(
    "Scan a card's QR code to reveal its icon. "
    "Then, scan another card to see if you've found the matching pair. "
    "Keep scanning and setting aside pairs until you've matched them all."
)
MATCHING_INTRO += paragraph_pages("Choose 1-8 to flip a card and scan to begin")

tutorial_sequence = []

tutorial_sequence += paragraph_pages(
    "Tap the side of your glasses once to continue reading."
)

tutorial_sequence += paragraph_pages(
    "Perfect!"
)

tutorial_sequence += paragraph_pages(
    "Now you can tap the side of your glasses to advance through the tutorial."
)

tutorial_sequence += paragraph_pages(
    "Lets display a sprite!"
)

tutorial_sequence.append({
    "type": "sprite",
    "filename": "hotdog_4bit.png"
})

tutorial_sequence += paragraph_pages(
    "Double tap the side of your glasses to scan a QR code"
)

tutorial_sequence.append({
    "type": "qr",
    "filename": "QR.png"
})

tutorial_sequence.append({
    "type": "sprite",
    "filename": "check.png"
})

tutorial_sequence += paragraph_pages(
    "Now lets test your timing. Tap when you think 2 seconds have passed"
)

tutorial_sequence.append({
    "type": "countdown"
})

tutorial_sequence.append({
    "type": "timing"
})

tutorial_sequence.append({
    "type": "result"
})

tutorial_sequence += paragraph_pages(
    "This concludes the demo!"
)

tutorial_sequence += paragraph_pages(
    "You're now ready to explore the Digital Arcade."
)

# Function to generate a new timer_guess sequence
def create_timer_guess_sequence(target_seconds):
    sequence = []
    sequence += paragraph_pages(
        "Welcome to Second Guesser! You will be shown a number, once it disappears, try to tap exactly that many seconds later. The closer you are to the target time, the better your score. Ready to test your timing?"
    )
    sequence.append({
        "type": "timer_number",
        "number": target_seconds
    })
    sequence.append({
        "type": "timer_blank"
    })
    sequence.append({
        "type": "timer_result"
    })
    return sequence

def create_ddr_sequence():
    sequence = []
    sequence += paragraph_pages("Welcome to DDR! Press the arrow key that matches the arrow on screen!")
    sequence += paragraph_pages("You have 10 arrows. Good luck!")
    sequence.append({"type": "ddr_game"})
    sequence.append({"type": "ddr_result"})  # results page as different type so we can show score/time at end without needing to generate new random arrows
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
measured_time_seconds = None
last_space_time = None

# ddr state variables
ddr_current_arrow = None
ddr_feedback = None # hit or miss feedback
ddr_feedback_time = None # moment player presses key
DDR_FEEDBACK_DURATION_MS = 600 # how long to show feedback message
DDR_ARROWS = ["up", "down", "left", "right"] # will be different folders
ddr_current_sprite = None # current sprite chosen randomly from folders
ddr_moves_completed = 0
DDR_MAX_MOVES = 10 # game length
# for pages
ddr_sequence = []
ddr_page_index = 0
# scoring
ddr_score = 0
ddr_game_start_time = None
ddr_total_time = None

# -----------------------------
# STATE HELPERS
# -----------------------------
def set_state(new_state):
    global state, state_start_time, timer_guess_sequence, timer_guess_page_index, timer_guess_target
    old_state = state
    state = new_state
    state_start_time = pygame.time.get_ticks()

    if old_state == STATE_MATCHING and new_state != STATE_MATCHING:
        close_matching_window()

    if new_state == STATE_MATCHING:
        matching_game.reset()
        matching_intro_index = 0
        open_matching_window()
    
    if new_state == STATE_TIMER_GUESS:
        timer_guess_target = random.randint(2, 8)
        timer_guess_sequence = create_timer_guess_sequence(timer_guess_target)
        timer_guess_page_index = 0

    # When entering DDR state, immediately select a random arrow and reset feedback
    if new_state == STATE_DDR:
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
    global current_page_index, last_space_time
    if current_page_index < len(tutorial_sequence) - 1:
        current_page_index += 1
    else:
        set_state(STATE_BETWEEN_GAMES)
    last_space_time = None

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
            new_ddr_arrow()  # only pick first arrow once game actually starts
    else:
        set_state(STATE_BETWEEN_GAMES)

# Function to select a new random DDR arrow
def new_ddr_arrow():
    global ddr_current_arrow, ddr_current_sprite
    ddr_current_arrow = random.choice(DDR_ARROWS)

    # list all files in that arrow's folder and pick one randomly
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

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:

            if state == STATE_MATCHING and SDL2_MULTI_WINDOW_AVAILABLE and matching_window is not None:
                if matching_intro_index < len(MATCHING_INTRO):
                    if event.key == pygame.K_ESCAPE:
                        set_state(STATE_BETWEEN_GAMES)
                    elif event.key == pygame.K_SPACE:
                        matching_intro_index += 1
                    continue

                if event.key == pygame.K_ESCAPE:
                    set_state(STATE_BETWEEN_GAMES)
                    continue

                if event.key == pygame.K_SPACE and matching_game.done:
                    set_state(STATE_BETWEEN_GAMES)
                    continue

                if event.key == pygame.K_SPACE and matching_game.pending_reveal_symbol is not None:
                    if (
                        matching_game.reveal_space_time is not None
                        and (current_time - matching_game.reveal_space_time) <= DOUBLE_TAP_WINDOW_MS
                    ):
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
                if event.key == pygame.K_ESCAPE:
                    set_state(STATE_BETWEEN_GAMES)
                elif event.key == pygame.K_SPACE and matching_game.done:
                    set_state(STATE_BETWEEN_GAMES)
                elif event.key == pygame.K_SPACE and matching_game.pending_reveal_symbol is not None:
                    if (
                        matching_game.reveal_space_time is not None
                        and (current_time - matching_game.reveal_space_time) <= DOUBLE_TAP_WINDOW_MS
                    ):
                        matching_game.confirm_pending_scan(current_time)
                    else:
                        matching_game.reveal_space_time = current_time
                elif pygame.K_1 <= event.key <= pygame.K_8:
                    matching_game.select(event.key - pygame.K_1)
                continue

            if event.key == pygame.K_ESCAPE:
                set_state(STATE_BETWEEN_GAMES)
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
                if event.key == pygame.K_1:
                    set_state(STATE_MATCHING)
                elif event.key == pygame.K_2:
                    set_state(STATE_FAST_REFLEXES)
                elif event.key == pygame.K_3:
                    set_state(STATE_TIMER_GUESS)
                elif event.key == pygame.K_4:
                    set_state(STATE_DDR)

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

            elif state == STATE_DDR:
                page = ddr_current_page()

                if page["type"] == "text":
                    if event.key == pygame.K_SPACE:
                        advance_ddr()

                elif page["type"] == "ddr_game":
                    arrow_key_map = {
                        pygame.K_UP: "up",
                        pygame.K_DOWN: "down",
                        pygame.K_LEFT: "left",
                        pygame.K_RIGHT: "right",
                    }
                    if event.key in arrow_key_map:
                        pressed = arrow_key_map[event.key]
                        if pressed == ddr_current_arrow:
                            ddr_feedback = "hit"
                        else:
                            ddr_feedback = "miss"
                        ddr_feedback_time = current_time

                elif page["type"] == "ddr_result":
                    if event.key == pygame.K_SPACE:
                        advance_ddr()

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
        # Once complete, close the secondary board window and keep result UI on main screen.
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
            draw_multiline_text(
                page["lines"],
                TEXT_SIZE,
                COLOR_WHITE,
                SCREEN_CENTER_X,
                SCREEN_CENTER_Y,
                line_spacing=LINE_SPACING,
            )

        elif page_type == "sprite":
            draw_sprite(page["filename"])

        elif page_type == "qr":
            draw_sprite(page["filename"], fit_to_screen=True)
            text("Double tap SPACE to continue", 22, COLOR_WHITE, SCREEN_CENTER_X, HEIGHT - 25)

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

        elif page_type == "timing": text("", 48, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y - 20)

        elif page_type == "result":
            result_message = f"Your time was {measured_time_seconds:.2f} seconds"
            result_lines = split_paragraph_into_pages(
                result_message,
                max_chars_per_line=PARAGRAPH_MAX_CHARS_PER_LINE,
                max_lines_per_page=PARAGRAPH_MAX_LINES_PER_PAGE
            )[0]

            draw_multiline_text(
                result_lines,
                TEXT_SIZE,
                COLOR_WHITE,
                SCREEN_CENTER_X,
                SCREEN_CENTER_Y,
                line_spacing=LINE_SPACING,
            )
    elif state == STATE_BETWEEN_GAMES:
        pass  # blank screen on purpose

    elif state == STATE_MATCHING:
        if matching_intro_index < len(MATCHING_INTRO):
            page = MATCHING_INTRO[matching_intro_index]
            draw_multiline_text(page["lines"], TEXT_SIZE, COLOR_WHITE,
                                SCREEN_CENTER_X, SCREEN_CENTER_Y, line_spacing=LINE_SPACING)
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
        text("TODO: FAST REFLEXES", TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)

    elif state == STATE_TIMER_GUESS:
        page = timer_guess_current_page()
        page_type = page["type"]

        if page_type == "text":
            draw_multiline_text(
                page["lines"],
                TEXT_SIZE,
                COLOR_WHITE,
                SCREEN_CENTER_X,
                SCREEN_CENTER_Y,
                line_spacing=LINE_SPACING,
            )

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
                max_lines_per_page=PARAGRAPH_MAX_LINES_PER_PAGE
            )[0]

            draw_multiline_text(
                result_lines,
                TEXT_SIZE,
                COLOR_WHITE,
                SCREEN_CENTER_X,
                SCREEN_CENTER_Y,
                line_spacing=LINE_SPACING,
            )

    elif state == STATE_DDR:
        # text("TODO: DDR", TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)
        page = ddr_current_page()

        if page["type"] == "text":
            draw_multiline_text(
                page["lines"], TEXT_SIZE, COLOR_WHITE,
                SCREEN_CENTER_X, SCREEN_CENTER_Y, line_spacing=LINE_SPACING
            )

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
                max_lines_per_page=PARAGRAPH_MAX_LINES_PER_PAGE
            )[0]
            draw_multiline_text(result_lines, TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y,
                                line_spacing=LINE_SPACING)

    pygame.display.flip()

    if state == STATE_MATCHING:
        draw_matching_window(current_time)

    clock.tick(60)

close_matching_window()
pygame.quit()
sys.exit()
