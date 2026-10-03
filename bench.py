#!/usr/bin/env python3
"""SenseVoice-Small int8 batch-decode latency bench (sherpa-onnx, CPU).

Downloads the model, verifies sha256, builds a 10.0 s clip from the model's
bundled test wavs, then times OfflineRecognizer.decode_stream.
"""
import argparse, hashlib, json, os, platform, shutil, statistics, subprocess
import sys, tarfile, time, urllib.request, wave

MODEL_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
             "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2")
MODEL_SHA256 = "7d1efa2138a65b0b488df37f8b89e3d91a60676e416f515b952358d83dfd347e"
MODEL_DIR = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
# sha256 of the bundled test wavs (also recorded in clips.md)
WAV_SHA256 = {
    "yue.wav": "0960b2db54ae202071d250e6462fbf74a3c863f0e3e7f01273e4939c996875a0",
    "en.wav": "eb1eb008904465b74c304aad8342e8c7d3c6e61ffe9f66adcaca9cf0f76a93f4",
    "zh.wav": "b77f1794fe374a0ba1ee1dc458bfaf9349496cbbfc32780c50ba3c5a7ad8e373",
}
SR = 16000
CLIP10_SAMPLES = 10 * SR
WARMUP, RUNS = 5, 30


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch_model(work):
    os.makedirs(work, exist_ok=True)
    tgz = os.path.join(work, "model.tar.bz2")
    if not os.path.exists(tgz):
        print("downloading model", flush=True)
        urllib.request.urlretrieve(MODEL_URL, tgz)
    got = sha256(tgz)
    if got != MODEL_SHA256:
        sys.exit(f"model sha256 mismatch: {got}")
    d = os.path.join(work, MODEL_DIR)
    if not os.path.isdir(d):
        with tarfile.open(tgz, "r:bz2") as t:
            t.extractall(work, filter="data")
    for name, want in WAV_SHA256.items():
        got = sha256(os.path.join(d, "test_wavs", name))
        if got != want:
            sys.exit(f"{name} sha256 mismatch: {got}")
    return d


def read_wav(path):
    with wave.open(path) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2
        raw = w.readframes(w.getnframes())
    import array
    a = array.array("h")
    a.frombytes(raw)
    if sys.byteorder == "big":
        a.byteswap()
    return [x / 32768.0 for x in a]


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception:
        return ""


def cpu_model():
    s = platform.system()
    if s == "Darwin":
        return run(["sysctl", "-n", "machdep.cpu.brand_string"]) or "unknown"
    if s == "Windows":
        out = run(["wmic", "cpu", "get", "name"])
        lines = [l.strip() for l in out.splitlines() if l.strip() and l.strip() != "Name"]
        if not lines:
            out = run(["powershell", "-NoProfile", "-Command",
                       "(Get-CimInstance Win32_Processor).Name"])
            lines = [l.strip() for l in out.splitlines() if l.strip()]
        return lines[0] if lines else "unknown"
    for l in run(["lscpu"]).splitlines():
        if l.startswith("Model name"):
            return l.split(":", 1)[1].strip()
    return "unknown"


def pct(sorted_ms, p):
    # nearest-rank percentile
    k = max(0, min(len(sorted_ms) - 1, int(-(-p / 100 * len(sorted_ms) // 1)) - 1))
    return sorted_ms[k]


def bench(d, samples, threads):
    import sherpa_onnx
    rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=os.path.join(d, "model.int8.onnx"),
        tokens=os.path.join(d, "tokens.txt"),
        num_threads=threads, use_itn=True, language="auto", provider="cpu")
    ms, text = [], ""
    for i in range(WARMUP + RUNS):
        s = rec.create_stream()
        s.accept_waveform(SR, samples)
        t0 = time.perf_counter()
        rec.decode_stream(s)
        dt = (time.perf_counter() - t0) * 1000
        text = s.result.text
        if i >= WARMUP:
            ms.append(dt)
    srt = sorted(ms)
    dur = len(samples) / SR
    return {"threads": threads, "audio_s": dur, "runs": RUNS, "warmup": WARMUP,
            "p50_ms": pct(srt, 50), "p95_ms": pct(srt, 95), "max_ms": srt[-1],
            "mean_ms": statistics.fmean(ms), "rtf_p50": pct(srt, 50) / 1000 / dur,
            "text": text}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="human label for the runner")
    ap.add_argument("--out", default="result.json")
    ap.add_argument("--work", default="work")
    a = ap.parse_args()

    d = fetch_model(a.work)
    wavs = {n: read_wav(os.path.join(d, "test_wavs", n)) for n in WAV_SHA256}
    clip10 = (wavs["yue.wav"] + wavs["en.wav"])[:CLIP10_SAMPLES]
    assert len(clip10) == CLIP10_SAMPLES
    clips = {"mix-10s (yue+en, cut at 10.0 s)": clip10,
             "yue.wav": wavs["yue.wav"], "en.wav": wavs["en.wav"]}

    ncpu = os.cpu_count() or 1
    thread_set = sorted({4, ncpu})
    import sherpa_onnx
    res = {"label": a.label, "cpu_model": cpu_model(), "vcpus": ncpu,
           "os": platform.platform(), "python": platform.python_version(),
           "sherpa_onnx": sherpa_onnx.__version__, "model_sha256": MODEL_SHA256,
           "results": []}
    for t in thread_set:
        for name, smp in clips.items():
            r = bench(d, smp, t)
            r["clip"] = name
            res["results"].append(r)
            print(f"{name} threads={t} p50={r['p50_ms']:.1f} p95={r['p95_ms']:.1f} "
                  f"max={r['max_ms']:.1f} rtf={r['rtf_p50']:.4f}", flush=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

    lines = [f"### {a.label}", "",
             f"CPU: {res['cpu_model']} | vCPUs: {ncpu} | {res['os']} | "
             f"sherpa-onnx {res['sherpa_onnx']}", "",
             f"{WARMUP} warm-up + {RUNS} timed decodes, CPU, batch (offline) decode_stream only.", "",
             "| clip | threads | audio s | p50 ms | p95 ms | max ms | RTF (p50) |",
             "|---|---|---|---|---|---|---|"]
    for r in res["results"]:
        lines.append(f"| {r['clip']} | {r['threads']} | {r['audio_s']:.1f} | {r['p50_ms']:.1f} | "
                     f"{r['p95_ms']:.1f} | {r['max_ms']:.1f} | {r['rtf_p50']:.4f} |")
    md = "\n".join(lines) + "\n"
    print(md)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(md)


if __name__ == "__main__":
    main()
