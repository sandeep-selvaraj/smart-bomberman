import pygame # type: ignore
# from .settings import GameWindow
from .maingame import start_game
from .utils.fileutils import import_sprite
# from pathlib import Path
from .button import Button


def main_menu(level_number: int):

    pygame.init()
    BG = import_sprite("graphics/bomberman_title.png")  #https://miscrave.com/articles/bomberman-history/
    SCREEN = pygame.display.set_mode((BG.get_width(),BG.get_height()))
    pygame.display.set_caption("Menu")

    play_img = import_sprite("graphics/Start.png")  #https://www.freepik.com/premium-vector/set-pixel-graphics-icons-game-art-play-buttons-animation_36747298.htm
    score_img = import_sprite("graphics/Score.png")  #https://www.freepik.com/premium-vector/set-pixel-graphics-icons-game-art-play-buttons-animation_36747298.htm
    exit_img = import_sprite("graphics/Exit.png")  #https://www.freepik.com/premium-vector/set-pixel-graphics-icons-game-art-play-buttons-animation_36747298.htm

    height_align = 70
    width_align = 60

    play_but = Button((BG.get_width()/2)-width_align,BG.get_height()/2, play_img, 0.3)
    score_but = Button((BG.get_width()/2)-width_align,(BG.get_height()/2)+height_align, score_img, 0.3)
    exit_but = Button((BG.get_width()/2)-width_align,(BG.get_height()/2)+(height_align*2), exit_img, 0.3)

    run = True
    while run:
        SCREEN.blit(BG, (0,0))

        if play_but.draw(SCREEN):
            start_game(level_number)
        if score_but.draw(SCREEN):
            pass
        if exit_but.draw(SCREEN):
            run = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        pygame.display.update()

    pygame.quit()