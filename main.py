# pylint: disable=import-error
from machine import Pin
from usb.device.keyboard import KeyCode
import utime

import keyboard_itf
# pylint: enable=import-error

# TODO initialize HID mouse (for gyro)

keys = {
    '19:80:F6:04': KeyCode.Q,
    'C5:56:64:01': KeyCode.W,
    '83:C4:B9:27': KeyCode.E,
    'C3:57:B2:27': KeyCode.R,
    '83:0A:47:28': KeyCode.T,
    '83:94:31:2A': KeyCode.Y,
    'C3:35:C3:27': KeyCode.U,
    '23:9E:C4:27': KeyCode.I,
    'A3:A6:84:28': KeyCode.O,
    'A3:97:6E:29': KeyCode.P,
    '63:C8:80:29': KeyCode.A,
    'E3:4F:9B:E4': KeyCode.S,
    'C3:74:7B:29': KeyCode.D,
    '4A:EA:F4:04': KeyCode.F,
}

rfid_kbd = keyboard_itf.RFIDToKeyboard(keys, led = Pin("LED", Pin.OUT))

rfid_kbd.flash(100)
rfid_kbd.flash(100)
rfid_kbd.flash(100)

try:
    print('Enter main loop')
    while True:
        # print('--------------')
        utime.sleep_ms(500)
        rfid_kbd.loop()

except KeyboardInterrupt:
    pass
