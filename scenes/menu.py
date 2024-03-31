from typing import TYPE_CHECKING

import pygame

from engine import Scene

from .cursor import Cursor

if TYPE_CHECKING:
    from engine import Engine


class Menu(Scene):
    def __init__(self, engine: "Engine"):
        super().__init__(engine)

        self.bg = pygame.transform.smoothscale(
            self.engine.asset_manager.assets["images"]["background"],
            (self.engine.window_width, self.engine.window_height)
        ).convert()

        self.cursor = Cursor(self)

    def update(self):
        self.cursor.update()

    def render_before(self):
        self.engine.display.blit(self.bg, (0, 0))