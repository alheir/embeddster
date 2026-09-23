import os

import numpy as np
import pyrr
from OpenGL.GL import *
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from src.package.Entity import Entity
from src.package.Material import Material
from src.package.Mesh import Mesh
from src.package.OpenGLUtils import create_shader
from src.package.Station import DEFAULT_GROUP_COUNT, MAX_GROUP_COUNT

# Original fixed layout. Model size stays at this framing; other counts are recentered.
FRAME_GROUPS = DEFAULT_GROUP_COUNT


class FrdmViewerWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.base_dir = os.path.dirname(__file__)
        self.group_count = DEFAULT_GROUP_COUNT
        self.stations = []
        self.stations_mesh = []
        self.stations_active = [False] * MAX_GROUP_COUNT
        self.modelIndex = 0
        self.theme = "light"
        self._gl_ready = False

    def initializeGL(self) -> None:
        for _ in range(MAX_GROUP_COUNT):
            self.stations.append(Entity(position=[0, 0, -100], eulers=[0, 0, 90]))
            self.stations_mesh.append(
                [
                    Mesh(os.path.join(self.base_dir, "..", "models", "frdm.obj")),
                    Mesh(os.path.join(self.base_dir, "..", "models", "plane.obj")),
                ]
            )

        self.enabled_texture = [
            Material(os.path.join(self.base_dir, "..", "models", "frdm_en.png")),
            Material(os.path.join(self.base_dir, "..", "models", "plane_en.png")),
        ]

        self.disabled_texture = [
            Material(os.path.join(self.base_dir, "..", "models", "frdm_dis.png")),
            Material(os.path.join(self.base_dir, "..", "models", "plane_dis.png")),
        ]

        self.shader = create_shader(
            vertex_filepath=os.path.join(self.base_dir, "..", "shaders", "vertex.txt"),
            fragment_filepath=os.path.join(self.base_dir, "..", "shaders", "fragment.txt"),
        )

        glUseProgram(self.shader)
        glUniform1i(glGetUniformLocation(self.shader, "imageTexture"), 0)
        self._layout_stations()
        self._apply_projection()
        self.modelMatrixLocation = glGetUniformLocation(self.shader, "model")
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        self._gl_ready = True

    def paintGL(self):
        for x in range(self.group_count):
            self.stations[x].update()

        if self.theme == "dark":
            glClearColor(0.2, 0.2, 0.2, 1.0)
        else:
            glClearColor(0.941, 0.941, 0.941, 1.0)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.shader)

        for x in range(self.group_count):
            if self.stations_active[x]:
                self.enabled_texture[self.modelIndex].use()
            else:
                self.disabled_texture[self.modelIndex].use()
            glUniformMatrix4fv(
                self.modelMatrixLocation, 1, GL_FALSE, self.stations[x].get_model_transform()
            )
            self.stations_mesh[x][self.modelIndex].arm_for_drawing()
            self.stations_mesh[x][self.modelIndex].draw()

    def set_group_count(self, count: int) -> None:
        self.group_count = count
        if not self._gl_ready:
            return
        for station in self.stations:
            station.eulers = np.array([0, 0, 90], dtype=np.float32)
        self.stations_active = [False] * len(self.stations)
        self._layout_stations()
        self.update()

    def _layout_stations(self) -> None:
        n = max(self.group_count, 1)
        center = -50.0
        origin = center - (n - 1) * 50.0
        for x, station in enumerate(self.stations):
            station.position = np.array([origin + 100 * x, 0, -100], dtype=np.float32)
            if x >= self.group_count:
                self.stations_active[x] = False

    def _apply_projection(self) -> None:
        n = FRAME_GROUPS
        projection = pyrr.matrix44.create_orthogonal_projection(
            left=-n * 100 / 2 - 50,
            right=n * 100 / 2 - 50,
            top=100,
            bottom=-100,
            near=1,
            far=1000,
            dtype=np.float32,
        )
        glUseProgram(self.shader)
        glUniformMatrix4fv(glGetUniformLocation(self.shader, "projection"), 1, GL_FALSE, projection)

    def setOrientation(self, index, x, y, z):
        if not self.stations or index < 0 or index >= self.group_count:
            return
        self.stations[index].eulers = [x, y, z]
        self.stations_active[index] = True
        self.update()

    def setStationInactive(self, index):
        if not self.stations or index < 0 or index >= self.group_count:
            return
        self.stations_active[index] = False
        self.update()

    def setModelIndex(self, index):
        self.modelIndex = index
        self.update()

    def setTheme(self, theme):
        self.theme = theme
        self.update()

    def quit(self) -> None:
        if not self._gl_ready:
            return
        for meshes in self.stations_mesh:
            for mesh in meshes:
                mesh.destroy()
        for material in self.enabled_texture:
            material.destroy()
        for material in self.disabled_texture:
            material.destroy()
        glDeleteProgram(self.shader)
