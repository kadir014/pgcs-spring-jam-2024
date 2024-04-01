from typing import TYPE_CHECKING

import pygame

from engine import Scene

from .cursor import Cursor
from .button import MenuButton

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

        self.window_ratio = self.engine.window_width / 1920

        size = (310 * self.window_ratio, 180 * self.window_ratio)

        self.start_btn = MenuButton(
            self,
            pygame.Vector2(
                self.engine.window_width - 550 * self.window_ratio,
                self.engine.window_height - 700 * self.window_ratio
            ),
            size,
            "start"
        )

        self.settings_btn = MenuButton(
            self,
            pygame.Vector2(
                self.engine.window_width - 550 * self.window_ratio,
                self.engine.window_height - 500 * self.window_ratio
            ),
            size,
            "settings"
        )

        self.quit_btn = MenuButton(
            self,
            pygame.Vector2(
                self.engine.window_width - 550 * self.window_ratio,
                self.engine.window_height - 300 * self.window_ratio
            ),
            size,
            "quit"
        )

    def render_before(self):
        self.engine.display.blit(self.bg, (0, 0))