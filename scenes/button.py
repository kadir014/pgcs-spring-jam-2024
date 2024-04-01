import pygame

from engine import Scene, Entity


class Button(Entity):
    """
    Base button widget class.
    ( Why didn't I use my UI library? T_T )
    """

    def __init__(
            self,
            scene: Scene,
            position: pygame.Vector2,
            size: tuple[float, float]
        ) -> None:
        super().__init__(scene, position)
        self.size = size
        self.pressed = False
        self.hovered = False

    def update(self) -> None:
        if pygame.Rect((self.position.x, self.position.y, self.size[0], self.size[1])).collidepoint(self.engine.input.mouse):
            if not self.hovered:
                self.hovered_event()
                self.hovered = True
        else:
            self.hovered = False

        if self.engine.input.mouse_pressed("left"):
            if self.hovered:
                self.pressed = True

        if self.engine.input.mouse_released("left"):
            if self.pressed and self.hovered:
                self.clicked_event()
            self.pressed = False

    def hovered_event(self) -> None:
        """ Button mouse hover event. """
        ...

    def clicked_event(self) -> None:
        """ Button pressed event. """
        ...


class MenuButton(Button):
    def __init__(
            self,
            scene: Scene,
            position: pygame.Vector2,
            size: tuple[float, float],
            type_: str
        ) -> None:
        super().__init__(scene, position, size)
        self.type = type_

        self.window_ratio = self.engine.window_width / 1920

        self.open_surf = pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"][f"button_{self.type}_open"], self.window_ratio)
        self.close_surf = pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"][f"button_{self.type}_close"], self.window_ratio)
        self.hand_surf = pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"][f"menu_hand"], self.window_ratio)

    def render_before(self) -> None:
        surf = self.close_surf if self.pressed else self.open_surf
        self.engine.display.blit(surf, self.position)

        if self.hovered:
            offset = 240 if self.type == "settings" else 200
            self.engine.display.blit(self.hand_surf, (self.position.x - offset * self.window_ratio, self.position.y))

    def hovered_event(self) -> None:
        self.engine.asset_manager.assets["sounds"]["ui1"].set_volume(self.engine.master_volume)
        self.engine.asset_manager.assets["sounds"]["ui1"].play()

    def clicked_event(self) -> None:
        self.engine.asset_manager.assets["sounds"]["ui4"].set_volume(self.engine.master_volume)
        self.engine.asset_manager.assets["sounds"]["ui4"].play()

        if self.type == "start":
            self.engine.change_scene_transition("Game", 1.5)

        elif self.type == "quit":
            self.engine.stop()