# What was actually measured

Native USB was observed on a MacBook Pro M4 and Quest 3 using the official Quest
client and the patched Meta Mac host 110.0.0.1.108. The client was unmodified.

| Stage | Observation, 2026-10-13 |
|---|---|
| Transport | `highwind_Usb` native USB session |
| Desktop resolution in this run | 1920 × 1080 |
| Mac capture target | 120 FPS reported by the capture configuration |
| Virtual display mode | 120 Hz requested |
| Mac submitted frames | 37.2–83.8 FPS across 16 approximately five-second samples; aggregate 59.5 FPS |
| Quest Horizon runtime | 72 Hz; corroborated by runtime and compositor refresh-period readings |

Desktop activity varied. This was not a continuous-motion throughput benchmark.
Frame submissions are not a count of distinct decoded or displayed frames.
The receiver did not expose useful per-frame presentation timestamps in this run.

The patch changes capture-target, display-mode, and encoder-expectation
instructions. It does not force the Quest compositor or panel to 120 Hz.
1440p at 120 Hz has not been established. Do not infer delivered performance
from a display-mode label, encoder setting, perceived smoothness, or a CI pass.

CI checks the software artifact, not end-to-end headset performance. For a useful
future benchmark, record upstream and headset versions, negotiated transport,
USB link speed, resolution, continuous-motion content, capture/submission rates,
decoder/presentation timestamps, and headset compositor refresh rate together.
