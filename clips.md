# Clips

No clip is committed. `bench.py` takes them from the model archive after the
archive's sha256 is verified, then re-verifies each wav.

| clip | source | licence | sha256 |
|---|---|---|---|
| `test_wavs/yue.wav` (5.148 s, Cantonese) | bundled in the k2-fsa SenseVoice int8 archive | no separate clip licence stated; ships with the model package (FunASR Model License v1.1 applies to the model) | `0960b2db54ae202071d250e6462fbf74a3c863f0e3e7f01273e4939c996875a0` |
| `test_wavs/en.wav` (7.152 s, English) | same archive | same | `eb1eb008904465b74c304aad8342e8c7d3c6e61ffe9f66adcaca9cf0f76a93f4` |
| `test_wavs/zh.wav` (5.592 s, Mandarin; integrity-checked, not benchmarked) | same archive | same | `b77f1794fe374a0ba1ee1dc458bfaf9349496cbbfc32780c50ba3c5a7ad8e373` |
| mix-10s | `yue.wav` followed by `en.wav`, cut at exactly 160000 samples (10.0 s at 16 kHz), built in memory | derived from the two above | not stored (deterministic from the two hashes) |

Archive: `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2`,
sha256 `7d1efa2138a65b0b488df37f8b89e3d91a60676e416f515b952358d83dfd347e`.

Why not Common Voice: its downloads need an authenticated account and click-through, which a
secret-free public workflow cannot do. The bundled wavs are fetched with the
model, so the repo redistributes no audio.
