from typing import TYPE_CHECKING, Optional

from time import perf_counter
from math import pi, atan2
from random import uniform
import array
import json

import pygame
import pymunk

from engine import Scene, Entity
from engine.draw import draw_shadow_text
from engine.path import source_path

from .cursor import Cursor
from .water_postprocess import WaterPostProcess
from .textbox import DurkTextbox
from .gauge import Gauge

if TYPE_CHECKING:
    from engine import Engine


class RigidBody(Entity):
    def __init__(
            self,
            scene: "Scene",
            static: bool,
            body: pymunk.Body,
            shape: pymunk.Shape,
            size: Optional[tuple[float, float]] = None
            ) -> None:
        super().__init__(
            scene,
            pygame.Vector2(),
        )

        self.phypos = pygame.Vector2()
        self.static = static
        self.body = body
        self.shape = shape
        self.size = size

        if isinstance(self.shape, pymunk.Circle):
            self.scene.particles.append(self)

    @classmethod
    def from_box(
            cls,
            scene: "Scene",
            position: pygame.Vector2,
            size: tuple[float, float],
            angle: float = 0.0,
            friction: float = 0.5,
            restitution: float = 0.15,
            density: float = 1.0,
            static: bool = False
            ):
        width, height = size[0] / 2.0, size[1]  /2.0

        points = [
            (-width, -height),
            (-width, height),
            (width, height),
            (width, -height)
        ]

        mass = width * height * density
        moment = pymunk.moment_for_poly(mass, points, (0, 0))

        if static: body = pymunk.Body(mass, moment, pymunk.Body.STATIC)
        else: body = pymunk.Body(mass, moment, pymunk.Body.DYNAMIC)

        body.position = pymunk.Vec2d(position.x, position.y)
        body.angle = angle

        shape = pymunk.Poly(body, points)
        shape.friction = friction
        shape.elasticity = restitution

        scene.space.add(body, shape)
        return cls(scene, static, body, shape, size=size)
    
    @classmethod
    def from_circle(
            cls,
            scene: "Scene",
            position: pygame.Vector2,
            radius: float,
            angle: float = 0.0,
            friction: float = 0.5,
            restitution: float = 0.15,
            density: float = 1.0,
            static: bool = False
            ):
        mass = pi * radius * radius * density
        moment = pymunk.moment_for_circle(mass, 0, radius, (0, 0))

        if static: body = pymunk.Body(mass, moment, pymunk.Body.STATIC)
        else: body = pymunk.Body(mass, moment, pymunk.Body.DYNAMIC)

        body.position = pymunk.Vec2d(position.x, position.y)
        body.angle = angle

        shape = pymunk.Circle(body, radius)
        shape.friction = friction
        shape.elasticity = restitution

        scene.space.add(body, shape)
        return cls(scene, static, body, shape)

    def update(self):
        phypos = self.body.position
        self.phypos = pygame.Vector2(phypos.x, phypos.y)
        self.position = self.phypos * 10.0
        border = pygame.Rect(0, 0, self.engine.window_width, self.engine.window_height)

        if not border.collidepoint(self.position):
            self.kill()
            self.scene.space.remove(self.body, self.shape)
            self.scene.particles.remove(self)

        if self.scene.temperature > 80 and isinstance(self.shape, pymunk.Circle):
            strength = (self.scene.temperature - 80) * 55
            force = (uniform(-strength, strength), uniform(-strength, strength))
            self.body.apply_force_at_local_point(force, (0, 0))

    def render_before(self):
        if self.scene.debug_drawing:
            if isinstance(self.shape, pymunk.Poly):
                points = []
                angle = self.body.angle
                for v in self.shape.get_vertices():
                    p = v.rotated(angle) + self.phypos
                    points.append((p.x * 10.0, (p.y) * 10.0))

                pygame.draw.polygon(self.engine.display, (134, 179, 161), points, 0)
                pygame.draw.polygon(self.engine.display, (0, 0, 0), points, 2)

            else:
                pygame.draw.circle(self.engine.display, (0, 0, 0), self.position, self.shape.radius * 10, 1)


class Game(Scene):
    def __init__(self, engine: "Engine"):
        super().__init__(engine)

        self.window_ratio = self.engine.window_width / 1920
        self.bg = pygame.transform.smoothscale(
            self.engine.asset_manager.assets["images"]["background"],
            (self.engine.window_width, self.engine.window_height)
        ).convert()

        self.textbox = DurkTextbox(self)
        self.cursor = Cursor(self)
        self.gauge = Gauge(self)

        self.temperature = 30.0
        self.temp_max = 100.0
        self.temp_min = 0.0

        self.space = pymunk.Space()
        self.space.iterations = 10
        self.space.sleep_time_threshold = 3.0
        self.space.gravity = (0.0, 50.0)
        self.sim_hz = 1.0 / 60.0
        self.step_time = 0.0

        self.debug_drawing = False

        self.drawing = False
        self.drawing_start = pygame.Vector2()
        self.drawing_end = pygame.Vector2()

        self.particle_size = 1.5 / 2.0
        self.max_particles = 5000
        self.particles = []

        self.water_post = WaterPostProcess(self)

        self.level_imgs = (
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"]["level0"], self.window_ratio),
        )
        self.levels = (
            json.load(open(source_path("assets", "levels", "level0.json"))),
        )
        self.current_level = 0

        self.load_level(0)

    def load_level(self, level: int) -> None:
        for body in self.levels[level]["bodies"]:
            b = RigidBody.from_box(
                self,
                pygame.Vector2(*body["position"]),
                (body["width"], body["height"]),
                body["angle"],
                restitution=body["restitution"],
                friction=body["friction"],
                static=True
            )
            b.z_index = 1

    def update(self):
        if self.engine.input.key_pressed("f2"):
            self.debug_drawing = not self.debug_drawing

        if self.engine.input.mouse_wheel_up() or self.engine.input.key_pressed("up"):
            self.temperature += 10.0
            if self.temperature > self.temp_max:
                self.temperature = self.temp_max

        if self.engine.input.mouse_wheel_down() or self.engine.input.key_pressed("down"):
            self.temperature -= 10.0
            if self.temperature < self.temp_min:
                self.temperature = self.temp_min

        if self.engine.input.mouse_pressed("left") and self.engine.input.key_held("lshift"):
            self.drawing = True
            self.drawing_start = self.engine.input.mouse.copy()

        if self.engine.input.mouse_released("left"):
            if self.drawing:
                self.drawing = False
                self.drawing_end = self.engine.input.mouse.copy()

                delta = (self.drawing_end - self.drawing_start) / 10.0
                position = self.drawing_start / 10 + delta / 2.0
                angle = atan2(delta.y, delta.x)

                b = RigidBody.from_box(self, position, (delta.length(), 2.0), angle, restitution=0.2, friction=0.0, static=True)
                b.z_index = 1

        if self.engine.input.key_held("space"):
            v = self.engine.input.mouse_rel * 3.0

            for _ in range(3):
                r = pygame.Vector2(uniform(-1.0, 1.0), uniform(-1.0, 1.0))
                pos = self.engine.input.mouse / 10.0 + r
                b = RigidBody.from_circle(self, pos, self.particle_size, restitution=0.5, friction=0.0, static=False)
                b.body.velocity = pymunk.Vec2d(v.x, v.y)

        if self.engine.input.key_pressed("q"):
            self.textbox.say(0, "Greetings student! I'm Dr. Durk, a thermodynamics and molecular physics professor.")

        if self.engine.input.key_pressed("w"):
            self.textbox.say(1, "I will be the one to guide you trough the numerous scientific experiments of the day!")

        if self.engine.input.key_pressed("e"):
            self.textbox.show()

        if self.engine.input.key_pressed("r"):
            self.textbox.hide()

        if self.engine.input.key_pressed("p"):
            level_save = {"bodies": []}
            for body in self.entities:
                if isinstance(body, RigidBody) and isinstance(body.shape, pymunk.Poly):
                    level_save["bodies"].append(
                        {
                            "position": [body.body.position.x, body.body.position.y],
                            "angle": body.body.angle,
                            "width": body.size[0],
                            "height": body.size[1],
                            "restitution": body.shape.elasticity,
                            "friction": body.shape.friction
                        }
                    )

            print(json.dumps(level_save))


        step_time_start = perf_counter()
        self.space.step(self.sim_hz)
        self.step_time = perf_counter() - step_time_start

    def render_before(self):
        self.engine.display.blit(self.bg, (0, 0))
        self.engine.display.blit(self.level_imgs[0], (0, 0))

    def render_after(self):
        if self.drawing:
            pygame.draw.line(self.engine.display, (255, 255, 255), self.drawing_start, self.engine.input.mouse)

        if self.engine.stat_drawing == 2:
            font = self.engine.asset_manager.get_font("FiraCode-Bold", 12)

            draw_shadow_text(
                self.engine.display,
                font,
                f"Physics Debug",
                (5, self.engine.window_height - 5 - 14 * 3),
                (255, 255, 255)
            )

            draw_shadow_text(
                self.engine.display,
                font,
                f"Step: {round(self.step_time * 1000, 2)}ms",
                (5, self.engine.window_height - 5 - 14 * 2),
                (255, 255, 255)
            )

            draw_shadow_text(
                self.engine.display,
                font,
                f"Bodies: {len(self.space.bodies)}",
                (5, self.engine.window_height - 5 - 14 * 1),
                (255, 255, 255)
            )

    def render_post(self):
        # Update particles buffer with new particle positions
        if not self.debug_drawing:
            self.water_post.particle_vbo.clear()
            self.water_post.particle_vbo.write(
                array.array("f", [c for p in self.particles for c in [p.position.x, p.position.y]])
            )

            self.water_post.render()
