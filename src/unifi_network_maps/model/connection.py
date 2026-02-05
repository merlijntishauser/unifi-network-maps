"""Connection quality data for wireless clients."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionInfo:
    """Quality metrics for a wireless client connection."""

    signal_dbm: int | None = None
    noise_dbm: int | None = None
    tx_rate_mbps: int | None = None
    rx_rate_mbps: int | None = None
    satisfaction: int | None = None
    quality: str | None = None


def classify_signal_quality(signal_dbm: int | None) -> str | None:
    """Classify wireless signal strength into quality categories.

    Thresholds:
        excellent: > -50 dBm
        good: -50 to -65 dBm
        fair: -65 to -75 dBm
        poor: < -75 dBm
    """
    if signal_dbm is None:
        return None
    if signal_dbm > -50:
        return "excellent"
    if signal_dbm > -65:
        return "good"
    if signal_dbm > -75:
        return "fair"
    return "poor"
