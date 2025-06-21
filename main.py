# pylint: disable=import-error
from usb.device.keyboard import KeyCode

import controller
import state
# pylint: enable=import-error

UNUSED_TAG = 'UNUSED'

_eyes = [
    ('default',  '19:80:F6:04', KeyCode.Q, 0x0C),
    ('vu',       'C5:56:64:01', KeyCode.W, 0x18),
    ('spiral',   '83:C4:B9:27', KeyCode.E, 0x5E),
    ('hacker',   'C3:57:B2:27', KeyCode.R, 0x08),
    ('bsod',     '83:0A:47:28', KeyCode.T, 0x1C),
    (UNUSED_TAG, '83:94:31:2A', KeyCode.Y, 0x5A),
    (UNUSED_TAG, 'C3:35:C3:27', KeyCode.U, 0x42),
    (UNUSED_TAG, '23:9E:C4:27', KeyCode.I, 0x52),
    (UNUSED_TAG, 'A3:A6:84:28', KeyCode.O, 0x4A),
    (UNUSED_TAG, 'A3:97:6E:29', KeyCode.P, None),
    (UNUSED_TAG, '63:C8:80:29', KeyCode.A, None),
    (UNUSED_TAG, 'E3:4F:9B:E4', KeyCode.S, None),
    (UNUSED_TAG, 'C3:74:7B:29', KeyCode.D, None),
    (UNUSED_TAG, '4A:EA:F4:04', KeyCode.F, None),
]
eyes = [state.EyeMode(name=name, rfid=rfid, key=key, ir=ir) for (name, rfid, key, ir) in _eyes]
for idx, eye in enumerate(eyes):
    eye.pos = idx

controller = controller.Controller(eyes, disable_hid=False)

print('[MAIN] Starting controller')
controller.main_loop()
