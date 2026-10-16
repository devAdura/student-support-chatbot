"""Reproducible development benchmark, not a replacement for a user study."""

import json
import sys
import time
import statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chatbot_engine import ChatbotEngine

root = Path(__file__).resolve().parents[1]
cases = json.loads((root / "tests/evaluation_cases.json").read_text())
bot = ChatbotEngine()
results = []
for query, expected in cases:
    start = time.perf_counter()
    r = bot.match(query)
    elapsed = (time.perf_counter() - start) * 1000
    results.append(
        dict(
            query=query,
            expected=expected,
            actual=r["intent"],
            correct=r["intent"] == expected,
            latency_ms=round(elapsed, 3),
        )
    )
latencies = sorted(r["latency_ms"] for r in results)
report = dict(
    dataset="44 manually authored development cases inspected during tuning; not an independent held-out test or a representative student survey",
    total=len(results),
    correct=sum(r["correct"] for r in results),
    accuracy_percent=round(100 * sum(r["correct"] for r in results) / len(results), 2),
    average_latency_ms=round(statistics.mean(latencies), 3),
    p95_latency_ms=latencies[int(0.95 * (len(latencies) - 1))],
    results=results,
)
print(json.dumps(report, indent=2))
if "--output" in sys.argv:
    target = Path(sys.argv[sys.argv.index("--output") + 1])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
# The benchmark reports errors honestly; use --check for a minimum regression gate.
if "--check" in sys.argv and report["accuracy_percent"] < 85:
    sys.exit(1)
