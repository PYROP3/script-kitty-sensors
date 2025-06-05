
# pylint: disable=import-error
from utime import sleep_ms
import usb.device
from usb.device.keyboard import KeyboardInterface, KeyCode, LEDCode
from machine import Pin

from rfid import mfrc522
# pylint: enable=import-error

class RFIDToKeyboard:
    def __init__(self, keys: dict[int, KeyCode], led: Pin=None, k: KeyboardInterface=None):
        self.keys = keys

        if k is None:
            k = KeyboardInterface()
            usb.device.get().init(k, builtin_driver=True)
        self.k = k
        self.led = led

        # Initialize RFID reader
        self.reader = mfrc522.MFRC522(sck=2,miso=4,mosi=3,cs=1,rst=0)
        self.reader.init()

    def flash(self, duration: int):
        if self.led is not None:
            self.led.on()
            sleep_ms(duration)
            self.led.off()
            sleep_ms(duration)

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
            self.k.send_keys([key])
            sleep_ms(60)
            self.k.send_keys([])
            sleep_ms(100)
            self.flash(200)
        # else:
        #     print('Unknown card!!!')
