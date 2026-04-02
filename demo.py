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

#bg_image = pygame.image.load("background/glasses_background.png")
#.convert()


# -----------------------------
# LAYOUT / STYLE
# -----------------------------
SCREEN_CENTER_X = WIDTH // 2
SCREEN_CENTER_Y = HEIGHT // 2

CALIBRATION_DURATION_MS = 10000
COUNTDOWN_STEP_MS = 1000
DOUBLE_TAP_WINDOW_MS = 500

# FAST REFLEXES GAME CONSTANTS
# Controls timing between sprite spawns (random delay between min and max)
FAST_REFLEX_MIN_GAP_MS = 500      # Minimum milliseconds to wait before next sprite
FAST_REFLEX_MAX_GAP_MS = 1800     # Maximum milliseconds to wait before next sprite
# Controls how long each sprite stays visible on screen
FAST_REFLEX_MIN_VISIBLE_MS = 1000 # Sprite visible for at least 1 second
FAST_REFLEX_MAX_VISIBLE_MS = 3000 # Sprite visible for at most 4 seconds
# Controls how long to show the opening instruction before switching to "Get ready..."
FAST_REFLEX_INSTRUCTION_MS = 3000
# Gameplay difficulty settings
FAST_REFLEX_BAD_CHANCE = 0.4      # 40% chance a sprite is "bad" (monster) vs "good"
FAST_REFLEX_TOTAL_ROUNDS = 15     # Total number of rounds before game ends

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

    #resize image to fit screen
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
        self.start_time = None
        self.end_time = None

    @property
    def done(self):
            return self.matched_pairs == 4

    def select(self, index):
        if self.revealed[index]:
            return
        if index == self.selected:
            return
        self.flash_card = None

        # Start timer on first card pick
        if self.start_time is None:
            self.start_time = pygame.time.get_ticks()

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
                # Stop timer on final pair
                if self.matched_pairs == 4:
                    self.end_time = pygame.time.get_ticks()
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

        below_y = GRID_Y + GRID_H + 24

        if self.done:
            congrats_surf = font_label.render("Congrats you found all the matches!", True, COLOR_GREEN)
            screen.blit(congrats_surf, congrats_surf.get_rect(center=(SCREEN_CENTER_X, below_y)))

            if time_str is not None:
                time_surf = font_label.render(time_str, True, COLOR_YELLOW)
                screen.blit(time_surf, time_surf.get_rect(center=(SCREEN_CENTER_X, below_y + 26)))
        else:
            lbl_surf = font_label.render("Pick a card 1-8", True, COLOR_WHITE)
            screen.blit(lbl_surf, lbl_surf.get_rect(center=(SCREEN_CENTER_X, below_y)))


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

def create_ddr_sequence():
    sequence = []
    sequence += paragraph_pages("Welcome to DDR!")
    sequence += paragraph_pages("Use 2 fingers to swipe on the touchpad in the direction that matches the arrow on screen!")
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

countdown_start_time = None
timing_start_time = None
measured_time_seconds = None
last_space_time = None


# FAST REFLEXES STATE VARIABLES
# Sprite lists: good sprites are safe to ignore, bad sprites must be caught by pressing SPACE
fast_reflex_good_sprites = ["Fast_Reflexes/Fish1.png", "Fast_Reflexes/Fish2.png", "Fast_Reflexes/Fish3.png", "Fast_Reflexes/Fish4.png", "Fast_Reflexes/Fish5.png"]
fast_reflex_bad_sprites = ["Fast_Reflexes/Ball1.png","Fast_Reflexes/Ball2.png","Fast_Reflexes/Tree.png","Fast_Reflexes/Boot.png"]
# Timing state: when the next sprite should spawn and when current sprite expires
fast_reflex_next_spawn_time = 0                # Milliseconds: when to show the next sprite
fast_reflex_sprite_end_time = None             # Milliseconds: when current sprite disappears
# Sprite display state: what sprite is showing and whether it's bad
fast_reflex_current_sprite = None              # Filename of sprite currently on screen, or None
fast_reflex_current_is_bad = False             # True if current sprite is a monster to catch
fast_reflex_bad_spawn_time = None              # Milliseconds: when the bad sprite appeared (for reaction time)
# Game progress and scoring
fast_reflex_rounds_completed = 0               # How many sprites have been shown so far
fast_reflex_hits = 0                           # Number of bad sprites successfully caught
fast_reflex_misses = 0                         # Number of bad sprites that expired without being caught
fast_reflex_false_alarms = 0                   # Number of times player pressed SPACE on good sprites or empty screen
fast_reflex_score = 0                          # Total points earned (faster catches = higher score)
fast_reflex_instruction_until = 0              # Milliseconds: when to stop showing opening instruction text
# Game state
fast_reflex_game_over = False                  # True when 15 rounds are completed

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
# for swiping
swipe_start_x = None
swipe_start_y = None
SWIPE_MIN_DISTANCE = 50  # pixels = how far you need to swipe for it to count

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
    elif new_state == STATE_FAST_REFLEXES:
        reset_fast_reflexes()
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


def fast_reflex_schedule_next_spawn(now_ms):
    """Schedule the next sprite to appear at a random time in the future"""
    global fast_reflex_next_spawn_time
    fast_reflex_next_spawn_time = now_ms + random.randint(FAST_REFLEX_MIN_GAP_MS, FAST_REFLEX_MAX_GAP_MS)


def reset_fast_reflexes():
    """Reset all fast-reflex game state to start a new game"""
    global fast_reflex_next_spawn_time, fast_reflex_sprite_end_time, fast_reflex_current_sprite
    global fast_reflex_current_is_bad, fast_reflex_bad_spawn_time, fast_reflex_rounds_completed
    global fast_reflex_hits, fast_reflex_misses, fast_reflex_false_alarms, fast_reflex_score
    global fast_reflex_instruction_until, fast_reflex_game_over

    now_ms = pygame.time.get_ticks()
    fast_reflex_schedule_next_spawn(now_ms + 3000)
    fast_reflex_sprite_end_time = None
    fast_reflex_current_sprite = None
    fast_reflex_current_is_bad = False
    fast_reflex_bad_spawn_time = None
    fast_reflex_rounds_completed = 0
    fast_reflex_hits = 0
    fast_reflex_misses = 0
    fast_reflex_false_alarms = 0
    fast_reflex_score = 0
    # Show controls briefly before falling back to "Get ready..." while waiting for spawns.
    fast_reflex_instruction_until = now_ms + FAST_REFLEX_INSTRUCTION_MS
    fast_reflex_game_over = False

#return current page



def current_page():
    return tutorial_sequence[current_page_index]

#go to next page in tutorial
def advance_tutorial():
    global current_page_index, last_space_time
    if current_page_index < len(tutorial_sequence) - 1:
        current_page_index += 1
    else:
        set_state(STATE_BETWEEN_GAMES)
    last_space_time = None

#return current timer page
def timer_guess_current_page():
    return timer_guess_sequence[timer_guess_page_index]

#go to next timer page
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

    # screen.blit(bg_image, (0, 0))
    # pygame.display.update()
    #end game
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        #key press logic
        elif event.type == pygame.KEYDOWN:

            # leave tutorial or game early by pressing ESC
            if event.key == pygame.K_ESCAPE:
                set_state(STATE_BETWEEN_GAMES)
            #tutorial logic
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
            # Handling switching between game modes
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
            elif state ==  STATE_MATCHING:
                if pygame.K_1 <= event.key < + pygame.K_9:
                    index = event.key - pygame.K_1
                    matching_game.select(index)

            elif state == STATE_FAST_REFLEXES:
                # Handle SPACE key presses during fast-reflex game
                if event.key == pygame.K_SPACE:
                    if fast_reflex_game_over:
                        # Game is over - restart it
                        reset_fast_reflexes()
                    elif fast_reflex_current_sprite is None:
                        # Player pressed SPACE but no sprite is on screen - penalize
                        fast_reflex_false_alarms += 1
                        fast_reflex_score = max(0, fast_reflex_score - 60)
                    elif fast_reflex_current_is_bad:
                        # Player pressed SPACE on a bad sprite (monster) - SUCCESS!
                        # Calculate reaction time and award points: faster = more points
                        reaction_ms = current_time - fast_reflex_bad_spawn_time
                        points = max(100, 1300 - reaction_ms)  # Fast catches get ~1000+ points
                        fast_reflex_hits += 1
                        fast_reflex_score += points
                        fast_reflex_rounds_completed += 1
                        fast_reflex_current_sprite = None
                        fast_reflex_bad_spawn_time = None
                        fast_reflex_sprite_end_time = None

                        if fast_reflex_rounds_completed >= FAST_REFLEX_TOTAL_ROUNDS:
                            fast_reflex_game_over = True
                        else:
                            fast_reflex_schedule_next_spawn(current_time)
                    else:
                        # Player pressed SPACE on a good sprite - MISTAKE!
                        fast_reflex_false_alarms += 1
                        fast_reflex_score = max(0, fast_reflex_score - 80)
                        fast_reflex_rounds_completed += 1
                        fast_reflex_current_sprite = None
                        fast_reflex_bad_spawn_time = None
                        fast_reflex_sprite_end_time = None

                        if fast_reflex_rounds_completed >= FAST_REFLEX_TOTAL_ROUNDS:
                            fast_reflex_game_over = True
                        else:
                            fast_reflex_schedule_next_spawn(current_time)
            elif state == STATE_DDR:
                page = ddr_current_page()

                if page["type"] == "text":
                    if event.key == pygame.K_SPACE:
                        advance_ddr()

                # elif page["type"] == "ddr_game":
                #     arrow_key_map = {
                #         pygame.K_UP: "up",
                #         pygame.K_DOWN: "down",
                #         pygame.K_LEFT: "left",
                #         pygame.K_RIGHT: "right",
                #     }
                #     if event.key in arrow_key_map:
                #         pressed = arrow_key_map[event.key]
                #         if pressed == ddr_current_arrow:
                #             ddr_feedback = "hit"
                #         else:
                #             ddr_feedback = "miss"
                #         ddr_feedback_time = current_time
                #
                elif page["type"] == "ddr_result":
                    if event.key == pygame.K_SPACE:
                        advance_ddr()

        elif event.type == pygame.MOUSEWHEEL:
            if state == STATE_DDR:
                page = ddr_current_page()
                if page["type"] == "ddr_game":
                    if abs(event.x) > abs(event.y):  # horizontal scroll
                        direction = "right" if event.x < 0 else "left"
                    else:  # vertical scroll
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
        # Update fast-reflex game logic
        if not fast_reflex_game_over:
            # Check if it's time to spawn the next sprite
            if fast_reflex_current_sprite is None and fast_reflex_next_spawn_time is not None and current_time >= fast_reflex_next_spawn_time:
                # Randomly decide if this sprite is good or bad (monster)
                show_bad_sprite = random.random() < FAST_REFLEX_BAD_CHANCE

                if show_bad_sprite:
                    # Spawn a bad sprite (monster) - player must catch with SPACE
                    fast_reflex_current_sprite = random.choice(fast_reflex_bad_sprites)
                    fast_reflex_current_is_bad = True
                    fast_reflex_bad_spawn_time = current_time
                else:
                    # Spawn a good sprite - player should NOT press SPACE
                    fast_reflex_current_sprite = random.choice(fast_reflex_good_sprites)
                    fast_reflex_current_is_bad = False
                    fast_reflex_bad_spawn_time = None

                # Determine how long this sprite stays visible (1-4 seconds)
                visible_ms = random.randint(FAST_REFLEX_MIN_VISIBLE_MS, FAST_REFLEX_MAX_VISIBLE_MS)
                fast_reflex_sprite_end_time = current_time + visible_ms

            # Check if current sprite has expired (time to remove it from screen)
            elif fast_reflex_current_sprite is not None and current_time >= fast_reflex_sprite_end_time:
                # Sprite expired - if it was a bad sprite, that's a miss
                if fast_reflex_current_is_bad:
                    fast_reflex_misses += 1
                    fast_reflex_score = max(0, fast_reflex_score - 120)

                fast_reflex_rounds_completed += 1
                fast_reflex_current_sprite = None
                fast_reflex_current_is_bad = False
                fast_reflex_bad_spawn_time = None
                fast_reflex_sprite_end_time = None

                # Check if we've completed all 15 rounds
                if fast_reflex_rounds_completed >= FAST_REFLEX_TOTAL_ROUNDS:
                    fast_reflex_game_over = True
                else:
                    fast_reflex_schedule_next_spawn(current_time)
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

    # -----------------------------
    # DRAW
    # -----------------------------
    screen.fill(COLOR_BLACK)

    if state == STATE_CALIBRATING:
        text("Calibrating...", TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)

    #state drawing

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
        # Draw only the fast-reflex HUD and active sprite
        rounds_text = f"Round {fast_reflex_rounds_completed}/{FAST_REFLEX_TOTAL_ROUNDS}"
        score_text = f"Score: {fast_reflex_score}"
        if current_time >= fast_reflex_instruction_until :
            text(rounds_text, 24, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y - 90)
            text(score_text, 26, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y - 45)

        # Draw sprite only when one is active
        if fast_reflex_current_sprite is not None:
            draw_sprite(fast_reflex_current_sprite)
        elif not fast_reflex_game_over:
            # Show instruction first, then "Get ready..." while no sprite is on screen.
            if current_time < fast_reflex_instruction_until:
                text("Tap SPACE to catch anything that is not a fish to clean the ocean.", 25, COLOR_WHITE,
                     SCREEN_CENTER_X, SCREEN_CENTER_Y)
            else:
                text("Get ready...", 36, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)


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
    clock.tick(60)

pygame.quit()
sys.exit()