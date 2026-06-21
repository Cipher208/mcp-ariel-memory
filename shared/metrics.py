"""
Metrics — Prometheus-compatible metrics collection
"""
import time
import threading
from typing import Dict, Any
from collections import defaultdict


class MetricsCollector:
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = defaultdict(list)
        self._start_time = time.time()
        self._lock = threading.Lock()

    def inc(self, name: str, value: int = 1):
        with self._lock:
            self._counters[name] += value

    def gauge(self, name: str, value: float):
        with self._lock:
            self._gauges[name] = value

    def histogram(self, name: str, value: float):
        with self._lock:
            self._histograms[name].append(value)
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-500:]

    def render_prometheus(self) -> str:
        lines = []
        lines.append("# HELP ariel_memory_uptime_seconds Server uptime")
        lines.append("# TYPE ariel_memory_uptime_seconds gauge")
        lines.append(f"ariel_memory_uptime_seconds {time.time() - self._start_time:.1f}")

        with self._lock:
            for name, val in sorted(self._counters.items()):
                lines.append(f"# TYPE ariel_memory_{name} counter")
                lines.append(f"ariel_memory_{name} {val}")

            for name, val in sorted(self._gauges.items()):
                lines.append(f"# TYPE ariel_memory_{name} gauge")
                lines.append(f"ariel_memory_{name} {val}")

            for name, vals in sorted(self._histograms.items()):
                if vals:
                    lines.append(f"# TYPE ariel_memory_{name}_summary summary")
                    s = sorted(vals)
                    lines.append(f"ariel_memory_{name}_summary{{quantile=\"0.5\"}} {s[len(s)//2]}")
                    lines.append(f"ariel_memory_{name}_summary{{quantile=\"0.9\"}} {s[int(len(s)*0.9)]}")
                    lines.append(f"ariel_memory_{name}_summary{{quantile=\"0.99\"}} {s[int(len(s)*0.99)]}")
                    lines.append(f"ariel_memory_{name}_count {len(vals)}")

        return "\n".join(lines) + "\n"

    def render_json(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "uptime_seconds": time.time() - self._start_time,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    k: {"count": len(v), "sum": sum(v), "avg": sum(v)/len(v) if v else 0}
                    for k, v in self._histograms.items()
                },
            }


metrics = MetricsCollector()
