# sensor.py — SparkFun AS7265x 18-channel spectral sensor interface
# Communicates over I2C at address 0x49 using the qwiic_as7265x library.

import time
import qwiic_as7265x
from config import GAIN, INTEGRATION_CYCLES, MEASUREMENT_MODE, WAVELENGTHS


class SpectralSensor:
    def __init__(self):
        self.sensor    = qwiic_as7265x.QwiicAS7265x()
        self.connected = False

    def begin(self):
        if not self.sensor.begin():
            print("[Sensor] NOT connected — check I2C wiring (SDA=GPIO2, SCL=GPIO3).")
            return False
        self.sensor.disable_indicator()
        self.sensor.set_measurement_mode(MEASUREMENT_MODE)
        self.sensor.set_gain(GAIN)
        self.sensor.set_integration_cycles(INTEGRATION_CYCLES)
        time.sleep(1)
        self.connected = True
        print("[Sensor] Connected and initialized.")
        return True

    def read(self):
        """
        Take a single measurement with the onboard bulb illumination.
        Returns:
            readings (dict): {wavelength_nm: calibrated_value}
            raw_list (list): 18 float values in channel order
        """
        if not self.connected:
            return {wl: 0.0 for wl in WAVELENGTHS}, [0.0] * 18

        self.sensor.take_measurements_with_bulb()
        time.sleep(0.5)

        getters = [
            self.sensor.get_calibrated_a, self.sensor.get_calibrated_b,
            self.sensor.get_calibrated_c, self.sensor.get_calibrated_d,
            self.sensor.get_calibrated_e, self.sensor.get_calibrated_f,
            self.sensor.get_calibrated_g, self.sensor.get_calibrated_h,
            self.sensor.get_calibrated_i, self.sensor.get_calibrated_j,
            self.sensor.get_calibrated_k, self.sensor.get_calibrated_l,
            self.sensor.get_calibrated_r, self.sensor.get_calibrated_s,
            self.sensor.get_calibrated_t, self.sensor.get_calibrated_u,
            self.sensor.get_calibrated_v, self.sensor.get_calibrated_w,
        ]

        readings, raw_list = {}, []
        for i, getter in enumerate(getters):
            val = getter()
            readings[WAVELENGTHS[i]] = val
            raw_list.append(val)

        return readings, raw_list
