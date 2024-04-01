from typing import Union

import os; os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
from contextlib import contextmanager
from time import perf_counter, time
from pathlib import Path
import configparser

import pygame
import moderngl

from .common import DISPLAY_RESOLUTIONS
from .input import InputManager
from .scene import Scene
from .hwinfo import get_cpu_info, is_web
from .asset_manager import AssetManager
from .draw import draw_debug_ui
from .gl import BasicScreenQuad


def _cfg_to_bool(value: str) -> bool:
    """ Convert config entry value to bool. """
    return value.lower() in ("true", "t", "1", "on", "yes", "y", "enabled")


EPSILON = 0.000001

def near_enough(a: float, b: float) -> bool:
    return (a > b - EPSILON) or (a < b + EPSILON) or a == b


class Engine:
    """
    Top-level core engine class.
    """

    def __init__(self, config_path: Path) -> None:
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
        self.start_time = time()

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
        self.window_title = self.config["Engine"]["title"]

        self.hardware_scaling = self.config["Engine"]["hardware_scaling"]

        if "forced_width" in self.config["Engine"]: self.window_width = int(self.config["Engine"]["forced_width"])
        if "forced_height" in self.config["Engine"]:self.window_height = int(self.config["Engine"]["forced_height"])
        self.create_window()
        if _cfg_to_bool(self.config["Engine"]["fullscreen"].lower()): pygame.display.toggle_fullscreen()

        self.context = moderngl.create_context()
        self.context.enable(moderngl.BLEND)

        self.display_tex = self.context.texture(self.display.get_size(), 4)

        self.final_fbo = self.context.framebuffer(
            color_attachments=self.context.texture((self.window_width, self.window_height), 4)
        )

        self.screenquad = BasicScreenQuad(
            self,
            vertex_shader="""

#version 330

in vec2 in_position;
in vec2 in_uv;
out vec2 v_uv;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
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

        self.post = BasicScreenQuad(
            self,
            vertex_shader="""

#version 330

in vec2 in_position;
in vec2 in_uv;
out vec2 v_uv;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    v_uv = in_uv;
}

            """,
            fragment_shader="""
#version 330

// Vignette shader from: https://www.shadertoy.com/view/lsKSWR
// 2D Simplex (slightly modified) from: https://www.shadertoy.com/view/ttcSR8

in vec2 v_uv;
out vec4 f_color;

uniform float u_time;
uniform float u_temp;
uniform float u_fade;
uniform sampler2D s_texture;

vec3 permute(vec3 x) {
    return mod(((x * 34.0) + 1.0) * x, 289.0);
}

float snoise(vec2 v) {
    const vec4 C = vec4(
        0.211324865405187, 0.366025403784439,
        -0.577350269189626, 0.024390243902439
    );

    vec2 i = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod(i, 289.0);
    vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
    + i.x + vec3(0.0, i1.x, 1.0 ));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
    m = m*m;
    m = m*m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
    vec3 g;
    g.x  = a0.x  * x0.x  + h.x  * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
}

float snoise_octaves(vec2 uv, int octaves, float alpha, float beta, vec2 gamma, float delta) {
    vec2 pos = uv;
    float t = 1.0;
    float s = 1.0;
    vec2 q = gamma;
    float r = 0.0;
    for (int i = 0; i < octaves; i++) {
        r += s * snoise(pos + q);
        pos += t * uv;
        t *= beta;
        s *= alpha;
        q *= delta;
    }
    return r;
}

void main() {
    vec2 uv = v_uv;

    vec2 uv_vig = uv * (1.0 - uv.yx);
    float vig = uv_vig.x * uv_vig.y * 45.0;
    vig = pow(vig, 0.07); 

    vec3 color;

    if (u_temp > 0.65) {
        float temp = (u_temp - 0.65) * 2.0;
        float noise_factor_x = 0.0033 * temp;
        float noise_factor_y = 0.0023 * temp;

        vec2 uv_noise = uv + vec2(
            noise_factor_x * snoise_octaves(uv * 2.0 + u_time * vec2(0.00323, 0.00345), 9,0.85, -3.0, u_time * vec2(-0.0323, -0.345), 1.203),
            noise_factor_y * snoise_octaves(uv * 2.0 + 3.0 + u_time * vec2(-0.00323, 0.00345), 9,0.85, -3.0, u_time * vec2(-0.0323, -0.345), 1.203)
        );

        color = texture(s_texture, uv_noise).rgb;
        color = mix(color, vec3(1.0, 0.349, 0.109), u_temp - 0.65);
    }
    else {
        color = texture(s_texture, uv).rgb;
    }

    f_color = vec4(color * vig, u_fade);
}

            """
        )

        self.scenes = {}
        self.__current_scene = None

        self.in_transition = False
        self.transitioned = False
        self.transition_start = time()
        self.transition_scene = ""
        self.transition_duration = 0

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
        pygame.display.set_mode(
           (self.window_width, self.window_height),
           pygame.OPENGL | pygame.DOUBLEBUF
        )

        self.display = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA).convert_alpha()

    @property
    def aspect_ratio(self) -> float:
        return self.window_width / self.window_height
    
    def set_icon(self, filepath: Union[Path, str]) -> None:
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
    
    def add_scene(self, scene: Scene) -> None:
        """
        Add a scene to the engine.
        This function also sets the current scene as the last added one.
        """
        scene_ = scene(self)
        self.__current_scene = scene_.__class__.__name__
        self.scenes[self.__current_scene] = scene_

    def change_scene(self, scene_name: str) -> None:
        """ Change the current scene. """
        self.__current_scene = scene_name

    def change_scene_transition(self, scene_name: str, duration: float) -> None:
        """ Change the current scene with a transition. """
        self.in_transition = True
        self.transition_scene = scene_name
        self.transition_duration = duration
        self.transition_start = time()
        self.transitioned = False

    def handle_events(self) -> None:
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

    def _accumulate(self, stat: str, value: float) -> None:
        """ Accumulate stat value. """

        acc = self.stats[stat]["acc"]
        acc.append(value)

        if len(acc) > self.stat_accumulate:
            acc.pop(0)

            self.stats[stat]["avg"] = sum(acc) / len(acc)
            self.stats[stat]["min"] = min(acc)
            self.stats[stat]["max"] = max(acc)

    def stop(self) -> None:
        """ Stop the engine. """
        self.is_running = False

    def run(self) -> None:
        """ Run the engine. """
        self.is_running = True

        while self.is_running:
            with self.profile("frame"):

                self.dt = self.clock.tick(self.max_fps) * 0.001
                self.fps = self.clock.get_fps()
                if self.fps == float("inf"): self.fps = 0 # Prevent OverflowError for rendering
                self._accumulate("fps", self.fps)

                self.handle_events()

                if self.input.key_pressed("f1"):
                    self.stat_drawing = (self.stat_drawing + 1) % 3

                if self.input.key_held("lshift") and self.input.key_pressed("escape"):
                    self.stop()

                with self.profile("update"):
                    for entity in self.scene.entities:
                        entity.update()

                    self.scene.update()

                with self.profile("render"):
                    self.context.screen.use()
                    self.context.clear(0, 0, 0)
                    self.final_fbo.use()
                    self.context.clear(0, 0, 0)
                    self.display.fill((14, 12, 28))

                    self.scene.render_before()

                    entities = sorted(self.scene.entities, key=lambda e: e.z_index, reverse=False)

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
                    self.screenquad.vao.render()

                    self.scene.render_post()

                    fade = 1.0
                    if self.in_transition:
                        t = (time() - self.transition_start) / self.transition_duration

                        if not self.transitioned and t >= 0.5:
                            self.transitioned = True
                            self.change_scene(self.transition_scene)

                        if t >= 1.0:
                            self.in_transition = False

                        if t >= 0.5:
                            fade = t * 2.0 - 1.0
                        else:
                            fade = (1.0 - t) * 2.0 - 1.0

                    self.context.screen.use()
                    self.final_fbo.color_attachments[0].use(0)
                    self.post.shader["u_time"] = time() - self.start_time
                    self.post.shader["u_fade"] = fade
                    if hasattr(self.scene, "temperature"):
                        self.post.shader["u_temp"] = self.scene.temperature / 100.0
                    else:
                        self.post.shader["u_temp"] = 25.0 / 100.0
                    self.post.vao.render()

                    pygame.display.flip()

        pygame.quit()