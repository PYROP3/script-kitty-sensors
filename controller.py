# pylint: disable=import-error
import errno

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
OLED_LINE_LIMIT = 6

class Controller:
    """Controller for all sensors and outputs."""
    def __init__(self, eye_list: list[state.EyeMode], disable_hid: bool=False):
        self._eye_by_rfid = {eye.rfid: eye for eye in eye_list}
        self._eye_by_ir = {eye.ir: eye for eye in eye_list if eye.ir is not None}
        self._ordered_eyes = eye_list
        self._eyes_amount = len(eye_list)

        # System state
        self.state = state.SystemState(eye_list[0])

        self._setup()

        self._disable_hid = disable_hid

    def _change_selected_eye(self, delta: int):
        self.state.ordered_selection_idx += delta
        self.state.ordered_selection_idx %= self._eyes_amount

    def _ir_callback(self, data: int, _addr, _ctrl):
        if (not self.state.enable_ir) or (not self.state.enable_keyboard):
            return

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
        if self.ssd1306 is None:
            return
        try:
            self.ssd1306.text(text, x, 10*line)
            self.state.display_updated = True
            if show:
                self.ssd1306.show()
        except Exception as e:
            self.state.last_exception = e
            self.state.last_exception_module = 'oledtext'
            self.state.enable_mouse = False
            raise e

    def _typewrite_text(self, text: str, x: int=30, show: bool=True):
        if self.state.display_text[self.state.display_line] != text:
            self._display_text(text, self.state.display_line, x=x, show=show)
            self.state.display_text[self.state.display_line] = text
        self.state.display_line += 1
        self.state.display_line %= OLED_LINE_LIMIT

    def _clear_display(self, show: bool=True):
        if self.ssd1306 is None:
            return
        try:
            self.ssd1306.fill(0)
            self.state.display_line = 1
            self.state.display_text = ['', '', '', '', '', '']
            if show:
                self.ssd1306.show()
        except Exception as e:
            self.state.last_exception = e
            self.state.last_exception_module = 'oledclear'
            self.state.enable_mouse = False
            raise e

    def _send_single_key(self, key: KeyCode, down: int=60, up: int=100):
        if self.keyboard is None:
            return

        try:
            self.keyboard.send_keys([key])
            sleep_ms(down)
            self.keyboard.send_keys([])
            sleep_ms(up)
        except Exception as e:
            self.state.last_exception = e
            self.state.last_exception_module = 'keyboard'
            self.state.enable_keyboard = False
            raise e

    def _click_left(self, down: int=50):
        if self.mouse is None:
            return
        try:
            self.mouse.click_left()
            sleep_ms(down)
            self.mouse.click_left(down=False)
        except Exception as e:
            self.state.last_exception = e
            self.state.last_exception_module = 'mouseclick'
            self.state.enable_mouse = False
            raise e

    def _setup(self):
        self.i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA))
        print(str(self.i2c.scan()))

        # On-board LED
        self.led = Pin("LED", Pin.OUT)

        self._flash(200)

        # Gyro, Accel, Magnet, Temp
        if self.state.enable_gyro:
            try:
                self.mpu9250 = mpu9250.BiasedMPU9250(self.i2c)
            except Exception as e:
                self.state.last_exception = e
                self.state.last_exception_module = 'gyrosetup'
                self.state.enable_gyro = False
                self.mpu9250 = None

            self._flash(200)
        else:
            self.mpu9250 = None

        # RFID
        if self.state.enable_rfid:
            try:
                self.mfrc522 = mfrc522.MFRC522(sck=SPI_SCK, miso=SPI_MISO, mosi=SPI_MOSI, cs=SPI_CS, rst=SPI_RST)
            except Exception as e:
                self.state.last_exception = e
                self.state.last_exception_module = 'rfidsetup'
                self.state.enable_rfid = False
                self.mfrc522 = None

            self._flash(200)
        else:
            self.mfrc522 = None

        # OLED
        if self.state.enable_oled:
            try:
                self.ssd1306 = ssd1306.SSD1306_I2C(self.i2c)
            except Exception as e:
                self.state.last_exception = e
                self.state.last_exception_module = 'oledsetup'
                self.state.enable_oled = False
                self.ssd1306 = None

            self._flash(200)
        else:
            self.ssd1306 = None

        # IR receiver
        if self.state.enable_ir:
            try:
                self.hx1838 = hx1838.HX1838(Pin(IR_SIGNAL), self._ir_callback)
            except Exception as e:
                self.state.last_exception = e
                self.state.last_exception_module = 'irsetup'
                self.state.enable_ir = False
                self.hx1838 = None

            self._flash(200)
        else:
            self.hx1838 = None

        # Keyboard
        if self.state.enable_keyboard:
            try:
                self.keyboard = KeyboardInterface()
            except Exception as e:
                self.state.last_exception = e
                self.state.last_exception_module = 'kbdsetup'
                self.state.enable_keyboard = False
                self.keyboard = None

            self._flash(200)
        else:
            self.keyboard = None

        # Mouse
        if self.state.enable_mouse:
            try:
                self.mouse = MouseInterface()
            except Exception as e:
                self.state.last_exception = e
                self.state.last_exception_module = 'mousesetup'
                self.state.enable_mouse = False
                self.mouse = None

            self._flash(200)
        else:
            self.mouse = None

    def _initialize(self):
        # Flash
        self._flash(300)

        # Clear display
        self._clear_display(show=False)
        self._typewrite_text('Initialize')

        # Initialize HID
        if not self._disable_hid:
            args = []
            if self.keyboard is not None:
                args += [self.keyboard]
            if self.mouse is not None:
                args += [self.mouse]
            if args:
                usb.device.get().init(*args, builtin_driver=True)

            if self.keyboard is not None:
                while not self.keyboard.is_open():
                    sleep_ms(100)
                self._typewrite_text('Keyboard OK')
            else:
                self._typewrite_text('Keyboard SKIP')

            if self.mouse is not None:
                while not self.mouse.is_open():
                    sleep_ms(100)
                self._typewrite_text('Mouse OK')
            else:
                self._typewrite_text('Mouse SKIP')

        # Gyro calibration
        if self.mpu9250 is not None:
            self._typewrite_text('Calibrate...')
            try:
                self.mpu9250.calibrate(100)
            except Exception as e:
                self.state.last_exception = e
                self.state.last_exception_module = 'gyrocal'
                self.state.enable_mouse = False
                raise e
            
            self._typewrite_text('Done!')
            print(f'bias={self.mpu9250.calibration})')
            print(f'std={self.mpu9250.calibration_deviation})')
        else:
            self._typewrite_text('Gyro SKIP')

        # Flash 3x
        self._flash(300)
        self._flash(300)
        self._flash(300)

        if not self._disable_hid:
            self._click_left()
            sleep_ms(500)
            self._click_left()
            sleep_ms(500)
            self._click_left()
            sleep_ms(500)

# pylint: disable=bare-except
    def _input_data(self):
        if self.state.enable_gyro and self.state.enable_mouse:
            try:
                self.state.gyro = self.mpu9250.gyro
                print(f'[GYRO] {self.state.gyro}')
            except:
                self.state.enable_gyro = False
        if self.state.enable_rfid and self.state.enable_keyboard:
            try:
                self.state.rfid = self.mfrc522.tag
            except:
                self.state.enable_rfid = False
# pylint: enable=bare-except

    def _process_data(self):
        # RFID data
        if tag := self.state.rfid:
            if rfid_eye := self._eye_by_rfid.get(tag):
                print(f'[CTRL] New eye {rfid_eye.name}')
                self.state.next_eye = rfid_eye
            else:
                print(f'[CTRL] Unknown tag {tag}')

        # Gyro data
        mouse_state_x = int(self.state.gyro[0] * GYRO_TO_MOUSE_K)
        mouse_state_y = int(self.state.gyro[2] * GYRO_TO_MOUSE_K) * -1
        self.state.mouse = (mouse_state_x, mouse_state_y)

        # Magnet data
        # ...

    def _output_data(self):
        if not self._disable_hid:
            # Send keyboard
            if self.state.next_eye is not None:
                self._send_single_key(self.state.next_eye.key)

            # Send mouse
            if self.mouse is not None:
                mx, my = self.state.mouse
                mx = max(-127, min(mx, 127))
                my = max(-127, min(my, 127))
                if mx != 0 or my != 0:
                    try:
                        self.mouse.move_by(mx, my)
                    except Exception as e:
                        self.state.last_exception = e
                        self.state.last_exception_module = 'mousemove'
                        self.state.enable_mouse = False
                        raise e

        # Update current eye
        if self.state.next_eye:
            self.state.current_eye = self.state.next_eye
            self.state.next_eye = None
            self.state.ordered_selection_idx = self.state.current_eye.pos

        current_selecting_eye = self._ordered_eyes[self.state.ordered_selection_idx]

        # Update display
        # TODO temporary only (add arrows for gyro/mouse, separate line for state.selecting_eye)
        if self.ssd1306 is not None:
            try:
                self._clear_display(show=False)
                self._typewrite_text(self.state.current_eye.name, show=False)
                self._typewrite_text(f'> {current_selecting_eye.name}', show=False)
                self._typewrite_text(f'MX: {self.state.mouse[0]}', show=False)
                self._typewrite_text(f'MY: {self.state.mouse[1]}', show=False)
                _feature_flags = [
                    self.state.enable_gyro,
                    self.state.enable_ir,
                    self.state.enable_rfid,
                    self.state.enable_oled,
                    self.state.enable_keyboard,
                    self.state.enable_mouse,
                ]
                feature_flags = ''.join(['-' if f else 'X' for f in _feature_flags])
                self._typewrite_text(feature_flags, show=False)
                if self.state.display_updated:
                    self.ssd1306.show()
                    self.state.display_updated = False
            except Exception as e:
                self.state.last_exception = e
                self.state.last_exception_module = 'oledout'
                self.state.enable_mouse = False
                raise e

    def main_loop(self):
        while True:
            self._setup()

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

                    # # Sleep
                    # sleep_ms(LOOP_DELAY_MS)

            except KeyboardInterrupt:
                print('Exit')
                if self.ssd1306 is not None:
                    self.ssd1306.fill(0)
                    self.ssd1306.show()
                if self.hx1838 is not None:
                    self.hx1838.close()
                return

            except OSError as e:
                print(f'{e.errno} -> {errno.errorcode[e.errno]}')
                if self.ssd1306 is not None:
                    self._clear_display(show=True)
                    self._typewrite_text(e.__class__.__name__, x=0, show=False)
                    self._typewrite_text(str(e.errno), x=0, show=False)
                    self._typewrite_text(errno.errorcode[e.errno], x=0, show=False)
                    self._typewrite_text(self.state.last_exception.__class__.__name__, x=0, show=False)
                    self._typewrite_text(self.state.last_exception_module, x=0, show=False)
                    self.ssd1306.show()
                sleep_ms(3000)

            except Exception as e:
                if self.ssd1306 is not None:
                    self._clear_display(show=True)
                    self._typewrite_text(e.__class__.__name__, x=0, show=False)
                    self._typewrite_text(self.state.last_exception.__class__.__name__, x=0, show=False)
                    self._typewrite_text(self.state.last_exception_module, x=0, show=False)
                    self.ssd1306.show()
                sleep_ms(3000)
                # content = str(e)
                # line_size = 128 // 8
                # for i in range(min(6, len(content)//line_size)):
                #     self._typewrite_text(content[i*line_size:(i+1)*line_size], x=0)
