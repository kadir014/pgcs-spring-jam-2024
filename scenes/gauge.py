import pygame

from engine import Scene, Entity


def map_range(x: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class Gauge(Entity):
    """
    Thermometer gauge.
    """

    def __init__(self, scene: Scene):
        super().__init__(scene, pygame.Vector2())

        self.window_ratio = self.engine.window_width / 1920

        self.overlay = pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][0], self.window_ratio)

        self.frames = (
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][1], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][2], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][3], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][4], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][5], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][6], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][7], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][8], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][9], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["animations"]["gauge"][10], self.window_ratio)
        )

    def render_before(self):
        frame = int(map_range(self.scene.temperature, self.scene.temp_min, self.scene.temp_max, 0, 9))
        self.engine.display.blit(self.frames[frame], (0, 0))
        self.engine.display.blit(self.overlay, (0, 0))