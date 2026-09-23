import numpy as np
from OpenGL.GL import *


def loadMesh(filename: str) -> list[float]:
    """Load an OBJ file into a flat vertex list (position, uv, normal)."""

    v = []
    vt = []
    vn = []

    vertices = []

    with open(filename) as file:
        line = file.readline()

        while line:
            words = line.split(" ")
            match words[0]:
                case "v":
                    v.append(read_vertex_data(words))

                case "vt":
                    vt.append(read_texcoord_data(words))

                case "vn":
                    vn.append(read_normal_data(words))

                case "f":
                    read_face_data(words, v, vt, vn, vertices)

            line = file.readline()

    return vertices


def read_vertex_data(words: list[str]) -> list[float]:
    return [float(words[1]), float(words[2]), float(words[3])]


def read_texcoord_data(words: list[str]) -> list[float]:
    return [float(words[1]), float(words[2])]


def read_normal_data(words: list[str]) -> list[float]:
    return [float(words[1]), float(words[2]), float(words[3])]


def read_face_data(
    words: list[str],
    v: list[list[float]],
    vt: list[list[float]],
    vn: list[list[float]],
    vertices: list[float],
) -> None:
    """Triangulate one OBJ face into the vertex list."""

    triangleCount = len(words) - 3

    for i in range(triangleCount):
        make_corner(words[1], v, vt, vn, vertices)
        make_corner(words[2 + i], v, vt, vn, vertices)
        make_corner(words[3 + i], v, vt, vn, vertices)


def make_corner(
    corner_description: str,
    v: list[list[float]],
    vt: list[list[float]],
    vn: list[list[float]],
    vertices: list[float],
) -> None:
    """Append one corner: position, uv, normal."""

    v_vt_vn = corner_description.split("/")

    for element in v[int(v_vt_vn[0]) - 1]:
        vertices.append(element)
    for element in vt[int(v_vt_vn[1]) - 1]:
        vertices.append(element)
    for element in vn[int(v_vt_vn[2]) - 1]:
        vertices.append(element)


class Mesh:
    """OBJ mesh ready to draw."""

    def __init__(self, filename: str):

        # x, y, z, s, t, nx, ny, nz
        vertices = loadMesh(filename)
        self.vertex_count = len(vertices) // 8
        vertices = np.array(vertices, dtype=np.float32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        # Vertices
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        # position
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(0))
        # texture
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(12))

    def arm_for_drawing(self) -> None:
        """Bind the vertex array."""
        glBindVertexArray(self.vao)

    def draw(self) -> None:

        glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)

    def destroy(self) -> None:
        """Delete the GL buffers."""

        glDeleteVertexArrays(1, (self.vao,))
        glDeleteBuffers(1, (self.vbo,))
