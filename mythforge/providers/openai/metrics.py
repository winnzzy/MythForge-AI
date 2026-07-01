"""
Provider metrics — operational telemetry for the OpenAI provider.

Tracks latency, throughput, error rates, and token usage.
Thread-safe for concurrent use.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RequestMetric:
    """A single request metric record."""

    timestamp: float = 0.0
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""
    success: bool = True
    error_type: Optional[str] = None
    streamed: bool = False


class ProviderMetrics:
    """Tracks operational metrics for the OpenAI provider.

    Thread-safe — can be used from concurrent async tasks.

    Usage::

        metrics = ProviderMetrics()

        # Record a successful request
        metrics.record_request(
            latency_ms=1234.5,
            tokens_in=100,
            tokens_out=50,
            model="gpt-4o",
            success=True,
        )

        # Get summary
        summary = metrics.summary()
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._lock = threading.Lock()
        self._max_history = max_history
        self._history: List[RequestMetric] = []
        self._total_requests: int = 0
        self._total_errors: int = 0
        self._total_streamed: int = 0
        self._total_latency_ms: float = 0.0
        self._latencies: List[float] = []
        self._errors_by_type: Dict[str, int] = {}
        self._requests_by_model: Dict[str, int] = {}

    def record_request(
        self,
        latency_ms: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        model: str = "",
        success: bool = True,
        error_type: Optional[str] = None,
        streamed: bool = False,
    ) -> None:
        """Record a single API request metric.

        Parameters
        ----------
        latency_ms:
            Request latency in milliseconds.
        tokens_in:
            Input tokens consumed.
        tokens_out:
            Output tokens generated.
        model:
            Model used.
        success:
            Whether the request succeeded.
        error_type:
            Error type if failed.
        streamed:
            Whether streaming was used.
        """
        metric = RequestMetric(
            timestamp=time.time(),
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=model,
            success=success,
            error_type=error_type,
            streamed=streamed,
        )

        with self._lock:
            self._history.append(metric)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            self._total_requests += 1
            self._total_latency_ms += latency_ms
            self._latencies.append(latency_ms)

            if not success:
                self._total_errors += 1
                if error_type:
                    self._errors_by_type[error_type] = (
                        self._errors_by_type.get(error_type, 0) + 1
                    )

            if streamed:
                self._total_streamed += 1

            if model:
                self._requests_by_model[model] = (
                    self._requests_by_model.get(model, 0) + 1
                )

    @property
    def total_requests(self) -> int:
        """Total number of recorded requests."""
        with self._lock:
            return self._total_requests

    @property
    def total_errors(self) -> int:
        """Total number of failed requests."""
        with self._lock:
            return self._total_errors

    @property
    def error_rate(self) -> float:
        """Error rate as a fraction (0.0–1.0)."""
        with self._lock:
            if self._total_requests == 0:
                return 0.0
            return self._total_errors / self._total_requests

    @property
    def average_latency_ms(self) -> float:
        """Average request latency in milliseconds."""
        with self._lock:
            if not self._latencies:
                return 0.0
            return self._total_latency_ms / len(self._latencies)

    @property
    def p50_latency_ms(self) -> float:
        """Median latency in milliseconds."""
        return self._percentile(50)

    @property
    def p95_latency_ms(self) -> float:
        """95th percentile latency in milliseconds."""
        return self._percentile(95)

    @property
    def p99_latency_ms(self) -> float:
        """99th percentile latency in milliseconds."""
        return self._percentile(99)

    def _percentile(self, p: int) -> float:
        """Calculate the p-th percentile of latencies."""
        with self._lock:
            if not self._latencies:
                return 0.0
            sorted_latencies = sorted(self._latencies)
            idx = int(len(sorted_latencies) * p / 100)
            idx = min(idx, len(sorted_latencies) - 1)
            return sorted_latencies[idx]

    def summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics.

        Returns
        -------
        Dict[str, Any]
            Comprehensive metrics summary.
        """
        with self._lock:
            return {
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "error_rate": round(self.error_rate, 4),
                "total_streamed": self._total_streamed,
                "average_latency_ms": round(self.average_latency_ms, 2),
                "p50_latency_ms": round(self.p50_latency_ms, 2),
                "p95_latency_ms": round(self.p95_latency_ms, 2),
                "p99_latency_ms": round(self.p99_latency_ms, 2),
                "errors_by_type": dict(self._errors_by_type),
                "requests_by_model": dict(self._requests_by_model),
            }

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent error records.

        Parameters
        ----------
        limit:
            Maximum number of errors to return.

        Returns
        -------
        List[Dict[str, Any]]
            Recent error details.
        """
        with self._lock:
            errors = [
                {
                    "timestamp": m.timestamp,
                    "latency_ms": m.latency_ms,
                    "model": m.model,
                    "error_type": m.error_type,
                }
                for m in reversed(self._history)
                if not m.success
            ]
            return errors[:limit]

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._history.clear()
            self._total_requests = 0
            self._total_errors = 0
            self._total_streamed = 0
            self._total_latency_ms = 0.0
            self._latencies.clear()
            self._errors_by_type.clear()
            self._requests_by_model.clear()