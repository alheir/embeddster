# LED frames store the group index in 3 bits (0..7).
MIN_GROUP_COUNT = 1
MAX_GROUP_COUNT = 8
DEFAULT_GROUP_COUNT = 7
BASE_CAN_ID = 0x100

STATION_ANGLES = [b"R", b"C", b"O"]
STATION_ANGLES_COUNT = len(STATION_ANGLES)


def clamp_group_count(count: int) -> int:
    return max(MIN_GROUP_COUNT, min(MAX_GROUP_COUNT, int(count)))


def group_can_id(index: int) -> int:
    return BASE_CAN_ID + index


def group_label(index: int) -> str:
    return f"0x{group_can_id(index):03X}"


def group_id_bytes(index: int) -> bytes:
    return str(index).encode("ascii")


class Station:
    def __init__(self, id, roll=0, pitch=0, yaw=0):
        self.id = id
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.angles = [self.roll, self.pitch, self.yaw]

    def resetAngles(self):
        self.roll = 0
        self.pitch = 0
        self.yaw = 0

    def assignAngle(self, angleIdentifier, value):
        try:
            if isinstance(angleIdentifier, bytes):
                angleIndex = STATION_ANGLES.index(angleIdentifier)
            else:
                angleIndex = angleIdentifier
            self.angles[angleIndex] = value
            self.roll = self.angles[0]
            self.pitch = self.angles[1]
            self.yaw = self.angles[2]
            return True

        except ValueError:
            print("Angle not recognized")

        return False
