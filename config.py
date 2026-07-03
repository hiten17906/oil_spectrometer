# config.py — Pin definitions and system constants
# Raspberry Pi 5 + Smartelex 2.4" ILI9341 TFT + SparkFun AS7265x

# ─── TFT SPI Display Pins ───────────────────────────────────────────────────
TFT_CS    = 8     # GPIO8  — SPI0 CE0 (driven manually via lgpio)
TFT_DC    = 24    # GPIO24 — Data/Command
TFT_RST   = 25    # GPIO25 — Reset
TFT_BL    = 18    # GPIO18 — Backlight
TFT_WIDTH  = 240
TFT_HEIGHT = 320

# ─── Touch Controller Pins ──────────────────────────────────────────────────
TOUCH_CS  = 7     # GPIO7  — Touch chip select
TOUCH_IRQ = 17    # GPIO17 — Touch interrupt

# ─── Display Settings ───────────────────────────────────────────────────────
SPI_PORT     = 0
SPI_DEVICE   = 0
SPI_SPEED_HZ = 500_000   # 500 kHz — confirmed stable on Pi 5 with this panel
DC_DELAY     = 0.001     # 1 ms DC pin settle (fixes Pi 5 lgpio/spidev race)
MADCTL       = 0x40      # RGB portrait — fixes red/blue color swap (not BGR)

# ─── Sensor Settings ────────────────────────────────────────────────────────
GAIN              = 64
INTEGRATION_CYCLES = 50
MEASUREMENT_MODE  = 3

# ─── UI Colors (RGB tuples) ─────────────────────────────────────────────────
COLOR_BG      = (10,  10,  20)
COLOR_PANEL   = (20,  20,  40)
COLOR_ACCENT  = (0,  220, 180)   # Teal
COLOR_ACCENT2 = (255, 160,  0)   # Amber
COLOR_WHITE   = (255, 255, 255)
COLOR_GRAY    = (120, 120, 140)
COLOR_GREEN   = (50,  220, 100)
COLOR_YELLOW  = (255, 210,   0)
COLOR_RED     = (255,  60,  60)
COLOR_PURE    = (50,  220, 100)
COLOR_MILD    = (255, 210,   0)
COLOR_HEAVY   = (255,  60,  60)

# ─── Oil Types ──────────────────────────────────────────────────────────────
OIL_TYPES = [
    "Mustard Oil",
    "Coconut Oil",
    "Olive Oil",
    "Sunflower Oil",
    "Groundnut Oil",
]

# ─── Adulteration Thresholds ────────────────────────────────────────────────
PURE_THRESHOLD = 10   # < 10%  → Pure
MILD_THRESHOLD = 35   # 10–35% → Mildly Adulterated
                      # > 35%  → Heavily Adulterated

# ─── AS7265x Channel Wavelengths (nm) ───────────────────────────────────────
WAVELENGTHS = [
    410, 435, 460, 485, 510, 535,
    560, 585, 610, 645, 680, 705,
    730, 760, 810, 860, 900, 940,
]

CHANNEL_LABELS = [
    'A', 'B', 'C', 'D', 'E', 'F',
    'G', 'H', 'I', 'J', 'K', 'L',
    'R', 'S', 'T', 'U', 'V', 'W',
]
