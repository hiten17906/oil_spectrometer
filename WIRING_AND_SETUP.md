# Wiring & Setup Guide
## Oil Adulteration Spectrometer — Raspberry Pi 5

---

## 1. Wiring

### AS7265x → Raspberry Pi 5 (I2C)

| AS7265x | Pi 5 Pin | GPIO   |
|---------|----------|--------|
| VCC     | Pin 1    | 3.3V   |
| GND     | Pin 6    | GND    |
| SDA     | Pin 3    | GPIO2  |
| SCL     | Pin 5    | GPIO3  |

### Smartelex 2.4" TFT → Raspberry Pi 5 (SPI)

| TFT Pin | Pi 5 Pin | GPIO   | Notes                        |
|---------|----------|--------|------------------------------|
| VCC     | Pin 17   | 3.3V   |                              |
| GND     | Pin 20   | GND    |                              |
| CS      | Pin 24   | GPIO8  | SPI0 CE0 — manual via lgpio  |
| RESET   | Pin 22   | GPIO25 | Manual via lgpio             |
| DC/RS   | Pin 18   | GPIO24 | Manual via lgpio             |
| MOSI    | Pin 19   | GPIO10 | SPI0 MOSI                   |
| SCK     | Pin 23   | GPIO11 | SPI0 SCLK                   |
| LED/BL  | Pin 12   | GPIO18 | Backlight via lgpio          |
| T_CS    | Pin 26   | GPIO7  | Touch chip select            |
| T_IRQ   | Pin 11   | GPIO17 | Touch interrupt              |

> ⚠️ All signals are 3.3V. Do not use 5V — it will damage the display.

---

## 2. Enable SPI & I2C on Pi 5

```bash
sudo raspi-config
# Interface Options → SPI → Enable
# Interface Options → I2C → Enable
sudo reboot
```

Verify:
```bash
ls /dev/spidev*      # expect /dev/spidev0.0 and /dev/spidev0.1
i2cdetect -y 1       # expect 0x49 for AS7265x
```

Also confirm `/boot/firmware/config.txt` contains:
```
dtparam=spi=on
dtoverlay=spi0-0cs
```

---

## 3. Install Dependencies

```bash
sudo apt update && sudo apt install -y \
    python3-pip python3-dev fonts-dejavu \
    python3-numpy python3-pil libjpeg-dev libfreetype6-dev

# Create venv with system-site-packages (needed for lgpio access)
python3 -m venv venv --system-site-packages
source venv/bin/activate

pip install sparkfun-qwiic-as7265x pillow numpy spidev lgpio
```

> ❌ Do **not** install `RPi.GPIO` — it is not supported on Pi 5 and will throw:
> `RuntimeError: Cannot determine SOC peripheral base address`

---

## 4. Run

```bash
source venv/bin/activate
python main.py
```

---

## 5. Pi 5 Known Issues & Fixes

| Issue | Cause | Fix Applied |
|---|---|---|
| `RuntimeError: Cannot determine SOC peripheral base address` | RPi.GPIO unsupported on Pi 5 | Replaced with lgpio, chip index 4 |
| `OSError: [Errno 22] Invalid argument` on `spi.no_cs` | Pi 5 spidev doesn't support `no_cs` | Removed; CS driven manually via lgpio |
| White screen on TFT | lgpio writes and spidev don't synchronize on Pi 5 — DC pin not settled | Added 1ms delay after every DC pin change |
| Red and blue colors swapped | MADCTL BGR bit wrong for this panel | Changed `0x48` → `0x40` (RGB mode) |
| luma.lcd fails on Pi 5 | luma.lcd internally uses RPi.GPIO | Replaced with direct spidev + PIL rendering |

---

## 6. Auto-start on Boot (Optional)

```bash
sudo nano /etc/rc.local
# Add before exit 0:
# cd /home/admin/oil-adulteration-spectrometer && source venv/bin/activate && python main.py &
```
