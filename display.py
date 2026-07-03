# display.py — ILI9341 TFT driver + UI screens
#
# Drives the Smartelex 2.4" ILI9341 240x320 SPI display using direct spidev
# and lgpio. luma.lcd is NOT used — it relies on RPi.GPIO which is broken on
# Raspberry Pi 5.
#
# Key Pi 5 fixes applied here:
#   1. All GPIO via lgpio (chip index 4 = Pi 5 RP1 controller)
#   2. 1 ms DC pin settle delay before every SPI transfer (race condition fix)
#   3. Manual CS control via lgpio (spi.no_cs unsupported on Pi 5)
#   4. MADCTL = 0x40 (RGB mode, not BGR — fixes red/blue swap)
#   5. SPI at 500 kHz for reliable operation

import spidev
import lgpio
import time
import math
from PIL import Image, ImageDraw, ImageFont

from config import (
    TFT_CS, TFT_DC, TFT_RST, TFT_BL,
    TFT_WIDTH, TFT_HEIGHT,
    SPI_PORT, SPI_DEVICE, SPI_SPEED_HZ, DC_DELAY, MADCTL,
    COLOR_BG, COLOR_PANEL, COLOR_ACCENT, COLOR_ACCENT2,
    COLOR_WHITE, COLOR_GRAY, COLOR_GREEN, COLOR_YELLOW, COLOR_RED,
    WAVELENGTHS, PURE_THRESHOLD, MILD_THRESHOLD,
)

W, H = TFT_WIDTH, TFT_HEIGHT
_GPIO_CHIP = 4  # Pi 5 RP1 GPIO chip index

SPECTRUM_COLORS = [
    (148, 0, 211), (100, 0, 200), (0,  80, 255), (0, 140, 255),
    (0, 200, 200), (0, 210, 100), (50, 220,  50), (120, 230, 0),
    (200, 230,  0), (255, 200,  0), (255, 160,  0), (255, 120, 0),
    (255,  80,  0), (255,  40,  0), (220,   0,  0), (180,   0, 30),
    (140,   0, 50), (100,   0, 60),
]


def load_font(size, bold=False):
    try:
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf".format(
            "-Bold" if bold else "")
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


class OilDisplay:
    def __init__(self):
        self._h   = None   # lgpio handle
        self._spi = None

    # ── Initialisation ────────────────────────────────────────────────────────
    def begin(self):
        # Claim all control pins via lgpio
        self._h = lgpio.gpiochip_open(_GPIO_CHIP)
        for pin in [TFT_DC, TFT_RST, TFT_BL, TFT_CS]:
            lgpio.gpio_claim_output(self._h, pin, 1)
        lgpio.gpio_write(self._h, TFT_CS, 1)
        lgpio.gpio_write(self._h, TFT_BL, 0)

        # Open SPI bus
        self._spi = spidev.SpiDev()
        self._spi.open(SPI_PORT, SPI_DEVICE)
        self._spi.max_speed_hz = SPI_SPEED_HZ
        self._spi.mode = 0

        self._hard_reset()
        self._init_ili9341()
        lgpio.gpio_write(self._h, TFT_BL, 1)
        print("[Display] TFT initialized.")

    # ── Low-level SPI helpers ─────────────────────────────────────────────────
    def _cs(self, v):
        lgpio.gpio_write(self._h, TFT_CS, v)

    def _cmd(self, c):
        """Send a command byte (DC=0)."""
        lgpio.gpio_write(self._h, TFT_DC, 0)
        time.sleep(DC_DELAY)          # Pi 5 DC settle fix
        self._cs(0)
        self._spi.xfer2([c])
        self._cs(1)

    def _data(self, d):
        """Send data bytes (DC=1)."""
        lgpio.gpio_write(self._h, TFT_DC, 1)
        time.sleep(DC_DELAY)
        self._cs(0)
        for i in range(0, len(d), 4096):
            self._spi.xfer2(list(d[i:i + 4096]))
        self._cs(1)

    def _hard_reset(self):
        lgpio.gpio_write(self._h, TFT_RST, 0); time.sleep(0.5)
        lgpio.gpio_write(self._h, TFT_RST, 1); time.sleep(0.5)

    def _init_ili9341(self):
        """Full ILI9341 initialisation sequence."""
        self._cmd(0x01); time.sleep(0.15)   # Software reset
        self._cmd(0x11); time.sleep(0.15)   # Sleep out

        self._cmd(0xEF); self._data([0x03, 0x80, 0x02])
        self._cmd(0xCF); self._data([0x00, 0xC1, 0x30])
        self._cmd(0xED); self._data([0x64, 0x03, 0x12, 0x81])
        self._cmd(0xE8); self._data([0x85, 0x00, 0x78])
        self._cmd(0xCB); self._data([0x39, 0x2C, 0x00, 0x34, 0x02])
        self._cmd(0xF7); self._data([0x20])
        self._cmd(0xEA); self._data([0x00, 0x00])
        self._cmd(0xC0); self._data([0x23])           # Power control
        self._cmd(0xC1); self._data([0x10])
        self._cmd(0xC5); self._data([0x3E, 0x28])     # VCOM
        self._cmd(0xC7); self._data([0x86])
        self._cmd(0x36); self._data([MADCTL])          # 0x40 = RGB portrait
        self._cmd(0x3A); self._data([0x55])            # 16-bit RGB565
        self._cmd(0xB1); self._data([0x00, 0x18])
        self._cmd(0xB6); self._data([0x08, 0x82, 0x27])
        self._cmd(0xF2); self._data([0x00])
        self._cmd(0x26); self._data([0x01])
        self._cmd(0xE0); self._data([
            0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08,
            0x4E, 0xF1, 0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00])
        self._cmd(0xE1); self._data([
            0x00, 0x0E, 0x14, 0x03, 0x11, 0x07,
            0x31, 0xC1, 0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F])
        self._cmd(0x29); time.sleep(0.1)               # Display ON

    # ── Frame push ───────────────────────────────────────────────────────────
    def push(self, img):
        """Send a 240×320 PIL RGB Image to the display as RGB565."""
        self._cmd(0x2A); self._data([0x00, 0x00, 0x00, 0xEF])
        self._cmd(0x2B); self._data([0x00, 0x00, 0x01, 0x3F])
        self._cmd(0x2C)

        lgpio.gpio_write(self._h, TFT_DC, 1)
        time.sleep(DC_DELAY)
        self._cs(0)

        buf = []
        for r, g, b in img.getdata():
            c16 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buf.append(c16 >> 8)
            buf.append(c16 & 0xFF)
        for i in range(0, len(buf), 4096):
            self._spi.xfer2(buf[i:i + 4096])

        self._cs(1)

    # ── Screen 1: Splash ─────────────────────────────────────────────────────
    def draw_splash(self, frame=0):
        img = Image.new("RGB", (W, H), COLOR_BG)
        d   = ImageDraw.Draw(img)

        cx, cy = W // 2, H // 2 - 30
        for i in range(3):
            r     = 40 + i * 25 + (frame % 20) * 2
            alpha = max(0, 255 - i * 60 - (frame % 20) * 8)
            col   = (0, int(220 * alpha / 255), int(180 * alpha / 255))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=2)

        drop_pts = [(cx, cy-35), (cx+22, cy+10), (cx, cy+28), (cx-22, cy+10)]
        d.polygon(drop_pts, fill=COLOR_ACCENT)
        d.ellipse([cx-22, cy-15, cx+22, cy+28], fill=COLOR_ACCENT)

        stripe_y = cy + 50
        bar_w    = W // 18
        for i, col in enumerate(SPECTRUM_COLORS):
            x0 = i * bar_w
            d.rectangle([x0, stripe_y, x0 + bar_w - 1, stripe_y + 6], fill=col)

        f_title = load_font(22, bold=True)
        f_sub   = load_font(13)
        title   = "OIL PURITY ANALYZER"
        d.text(((W - d.textlength(title, font=f_title)) / 2, stripe_y + 16),
               title, font=f_title, fill=COLOR_WHITE)
        sub = "AS7265x · 18-Channel Spectroscopy"
        d.text(((W - d.textlength(sub, font=f_sub)) / 2, stripe_y + 44),
               sub, font=f_sub, fill=COLOR_GRAY)

        btn_y = H - 80
        d.rounded_rectangle([30, btn_y, W-30, btn_y+44],
                             radius=22, fill=COLOR_ACCENT)
        btn_text = "TAP TO SCAN"
        f_btn = load_font(15, bold=True)
        d.text(((W - d.textlength(btn_text, font=f_btn)) / 2, btn_y + 13),
               btn_text, font=f_btn, fill=COLOR_BG)

        d.text((4, H-14), "v1.0 · SparkFun AS7265x",
               font=load_font(9), fill=COLOR_GRAY)
        return img

    # ── Screen 2: Scanning ───────────────────────────────────────────────────
    def draw_scanning(self, frame=0, partial_readings=None):
        img = Image.new("RGB", (W, H), COLOR_BG)
        d   = ImageDraw.Draw(img)

        d.rectangle([0, 0, W, 32], fill=COLOR_PANEL)
        d.text((10, 8), "SCANNING...",
               font=load_font(16, bold=True), fill=COLOR_ACCENT)

        scan_x = int((frame % 60) / 60 * W)
        d.rectangle([max(0, scan_x - 30), 33, scan_x, 34], fill=COLOR_ACCENT)

        if partial_readings:
            self._draw_spectrum_bars(d, partial_readings, y_top=42, height=100)

        dot_y = 160
        for i in range(8):
            angle = (frame * 12 + i * 45) % 360
            rad   = math.radians(angle)
            dx, dy = int(math.cos(rad) * 20), int(math.sin(rad) * 20)
            brightness = int(255 * i / 8)
            d.ellipse([W//2+dx-4, dot_y+dy-4, W//2+dx+4, dot_y+dy+4],
                      fill=(0, brightness, int(brightness * 0.8)))

        f_med = load_font(12)
        for row, text in enumerate([
            "Illuminating with white LED...",
            "Reading 18 spectral channels",
            "Comparing to oil fingerprints",
        ]):
            d.text((10, 195 + row * 17), text, font=f_med, fill=COLOR_GRAY)

        progress = min(1.0, (frame % 90) / 90)
        d.rounded_rectangle([20, 255, W-20, 270], radius=6, fill=COLOR_PANEL)
        prog_w = int((W - 40) * progress)
        if prog_w > 0:
            d.rounded_rectangle([20, 255, 20+prog_w, 270],
                                 radius=6, fill=COLOR_ACCENT)

        d.text((10, H-14), "Do not move the sensor",
               font=load_font(10), fill=COLOR_GRAY)
        return img

    # ── Screen 3: Results ────────────────────────────────────────────────────
    def draw_results(self, result):
        img = Image.new("RGB", (W, H), COLOR_BG)
        d   = ImageDraw.Draw(img)

        f_title = load_font(14, bold=True)
        f_big   = load_font(20, bold=True)
        f_med   = load_font(12)
        f_xs    = load_font(9)

        verdict       = result.get("verdict",          "UNKNOWN")
        verdict_color = result.get("verdict_color",    "gray")
        oil_type      = result.get("oil_type",         "Unknown")
        oil_match     = result.get("oil_match_pct",    0)
        adult_pct     = result.get("adulteration_pct", 0)
        adulterant    = result.get("adulterant",       "None")
        adult_conf    = result.get("adulterant_conf",  0)
        peak_wl       = result.get("peak_wavelength",  0)
        raw           = result.get("raw",              [0] * 18)

        vcol = (COLOR_GREEN  if verdict_color == "green"  else
                COLOR_YELLOW if verdict_color == "yellow" else COLOR_RED)

        # Header
        d.rectangle([0, 0, W, 28], fill=COLOR_PANEL)
        d.text((8, 6), "ANALYSIS COMPLETE", font=f_title, fill=COLOR_ACCENT)
        d.text((W-55, 9), "TAP=RESCAN", font=f_xs, fill=COLOR_GRAY)
        y = 34

        # Oil type badge
        d.rounded_rectangle([8, y, W-8, y+30], radius=6, fill=COLOR_PANEL)
        d.text((14, y+4), "OIL TYPE", font=f_xs, fill=COLOR_GRAY)
        oil_w = d.textlength(oil_type, font=f_title)
        d.text((W-oil_w-14, y+6), oil_type, font=f_title, fill=COLOR_WHITE)
        d.text((14, y+17), f"Match: {oil_match:.0f}%",
               font=f_xs, fill=COLOR_ACCENT)
        y += 36

        # Verdict banner
        d.rounded_rectangle([8, y, W-8, y+36], radius=8, fill=vcol)
        vw = d.textlength(verdict, font=f_big)
        d.text(((W - vw) / 2, y+7), verdict, font=f_big, fill=COLOR_BG)
        y += 42

        # Adulteration gauge
        d.text((10, y), "ADULTERATION LEVEL", font=f_xs, fill=COLOR_GRAY)
        y += 13
        gh = 18
        d.rounded_rectangle([8, y, W-8, y+gh], radius=9, fill=COLOR_PANEL)
        fw = int((W - 16) * min(adult_pct, 100) / 100)
        if fw > 0:
            gc = (COLOR_GREEN  if adult_pct < PURE_THRESHOLD else
                  COLOR_YELLOW if adult_pct < MILD_THRESHOLD else COLOR_RED)
            d.rounded_rectangle([8, y, 8+fw, y+gh], radius=9, fill=gc)
        pct_txt = f"{adult_pct:.1f}%"
        pw = d.textlength(pct_txt, font=f_title)
        d.text(((W - pw) / 2, y+2), pct_txt, font=f_title,
               fill=COLOR_BG if fw > W//2 else COLOR_WHITE)
        y += gh + 4
        d.text((8, y), "0%",    font=f_xs, fill=COLOR_GRAY)
        d.text((W-28, y), "100%", font=f_xs, fill=COLOR_GRAY)
        y += 14

        # Adulterant
        if adulterant != "None":
            d.rounded_rectangle([8,y,W-8,y+24], radius=5, fill=(50,20,20))
            d.text((12,y+4),
                   f"Adulterant: {adulterant}  ({adult_conf:.0f}% conf.)",
                   font=f_med, fill=COLOR_RED)
        else:
            d.rounded_rectangle([8,y,W-8,y+24], radius=5, fill=(10,40,20))
            d.text((12,y+4), "No adulterant detected",
                   font=f_med, fill=COLOR_GREEN)
        y += 30

        # Spectrum mini-bars
        d.text((10, y), "SPECTRAL PROFILE", font=f_xs, fill=COLOR_GRAY)
        y += 12
        self._draw_spectrum_bars(d, raw, y_top=y, height=55)
        y += 60

        # Stats row
        stats = [
            ("PEAK",      f"{peak_wl}nm"),
            ("CHANNELS",  "18"),
            ("INTENSITY", f"{result.get('total_intensity', 0):.1f}"),
        ]
        box_w = (W - 16) // 3
        for i, (label, val) in enumerate(stats):
            bx = 8 + i * (box_w + 4)
            d.rounded_rectangle([bx,y,bx+box_w,y+34], radius=5, fill=COLOR_PANEL)
            lw = d.textlength(label, font=f_xs)
            d.text((bx + (box_w - lw) / 2, y+3),  label, font=f_xs,  fill=COLOR_GRAY)
            vw2 = d.textlength(val, font=f_med)
            d.text((bx + (box_w - vw2) / 2, y+15), val,   font=f_med, fill=COLOR_ACCENT2)
        y += 40

        # Rescan button
        d.rounded_rectangle([30,y,W-30,y+36], radius=18,
                             outline=COLOR_ACCENT, width=2)
        btn = "SCAN AGAIN"
        bw  = d.textlength(btn, font=f_title)
        d.text(((W - bw) / 2, y+10), btn, font=f_title, fill=COLOR_ACCENT)
        return img

    # ── Helper: spectrum bar graph ────────────────────────────────────────────
    def _draw_spectrum_bars(self, d, raw, y_top, height):
        if not raw:
            return
        max_val = max(raw) or 1
        bar_w   = max(1, (W - 16) // len(raw))
        for i, val in enumerate(raw):
            bh  = int((val / max_val) * (height - 14))
            col = SPECTRUM_COLORS[i % len(SPECTRUM_COLORS)]
            x0  = 8 + i * bar_w
            if bh > 0:
                d.rectangle([x0, y_top+height-14-bh,
                              x0+bar_w-2, y_top+height-14], fill=col)
            if i % 3 == 0:
                d.text((x0, y_top+height-12),
                       str(WAVELENGTHS[i]), font=load_font(7), fill=COLOR_GRAY)

    # ── Cleanup ──────────────────────────────────────────────────────────────
    def cleanup(self):
        if self._h:
            lgpio.gpio_write(self._h, TFT_BL, 0)
            lgpio.gpiochip_close(self._h)
            self._h = None
        if self._spi:
            self._spi.close()
            self._spi = None
