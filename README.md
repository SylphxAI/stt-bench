# stt-bench

Speech-to-text latency on GitHub-hosted runners (free for public repos):
SenseVoice-Small int8 through [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)
(Apache-2.0), CPU only.

- Runners: `macos-14` (Apple M1, 3 vCPU), `windows-latest` (x64), `ubuntu-latest` (x64, reference).
- Method: batch (offline) decode, 4 threads and the runner's vCPU count (one set when equal),
  5 warm-up then 30 timed runs, `decode_stream` only. Reports p50 / p95 / max ms and RTF
  (p50 decode time / audio duration) for a 10.0 s clip, plus the two source clips.
- Output: `result-<runner>.json` artifact and a job summary labelled with the runner and its
  CPU model (read at run time via `sysctl` / `wmic`-or-CIM / `lscpu`).
- Run: Actions, `bench`, Run workflow. Triggered only by `workflow_dispatch`; `contents: read`;
  no secrets; actions pinned to commit SHAs.
- Pins: `sherpa-onnx` and `sherpa-onnx-core` 1.13.8 wheels, installed with `--require-hashes`
  (`requirements.txt`); model archive sha256 verified in `bench.py`. Clips: see [clips.md](clips.md).

Numbers describe shared VMs and vary run to run; they are not a statement about bare-metal hardware.

Local: `pip install --require-hashes -r requirements.txt && python bench.py --label local`
(Python 3.12; hashes cover cp312 wheels for Linux x86_64, macOS, Windows x64).

## Attribution

Model: SenseVoice-Small (FunAudioLLM / Alibaba, via FunASR), ONNX int8 export by k2-fsa,
used under the [FunASR Model License v1.1](https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE)
(source: https://github.com/FunAudioLLM/SenseVoice). The model is downloaded at run time and not
redistributed here. sherpa-onnx is Apache-2.0. This repository's own code is MIT (see LICENSE).
