from typing import TYPE_CHECKING

from time import perf_counter
from math import pi, atan2
from random import uniform

import pygame
import pymunk

from engine import Scene, Entity
from engine.draw import draw_shadow_text

if TYPE_CHECKING:
    from engine import Engine


class Player(Entity):
    def __init__(self, scene: "Scene"):
        super().__init__(
            scene,
            pygame.Vector2(100, 100),
        )

        self.velocity = pygame.Vector2(0)

    def update(self):
        linear_acceleration = 13_000 * self.engine.dt

        key_dir = pygame.Vector2()

        if self.engine.input.key_held("d"):
            key_dir.x = 1

        if self.engine.input.key_held("a"):
            key_dir.x = -1

        if self.engine.input.key_held("w"):
            key_dir.y = -1

        if self.engine.input.key_held("s"):
            key_dir.y = 1

        if key_dir.length_squared() > 0:
            key_dir = key_dir.normalize()
            self.velocity += key_dir * linear_acceleration

        left_axis = self.engine.input.get_stick()
        self.velocity += left_axis * linear_acceleration

        self.velocity *= 1 / (1 + (self.engine.dt * 25))
        self.position += self.velocity * self.engine.dt

    def render_before(self):
        pygame.draw.circle(self.engine.display, (255, 255, 255), self.position, 18, 1)
        pygame.draw.circle(self.engine.display, (97, 255, 18), self.position, 6, 0)


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

        self.static = static
        self.body = body
        self.shape = shape

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
        pos = pygame.Vector2(self.body.position.x, self.body.position.y) * 10
        border = pygame.Rect(50, 50, self.engine.window_width - 100, self.engine.window_height - 100)

        if not border.collidepoint(pos):
            self.kill()
            self.scene.space.remove(self.body, self.shape)

    def render_before(self):
        if self.static:
            color = (134, 179, 161)
        else:
            if self.body.is_sleeping:
                color = (218, 184, 255)
            else:
                color = (255, 255, 255)

        if isinstance(self.shape, pymunk.Poly):
            points = []
            for v in self.shape.get_vertices():
                p = v.rotated(self.body.angle) + self.body.position
                points.append((p.x * 10.0, (p.y) * 10.0))

            if self.scene.debug_drawing:
                pygame.draw.polygon(self.engine.display, color, points, 1)

            else:
                pygame.draw.polygon(self.engine.display, color, points, 0)

        elif isinstance(self.shape, pymunk.Circle):
            if self.scene.debug_drawing:
                pygame.draw.circle(self.engine.display, color, self.body.position * 10.0, self.shape.radius * 10.0, 1)

            else:
                t = 10 / self.scene.res
                r = self.shape.radius * t
                radius = r if r > 2.0 else 2.0

                v = pygame.Vector2(self.body.velocity[0], self.body.velocity[1]).length() / 20.0
                if v > 1.0: v = 1.0
                start_color = pygame.Color(29, 95, 219)
                end_color = pygame.Color(71, 206, 255)
                color = start_color.lerp(end_color, v)

                pygame.draw.circle(self.scene.lowres, color, self.body.position * t, radius, 0)


class Game(Scene):
    def __init__(self, engine: "Engine"):
        super().__init__(engine)

        self.engine.window_title = "PGCS Spring Jam 2024"

        self.space = pymunk.Space()
        self.space.iterations = 10
        self.space.sleep_time_threshold = 3.0
        self.space.gravity = (0.0, 20.0)
        self.sim_hz = 1.0 / 60.0
        self.step_time = 0.0

        self.debug_drawing = False

        #self.player = Player(self)

        self.drawing = False
        self.drawing_start = pygame.Vector2()
        self.drawing_end = pygame.Vector2()

        self.res = 7.0
        self.lowres = pygame.Surface(
            (self.engine.window_width / self.res, self.engine.window_height / self.res),
            pygame.SRCALPHA
        ).convert_alpha()

    def update(self):
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

            for _ in range(6):
                r = pygame.Vector2(uniform(-1.0, 1.0), uniform(-1.0, 1.0))
                pos = self.engine.input.mouse / 10.0 + r
                b = RigidBody.from_circle(self, pos, 0.7, restitution=0.85, friction=0.0, static=False)
                b.body.velocity = pymunk.Vec2d(v.x, v.y)

        step_time_start = perf_counter()
        self.space.step(self.sim_hz)
        self.step_time = perf_counter() - step_time_start

    def render_before(self):
        blur = pygame.transform.gaussian_blur(self.lowres, 2)

        scaled = pygame.transform.smoothscale_by(blur, (self.res, self.res))

        t = 35
        arr = pygame.surfarray.pixels_alpha(scaled)
        arr[arr >= t] = 255
        arr[arr < t] = 0
        del arr

        #scaled = pygame.transform.scale_by(self.lowres, self.res)
        self.engine.display.blit(scaled, (0, 0))

        self.lowres.fill((255, 255, 255, 0))

    def render_after(self):
        if self.drawing:
            pygame.draw.line(self.engine.display, (255, 255, 255), self.drawing_start, self.engine.input.mouse)

        font = self.engine.asset_manager.get_font("FiraCode-Bold", 12)

        draw_shadow_text(
            self.engine.display,
            font,
            f"Physics Debug",
            (350, 5 + 14 * 0),
            (255, 255, 255)
        )

        draw_shadow_text(
            self.engine.display,
            font,
            f"Step: {round(self.step_time * 1000, 2)}ms",
            (350, 5 + 14 * 1),
            (255, 255, 255)
        )

        draw_shadow_text(
            self.engine.display,
            font,
            f"Bodies: {len(self.space.bodies)}",
            (350, 5 + 14 * 2),
            (255, 255, 255)
        )