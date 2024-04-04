from typing import TYPE_CHECKING, Optional

from time import perf_counter, time
from math import pi, atan2, degrees, radians
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
        self.icecube_size = 0

        if isinstance(self.shape, pymunk.Circle):
            self.scene.particles.append(self)

        self.window_ratio = self.engine.window_width / 1280

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
        width, height = size[0] / 2.0, size[1] / 2.0

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
        self.position = self.phypos * 10.0 * self.window_ratio
        border = pygame.Rect(0, 0, self.engine.window_width, self.engine.window_height)

        if not border.collidepoint(self.position):
            self.kill()
            self.scene.space.remove(self.body, self.shape)
            if isinstance(self.shape, pymunk.Circle): self.scene.particles.remove(self)
            else: self.scene.icecubes.remove(self)

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
                    points.append((p.x * 10.0 * self.window_ratio, (p.y) * 10.0 * self.window_ratio))

                pygame.draw.polygon(self.engine.display, (134, 179, 161), points, 0)
                pygame.draw.polygon(self.engine.display, (0, 0, 0), points, 2)

            else:
                pygame.draw.circle(self.engine.display, (0, 0, 0), self.position, self.shape.radius * 10.0 * self.window_ratio, 1)
        

        else:
            if self in self.scene.icecubes:
                if self.icecube_size == 0:
                    surf = self.scene.icecube1
                elif self.icecube_size == 1:
                    surf = self.scene.icecube0
                rotated = pygame.transform.rotate(surf, degrees(-self.body.angle))
                self.engine.display.blit(rotated, rotated.get_rect(center=self.position))


class Game(Scene):
    def __init__(self, engine: "Engine"):
        super().__init__(engine)

        self.window_ratio = self.engine.window_width / 1920
        self.window_ratio2 = self.engine.window_width / 1280
        self.bg = pygame.transform.smoothscale(
            self.engine.asset_manager.assets["images"]["background"],
            (self.engine.window_width, self.engine.window_height)
        ).convert()

        # today was a good day
        self.icecube0 = pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"]["icecube0"], self.window_ratio)
        self.icecube1 = pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"]["icecube1"], self.window_ratio)

        self.textbox = DurkTextbox(self)
        self.cursor = Cursor(self)
        self.gauge = Gauge(self)

        self.temperature = 0.0
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
        self.drawing_type = 0
        self.drawing_start = pygame.Vector2()
        self.drawing_end = pygame.Vector2()

        self.particle_size = 1.5 / 2.0
        self.max_particles = 5000
        self.particles = []
        self.icecubes = []

        self.water_post = WaterPostProcess(self)

        self.level_imgs = (
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"]["level0"], self.window_ratio),
            pygame.transform.smoothscale_by(self.engine.asset_manager.assets["images"]["level1"], self.window_ratio),
        )
        self.levels = (
            json.load(open(source_path("assets", "levels", "level0.json"))),
            json.load(open(source_path("assets", "levels", "level1.json"))),
        )
        self.current_level = 0

        self.load_level(0)

        self.textbox.show()
        self.textbox.say(0, "Greetings student! I'm Dr. Durk, a thermodynamics and molecular physics professor.", 1.7)
        self.textbox_slide = 0
        self.textbox_slides = (
            (1, "I will be the one to guide you trough the numerous scientific experiments of the day!"),
            (1, "The main control I will allow you to play around with is the temperature of the room."),
            (0, "You can use your mouse wheel to adjust the temperature, you can see the changes on the thermometer gauge."),
            (1, "You can solve the first puzzle by simply melting the ice cube I will throw in a few seconds."),
            (0, "I leave the rest of the puzzles to you, good luck!")
        )

        #self.spawn_icecube(pygame.Vector2(self.engine.scaled_width/2, 40), 1)

        self.score_start = time()

        self.level_change_timer = time()
        self.level_change = False

    def load_level(self, level: int) -> None:
        if "bodies" not in self.levels[level]: return

        for particle in self.particles:
            particle.kill()
            self.space.remove(particle.body, particle.shape)
        self.particles.clear()

        for b in self.icecubes:
            b.kill()
            self.space.remove(b.body, b.shape)
        self.icecubes.clear()

        for e in self.entities:
            if isinstance(e, RigidBody):
                e.kill()
                self.space.remove(e.body, e.shape)
                
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

        self.temperature = 0.0

        if level == 1:
            self.spawn_icecube(pygame.Vector2(self.engine.scaled_width/2 + 23, 40), 0)

    def spawn_icecube(self, position: pygame.Vector2, type_: int) -> None:
        #center = self.engine.input.mouse / 10
        if type_ == 0:
            width, height = 7.5, 7.5
        elif type_ == 1:
            width, height = 16.5, 16.5
        b = RigidBody.from_box(self, position / 10, (width, height), 0, restitution=0.5, friction=0.0, static=False)
        b.icecube_size = type_
        self.icecubes.append(b)

    def spawn_particle(self, position: pygame.Vector2) -> None:
        # r = pygame.Vector2(uniform(-1.0, 1.0), uniform(-1.0, 1.0))
        # pos = self.engine.input.mouse / 10.0 / self.window_ratio2 + r
        # b = RigidBody.from_circle(self, pos, self.particle_size, restitution=0.7, friction=0.0, static=False)
        # b.body.velocity = pymunk.Vec2d(v.x, v.y)

        b = RigidBody.from_circle(self, position, self.particle_size, restitution=0.7, friction=0.0, static=False)

    def melt(self):
        for icecube in self.icecubes:
            points = []
            for v in icecube.shape.get_vertices():
                p = v.rotated(icecube.body.angle) + icecube.body.position
                points.append(p)

            start0 = pygame.Vector2(points[0].x, points[0].y)
            end0 = pygame.Vector2(points[1].x, points[1].y)
            end1 = pygame.Vector2(points[3].x, points[3].y)
            dir = (end0 - start0).normalize()
            dir1 = (end1 - start0).normalize()
            for j in range(round((end1 - start0).length() / (self.particle_size * 2))):
                for i in range(round((end0 - start0).length() / (self.particle_size * 2))):
                    pos = start0 + dir1 * j * (self.particle_size * 2) + dir * i * (self.particle_size * 2)
                    pos.x += uniform(-0.1, 0.1) # This is to avoid perfectly stacking particles
                    self.spawn_particle(pos)

            icecube.kill()
            self.space.remove(icecube.body, icecube.shape)

        self.icecubes.clear()

    # def group_points(points, threshold):
    #     groups = []
    #     while len(points) > 0:
    #         current_point = points.pop()
    #         current_group = [current_point]
    #         i = 0
    #         while i < len(points):
    #             if (current_point.position - points[i].position).length() < threshold:
    #                 current_group.append(points.pop(i))
    #             else:
    #                 i += 1
    #         groups.append(current_group)
    #     return groups

    def freeze(self):pass
        # grouping = []
        # for p in self.particles:
        #     grouping.append(p)

        # groups = self.group_points(grouping, 50)

        # for group in groups:

    def level_clear(self):
        self.level_change = True
        self.level_change_timer = time()

    def update(self):
        if self.engine.input.key_pressed("f2"):
            self.debug_drawing = not self.debug_drawing

        if self.engine.input.mouse_wheel_up() or self.engine.input.key_pressed("up"):
            self.temperature += 10.0
            if self.temperature > self.temp_max:
                self.temperature = self.temp_max

            if self.temperature > 10.1:
                self.melt()

                if self.current_level == 0 and not self.textbox.visible:
                    self.level_clear()

        if self.engine.input.mouse_wheel_down() or self.engine.input.key_pressed("down"):
            self.temperature -= 10.0
            if self.temperature < self.temp_min:
                self.temperature = self.temp_min

            if self.temperature < 10.1:
                self.freeze()

        # if self.engine.input.key_held("lshift"):
        #     if self.engine.input.mouse_pressed("left"):
        #         self.drawing = True
        #         self.drawing_type = 0
        #         self.drawing_start = self.engine.input.mouse.copy()

        #     elif self.engine.input.mouse_pressed("right"):
        #         self.drawing = True
        #         self.drawing_type = 1
        #         self.drawing_start = self.engine.input.mouse.copy()

        if self.engine.input.mouse_released("left") or self.engine.input.mouse_released("right"):
            if self.drawing:
                self.drawing = False
                self.drawing_end = self.engine.input.mouse.copy()

                e = 0.7
                u = 0.0

                if self.drawing_type == 0:
                    delta = (self.drawing_end - self.drawing_start) / 10.0
                    position = self.drawing_start / 10 + delta / 2.0
                    angle = atan2(delta.y, delta.x)

                    b = RigidBody.from_box(self, position, (delta.length(), 2.0), angle, restitution=e, friction=u, static=True)
                    b.z_index = 1

                elif self.drawing_type == 1:
                    width = (self.drawing_end.x - self.drawing_start.x) / 10
                    height = (self.drawing_end.y - self.drawing_start.y) / 10
                    center = (self.drawing_start + self.drawing_end) / 20

                    b = RigidBody.from_box(self, center, (width, height), 0, restitution=e, friction=u, static=True)
                    b.z_index = 1

        if (self.engine.input.key_pressed("space") or self.engine.input.key_pressed("return")) and self.textbox.done and self.textbox.visible:
            
            if self.textbox_slide == len(self.textbox_slides):
                self.textbox.hide()
                self.temperature = 0
                self.spawn_icecube(pygame.Vector2(self.engine.scaled_width/2, 40), 1)
            
            else:
                self.textbox.say(self.textbox_slides[self.textbox_slide][0], self.textbox_slides[self.textbox_slide][1])
                self.textbox_slide += 1

        if self.engine.input.key_pressed("r") and self.current_level > 0:
            self.load_level(self.current_level)

        if self.engine.input.key_held("q"):
            v = self.engine.input.mouse_rel * 3.0

            for _ in range(3):
                r = pygame.Vector2(uniform(-1.0, 1.0), uniform(-1.0, 1.0))
                pos = self.engine.input.mouse / 10.0 / self.window_ratio2 + r
                b = RigidBody.from_circle(self, pos, self.particle_size, restitution=0.7, friction=0.0, static=False)
                b.body.velocity = pymunk.Vec2d(v.x, v.y)

        if self.level_change:
            if time() - self.level_change_timer > 3.0:
                self.current_level += 1
                self.load_level(self.current_level)
                self.level_change = False

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
        self.engine.display.blit(self.level_imgs[self.current_level], (0, 0))

    def render_after(self):
        if self.drawing:
            if self.drawing_type == 0:
                pygame.draw.line(self.engine.display, (255, 255, 255), self.drawing_start, self.engine.input.mouse)

            elif self.drawing_type == 1:
                width = self.engine.input.mouse.x - self.drawing_start.x
                height = self.engine.input.mouse.y - self.drawing_start.y
                pygame.draw.rect(self.engine.display, (255, 255, 255), (self.drawing_start, (width, height)), 1)

        if self.level_change:
            font = self.engine.asset_manager.get_font("LoveYaLikeASister", 160)
            surf = font.render("Level Clear!", True, (69, 19, 13)).convert_alpha()
            w, h = surf.get_size()
            self.engine.display.blit(surf, (self.engine.scaled_width/2 - w/2, self.engine.scaled_height/2 - h/2))

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
