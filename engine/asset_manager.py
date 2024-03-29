import json

import pygame

from .path import source_path


class AssetManager:
    """
    Asset manager.
    """

    def __init__(self):
        with open(source_path("assets", "assets.json"), "r") as f:
            self.assets = json.load(f)

        self.__font_cache = {}

        if "images" in self.assets:
            for image in self.assets["images"]:
                surface = pygame.image.load(
                    source_path("assets", self.assets["images"][image])
                )

                if surface.get_flags() == 0x00010000:
                    surface = surface.convert_alpha()
                else:
                    surface = surface.convert()

                self.assets["images"][image] = surface

        if "animations" in self.assets:
            for animation in self.assets["animations"]:
                for i, sprite in enumerate(self.assets["animations"][animation]):
                    surface = pygame.image.load(
                        source_path("assets", self.assets["animations"][animation][i])
                    )

                    if surface.get_flags() == 0x00010000:
                        surface = surface.convert_alpha()
                    else:
                        surface = surface.convert()

                    self.assets["animations"][animation][i] = surface

    def get_font(self, name: str, size: int) -> pygame.Font:
        """ Get a loaded font. """

        if (name, size) not in self.__font_cache:
            self.__font_cache[(name, size)] = pygame.Font(
                source_path("assets", self.assets["fonts"][name]), size)

        return self.__font_cache[(name, size)]