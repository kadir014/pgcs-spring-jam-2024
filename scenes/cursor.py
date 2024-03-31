from time import time

import pygame

from engine import Scene


class Cursor:
    def __init__(self, scene: Scene):
        self.scene = scene
        self.engine = self.scene.engine

        self.cursor_anim = (
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["cursor"][0], 0.3),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["cursor"][1], 0.3),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["cursor"][2], 0.3)
        )
        self.cursor_frame = 0
        self.cursor_last = time()

        pygame.mouse.set_cursor(pygame.Cursor((3, 3), self.cursor_anim[0]))

    def update(self):
        now = time()
        if now - self.cursor_last > 1.0:
            self.cursor_last = now
            self.cursor_frame = (self.cursor_frame + 1) % (len(self.cursor_anim))
            pygame.mouse.set_cursor(pygame.Cursor((3, 3), self.cursor_anim[self.cursor_frame]))