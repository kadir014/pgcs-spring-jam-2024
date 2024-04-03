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

        elif self.type == "settings":
            self.engine.change_scene("Settings")

        elif self.type == "quit":
            self.engine.stop()


class SettingsButton(Button):
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

        self.default_toggle = self.engine.hardware_scaling
        if self.engine.hardware_scaling:
            self.default_w, self.default_h = self.engine.scaled_width, self.engine.scaled_height
        else:
            self.default_w, self.default_h = self.engine.window_width, self.engine.window_height

        self.toggle = self.default_toggle

        if self.type == "res":
            self.res_surfs = {
                "1280x720": pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"][f"res_1280x720"], self.window_ratio),
                "1366x768": pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"][f"res_1366x768"], self.window_ratio),
                "1600x900": pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"][f"res_1600x900"], self.window_ratio),
                "1920x1080": pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"][f"res_1920x1080"], self.window_ratio),
                "2560x1440": pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"][f"res_2560x1440"], self.window_ratio),
            }
            self.res_i = list(self.res_surfs.keys()).index(f"{self.default_w}x{self.default_h}")

        elif self.type == "hw":
            self.on_surf = pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"][f"button_on"], self.window_ratio)
            self.off_surf = pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"][f"button_off"], self.window_ratio)

    def render_before(self) -> None:
        if self.type == "hw":
            surf = self.on_surf if self.toggle else self.off_surf
            self.engine.display.blit(surf, self.position)

        elif self.type == "res":
            surf = self.res_surfs[list(self.res_surfs.keys())[self.res_i]]
            self.engine.display.blit(surf, self.position)

    def clicked_event(self) -> None:
        self.engine.asset_manager.assets["sounds"]["ui4"].set_volume(self.engine.master_volume)
        self.engine.asset_manager.assets["sounds"]["ui4"].play()

        if self.type == "hw":
            self.toggle = not self.toggle

        elif self.type == "res":
            r = self.engine.input.mouse - self.position

            if r.x < self.size[0] / 2:
                self.res_i -= 1
                if self.res_i < 0: self.res_i = 0
                
            if r.x > self.size[0] / 2:
                self.res_i += 1
                if self.res_i > len(self.res_surfs) - 1: self.res_i = len(self.res_surfs) - 1

    def get_res(self) -> tuple[int, int]:
        k = list(self.res_surfs.keys())[self.res_i]
        s = k.split("x")
        return (int(s[0]), int(s[1]))

    def changed(self) -> bool:
        if self.type == "hw":
            return self.toggle != self.default_toggle

        elif self.type == "res":
            return list(self.res_surfs.keys())[self.res_i] != f"{self.default_w}x{self.default_h}"