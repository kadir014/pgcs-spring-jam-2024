from time import time

import moderngl

from engine import Scene
from engine.gl import BasicScreenQuad


class WaterPostProcess:
    """
    Water post-process effect.

    Rendering Phases:
    -----------------
    1.              2.      3.                4.       5.
    Batch render -> blur -> fake metaballs -> water -> blur water
    """

    def __init__(self, scene: Scene):
        self.scene = scene
        self.engine = scene.engine
        self.window_ratio = self.engine.window_width / 1280

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

// Blur algorithm from: https://www.shadertoy.com/view/Xltfzj

in vec2 v_uv;
out vec4 out_color;

uniform vec2 u_resolution;
uniform sampler2D s_texture;

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
        size = self.scene.particle_size * 2.0 * 10.0 * self.window_ratio
        self.particle_shader["u_size"] = (size, size)

        # 2 floats (4 bytes)
        self.particle_stride = 2 * 4
        self.particle_vbo = self.engine.context.buffer(reserve=self.scene.max_particles * self.particle_stride)

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

// Water algorithm is taken and slightly edited from: https://www.shadertoy.com/view/4slGRM

in vec2 v_uv;
out vec4 out_color;

uniform float u_time;
uniform vec2 u_resolution;
uniform sampler2D s_texture0;
uniform sampler2D s_texture1;

#define PI 3.1415926535897932
#define TAU 6.28318530718

// Speed
#define SPEED 0.03
#define SPEED_X 0.075
#define SPEED_Y 0.075

// Refraction (It's better when ANGLE is a prime)
#define EMBOSS 0.40
#define INTENSITY 0.7
#define STEPS 8
#define FREQUENCY 12.0
#define ANGLE 7

// Reflection
#define DELTA 60.0
#define GAIN 700.0
#define REFL_CUTOFF 5.000
#define REFL_INTENSITY 100000.0

// 48, 210, 255
#define WATER_COLOR vec3(0.188, 0.823, 1.0)
#define WATER_MIX 0.1

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

        //vec4 final_col = mix(refl, vec4(WATER_COLOR.bgr, 1.0), WATER_MIX);
        vec4 final_col = refl * vec4(WATER_COLOR.bgr, 1.0);

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

// Blur algorithm from: https://www.shadertoy.com/view/Xltfzj

in vec2 v_uv;
out vec4 out_color;

uniform vec2 u_resolution;
uniform sampler2D s_texture0;
uniform sampler2D s_texture1;

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

        self.time_start = time()

    def render(self):
        # First phase (batch render bodies)
        self.first_fbo.use()
        self.engine.context.clear()

        self.particle_vao.render(moderngl.POINTS, vertices=len(self.scene.particles))

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
        self.engine.final_fbo.use()
        self.engine.context.clear()

        self.blurwater.shader["s_texture0"] = 0
        self.blurwater.shader["s_texture1"] = 1
        self.fourth_fbo.color_attachments[0].use(0)
        self.third_fbo.color_attachments[0].use(1)
        self.blurwater.vao.render()