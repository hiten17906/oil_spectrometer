# main.py — Oil Adulteration Spectrometer — Entry Point
#
# State machine:
#   SPLASH → (tap) → SCANNING → (done) → RESULT → (tap) → SPLASH
#
# Hardware: Raspberry Pi 5 + SparkFun AS7265x + Smartelex 2.4" ILI9341 TFT

import time
import threading

from config  import TFT_HEIGHT
from sensor  import SpectralSensor
from display import OilDisplay
from touch   import TouchScreen
from model   import analyze

# ─── States ──────────────────────────────────────────────────────────────────
STATE_SPLASH   = "splash"
STATE_SCANNING = "scanning"
STATE_RESULT   = "result"

state       = STATE_SPLASH
result_data = None
scan_lock   = threading.Lock()
frame       = 0

# ─── Hardware init ────────────────────────────────────────────────────────────
sensor  = SpectralSensor()
display = OilDisplay()
touch   = TouchScreen()

sensor_ok = sensor.begin()
display.begin()
touch.begin()

print("[Main] All hardware initialized. Starting UI loop.")

# ─── Background scan thread ───────────────────────────────────────────────────
def do_scan():
    global state, result_data
    _, raw_list = sensor.read()
    result = analyze(raw_list)
    with scan_lock:
        result_data = result
        state = STATE_RESULT
    print(f"[Scan] {result['oil_type']} | "
          f"Adulteration: {result['adulteration_pct']}% | "
          f"{result['verdict']}")

# ─── Touch handler ────────────────────────────────────────────────────────────
def handle_touch(x, y):
    global state
    if state == STATE_SPLASH:
        # Bottom area = TAP TO SCAN button
        if y > TFT_HEIGHT - 100:
            state = STATE_SCANNING
            threading.Thread(target=do_scan, daemon=True).start()
    elif state == STATE_RESULT:
        # Bottom area = SCAN AGAIN button
        if y > TFT_HEIGHT - 80:
            state = STATE_SPLASH

# ─── Main loop ────────────────────────────────────────────────────────────────
try:
    while True:
        pt = touch.get_touch()
        if pt:
            handle_touch(*pt)

        if state == STATE_SPLASH:
            img = display.draw_splash(frame=frame)

        elif state == STATE_SCANNING:
            _, partial = sensor.read() if sensor_ok else (None, [0] * 18)
            img = display.draw_scanning(frame=frame, partial_readings=partial)

        elif state == STATE_RESULT:
            with scan_lock:
                img = display.draw_results(result_data)

        display.push(img)
        frame += 1
        time.sleep(0.05)   # ~20 FPS target (actual ~2–3 FPS at 500 kHz SPI)

except KeyboardInterrupt:
    print("\n[Main] Shutting down.")

finally:
    display.cleanup()
    touch.cleanup()
    print("[Main] Bye!")
