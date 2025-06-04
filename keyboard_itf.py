
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

    def loop(self):
        self.reader.init()

        # (stat, _) = self.reader.request(self.reader.REQIDL)
        # if stat != self.reader.OK:
        #     return

        # (stat, uid) = self.reader.SelectTagSN()
        # if stat != self.reader.OK:
        #     return
        uid = self.reader.get_uid()
        if not uid:
            return

        card = int.from_bytes(bytes(uid),"little",False)
        print("CARD ID: "+str(card))
        self.k.send_keys([KeyCode.A + card % 25])
        sleep_ms(60)
        self.k.send_keys([])
        sleep_ms(100)
        # if key := self.keys.get(card):
        #     self.k.send_keys([key])
        #     sleep_ms(60)
        #     self.k.send_keys([])
        #     sleep_ms(100)
        #     self.flash(100)
        # else:
        #     print('Unknown card!!!')
