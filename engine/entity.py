from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from .sprite import Sprite
    from .scene import Scene


class Entity:
    """
    Base class for all game objects in a scene.
    """

    def __init__(self,
            scene: "Scene",
            position: pygame.Vector2 | tuple[float, float],
            sprite: "Sprite" = None,
            ):
        self.scene = scene
        self.engine = scene.engine
        self.scene.add_entity(self)

        self.killed = False
        self.position = pygame.Vector2(position)
        self.sprite = sprite
        self.z_index = 0

    def kill(self):
        """ Remove the entity from the scene. """
        self.scene.entities.remove(self)
        self.killed = True

    def update(self):
        """ Entity update callback. """
        ...
        
    def render_before(self):
        """ Callback before rendering entity sprite. """
        ...

    def render_after(self):
        """ Callback after rendering entity sprite. """
        ...