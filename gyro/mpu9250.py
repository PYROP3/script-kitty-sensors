# Copyright (c) 2018-2023 Mika Tuupola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of  this software and associated documentation files (the "Software"), to
# deal in  the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copied of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# https://github.com/tuupola/micropython-mpu9250

"""
MicroPython I2C driver for MPU9250 9-axis motion tracking device
"""

# pylint: disable=import-error
import math

from utime import sleep_ms
from micropython import const
from machine import I2C, Pin

from mpu6500 import MPU6500
from ak8963 import AK8963
# pylint: enable=import-error

__version__ = "0.4.0"

# Used for enabling and disabling the I2C bypass access
_INT_PIN_CFG = const(0x37)
_I2C_BYPASS_MASK = const(0b00000010)
_I2C_BYPASS_EN = const(0b00000010)
_I2C_BYPASS_DIS = const(0b00000000)

class MPU9250:
    """Class which provides interface to MPU9250 9-axis motion tracking device."""
    def __init__(self, i2c, mpu6500 = None, ak8963 = None):
        if mpu6500 is None:
            self.mpu6500 = MPU6500(i2c)
        else:
            self.mpu6500 = mpu6500

        # Enable I2C bypass to access AK8963 directly.
        char = self.mpu6500._register_char(_INT_PIN_CFG)
        char &= ~_I2C_BYPASS_MASK # clear I2C bits
        char |= _I2C_BYPASS_EN
        self.mpu6500._register_char(_INT_PIN_CFG, char)

        if ak8963 is None:
            self.ak8963 = AK8963(i2c)
        else:
            self.ak8963 = ak8963

    @property
    def acceleration(self):
        """
        Acceleration measured by the sensor. By default will return a
        3-tuple of X, Y, Z axis values in m/s^2 as floats. To get values in g
        pass `accel_fs=SF_G` parameter to the MPU6500 constructor.
        """
        return self.mpu6500.acceleration

    @property
    def gyro(self):
        """
        Gyro measured by the sensor. By default will return a 3-tuple of
        X, Y, Z axis values in rad/s as floats. To get values in deg/s pass
        `gyro_sf=SF_DEG_S` parameter to the MPU6500 constructor.
        """
        return self.mpu6500.gyro

    @property
    def temperature(self):
        """
        Die temperature in celcius as a float.
        """
        return self.mpu6500.temperature

    @property
    def magnetic(self):
        """
        X, Y, Z axis micro-Tesla (uT) as floats.
        """
        return self.ak8963.magnetic

    @property
    def whoami(self):
        return self.mpu6500.whoami

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass

class BiasedMPU9250(MPU9250):
    def __init__(self, i2c, mpu6500 = None, ak8963 = None, calibration_samples: int=None):
        super().__init__(i2c, mpu6500=mpu6500, ak8963=ak8963)
        self.calibration = (0., 0., 0.)
        self.calibration_deviation = (0., 0., 0.)
        if calibration_samples is not None:
            self.calibrate(calibration_samples)

    def calibrate(self, samples: int):
        (x, y, z) = (0., 0., 0.)
        sx = []
        sy = []
        sz = []
        f = float(samples)

        for i in range(samples):
            (dx, dy, dz) = self.mpu6500.gyro
            sx += [dx]
            sy += [dy]
            sz += [dz]
            x += dx / f
            y += dy / f
            z += dz / f
            sleep_ms(10)

        (dx, dy, dz) = (0., 0., 0.)
        for i in range(samples):
            dx += (sx[i] - x)*(sx[i] - x)/f
            dy += (sy[i] - y)*(sy[i] - y)/f
            dz += (sz[i] - z)*(sz[i] - z)/f
        
        self.calibration = (x, y, z)
        self.calibration_deviation = (2*math.sqrt(dx), 2*math.sqrt(dy), 2*math.sqrt(dz))


    @property
    def gyro(self):
        (x, y, z) = self.mpu6500.gyro
        (cx, cy, cz) = self.calibration
        (dx, dy, dz) = self.calibration_deviation
        x -= cx
        if abs(cx) < dx:
            x = 0
        y -= cy
        if abs(cy) < dy:
            y = 0
        z -= cz
        if abs(cz) < dz:
            z = 0
        return (x, y, z)

if __name__ == '__main__':
    i2c = I2C(0, scl=Pin(5), sda=Pin(4))
    print(str(i2c.scan()))

    # gyro = MPU9250(i2c)
    gyro = BiasedMPU9250(i2c)
    gyro.calibrate(100)
    print(f'Calibration done! (bias={gyro.calibration})')

    print("MPU9250 id: " + hex(gyro.whoami))

    while True:
        try:
            (x, y, z) = gyro.gyro
            print(f'{x},{y},{z}')
            # print(f'{gyro.acceleration=}')
            # print(f'{gyro.gyro=}')
            # print(f'{gyro.magnetic=}')
            # print(f'{gyro.temperature=}')
            # print('')

            sleep_ms(10)
        except KeyboardInterrupt:
            break
