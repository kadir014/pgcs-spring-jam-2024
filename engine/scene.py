from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from .engine import Engine
    from .entity import Entity
    

class Scene:
    """
    Base scene class.
    """

    def __init__(self, engine: "Engine"):
        self.engine = engine

        # Active camera
        self.camera = pygame.Vector2(0)

        self.entities = []

    def add_entity(self, entity: "Entity"):
        """ Add entity to the scene. """
        self.entities.append(entity)

    def update(self):
        """ Scene update callback. """
        ...

    def render_before(self):
        """ Scene render callback before drawing entities. """
        ...

    def render_after(self):
        """ Scene render callback after drawing entities. """
        ...

    def render_post(self):
        """ Scene render callback for post-process. """
        ...