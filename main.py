# pylint: disable=import-error
from machine import Pin
from usb.device.keyboard import KeyCode
import utime

import keyboard_itf
# pylint: enable=import-error

# TODO initialize HID mouse (for gyro)

keys = {
    2061740185: KeyCode.Q,
    3835383779: KeyCode.W
}

rfid_kbd = keyboard_itf.RFIDToKeyboard(keys, led = Pin("LED", Pin.OUT))

rfid_kbd.flash(100)
rfid_kbd.flash(100)
rfid_kbd.flash(100)

try:
    print('Enter main loop')
    while True:
        print('--------------')
        utime.sleep_ms(500)
        rfid_kbd.loop()

except KeyboardInterrupt:
    pass
