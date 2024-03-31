import pygame

from engine import Scene, Entity


class Button(Entity):
    def __init__(
            self,
            scene: Scene,
            position: pygame.Vector2
        ):
        super().__init__(scene, position)