
# pylint: disable=import-error
from machine import I2C, Pin
from utime import sleep_ms

from gyro import mpu9250
from display import ssd1306
# pylint: enable=import-error


i2c = I2C(0, scl=Pin(5), sda=Pin(4))
print(str(i2c.scan()))


gyro = mpu9250.BiasedMPU9250(i2c)
oled = ssd1306.SSD1306_I2C(i2c)

print('Calibrating...')
oled.text('Calibrating...', 0, 0)
oled.show()
gyro.calibrate(500)
print('Done!')
oled.text('Done!', 0, 10)
oled.show()

sleep_ms(3000)
oled.fill(0)
oled.show()

x, y, z = 0., 0., 0.
try:
    while True:
        # (dx, dy, dz) = gyro.gyro
        # # print(f'{x},{y},{z}')
        # x += dx
        # y += dy
        # z += dz
        # oled.fill(0)
        # oled.text(f'{x:.7f}', 0, 0)
        # oled.text(f'{y:.7f}', 0, 10)
        # oled.text(f'{z:.7f}', 0, 20)

        (mx, my, mz) = gyro.magnetic
        oled.text(f'{mx:.7f}', 10, 30)
        oled.text(f'{my:.7f}', 10, 40)
        oled.text(f'{mz:.7f}', 10, 50)

        oled.show()
        sleep_ms(50)

except KeyboardInterrupt:
    oled.fill(0)
    oled.show()
