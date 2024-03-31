from typing import TYPE_CHECKING

import array

if TYPE_CHECKING:
    from .engine import Engine


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