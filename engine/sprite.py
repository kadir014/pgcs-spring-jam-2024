from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from .engine import Engine


class Sprite:
    """
    Class representing graphics of entities on screen.
    """

    def __init__(self, engine: "Engine", asset: str):
        self.engine = engine

        self.asset = asset

        self.has_animation = self.asset in engine.asset_manager.assets["animations"]
        self.frames = len(engine.asset_manager.assets["animations"][self.asset])
        self.frame = 0
        self.duration = 250
        self.is_playing = False
        self.is_looped = False
        self.reverse_loop = False
        self.__loop_turn = False
        self.__last_frame = pygame.time.get_ticks()

        if self.has_animation:
            self.og_surface = engine.asset_manager.assets["animations"][asset][0]
        else:
            self.og_surface = engine.asset_manager.assets["sprites"][asset]
        self.surface = self.og_surface.copy()

        self.__angle = 0
        self.__scale = 1
        self.__scaled_surface = None
        self.__is_rotated = False
        self.__is_scaled = False

    @property
    def angle(self):
        return self.__angle

    @angle.setter
    def angle(self, value: float):
        self.__angle = value
        self.__is_rotated = False

    @property
    def scale(self):
        return self.__scale

    @scale.setter
    def scale(self, value: float):
        self.__scale = value
        self.__is_scaled = False

    def play(self, loop: bool = False, reverse_loop: bool = False):
        """ Start playing sprite animation. """
        self.is_playing = True
        self.is_looped = loop
        self.reverse_loop = reverse_loop

    def stop(self):
        """ Stop playing sprite animation. """
        self.is_playing = False
        self.is_looped = False
        self.reverse_loop = False

    def render_self(self, force: bool = False):
        """ Update the sprite surface. """

        if force:
            self.__is_scaled = False
            self.__is_rotated = False

        if not self.__is_scaled:
            self.__scaled_surface = pygame.transform.scale_by(self.og_surface, self.__scale)
            self.__is_scaled = True

        if not self.__is_rotated:
            self.surface = pygame.transform.rotate(self.__scaled_surface, self.__angle)
            self.__is_rotated = True

    def render(self, surface: pygame.Surface, position: pygame.Vector2):

        if self.has_animation and self.is_playing and pygame.time.get_ticks() - self.__last_frame > self.duration:
            if self.__loop_turn: self.frame -= 1
            else: self.frame += 1

            if self.frame == self.frames:
                if self.reverse_loop and self.is_looped:
                    self.__loop_turn = not self.__loop_turn
                    self.frame -= 2

                elif self.is_looped:
                    self.frame = 0

                else:
                    self.frame -= 1
                    self.stop()

            elif self.frame == -1 and self.reverse_loop:
                self.__loop_turn = not self.__loop_turn
                self.frame += 2

            self.og_surface = self.engine.asset_manager.assets["animations"][self.asset][self.frame]
            self.surface = self.og_surface.copy()
            self.__last_frame = pygame.time.get_ticks()
            self.render_self(force=True)

        else:
            self.render_self()

        surface.blit(self.surface, self.surface.get_rect(center=position))