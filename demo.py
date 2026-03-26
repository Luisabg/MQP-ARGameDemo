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
pygame.display.set_caption("Demo [TITLE]")

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
# Gameplay difficulty settings
FAST_REFLEX_BAD_CHANCE = 0.4      # 40% chance a sprite is "bad" (monster) vs "good"
FAST_REFLEX_TOTAL_ROUNDS = 15     # Total number of rounds before game ends

PARAGRAPH_MAX_CHARS_PER_LINE = 32
PARAGRAPH_MAX_LINES_PER_PAGE = 3
LINE_SPACING = 38
TEXT_SIZE = 32

COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (220, 70, 70)    # For bad sprite warnings (monsters)
COLOR_GREEN = (70, 220, 70)  # For good sprite instructions (safe sprites)

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

    #resize image to fit screen
    if fit_to_screen:
        img_w, img_h = image.get_size()
        scale_factor = min(WIDTH / img_w, HEIGHT / img_h)
        new_size = (int(img_w * scale_factor), int(img_h * scale_factor))
        image = pygame.transform.smoothscale(image, new_size)

    rect = image.get_rect(center=(SCREEN_CENTER_X, SCREEN_CENTER_Y))
    screen.blit(image, rect)

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
fast_reflex_last_reaction_ms = None            # Reaction time in ms for most recent catch
# Feedback display
fast_reflex_feedback = ""                      # Message to show player ("Caught!", "Too early!", etc.)
fast_reflex_feedback_until = 0                 # Milliseconds: when to stop showing feedback message
# Game state
fast_reflex_game_over = False                  # True when 15 rounds are completed

# -----------------------------
# STATE HELPERS
# -----------------------------
def set_state(new_state):
    global state, state_start_time, timer_guess_sequence, timer_guess_page_index, timer_guess_target
    state = new_state
    state_start_time = pygame.time.get_ticks()
    
    if new_state == STATE_TIMER_GUESS:
        timer_guess_target = random.randint(2, 8)
        timer_guess_sequence = create_timer_guess_sequence(timer_guess_target)
        timer_guess_page_index = 0
    elif new_state == STATE_FAST_REFLEXES:
        reset_fast_reflexes()


def fast_reflex_set_feedback(message, now_ms, duration_ms=1200):
    """Display feedback message for a set duration (e.g., 'Caught!' or 'Missed!')"""
    global fast_reflex_feedback, fast_reflex_feedback_until
    fast_reflex_feedback = message
    fast_reflex_feedback_until = now_ms + duration_ms


def fast_reflex_schedule_next_spawn(now_ms):
    """Schedule the next sprite to appear at a random time in the future"""
    global fast_reflex_next_spawn_time
    fast_reflex_next_spawn_time = now_ms + random.randint(FAST_REFLEX_MIN_GAP_MS, FAST_REFLEX_MAX_GAP_MS)


def reset_fast_reflexes():
    """Reset all fast-reflex game state to start a new game"""
    global fast_reflex_next_spawn_time, fast_reflex_sprite_end_time, fast_reflex_current_sprite
    global fast_reflex_current_is_bad, fast_reflex_bad_spawn_time, fast_reflex_rounds_completed
    global fast_reflex_hits, fast_reflex_misses, fast_reflex_false_alarms, fast_reflex_score
    global fast_reflex_last_reaction_ms, fast_reflex_feedback, fast_reflex_feedback_until, fast_reflex_game_over

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
    fast_reflex_last_reaction_ms = None
    fast_reflex_feedback = "Tap SPACE to catch anything that is not a fish to clean the ocean."
    fast_reflex_feedback_until = now_ms + 3000
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

# -----------------------------
# MAIN LOOP
# -----------------------------
running = True
while running:
    current_time = pygame.time.get_ticks()
    elapsed = current_time - state_start_time

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
                        fast_reflex_set_feedback("Too early! No sprite on screen.", current_time)
                    elif fast_reflex_current_is_bad:
                        # Player pressed SPACE on a bad sprite (monster) - SUCCESS!
                        # Calculate reaction time and award points: faster = more points
                        reaction_ms = current_time - fast_reflex_bad_spawn_time
                        points = max(100, 1300 - reaction_ms)  # Fast catches get ~1000+ points
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
                        else:
                            fast_reflex_schedule_next_spawn(current_time)
                    else:
                        # Player pressed SPACE on a good sprite - MISTAKE!
                        fast_reflex_false_alarms += 1
                        fast_reflex_score = max(0, fast_reflex_score - 80)
                        fast_reflex_rounds_completed += 1
                        fast_reflex_set_feedback("You caught a fish on accident!", current_time)
                        fast_reflex_current_sprite = None
                        fast_reflex_bad_spawn_time = None
                        fast_reflex_sprite_end_time = None

                        if fast_reflex_rounds_completed >= FAST_REFLEX_TOTAL_ROUNDS:
                            fast_reflex_game_over = True
                        else:
                            fast_reflex_schedule_next_spawn(current_time)

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
                    fast_reflex_set_feedback("You missed an object!", current_time)

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
        text("TODO: MATCHING", TEXT_SIZE, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)

    elif state == STATE_FAST_REFLEXES:
        # Draw the fast-reflex game HUD and sprites
        # Display round progress and scoring information at top of screen
        rounds_text = f"Round {fast_reflex_rounds_completed}/{FAST_REFLEX_TOTAL_ROUNDS}"
        score_text = f"Score: {fast_reflex_score}"
        stats_text = f"Hits: {fast_reflex_hits}  Misses: {fast_reflex_misses}  False alarms: {fast_reflex_false_alarms}"

        text(rounds_text, 24, COLOR_WHITE, SCREEN_CENTER_X, 24)
        text(score_text, 26, COLOR_WHITE, SCREEN_CENTER_X, 52)
        text(stats_text, 22, COLOR_WHITE, SCREEN_CENTER_X, 80)

        # Draw the current sprite if one is on screen, with colored instruction text
        if fast_reflex_current_sprite is not None:
            draw_sprite(fast_reflex_current_sprite)

        elif not fast_reflex_game_over:
            # No sprite on screen - tell player to get ready for next one
            text("Get ready...", 36, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)

        # Display feedback message if one is active (e.g., "Caught!", "Too early!")
        if current_time <= fast_reflex_feedback_until and fast_reflex_feedback:
            text(fast_reflex_feedback, 24, COLOR_WHITE, SCREEN_CENTER_X, HEIGHT - 58)

        # Display the last reaction time achieved
        if fast_reflex_last_reaction_ms is not None:
            text(f"Last reaction: {fast_reflex_last_reaction_ms}ms", 22, COLOR_WHITE, SCREEN_CENTER_X, 108)

        # Show game over message and restart instructions
        if fast_reflex_game_over:
            
            text("Game Over - Press SPACE to play again", 36, COLOR_WHITE, SCREEN_CENTER_X, SCREEN_CENTER_Y)

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