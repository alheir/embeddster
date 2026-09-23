from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader


def create_shader(vertex_filepath: str, fragment_filepath: str) -> int:
    """Compile a shader program from the vertex and fragment source files."""

    with open(vertex_filepath) as f:
        vertex_src = f.readlines()

    with open(fragment_filepath) as f:
        fragment_src = f.readlines()

    shader = compileProgram(
        compileShader(vertex_src, GL_VERTEX_SHADER), compileShader(fragment_src, GL_FRAGMENT_SHADER)
    )

    return shader
