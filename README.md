# Oil Adulteration Spectrometer

> A handheld, embedded oil purity analyzer built on **Raspberry Pi 5** using 18-channel visible/NIR spectroscopy. Detects oil type, estimates adulteration percentage, and identifies likely adulterants — all in real time on a 2.4" SPI TFT display.

---

## Table of Contents

- [Overview](#overview)
- [Hardware](#hardware)
- [Wiring](#wiring)
- [Software Architecture](#software-architecture)
- [How the Model Works](#how-the-model-works)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [Known Issues & Pi 5 Fixes](#known-issues--pi-5-fixes)
- [Future Work](#future-work)
- [License](#license)

---

## Overview

Food oil adulteration is a widespread public health problem, particularly in India. This project builds a low-cost, portable spectrometer that:

- Reads **18 spectral channels** (410–940 nm) using the SparkFun AS7265x sensor
- Identifies the **oil type** (Mustard, Coconut, Olive, Sunflower, Groundnut)
- Estimates the **adulteration percentage** using spectral fingerprint matching
- Identifies the most likely **adulterant** (Palm Oil, Mineral Oil, Soybean Oil, etc.)
- Displays a **verdict** (Pure / Mildly Adulterated / Heavily Adulterated) on a TFT screen

The model uses **cosine similarity** and **Euclidean distance** against pre-built spectral fingerprints derived from published NIR/VIS spectroscopy research (FOSS, USDA datasets).

**Current version:** v1.0 — Display + Sensor integration complete.

---

## Hardware

| Component | Details |
|---|---|
| **Microcomputer** | Raspberry Pi 5 (4GB) |
| **Spectral Sensor** | SparkFun AS7265x Triad (18-channel, 410–940nm) |
| **Display** | Smartelex 2.4" ILI9341 SPI TFT 240×320 |
| **Touch** | XPT2046 resistive touch (on display board) |
| **Interface** | I2C (sensor) + SPI (display + touch) |
| **Power** | 5V via USB-C (Pi 5) |

---

## Wiring

### AS7265x → Raspberry Pi 5 (I2C)

| AS7265x | Pi 5 Pin | GPIO |
|---|---|---|
| VCC | Pin 1 | 3.3V |
| GND | Pin 6 | GND |
| SDA | Pin 3 | GPIO2 |
| SCL | Pin 5 | GPIO3 |

### Smartelex 2.4" TFT → Raspberry Pi 5 (SPI)

| TFT Pin | Pi 5 Pin | GPIO | Notes |
|---|---|---|---|
| VCC | Pin 17 | 3.3V | |
| GND | Pin 20 | GND | |
| CS | Pin 24 | GPIO8 | SPI0 CE0 — driven manually via lgpio |
| RESET | Pin 22 | GPIO25 | Driven manually via lgpio |
| DC/RS | Pin 18 | GPIO24 | Driven manually via lgpio |
| MOSI | Pin 19 | GPIO10 | SPI0 MOSI |
| SCK | Pin 23 | GPIO11 | SPI0 SCLK |
| LED/BL | Pin 12 | GPIO18 | Backlight via lgpio |
| T_CS | Pin 26 | GPIO7 | Touch chip select |
| T_IRQ | Pin 11 | GPIO17 | Touch interrupt |

> ⚠️ All signals are 3.3V logic. Pi 5 GPIO is 3.3V — safe to connect directly.

---

## Software Architecture

```
oil-adulteration-spectrometer/
├── main.py          # Entry point — state machine (splash → scan → result)
├── display.py       # ILI9341 driver (direct spidev + PIL, no luma.lcd)
├── sensor.py        # AS7265x interface via qwiic_as7265x
├── model.py         # Spectral fingerprint ML (cosine sim + euclidean distance)
├── touch.py         # XPT2046 touch handler via spidev + lgpio
├── config.py        # All pin definitions, SPI settings, color constants
└── docs/
    └── WIRING_AND_SETUP.md
```

### State Machine

```
[SPLASH] ──tap──▶ [SCANNING] ──done──▶ [RESULT]
   ▲                                       │
   └───────────────tap────────────────────┘
```

---

## How the Model Works

The model in `model.py` runs entirely on-device without any API calls:

1. **Read** — 18 float values from AS7265x (410–940nm channels)
2. **Normalize** — Scale readings to 0–1 range
3. **Oil identification** — Cosine similarity against 5 pure oil fingerprints → best match
4. **Adulteration %** — Euclidean distance from pure fingerprint, scaled to 0–100%
5. **Adulterant ID** — Cosine similarity of residual spectrum against 5 adulterant fingerprints
6. **Verdict** — Pure (<10%), Mildly Adulterated (10–35%), Heavily Adulterated (>35%)

**Supported oils:** Mustard, Coconut, Olive, Sunflower, Groundnut

**Detected adulterants:** Palm Oil, Mineral Oil, Soybean Oil, Canola Oil, Rice Bran Oil

---

## Installation

### 1. Enable SPI and I2C

```bash
sudo raspi-config
# Interface Options → SPI → Enable
# Interface Options → I2C → Enable
sudo reboot
```

Verify:
```bash
ls /dev/spidev*    # should show /dev/spidev0.0
i2cdetect -y 1    # should show 0x49 for AS7265x
```

### 2. Create virtual environment

```bash
cd ~
git clone https://github.com/hiten17906/oil-adulteration-spectrometer.git
cd oil-adulteration-spectrometer
python3 -m venv venv --system-site-packages
source venv/bin/activate
```

> ⚠️ `--system-site-packages` is required so the venv can access system-level `lgpio`.

### 3. Install dependencies

```bash
# System packages
sudo apt update && sudo apt install -y \
    python3-pip python3-dev fonts-dejavu \
    python3-numpy python3-pil libjpeg-dev libfreetype6-dev

# Python packages (inside venv)
pip install sparkfun-qwiic-as7265x
pip install pillow numpy spidev lgpio
```

> ℹ️ Do **not** install `RPi.GPIO` — it is incompatible with Pi 5. This project uses `lgpio` directly.

---

## Running the Project

```bash
source venv/bin/activate
python main.py
```

Expected output:
```
[Sensor] Connected and initialized.
[Display] TFT initialized.
[Touch] Initialized.
[Main] All hardware initialized. Starting UI loop.
```

The splash screen appears on the TFT. Tap the **TAP TO SCAN** button to begin a measurement.

---

## Known Issues & Pi 5 Fixes

This project was developed and debugged entirely on **Raspberry Pi 5**, which has significant differences from Pi 4 in GPIO and SPI handling. The following issues were encountered and resolved:

### 1. `RPi.GPIO` — Not supported on Pi 5

**Error:** `RuntimeError: Cannot determine SOC peripheral base address`

**Fix:** Remove all `RPi.GPIO` usage. Use `lgpio` directly with chip index `4` (Pi 5's RP1 GPIO controller).

```python
h = lgpio.gpiochip_open(4)
lgpio.gpio_claim_output(h, pin)
lgpio.gpio_write(h, pin, 1)
```

### 2. `spi.no_cs = True` — Not supported on Pi 5

**Error:** `OSError: [Errno 22] Invalid argument`

**Fix:** Remove `spi.no_cs`. Drive CS manually via `lgpio` instead.

### 3. White screen on TFT — DC pin race condition

**Symptom:** Display powers on (backlight ON) but shows only white.

**Root cause:** On Pi 5, `lgpio` GPIO writes and `spidev` transfers are not synchronized. The DC pin hadn't settled before the SPI clock started, so the display controller couldn't distinguish commands from pixel data.

**Fix:** Add a 1ms delay after every DC pin change:

```python
lgpio.gpio_write(h, TFT_DC, 0)
time.sleep(0.001)          # settle before SPI transfer
spi.xfer2([command])
```

### 4. Red and blue colors swapped

**Symptom:** Sending RED showed blue on screen, and vice versa.

**Fix:** Change MADCTL byte from `0x48` (BGR) to `0x40` (RGB):

```python
cmd(0x36); data([0x40])    # RGB mode, not BGR
```

### 5. `luma.lcd` — Removed entirely

`luma.lcd` internally uses `RPi.GPIO` and does not support Pi 5. The display driver was rewritten to use direct `spidev` + `PIL`, converting PIL images to RGB565 bytes manually.

---

## Future Work

- [ ] **Touch calibration UI** — interactive screen-tap calibration for XPT2046
- [ ] **Scan history** — save timestamped results to CSV on SD card
- [ ] **Real sample training** — collect actual oil spectral readings and retrain model with real data (scikit-learn / XGBoost)
- [ ] **Confidence scoring** — per-oil probability scores displayed on result screen
- [ ] **Palm oil & argemone detection** — expand adulterant fingerprint database
- [ ] **Battery + enclosure** — portable 3D-printed housing with LiPo battery
- [ ] **BLE export** — stream results to phone via Bluetooth Low Energy
- [ ] **Web dashboard** — Flask/FastAPI local server for scan history and charts

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built by [hiten17906](https://github.com/hiten17906) · NITK Surathkal · 2026*
