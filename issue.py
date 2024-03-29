import pygame
import moderngl
import array

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
MAX_FPS = 165

PARTICLE_SIZE = 1.5
MAX_PARTICLES = 5000

pygame.init()
window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
clock = pygame.Clock()
is_running = True

context = moderngl.create_context()
context.enable(moderngl.BLEND)

particle_shader =context.program(
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
particle_shader["u_resolution"] = (WINDOW_WIDTH, WINDOW_HEIGHT)
size = PARTICLE_SIZE * 2.0 * 10.0
particle_shader["u_size"] = (size, size)

# 2 floats (4 bytes)
particle_stride = 2 * 4
particle_vbo = context.buffer(reserve=MAX_PARTICLES * particle_stride)

particle_vao = context.vertex_array(
    particle_shader,
    (
        particle_vbo.bind("in_position", layout="2f"),
    )
)

particles = []

while is_running:
    dt = clock.tick(MAX_FPS) / 1000

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_running = False

    mouse = pygame.Vector2(*pygame.mouse.get_pos())

    if pygame.mouse.get_pressed()[0]:
        particles.append((mouse.x, WINDOW_HEIGHT - mouse.y))

    # Update particle vertex buffer
    particle_vbo.clear()
    for i in range(len(particles)):
        particle_vbo.write(
            array.array("f", particles[i]),
            offset=i * particle_stride
        )

    context.clear()

    # Even though the vertex buffer is empty, it still generates geometry and renders!
    particle_vao.render(moderngl.POINTS)

    pygame.display.flip()

pygame.quit()