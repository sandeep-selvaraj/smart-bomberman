"""Setting up the Button for Main Menu"""
#code from https://www.youtube.com/watch?v=G8MYGDf_9ho&ab_channel=CodingWithRuss
import pygame # type: ignore

class Button(): # pylint: disable=too-few-public-methods
    """
    Constants related to Button
    """
    def __init__(self, x, y, image, scale): # pylint: disable=invalid-name
        width = image.get_width()
        height = image.get_height()
        self.image = pygame.transform.scale(image, (int(width * scale), int(height * scale)))
        self.rect = self.image.get_rect()
        self.rect.topleft = (x,y)
        self.clicked = False

    def draw(self, surface):
        """Draw button"""
        action = False
        pos = pygame.mouse.get_pos()

        if self.rect.collidepoint(pos):
            if pygame.mouse.get_pressed()[0] == 1 and self.clicked is False:
                self.clicked = True
                action = True

        if pygame.mouse.get_pressed()[0] == 0:
            self.clicked = False


        surface.blit(self.image, (self.rect.x, self.rect.y))

        return action
    