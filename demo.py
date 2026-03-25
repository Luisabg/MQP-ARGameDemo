import pygame
import sys
import os
import textwrap
import random

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
def draw_sprite(filename, fit_to_screen=False):
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
        image = pygame.transform.smoothscale(image, new_size)

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
        self.card_back = load_card_sprite("CardBack.png")
        self.face_images = {s: load_card_sprite(s) for s in set(CARD_SYMBOLS)}
        self.reset()

    def reset(self):
        symbols = CARD_SYMBOLS[:]
        random.shuffle(symbols)
        self.symbols = symbols
        self.revealed = [False] * 8
        self.selected = None
        self.matched_pairs = 0
        self.flash_card = None
        self.flash_start = None
        self.FLASH_MS = 800

    @property
    def done(self):
        return self.matched_pairs == 4

    def select(self, index):
        if self.revealed[index]:
            return
        if index == self.selected:
            return
        self.flash_card = None

        if self.selected is None:
            self.selected = index
        else:
            first = self.selected
            second = index
            if self.symbols[first] == self.symbols[second]:
                self.revealed[first] = True
                self.revealed[second] = True
                self.selected = None
                self.matched_pairs += 1
            else:
                self.flash_card = first
                self.flash_start = pygame.time.get_ticks()
                self.selected = second

    def update(self, current_time):
        if self.flash_card is not None:
            if current_time - self.flash_start >= self.FLASH_MS:
                self.flash_card = None

    def draw(self, screen, current_time):
        self.update(current_time)

        font_label = pygame.font.SysFont(None, 26)
        font_num = pygame.font.SysFont(None, 22)

        if self.done:
            label = "Congrats you found all the matches!"
        elif self.selected is None:
            label = "Pick a card 1-8"
        else:
            label = f"Pick a card 1-8"

        lbl_surf = font_label.render(label, True, COLOR_WHITE)
        screen.blit(lbl_surf, lbl_surf.get_rect(center=(SCREEN_CENTER_X, GRID_Y - 22)))

        for i in range(8):
            rect = card_rect(i)
            face_up = self.revealed[i]
            is_sel = (i == self.selected)
            is_flash = (i == self.flash_card)

            # Border color
            if is_flash:
                border_col = COLOR_GREEN
            elif face_up:
                border_col = COLOR_GREEN
            elif is_sel:
                border_col = COLOR_YELLOW
            else:
                border_col = COLOR_GRAY

            pygame.draw.rect(screen, COLOR_DARK_GRAY, rect, border_radius=10)
            pygame.draw.rect(screen, border_col, rect, 3, border_radius=10)

            # Card number
            num_surf = font_num.render(str(i + 1), True, COLOR_GRAY)
            screen.blit(num_surf, (rect.x + 6, rect.y + 5))

            # Sprite
            if face_up or is_sel or is_flash:
                img = self.face_images.get(self.symbols[i])
            else:
                img = self.card_back

            if img:
                img_rect = img.get_rect(center=rect.center)
                screen.blit(img, img_rect)
            else:
                # Fallback if sprite is  missing
                fb = font_label.render(self.symbols[i], True, COLOR_WHITE)
                screen.blit(fb, fb.get_rect(center=rect.center))

        score_surf = font_label.render(f"Pairs: {self.matched_pairs}/4", True, COLOR_WHITE)
        screen.blit(score_surf, score_surf.get_rect(center=(SCREEN_CENTER_X, GRID_Y + GRID_H + 22)))

matching_game = MatchingGame()

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

# -----------------------------
# STATE HELPERS
# -----------------------------
def set_state(new_state):
    global state, state_start_time, timer_guess_sequence, timer_guess_page_index, timer_guess_target
    state = new_state
    state_start_time = pygame.time.get_ticks()

    if new_state == STATE_MATCHING:
        matching_game.reset()
    
    if new_state == STATE_TIMER_GUESS:
        timer_guess_target = random.randint(2, 8)
        timer_guess_sequence = create_timer_guess_sequence(timer_guess_target)
        timer_guess_page_index = 0

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
            elif state == STATE_MATCHING:
                if pygame.K_1 <= event.key <+ pygame.K_9:
                    index = event.key - pygame.K_1
                    matching_game.select(index)
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
        text("TODO: DDR", TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()