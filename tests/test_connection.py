"""Tests for connection quality data."""

from unifi_network_maps.model.connection import ConnectionInfo, classify_signal_quality


class TestClassifySignalQuality:
    """Test signal quality classification thresholds."""

    def test_none_returns_none(self) -> None:
        assert classify_signal_quality(None) is None

    def test_excellent_above_minus_50(self) -> None:
        assert classify_signal_quality(-45) == "excellent"
        assert classify_signal_quality(-30) == "excellent"
        assert classify_signal_quality(-49) == "excellent"

    def test_good_boundary_at_minus_50(self) -> None:
        assert classify_signal_quality(-50) == "good"

    def test_good_range(self) -> None:
        assert classify_signal_quality(-55) == "good"
        assert classify_signal_quality(-64) == "good"

    def test_fair_boundary_at_minus_65(self) -> None:
        assert classify_signal_quality(-65) == "fair"

    def test_fair_range(self) -> None:
        assert classify_signal_quality(-70) == "fair"
        assert classify_signal_quality(-74) == "fair"

    def test_poor_boundary_at_minus_75(self) -> None:
        assert classify_signal_quality(-75) == "poor"

    def test_poor_range(self) -> None:
        assert classify_signal_quality(-80) == "poor"
        assert classify_signal_quality(-90) == "poor"


class TestConnectionInfo:
    """Test ConnectionInfo dataclass."""

    def test_default_values(self) -> None:
        conn = ConnectionInfo()
        assert conn.signal_dbm is None
        assert conn.noise_dbm is None
        assert conn.tx_rate_mbps is None
        assert conn.rx_rate_mbps is None
        assert conn.satisfaction is None
        assert conn.quality is None

    def test_with_values(self) -> None:
        conn = ConnectionInfo(
            signal_dbm=-65,
            noise_dbm=-95,
            tx_rate_mbps=866,
            rx_rate_mbps=433,
            satisfaction=98,
            quality="good",
        )
        assert conn.signal_dbm == -65
        assert conn.noise_dbm == -95
        assert conn.tx_rate_mbps == 866
        assert conn.rx_rate_mbps == 433
        assert conn.satisfaction == 98
        assert conn.quality == "good"

    def test_frozen(self) -> None:
        conn = ConnectionInfo(signal_dbm=-65)
        try:
            conn.signal_dbm = -70  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass  # Expected for frozen dataclass
