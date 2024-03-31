from time import time
from math import pi, cos

import pygame

from engine import Scene, Entity


def ease_in_out_sine(x: float) -> float:
    return -(cos(pi * x) - 1) / 2


class DurkTextbox(Entity):
    """
    Dr. Durk's textbox.
    """

    def __init__(self, scene: Scene):
        super().__init__(scene, pygame.Vector2())

        self.z_index = 2

        self.window_ratio = self.engine.window_width / 1920

        self.textboxes = (
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"]["textbox0"], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"]["textbox1"], self.window_ratio)
        )

        self.image = 0
        self.text = ""
        self.displayed_text = ""
        self.cursor = 0
        self.done = True
        self.last = time()

        self.duration_normal = 0.07
        self.duration_quick = 0.0
        self.duration = self.duration_normal

        self.visible = False
        self.show_start = 0
        self.anim_y = 0
        self.ease_duration = 1
        self.anim_type = 0

    def update(self):
        if self.engine.input.key_pressed("space") or self.engine.input.key_pressed("return"):
            self.last = time()

        if self.engine.input.key_held("space") or self.engine.input.key_held("return"):
            self.duration = self.duration_quick
        else:
            self.duration = self.duration_normal

        if not self.done:
            now = time()
            if now - self.last > self.duration:
                self.last = now

                self.displayed_text += self.text[self.cursor]

                self.cursor += 1

                if self.cursor == len(self.text):
                    self.done = True

    def render_after(self):
        if self.visible:
            ih = self.textboxes[self.image].get_height()
            h = self.engine.window_height - ih
            texty = 0

            t = (time() - self.show_start) / self.ease_duration
            if t > 1: t = 1

            if self.anim_type == 0:
                y = ease_in_out_sine(t) * ih
                self.engine.display.blit(self.textboxes[self.image], (0, self.engine.window_height - y))
            
            elif self.anim_type == 1:
                y = ease_in_out_sine(t) * ih
                texty = y
                self.engine.display.blit(self.textboxes[self.image], (0, h + y))
                if t >= 1: self.visible = False

            if self.displayed_text:
                font = self.engine.asset_manager.get_font("LoveYaLikeASister", int(45 * self.window_ratio))
                s = font.render(self.displayed_text, True, (92, 60, 55))
                self.engine.display.blit(s, (655 * self.window_ratio, h + 220 * self.window_ratio + texty))

                if self.cursor < len(self.text) - 1:
                    s = font.render(self.displayed_text + self.text[self.cursor + 1], True, (92, 60, 55))
                    if s.get_width() > (1790 - 655) * self.window_ratio:
                        self.displayed_text += "\n"

    def say(self, image: int, text: str):
        self.image = image
        self.text = text
        self.displayed_text = ""
        self.cursor = 0
        self.last = time()
        self.done = False

    def show(self):
        self.visible = True
        self.show_start = time()
        self.anim_type = 0

    def hide(self):
        self.show_start = time()
        self.anim_type = 1