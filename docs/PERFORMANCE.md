# Measurements

MacBook Pro **M4 Pro** + Quest 3 · Meta Mac app **110.0.0.1.108** · unmodified Quest client

**120 FPS is the requested target. Visible 120 Hz streaming is not verified.** These measurements used the earlier local 120 FPS patch build; they are not a benchmark of each packaged DMG.

## USB 3 · October 14, 2026

Native USB (`highwind_Usb`), negotiated at **5 Gbit/s**. Mac capture target: **120 FPS**.

| Measurement | Ultrawide | Compat |
|---|---:|---:|
| Encoded resolution | 3840 × 1080 | 1920 × 1080 |
| Average encoded FPS | 67.65 | 63.84 |
| One-second FPS range | 41.00–97.95 | 1.00–109.00 |
| Average encoding time | 9.82 ms | 5.72 ms |
| Average video bitrate | 1.64 Mbit/s | 0.70 Mbit/s |
| Configured bitrate target | 20 Mbit/s | 20 Mbit/s |
| Quest display / compositor | 90 Hz | 90 Hz |
| Sample length | 120 seconds | 90 seconds |

Windows: 18:44:01–18:46:00 and 18:51:03–18:52:32 EEST. A later 19-second Compat sample averaged **56.20 FPS** (40.64–67.06). The encoder confirmed 1920 × 1080 after the Compat switch, regardless of the previously reported Mac display mode.

These were normal desktop sessions with different activity, not a controlled motion benchmark. The averages do not establish that Compat is slower; its encoding work decreased. Idle or changing content can affect frame production.

The 5 Gbit/s figure is negotiated link capacity, not measured transfer throughput. Video bitrate excludes protocol overhead. Encoding time excludes transport, decoding and display latency.

Quest refresh was checked through SurfaceFlinger (11,111,111 ns) and Horizon runtime counters. The remote desktop surface returned zero per-frame presentation timestamps, so **distinct video frames displayed and end-to-end latency remain unmeasured**.

## Earlier session · October 13

At 1920 × 1080, Mac frame submissions averaged **59.5 FPS**, with **37.2–83.8 FPS** across roughly five-second intervals. The Quest runtime was **72 Hz**. Submission counters and interval lengths differ from the encoder samples above.

## Does 120 Hz require a modified client?

Not established. The Quest must present at 120 Hz, and the Mac must supply frames consistently enough to benefit. A 120 Hz Mac display mode alone does neither.

Meta documents a temporary `debug.oculus.refreshRate` setting, including 120 Hz on Quest 3. It resets on reboot. Testing that setting with the stock client is the next step; whether this Virtual Display session honors it is unverified. Client patching is only a hypothesis until a client-specific limit is identified. [Meta: system properties](https://developers.meta.com/vr/documentation/native/android/ts-systemproperties/)

CI checks the build and packaging. It does not measure headset performance.
