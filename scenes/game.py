from typing import TYPE_CHECKING

from time import perf_counter, time
from math import pi, atan2
from random import uniform
import array

import pygame
import pymunk

from engine import Scene, Entity
from engine.draw import draw_shadow_text

from .cursor import Cursor
from .water_postprocess import WaterPostProcess
from .textbox import DurkTextbox

if TYPE_CHECKING:
    from engine import Engine


class RigidBody(Entity):
    def __init__(
            self,
            scene: "Scene",
            static: bool,
            body: pymunk.Body,
            shape: pymunk.Shape
            ) -> None:
        super().__init__(
            scene,
            pygame.Vector2(),
        )

        self.phypos = pygame.Vector2()
        self.static = static
        self.body = body
        self.shape = shape

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
        return cls(scene, static, body, shape)
    
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

    def render_before(self):
        if isinstance(self.shape, pymunk.Poly):
            points = []
            angle = self.body.angle
            for v in self.shape.get_vertices():
                p = v.rotated(angle) + self.phypos
                points.append((p.x * 10.0, (p.y) * 10.0))

            pygame.draw.polygon(self.engine.display, (134, 179, 161), points, 0)
            pygame.draw.polygon(self.engine.display, (0, 0, 0), points, 2)


class Game(Scene):
    def __init__(self, engine: "Engine"):
        super().__init__(engine)

        self.bg = pygame.transform.smoothscale(
            self.engine.asset_manager.assets["images"]["background"],
            (self.engine.window_width, self.engine.window_height)
        ).convert()

        self.textbox = DurkTextbox(self)

        self.cursor = Cursor(self)

        self.space = pymunk.Space()
        self.space.iterations = 10
        self.space.sleep_time_threshold = 3.0
        self.space.gravity = (0.0, 20.0)
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

    def update(self):
        self.cursor.update()

        if self.engine.input.key_pressed("escape"):
            self.engine.stop()

        if self.engine.input.key_pressed("f2"):
            self.debug_drawing = not self.debug_drawing

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

                b = RigidBody.from_box(self, position, (delta.length(), 3.0), angle, friction=0.0, static=True)
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

        step_time_start = perf_counter()
        self.space.step(self.sim_hz)
        self.step_time = perf_counter() - step_time_start

    def render_before(self):
        self.engine.display.blit(self.bg, (0, 0))

    def render_after(self):
        if self.drawing:
            pygame.draw.line(self.engine.display, (255, 255, 255), self.drawing_start, self.engine.input.mouse)

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
        self.water_post.particle_vbo.clear()
        self.water_post.particle_vbo.write(
            array.array("f", [c for p in self.particles for c in [p.position.x, p.position.y]])
        )

        self.water_post.render()
