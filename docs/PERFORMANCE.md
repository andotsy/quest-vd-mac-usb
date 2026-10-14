# Measurements

MacBook Pro M4 + Quest 3 · Meta 110.0.0.1.108 · unmodified Quest client · October 13, 2026

| Stage | Observed |
|---|---|
| Transport | Native USB (`highwind_Usb`) |
| Stream resolution | 1920 × 1080 |
| Capture target / display mode | 120 FPS / 120 Hz |
| Mac frame submissions | 37.2–83.8 FPS; aggregate 59.5 FPS |
| Quest Horizon runtime | 72 Hz |

The submission samples covered varying desktop activity, not continuous motion. They don’t measure distinct frames displayed by the headset.

**The patch requests 120 FPS; it doesn’t force the Quest compositor to 120 Hz.** Delivered 1440p at 120 Hz hasn’t been established. CI checks the build, not headset performance.
