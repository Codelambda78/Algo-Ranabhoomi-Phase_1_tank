# Algo Ranabhoomi: Phase 1

This repository contains four algorithm challenge tracks:

- [Autoclave](autoclave/README.md)
- [Monitors](monitors/README.md)
- [Relief](relief/README.md)
- [Tanker Run](tanker/README.md)

Each track is self-contained and includes its problem statement, starter solver, validator, benchmark harness, and run instructions.

## Tanker Run solver

The custom solver is `tanker/adapters/mine.py`. It builds feasible tanker routes and improves them with local search, capacity-safe route exchanges, and deterministic randomized restarts. Every village must appear exactly once, and each route must stay within the tanker capacity.

### Run the checks

From the repository root in PowerShell:

```powershell
Set-Location tanker
python self_check.py
python run.py --adapter adapters.mine:MySolver --out mine-report.json
```

The first command checks two representative public instances using `MySolver` by default. The second runs the full six-instance public benchmark, prints the per-instance results and total score, and writes detailed results to `tanker/mine-report.json`.

Pass `--adapter module:Class` to `self_check.py` when you want to test a different solver. The full benchmark command names `MySolver` explicitly.

### Recorded public result

The latest benchmark report records a score of **90.63/100** across the six public Tanker instances. All six completed without crashes, overruns, or rejected candidate routes in that run. Runtime and score may vary slightly between machines.

| Instance | Villages | Route cost | Score |
| --- | ---: | ---: | ---: |
| tanker-01 | 40 | 6,325 | 1.000 |
| tanker-02 | 70 | 9,630 | 0.976 |
| tanker-03 | 110 | 11,851 | 0.893 |
| tanker-04 | 150 | 14,582 | 0.918 |
| tanker-05 | 60 | 10,382 | 0.931 |
| tanker-06 | 120 | 21,778 | 0.751 |

See [`tanker/mine-report.json`](tanker/mine-report.json) for the complete benchmark history and score breakdown. The private evaluation suite is not included in this repository; public benchmark results do not guarantee a particular private score.
