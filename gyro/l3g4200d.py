from machine import I2C, Pin
from time import sleep_ms

class L3G4200D:
    def __init__(self, i2c: I2C, i2c_address=0x69):
        self.i2c = i2c
        self.i2c_address = i2c_address
        self.initialize()

    def write_byte_data(self, register, value):
        self.i2c.writeto_mem(self.i2c_address, register, bytes([value]))

    def write_byte(self, value):
        self.i2c.writeto(self.i2c_address, bytes([value]))

    def read_byte(self) -> bytes:
        return self.i2c.readfrom(self.i2c_address, 1)[0]

    def initialize(self):
        #normal mode and all axes on to control reg1
        self.write_byte_data(0x20,0x0F)
        #full 2000dps to control reg4
        self.write_byte_data(0x23,0x20)

    def read_gyro(self):
        self.write_byte(0x28)
        x_lo = self.read_byte()
        self.write_byte(0x29)
        x_hi = self.read_byte()

        self.write_byte(0x2A)
        y_lo = self.read_byte()
        self.write_byte(0x2B)
        y_hi = self.read_byte()

        self.write_byte(0x2C)
        z_lo = self.read_byte()
        self.write_byte(0x2D)
        z_hi = self.read_byte()

        return (
            self._get_signed_number(x_hi << 8 | x_lo),
            self._get_signed_number(y_hi << 8 | y_lo),
            self._get_signed_number(z_hi << 8 | z_lo))

    #converts 16 bit two's compliment reading to signed int
    def _get_signed_number(self, number):
        if number & (1 << 15):
            return number | ~65535
        return number & 65535

if __name__ == '__main__':
    i2c = I2C(0, scl=Pin(9), sda=Pin(8))
    print(str(i2c.scan()))
    gyro = L3G4200D(i2c)
    while True:
        try:
            (x, y, z) = gyro.read_gyro()
            print(f'{x},{y},{z}')
            sleep_ms(10)
        except KeyboardInterrupt:
            break
