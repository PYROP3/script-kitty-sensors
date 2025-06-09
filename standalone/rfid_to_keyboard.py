
# pylint: disable=import-error
from utime import sleep_ms
import usb.device
from usb.device.keyboard import KeyboardInterface, KeyCode
from machine import Pin

from rfid import mfrc522
# pylint: enable=import-error

class RFIDToKeyboard:

    char_to_key = {
        '0123456789': KeyCode.0,
        'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ': KeyCode.A,
    }

    def __init__(self, keys: dict[int, KeyCode], led: Pin=None, k: KeyboardInterface=None):
        self.keys = keys

        if k is None:
            k = KeyboardInterface()
            usb.device.get().init(k, builtin_driver=True)
        self.k = k
        self.led = led

        # Initialize RFID reader
        # self.reader = mfrc522.MFRC522(sck=2,miso=4,mosi=3,cs=1,rst=0)
        self.reader = mfrc522.MFRC522(sck=2,miso=0,mosi=3,cs=1,rst=-1)
        self.reader.init()

    def flash(self, duration: int):
        if self.led is not None:
            self.led.on()
            sleep_ms(duration)
            self.led.off()
            sleep_ms(duration)

    def send_single_char(self, char: str, down: int=60, up: int=100):
        for charset, base_char in self.char_to_key.items():
            if char in charset:
                self.send_single_key(base_char + ord(char) - ord(charset[0]))

    def send_single_key(self, key: KeyCode, down: int=60, up: int=100):
        self.k.send_keys([key])
        sleep_ms(down)
        self.k.send_keys([])
        sleep_ms(up)

    def uid_to_id(self, uid) -> str:
        return f"{uid[0]:02X}:{uid[1]:02X}:{uid[2]:02X}:{uid[3]:02X}"

    def loop(self):
        self.reader.init()

        uid = self.reader.get_uid()
        if not uid:
            return

        # card = int.from_bytes(bytes(uid),"little",False)
        card = self.uid_to_id(uid)
        
        print("CARD ID: "+str(card))
        if key := self.keys.get(card):
            print(f'Sending key {key}')
            self.send_single_key(key)
            self.flash(200)
        # else:
        #     print('Unknown card!!!')
