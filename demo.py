import pygame
import sys
import os

pygame.init()

# Set screen size
WIDTH, HEIGHT = 640, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Demo [TITLE]")

# Centered text 
def text(text, size, color, x, y):
    font = pygame.font.SysFont(None, size)  # default font TODO: CHANGE TO BL
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(x, y))
    screen.blit(text_surface, text_rect)

# Display sprite
def draw_sprite(filename):
    path = os.path.join("sprites", filename)

    try:
        image = pygame.image.load(path).convert_alpha()
    except pygame.error:
        print(f"Could not load image: {path}")
        return

    rect = image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(image, rect)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Fill screen with a color (black) TODO: replace with photo of glasses
    screen.fill((0, 0, 0))

    # Update the display
    pygame.display.flip()

pygame.quit()
sys.exit()