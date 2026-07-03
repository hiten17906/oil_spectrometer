# touch.py — XPT2046 resistive touchscreen handler
# Pi 5 compatible: all GPIO via lgpio (chip index 4)

import spidev
import lgpio
import time
from config import TOUCH_CS, TOUCH_IRQ, TFT_WIDTH, TFT_HEIGHT

_GPIO_CHIP = 4  # Pi 5 RP1 GPIO chip


class TouchScreen:
    CMD_X = 0xD0   # X position command
    CMD_Y = 0x90   # Y position command

    def __init__(self):
        self._spi        = spidev.SpiDev()
        self._h          = None
        self.last_touch  = None
        self.touch_time  = 0.0

    def begin(self):
        self._h = lgpio.gpiochip_open(_GPIO_CHIP)
        lgpio.gpio_claim_input(self._h, TOUCH_IRQ)
        lgpio.gpio_claim_output(self._h, TOUCH_CS, 1)

        self._spi.open(0, 1)           # SPI bus 0, device 1 (CE1 = GPIO7)
        self._spi.max_speed_hz = 1_000_000
        self._spi.mode = 0
        print("[Touch] Initialized.")

    def _read_raw(self, cmd):
        lgpio.gpio_write(self._h, TOUCH_CS, 0)
        self._spi.xfer2([cmd, 0x00, 0x00])
        r = self._spi.xfer2([0x00, 0x00, 0x00])
        lgpio.gpio_write(self._h, TOUCH_CS, 1)
        return ((r[0] << 8) | r[1]) >> 3

    def is_touched(self):
        return lgpio.gpio_read(self._h, TOUCH_IRQ) == 0

    def get_touch(self, samples=5):
        """
        Return (x, y) in screen pixel coordinates, or None if not touched.
        Includes 300 ms debounce.
        """
        if not self.is_touched():
            return None

        now = time.time()
        if now - self.touch_time < 0.3:
            return None

        xs, ys = [], []
        for _ in range(samples):
            rx = self._read_raw(self.CMD_X)
            ry = self._read_raw(self.CMD_Y)
            if rx > 100 and ry > 100:
                xs.append(rx)
                ys.append(ry)

        if not xs:
            return None

        # Map raw ADC (0–4096) → screen pixels
        X_MIN, X_MAX = 200, 3900
        Y_MIN, Y_MAX = 200, 3900
        x = int((sum(xs) / len(xs) - X_MIN) / (X_MAX - X_MIN) * TFT_WIDTH)
        y = int((sum(ys) / len(ys) - Y_MIN) / (Y_MAX - Y_MIN) * TFT_HEIGHT)
        x = max(0, min(TFT_WIDTH  - 1, x))
        y = max(0, min(TFT_HEIGHT - 1, y))

        self.last_touch = (x, y)
        self.touch_time = now
        return (x, y)

    def cleanup(self):
        self._spi.close()
        if self._h:
            lgpio.gpiochip_close(self._h)
            self._h = None
