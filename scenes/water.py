from typing import TYPE_CHECKING

from time import perf_counter, time
from math import pi, atan2
from random import uniform
import array
import struct

import pygame
import pymunk
import moderngl

from engine import Scene, Entity
from engine.draw import draw_shadow_text

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
        if isinstance(self.shape, pymunk.Poly):
            points = []
            for v in self.shape.get_vertices():
                p = v.rotated(self.body.angle) + self.body.position
                points.append((p.x * 10.0, (p.y) * 10.0))

            pygame.draw.polygon(self.engine.display, (134, 179, 161), points, 0)


class BasicScreenQuad:
    def __init__(
            self,
            engine: "Engine",
            vertex_shader: str,
            fragment_shader: str
            ) -> None:
        self.engine = engine
        self.shader = self.engine.context.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

        self.vbo = self.engine.context.buffer(
            array.array("f", [
                1.0,  1.0,
                1.0, -1.0,
                -1.0, -1.0,
                -1.0,  1.0,
            ])
        )

        self.ibo = self.engine.context.buffer(
            array.array("i", [
                0, 1, 3,
                1, 2, 3
            ])
        )

        self.uvbo = self.engine.context.buffer(
            array.array("f", [
                1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0
            ])
        )

        self.vao = self.engine.context.vertex_array(
            self.shader,
            (
                self.vbo.bind("in_position", layout="2f"),
                self.uvbo.bind("in_uv", layout="2f")
            ),
            index_buffer=self.ibo
        )


class Game(Scene):
    def __init__(self, engine: "Engine"):
        super().__init__(engine)

        self.engine.window_title = "PGCS Spring Jam 2024"
        self.time_start = time()

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

        self.blur = BasicScreenQuad(
            self.engine,
            vertex_shader=
"""
#version 330
in vec2 in_position;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    v_uv = vec2(in_uv.x, in_uv.y);
}
""",
            fragment_shader=
"""
#version 330

in vec2 v_uv;
out vec4 out_color;

uniform vec2 u_resolution;
uniform sampler2D s_texture;

// Blur algorithm from https://www.shadertoy.com/view/Xltfzj
#define TAU 6.28318530718
#define DIRS 24.0   // Blur directions
#define QUALITY 3.0 // Blur quality
#define SIZE 12.0    // Blur size

void main() {
    vec2 radius = SIZE / u_resolution;

    vec4 color = texture(s_texture, v_uv);

    float inv_quality = 1.0 / QUALITY;

    for (float d = 0.0; d < TAU; d += TAU / DIRS) {
        for(float i = inv_quality; i <= 1.0; i += inv_quality) {
            color += texture(s_texture, v_uv + vec2(cos(d), sin(d)) * radius * i);		
        }
    }

    color /= QUALITY * DIRS - 15.0;
    out_color = color;
}
"""
        )
        self.blur.shader["u_resolution"] = (self.engine.window_width, self.engine.window_height)

        self.particle_shader = self.engine.context.program(
            vertex_shader=
"""
#version 330
in vec2 in_position;
uniform vec2 u_resolution;
void main() {
    // Map coordinates inside display
    vec2 pos = vec2(
        (in_position.x / u_resolution.x - 0.5) * 2.0,
        (in_position.y / u_resolution.y - 0.5) * 2.0
    );
    gl_Position = vec4(pos, 0.0, 1.0);
}
""",
            fragment_shader=
"""
#version 330
in vec2 g_uv;
out vec4 out_color;
uniform sampler2D s_texture;
void main() {
    //out_color = texture(s_texture, g_uv);
    //out_color = vec4(1.0);
    vec3 color;
    if (distance(g_uv, vec2(0.5, 0.5)) < 0.5)
        out_color = vec4(1.0, 1.0, 1.0, 1.0);
    else
        out_color = vec4(0.0, 0.0, 0.0, 0.0);
}
""",
            geometry_shader=
"""
#version 330
layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

out vec2 g_uv;

uniform vec2 u_resolution;
uniform vec2 u_size;

void main() {
    float w = u_size.x / u_resolution.x;
    float h = u_size.y / u_resolution.y;
    gl_Position = gl_in[0].gl_Position + vec4(-w, -h, 0.0, 0.0);
    g_uv = vec2(0.0, 1.0);
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4(w, -h, 0.0, 0.0);
    g_uv = vec2(1.0, 1.0);
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4(-w,  h, 0.0, 0.0);
    g_uv = vec2(0.0, 0.0);
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4(w,  h, 0.0, 0.0);
    g_uv = vec2(1.0, 0.0);
    EmitVertex();
    
    EndPrimitive();
}
"""
        )
        self.particle_shader["u_resolution"] = (self.engine.window_width, self.engine.window_height)
        size = self.particle_size * 2.0 * 10.0
        self.particle_shader["u_size"] = (size, size)

        # 2 floats (4 bytes)
        self.particle_stride = 2 * 4
        self.particle_vbo = self.engine.context.buffer(reserve=self.max_particles * self.particle_stride)

        self.particle_vao = self.engine.context.vertex_array(
            self.particle_shader,
            (
                self.particle_vbo.bind("in_position", layout="2f"),
            )
        )

        self.second_phase = BasicScreenQuad(
            self.engine,
            vertex_shader=
"""
#version 330
in vec2 in_position;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    v_uv = vec2(in_uv.x, in_uv.y);
}
""",
            fragment_shader=
"""
#version 330

in vec2 v_uv;
out vec4 out_color;

uniform sampler2D s_texture;

#define THRESHOLD 0.2

void main() {
    vec4 color = texture(s_texture, v_uv);

    vec3 bottom = vec3(24.0 / 255.0, 37.0 / 255.0, 217.0 / 255.0);
    vec3 top = vec3(92.0 / 255.0, 138.0 / 255.0, 1.0);

    if (color.a <= THRESHOLD)
        out_color = vec4(0.0);
    else {
        //vec3 c = bottom * (1.0 - v_uv.y) + top * v_uv.y;
        vec3 c = vec3(1.0);
        out_color = vec4(c, 1.0);
    }
}
"""
        )

        self.water = BasicScreenQuad(
            self.engine,
            vertex_shader=
"""
#version 330
in vec2 in_position;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    v_uv = vec2(in_uv.x, in_uv.y);
}
""",
            fragment_shader=
"""
#version 330

in vec2 v_uv;
out vec4 out_color;

uniform float u_time;
uniform vec2 u_resolution;
uniform sampler2D s_texture0;
uniform sampler2D s_texture1;

// Water algorithm is taken and slightly edited from https://www.shadertoy.com/view/4slGRM

#define PI 3.1415926535897932
#define TAU 6.28318530718

// Speed
#define SPEED 0.05
#define SPEED_X 0.075
#define SPEED_Y 0.075

// Refraction (It's better when ANGLE is a prime)
#define EMBOSS 0.50
#define INTENSITY 1.6
#define STEPS 8
#define FREQUENCY 12.0
#define ANGLE 7

// Reflection
#define DELTA 60.0
#define GAIN 700.0
#define REFL_CUTOFF 0.012
#define REFL_INTENSITY 200000.0

#define WATER_COLOR vec3(36.0 / 255.0, 233.0 / 255.0, 255.0 / 255.0)

float col(vec2 coord, float time) {
    float delta_theta = 2.0 * PI / float(ANGLE);
    float col = 0.0;
    float theta = 0.0;

    for (int i = 0; i < STEPS; i++) {
        vec2 adjc = coord;
        theta = delta_theta * float(i);
        adjc.x += cos(theta) * time * SPEED + time * SPEED_X;
        adjc.y -= sin(theta) * time * SPEED - time * SPEED_Y;
        col = col + cos((adjc.x * cos(theta) - adjc.y * sin(theta)) * FREQUENCY) * INTENSITY;
    }

    return cos(col);
}

void main() {
    vec4 frag0 = texture(s_texture0, v_uv);

    if (frag0.r == 1.0) {
        vec2 p = vec2(v_uv.x, 1.0 - v_uv.y);
        vec2 c1 = p;
        vec2 c2 = p;
        float cc1 = col(c1, u_time);

        c2.x += u_resolution.x / DELTA;
        float dx = EMBOSS * (cc1 - col(c2, u_time)) / DELTA;

        c2.x = p.x;
        c2.y += u_resolution.y / DELTA;
        float dy = EMBOSS * (cc1 - col(c2, u_time)) / DELTA;

        c1.x += dx * 2.0;
        c1.y = -(c1.y + dy * 2.0);

        float alpha = 1.0 + dot(dx, dy) * GAIN;

        float ddx = dx - REFL_CUTOFF;
        float ddy = dy - REFL_CUTOFF;
        if (ddx > 0.0 && ddy > 0.0)
            alpha = pow(alpha, ddx * ddy * REFL_INTENSITY);

        vec4 frag1 = texture(s_texture1, c1);

        vec4 refl = frag1 * (alpha);

        vec4 final_col = mix(refl, vec4(WATER_COLOR, 1.0), 0.09);

        float inv_quality = 1.0/3.0;
        float radius = 0.0035;
        float DIRS = 16.0;
    
        for (float d = 0.0; d < TAU; d += TAU / DIRS) {
            for(float i = inv_quality; i <= 1.0; i += inv_quality) {
                if (texture(s_texture0, v_uv + vec2(cos(d), sin(d)) * radius * i).r == 0.0) final_col *= 5.0;
            }
        }

        out_color = final_col;
    }
    else {
        out_color = texture(s_texture1, v_uv);
    }
}
"""
        )
        self.water.shader["u_resolution"] = (self.engine.window_width, self.engine.window_height)

        self.blurwater = BasicScreenQuad(
            self.engine,
            vertex_shader=
"""
#version 330
in vec2 in_position;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    v_uv = vec2(in_uv.x, 1.0 - in_uv.y);
}
""",
            fragment_shader=
"""
#version 330

in vec2 v_uv;
out vec4 out_color;

uniform vec2 u_resolution;
uniform sampler2D s_texture0;
uniform sampler2D s_texture1;

// Blur algorithm from https://www.shadertoy.com/view/Xltfzj
#define TAU 6.28318530718
#define DIRS 24.0   // Blur directions
#define QUALITY 8.0 // Blur quality
#define SIZE 4.0    // Blur size

void main() {
    vec2 uv = v_uv;

    if (texture(s_texture1, uv).r == 1.0) {
        vec2 radius = SIZE / u_resolution;

        vec4 color = texture(s_texture0, uv);

        float inv_quality = 1.0 / QUALITY;

        for (float d = 0.0; d < TAU; d += TAU / DIRS) {
            for(float i = inv_quality; i <= 1.0; i += inv_quality) {
                color += texture(s_texture0, uv + vec2(cos(d), sin(d)) * radius * i);
            }
        }

        color /= QUALITY * DIRS - 15.0;
        out_color = color.bgra;
    }

    else {
        out_color = texture(s_texture0, uv).bgra;
    }
}
"""
        )
        self.blurwater.shader["u_resolution"] = (self.engine.window_width, self.engine.window_height)

        self.first_fbo = self.engine.context.framebuffer(
            color_attachments=self.engine.context.texture((self.engine.window_width, self.engine.window_height), 4)
        )
        self.first_fbo.color_attachments[0].repeat_x = False
        self.first_fbo.color_attachments[0].repeat_y = False

        self.second_fbo = self.engine.context.framebuffer(
            color_attachments=self.engine.context.texture((self.engine.window_width, self.engine.window_height), 4)
        )
        self.second_fbo.color_attachments[0].repeat_x = False
        self.second_fbo.color_attachments[0].repeat_y = False

        self.third_fbo = self.engine.context.framebuffer(
            color_attachments=self.engine.context.texture((self.engine.window_width, self.engine.window_height), 4)
        )
        self.third_fbo.color_attachments[0].repeat_x = False
        self.third_fbo.color_attachments[0].repeat_y = False

        self.fourth_fbo = self.engine.context.framebuffer(
            color_attachments=self.engine.context.texture((self.engine.window_width, self.engine.window_height), 4)
        )
        self.fourth_fbo.color_attachments[0].repeat_x = False
        self.fourth_fbo.color_attachments[0].repeat_y = False

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
        bg = self.engine.asset_manager.assets["images"]["debug"]
        self.engine.display.blit(bg, (0, 0))

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

    def render_post(self):
        # Update particles buffer
        self.particle_vbo.clear()
        for i, body in enumerate(self.entities):
            if isinstance(body, RigidBody) and isinstance(body.shape, pymunk.Circle):
                self.particle_vbo.write(
                    array.array("f", (body.body.position.x * 10.0, body.body.position.y * 10.0)),
                    offset=(i+1) * self.particle_stride
                )

        # Phases:
        # 1.              2.      3.                4.       5.
        # Batch render -> blur -> fake metaballs -> water -> blur water

        # First phase (batch render bodies)
        self.first_fbo.use()
        self.engine.context.clear()

        self.particle_vao.render(moderngl.POINTS)

        # Second phase (blur)
        self.second_fbo.use()
        self.engine.context.clear()

        self.first_fbo.color_attachments[0].use()
        self.blur.vao.render()

        # Third phase (fake metaballs by cutting off threshold)
        self.third_fbo.use()
        self.engine.context.clear()

        self.second_fbo.color_attachments[0].use()
        self.second_phase.vao.render()

        # Fourth phase (water)
        self.fourth_fbo.use()
        self.engine.context.clear()

        self.water.shader["s_texture0"] = 0
        self.water.shader["s_texture1"] = 1
        self.water.shader["u_time"] = time() - self.time_start
        self.third_fbo.color_attachments[0].use(0)
        self.engine.display_tex.use(1)
        self.water.vao.render()

        # Fifth phase (blur water)
        self.engine.context.screen.use()
        self.engine.context.clear()

        self.blurwater.shader["s_texture0"] = 0
        self.blurwater.shader["s_texture1"] = 1
        self.fourth_fbo.color_attachments[0].use(0)
        self.third_fbo.color_attachments[0].use(1)
        self.blurwater.vao.render()
