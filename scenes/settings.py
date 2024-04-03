from typing import TYPE_CHECKING

import os

import pygame

from engine import Scene

from .cursor import Cursor
from .button import SettingsButton

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

        self.save = pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"]["button_saverestart"], self.window_ratio)

        self.init_btns()

    def init_btns(self):
        self.res_btn = SettingsButton(
            self,
            pygame.Vector2(1098 * self.window_ratio, 298 * self.window_ratio),
            (384 * self.window_ratio, 83 * self.window_ratio),
            "res"
        )

        self.hw_btn = SettingsButton(
            self,
            pygame.Vector2(1280 * self.window_ratio, 385 * self.window_ratio),
            (149 * self.window_ratio, 90 * self.window_ratio),
            "hw"
        )

    def save_settings(self):
        cwd = os.getcwd()
        settings_path = os.path.join(cwd, "settings.cfg")

        with open(settings_path, "w") as f:
            f.write(f"""
[Engine]
title = {self.engine.window_title}
max_fps = {self.engine.max_fps}
forced_width = {self.res_btn.get_res()[0]}
forced_height = {self.res_btn.get_res()[1]}
hardware_scaling = {self.hw_btn.toggle}
fullscreen = off
master_volume = {self.engine.master_volume}

[Graphics]
quality = 3
            """)

    def update(self):
        if self.engine.input.mouse_pressed("left"):
            if self.engine.input.mouse.x < 150 * self.window_ratio and self.engine.input.mouse.y < 100 * self.window_ratio:
                self.engine.change_scene("Menu")
                self.entities.clear()
                self.init_btns()

            elif self.engine.input.mouse.x < self.save.get_width() and self.engine.input.mouse.y < self.save.get_height():
                self.save_settings()
                self.engine.stop()

    def render_before(self):
        self.engine.display.blit(self.bg, (0, 0))

        if self.res_btn.changed() or self.hw_btn.changed():
            self.engine.display.blit(self.save, (0, 0))