import numpy as np
import pyrr


class Entity:
    """Position and euler angles, in degrees."""

    def __init__(self, position: list[float], eulers: list[float]):

        self.position = np.array(position, dtype=np.float32)
        self.eulers = np.array(eulers, dtype=np.float32)

    def update(self) -> None:
        pass

    def get_model_transform(self) -> np.ndarray:
        """Model matrix for this entity."""

        # model_transform = pyrr.matrix44.create_identity(dtype=np.float32)

        model_transform = pyrr.matrix44.create_from_eulers(
            np.radians([self.eulers[0], self.eulers[1], 0]), dtype=np.float32
        )

        model_transform = pyrr.matrix44.multiply(
            m1=model_transform,
            m2=pyrr.matrix44.create_from_axis_rotation(
                axis=[0, 1, 0], theta=np.radians(self.eulers[2]), dtype=np.float32
            ),
        )

        # model_transform = pyrr.matrix44.multiply(
        #     m1=model_transform,
        #     m2=pyrr.matrix44.create_from_axis_rotation(
        #         axis = [1, 0, 0],
        #         theta = np.radians(self.eulers[0]),
        #         dtype = np.float32
        #     )
        # )

        # model_transform += pyrr.matrix44.multiply(
        #     m1=model_transform,
        #     m2=pyrr.matrix44.create_from_axis_rotation(
        #         axis = [0, 1, 0],
        #         theta = np.radians(self.eulers[1]),
        #         dtype = np.float32
        #     )
        # )

        # model_transform += pyrr.matrix44.multiply(
        #     m1=model_transform,
        #     m2=pyrr.matrix44.create_from_axis_rotation(
        #         axis = [0, 0, 1],
        #         theta = np.radians(self.eulers[2]),
        #         dtype = np.float32
        #     )
        # )
        return pyrr.matrix44.multiply(
            m1=model_transform,
            m2=pyrr.matrix44.create_from_translation(vec=np.array(self.position), dtype=np.float32),
        )
