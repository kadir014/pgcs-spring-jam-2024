from typing import TYPE_CHECKING

import pygame

from engine import Scene

from .cursor import Cursor

if TYPE_CHECKING:
    from engine import Engine


class Settings(Scene):
    def __init__(self, engine: "Engine"):
        super().__init__(engine)

        self.bg = pygame.transform.smoothscale(
            self.engine.asset_manager.assets["images"]["background"],
            (self.engine.window_width, self.engine.window_height)
        ).convert()

        self.cursor = Cursor(self)

        self.window_ratio = self.engine.window_width / 1920

        self.overlay = pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"]["settings"], self.window_ratio)
        self.bg.blit(self.overlay, (0, 0))

        size = (310 * self.window_ratio, 180 * self.window_ratio)

    def update(self):
        if self.engine.input.mouse_pressed("left"):
            if self.engine.input.mouse.x < 150 * self.window_ratio and self.engine.input.mouse.y < 100 * self.window_ratio:
                self.engine.change_scene("Menu")

    def render_before(self):
        self.engine.display.blit(self.bg, (0, 0))