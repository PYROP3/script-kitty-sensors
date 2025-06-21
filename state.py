# pylint: disable=import-error
from usb.device.keyboard import KeyCode
# pylint: enable=import-error

class EyeMode:
    """Class for eye display mode."""
    def __init__(self, name: str, rfid: str, key: KeyCode, ir: int):
        self.name: str = name
        self.rfid: str = rfid
        self.key: KeyCode = key
        self.ir: int = ir

        self.pos: int = 0

class SystemState:
    """Class to keep track of system state."""
    def __init__(self, initial_eye: EyeMode):
        # IN data
        self.gyro: tuple[float, float, float] = (0., 0., 0.)
        self.magnet: tuple[float, float, float] = (0., 0., 0.)
        self.rfid: str = ''

        # OUT data
        self.mouse: tuple[int, int] = (0, 0)
        # self.keyboard: str = ''

        # Control data
        self.current_eye: EyeMode = initial_eye
        self.next_eye: EyeMode = None
        self.ordered_selection_idx = 0
        self.display_line: int = 0
        self.display_text: list[str] = ['', '', '', '', '', '']
        self.display_updated: bool = False
