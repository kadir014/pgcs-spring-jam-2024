from typing import Union

import os; os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
from contextlib import contextmanager
from time import perf_counter
from pathlib import Path
import configparser
import array

import pygame
import moderngl

from .common import DISPLAY_RESOLUTIONS
from .input import InputManager
from .scene import Scene
from .hwinfo import get_cpu_info, is_web
from .asset_manager import AssetManager
from .draw import draw_debug_ui


def _cfg_to_bool(value: str) -> bool:
    """ Convert config entry value to bool. """
    return value.lower() in ("true", "t", "1", "on", "yes", "y", "enabled")


class Engine:
    """
    Top-level core engine class.
    """

    def __init__(self, config_path: Path):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        pygame.init()

        # Events & timing
        self.events = []
        self.clock = pygame.time.Clock()
        self.max_fps = float(self.config["Engine"]["max_fps"])
        self.fps = self.max_fps
        self.dt = 1.0 / self.fps
        self.is_running = False
        self.frame = 0

        self.master_volume = float(self.config["Engine"]["master_volume"])

        self.input = InputManager(self)
        pygame.key.set_repeat(400, 40)

        display_info = pygame.display.Info()
        self.monitor_width = display_info.current_w
        self.monitor_height = display_info.current_h

        resolution = self.get_max_resolution(self.get_monitor_aspect_ratio())
        self.window_width = resolution[0]
        self.window_height = resolution[1]
        self.__window_title = ""

        if "forced_width" in self.config["Engine"]: self.window_width = int(self.config["Engine"]["forced_width"])
        if "forced_height" in self.config["Engine"]:self.window_height = int(self.config["Engine"]["forced_height"])
        self.create_window()
        if _cfg_to_bool(self.config["Engine"]["fullscreen"].lower()): pygame.display.toggle_fullscreen()

        self.context = moderngl.create_context()
        self.context.enable(moderngl.BLEND)

        self.display_tex = self.context.texture(self.display.get_size(), 4)

        self.screenquad_shader = self.context.program(
            vertex_shader="""

#version 330

in vec2 in_vert;
in vec2 in_uv;
out vec2 v_uv;

void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
    v_uv = in_uv;
}

            """,
            fragment_shader="""

#version 330

in vec2 v_uv;
out vec4 f_color;

uniform sampler2D s_texture;

void main() {
    // pygame.Surface.get_view("1") returns an upside down and BGR texture
    vec2 uv = v_uv;
    uv.y = 1.0 - uv.y;
    f_color = texture(s_texture, uv).bgra;
}

            """
        )

        self.screenquad_vbo = self.context.buffer(
            array.array("f", [
                1.0,  1.0,
                1.0, -1.0,
                -1.0, -1.0,
                -1.0,  1.0,
            ])
        )

        self.screenquad_ibo = self.context.buffer(
            array.array("i", [
                0, 1, 3,
                1, 2, 3
            ])
        )

        self.screenquad_uvbo = self.context.buffer(
            array.array("f", [
                1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0
            ])
        )

        self.screenquad_vao = self.context.vertex_array(
            self.screenquad_shader,
            (
                self.screenquad_vbo.bind("in_vert", layout="2f"),
                self.screenquad_uvbo.bind("in_uv", layout="2f")
            ),
            index_buffer=self.screenquad_ibo
        )

        self.scenes = {}
        self.__current_scene = None

        self.asset_manager = AssetManager()

        self.pygame_version = pygame.version.ver
        self.sdl_version = ".".join((str(v) for v in pygame.get_sdl_version()))

        self.cpu_info = get_cpu_info()
        self.platform = ("Desktop", "Web")[is_web()]

        # Profiling stuff
        self.stats = {
            "render": {"avg": 0.0, "min": 0.0, "max": 0.0, "acc": []},
            "update": {"avg": 0.0, "min": 0.0, "max": 0.0, "acc": []},
            "frame": {"avg": 0.0, "min": 0.0, "max": 0.0, "acc": []},
            "fps": {"avg": 0.0, "min": 0.0, "max": 0.0, "acc": []}
        }
        self.stat_accumulate = 30
        self.stat_drawing = 0

    @property
    def window_title(self):
        return self.__window_title
    
    @window_title.setter
    def window_title(self, new_title: str):
        self.__window_title = new_title
        pygame.display.set_caption(self.__window_title)

    def create_window(self):
        #self.display = pygame.display.set_mode(
        #    (self.window_width, self.window_height)
        #)
        pygame.display.set_mode(
           (self.window_width, self.window_height),
           pygame.OPENGL | pygame.DOUBLEBUF
        )

        self.display = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA).convert_alpha()

    @property
    def aspect_ratio(self) -> float:
        return self.window_width / self.window_height
    
    def set_icon(self, filepath: Union[Path, str]):
        """ Set window icon. """
        pygame.display.set_icon(pygame.image.load(filepath))

    def get_monitor_aspect_ratio(self) -> str:
        """ Get aspect ratio of the monitor. """

        monitor_tuple = (self.monitor_width, self.monitor_height)

        if monitor_tuple in DISPLAY_RESOLUTIONS["16:9"]:
            return "16:9"
        
        elif monitor_tuple in DISPLAY_RESOLUTIONS["4:3"]:
            return "4:3"

    def get_usable_resolutions(self) -> dict:
        """ Get usable resolutions on the monitor. """

        resolutions = {"16:9": [], "4:3": []}

        for res in DISPLAY_RESOLUTIONS["16:9"]:
            if res[0] <= self.monitor_width and res[1] <= self.monitor_height:
                resolutions["16:9"].append(res)

        for res in DISPLAY_RESOLUTIONS["4:3"]:
            if res[0] <= self.monitor_width and res[1] <= self.monitor_height:
                resolutions["4:3"].append(res)

        return resolutions
    
    def get_max_resolution(self, aspect_ratio: str) -> tuple[int, int]:
        """ Get maximum usable resolution on the monitor. """

        resolutions = self.get_usable_resolutions()

        return resolutions[aspect_ratio][-1]
    
    @property
    def scene(self) -> Scene:
        """ Get the current scene. """
        return self.scenes[self.__current_scene]
    
    def add_scene(self, scene: Scene):
        """
        Add a scene to the engine.
        This function also sets the current scene as the last added one.
        """
        scene_ = scene(self)
        self.__current_scene = scene_.__class__.__name__
        self.scenes[self.__current_scene] = scene_

    def handle_events(self):
        """ Handle Pygame events. """

        self.events = pygame.event.get()

        for event in self.events:
            if event.type == pygame.QUIT:
                self.stop()

        self.input.update()

    @contextmanager
    def profile(self, stat: str):
        """ Profile code. """

        start = perf_counter()
        
        try: yield None

        finally:
            elapsed = perf_counter() - start
            self._accumulate(stat, elapsed)

    def _accumulate(self, stat: str, value: float):
        """ Accumulate stat value. """

        acc = self.stats[stat]["acc"]
        acc.append(value)

        if len(acc) > self.stat_accumulate:
            acc.pop(0)

            self.stats[stat]["avg"] = sum(acc) / len(acc)
            self.stats[stat]["min"] = min(acc)
            self.stats[stat]["max"] = max(acc)

    def stop(self):
        """ Stop the engine. """
        self.is_running = False

    def run(self):
        """ Run the engine. """
        self.is_running = True

        while self.is_running:
            with self.profile("frame"):

                self.dt = self.clock.tick(self.max_fps) / 1000
                self.fps = self.clock.get_fps()
                if self.fps == float("inf"): self.fps = 0 # Prevent OverflowError for rendering
                self._accumulate("fps", self.fps)

                self.handle_events()

                if self.input.key_pressed("f1"):
                    self.stat_drawing = (self.stat_drawing + 1) % 3

                with self.profile("update"):
                    for entity in self.scene.entities:
                        entity.update()

                    self.scene.update()

                with self.profile("render"):
                    self.context.clear(255, 255, 255)
                    self.display.fill((14, 12, 28))

                    self.scene.render_before()

                    #entities = sorted(self.scene.entities, key = lambda e: e.z_index, reverse=True)
                    entities = self.scene.entities

                    for entity in entities:
                        entity.render_before()
                        
                        if entity.sprite is not None:
                            entity.sprite.render(
                                self.display,
                                entity.position
                            )

                        entity.render_after()

                    self.scene.render_after()

                    if self.stat_drawing in (1, 2):
                        # Ugly way to convert (1, 2) to (True, False)
                        draw_debug_ui(self, 1 - (self.stat_drawing - 1))

                    self.display_tex.write(self.display.get_view("1"))
                    self.display_tex.use(0)
                    self.screenquad_vao.render()

                    self.scene.render_post()

                    pygame.display.flip()

        pygame.quit()