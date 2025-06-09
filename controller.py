# pylint: disable=import-error
from utime import sleep_ms
from machine import I2C, Pin
from usb.device.mouse import MouseInterface
from usb.device.keyboard import KeyboardInterface, KeyCode

import usb.device

from gyro import mpu9250
from rfid import mfrc522
from display import ssd1306
from ir import hx1838

import state
# pylint: enable=import-error

# PIN Constants
SPI_RST = None
SPI_MISO = 0
SPI_CS = 1
SPI_SCK = 2
SPI_MOSI = 3
I2C_SDA = 4
I2C_SCL = 5
IR_SIGNAL = 6

# Scaling constants
GYRO_TO_MOUSE_K = 100.

# Loop delay
LOOP_DELAY_MS = 1

# OLED line limit
OLED_LINE_LIMIT = 5

class Controller:
    """Controller for all sensors and outputs."""
    def __init__(self, eye_list: list[state.EyeMode], disable_hid: bool=False):
        self._eye_by_rfid = {eye.rfid: eye for eye in eye_list}
        self._eye_by_ir = {eye.ir: eye for eye in eye_list if eye.ir is not None}
        self._ordered_eyes = eye_list
        self._eyes_amount = len(eye_list)

        self.i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA))
        print(str(self.i2c.scan()))

        # Gyro, Accel, Magnet, Temp
        self.mpu9250 = mpu9250.BiasedMPU9250(self.i2c)

        # RFID
        self.mfrc522 = mfrc522.MFRC522(sck=SPI_SCK, miso=SPI_MISO, mosi=SPI_MOSI, cs=SPI_CS, rst=SPI_RST)

        # OLED
        self.ssd1306 = ssd1306.SSD1306_I2C(self.i2c)

        # IR receiver
        self.hx1838 = hx1838.HX1838(Pin(IR_SIGNAL), self._ir_callback)

        # Keyboard
        self.keyboard = KeyboardInterface()

        # Mouse
        self.mouse = MouseInterface()

        # On-board LED
        self.led = Pin("LED", Pin.OUT)

        # System state
        self.state = state.SystemState(eye_list[0])

        self._disable_hid = disable_hid

    def _change_selected_eye(self, delta: int):
        self.state.ordered_selection_idx += delta
        self.state.ordered_selection_idx %= self._eyes_amount

    def _ir_callback(self, data: int, _addr, _ctrl):
        if data < 0:  # NEC protocol sends repeat codes.
            return

        if next_eye := self._eye_by_ir.get(data):
            print(f"[IR  ] Set next eye = {next_eye.name}")
            self.state.next_eye = next_eye
            return

        if data == 0x45: # Power
            print("[IR  ] Power")
            return

        if data == 0x47: # Lightning
            print("[IR  ] Lightning")
            return

        if data == 0x40: # Up
            print("[IR  ] Up")
            return

        if data == 0x19: # Down
            print("[IR  ] Down")
            return

        if data == 0x07: # Left
            print("[IR  ] Left")
            self._change_selected_eye(-1)
            return

        if data == 0x09: # Right
            print("[IR  ] Right")
            self._change_selected_eye(1)
            return

        if data == 0x15: # Enter
            print("[IR  ] Confirm")
            self.state.next_eye = self._ordered_eyes[self.state.ordered_selection_idx]
            return

        print(f"[IR  ] Unknown cmd 0x{data:02X}")

    def _flash(self, duration: int):
        print(f'[CTRL] flash {duration}ms')
        self.led.on()
        sleep_ms(duration)
        self.led.off()
        sleep_ms(duration)

    def _display_text(self, text: str, line: int, x: int=30, show: bool=True):
        print(f'[DISP] ({line}) {text}')
        self.ssd1306.text(text, x, 10*line)
        if show:
            self.ssd1306.show()

    def _typewrite_text(self, text: str, x: int=30, show: bool=True):
        self._display_text(text, self.state.display_line, x=x, show=show)
        self.state.display_line += 1
        self.state.display_line %= OLED_LINE_LIMIT

    def _send_single_key(self, key: KeyCode, down: int=60, up: int=100):
        self.keyboard.send_keys([key])
        sleep_ms(down)
        self.keyboard.send_keys([])
        sleep_ms(up)

    def _initialize(self):
        # Flash
        self._flash(300)

        # Clear display
        self.ssd1306.fill(0)
        self._typewrite_text('Initialize')

        # Initialize HID
        if not self._disable_hid:
            usb.device.get().init(self.keyboard, self.mouse, builtin_driver=True)

            while not self.keyboard.is_open():
                sleep_ms(100)
            self._typewrite_text('Keyboard OK')

            while not self.mouse.is_open():
                sleep_ms(100)
            self._typewrite_text('Mouse OK')

        # Gyro calibration
        self._typewrite_text('Calibrate...')
        self.mpu9250.calibrate(100)
        self._typewrite_text('Done!')
        print(f'bias={self.mpu9250.calibration})')
        print(f'std={self.mpu9250.calibration_deviation})')

        # Flash 3x
        self._flash(300)
        self._flash(300)
        self._flash(300)

    def _input_data(self):
        self.state.gyro = self.mpu9250.gyro
        print(f'[GYRO] {self.state.gyro}')
        self.state.magnet = self.mpu9250.magnetic
        self.state.rfid = self.mfrc522.tag

    def _process_data(self):
        # RFID data
        if tag := self.state.rfid:
            if rfid_eye := self._eye_by_rfid.get(tag):
                print(f'[CTRL] New eye {rfid_eye.name}')
                self.state.next_eye = rfid_eye
            else:
                print(f'[CTRL] Unknown tag {tag}')

        # Gyro data
        mouse_state_x = int(self.state.gyro[2] * GYRO_TO_MOUSE_K)
        mouse_state_y = int(self.state.gyro[0] * GYRO_TO_MOUSE_K)
        self.state.mouse = (mouse_state_x, mouse_state_y)

        # Magnet data
        # ...

    def _output_data(self):
        if not self._disable_hid:
            # Send keyboard
            if self.state.next_eye is not None:
                self._send_single_key(self.state.next_eye.key)

            # Send mouse
            mx, my = self.state.mouse
            if mx != 0 or my != 0:
                self.mouse.move_by(mx, my)

        # Update current eye
        if self.state.next_eye:
            self.state.current_eye = self.state.next_eye
            self.state.next_eye = None
            self.state.ordered_selection_idx = self.state.current_eye.pos

        current_selecting_eye = self._ordered_eyes[self.state.ordered_selection_idx]

        # Update display
        # TODO temporary only (add arrows for gyro/mouse, separate line for state.selecting_eye)
        self.ssd1306.fill(0)
        self.state.display_line = 1
        self._typewrite_text(self.state.current_eye.name, show=False)
        self._typewrite_text(f'> {current_selecting_eye.name}', show=False)
        self._typewrite_text(f'MX: {self.state.mouse[0]}', show=False)
        self._typewrite_text(f'MY: {self.state.mouse[1]}')

    def main_loop(self):
        try:
            self._initialize()

            sleep_ms(1000)

            while True:

                # Collect sensor data
                self._input_data()

                # Process sensor data
                self._process_data()

                # Output data
                self._output_data()

                # Sleep
                sleep_ms(LOOP_DELAY_MS)

        except KeyboardInterrupt:
            print('Exit')
            self.ssd1306.fill(0)
            self.ssd1306.show()
            self.hx1838.close()
