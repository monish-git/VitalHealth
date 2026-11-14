"""
tests/test_heart_rate_engine.py
Run with: python -m pytest tests/ -v
"""

import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.heart_rate_engine import HeartRateEngine
from core.frame_extractor import FrameExtractor, FrameChannels


def make_synthetic_signal(bpm: float, sample_rate: int = 30, duration: int = 10) -> list:
    """Generate a clean synthetic PPG signal at a given BPM."""
    t = np.linspace(0, duration, sample_rate * duration)
    freq = bpm / 60.0
    # Simulate reddish finger: baseline ~180 + pulsing signal
    signal = 180 + 15 * np.sin(2 * np.pi * freq * t)
    signal += np.random.normal(0, 1.5, len(signal))  # small noise
    return signal.tolist()


class TestHeartRateEngine:

    def test_returns_none_before_enough_frames(self):
        engine = HeartRateEngine(sample_rate=30)
        for _ in range(100):  # only 3.3s, need 5s
            engine.add_frame(180.0, 120.0, 60.0)
        assert engine.get_result() is None

    def test_returns_result_after_enough_frames(self):
        engine = HeartRateEngine(sample_rate=30)
        signal = make_synthetic_signal(bpm=72)
        for v in signal:
            engine.add_frame(v, v * 0.7, v * 0.4)
        result = engine.get_result()
        assert result is not None

    def test_bpm_accuracy_72(self):
        """Should detect ~72 BPM within ±10 BPM."""
        engine = HeartRateEngine(sample_rate=30)
        signal = make_synthetic_signal(bpm=72)
        for v in signal:
            engine.add_frame(v, v * 0.7, v * 0.4)
        result = engine.get_result()
        assert result is not None
        assert abs(result.bpm - 72) < 10, f"Expected ~72, got {result.bpm}"

    def test_bpm_accuracy_60(self):
        """Should detect ~60 BPM within ±10 BPM."""
        engine = HeartRateEngine(sample_rate=30)
        signal = make_synthetic_signal(bpm=60)
        for v in signal:
            engine.add_frame(v, v * 0.7, v * 0.4)
        result = engine.get_result()
        assert result is not None
        assert abs(result.bpm - 60) < 10, f"Expected ~60, got {result.bpm}"

    def test_bpm_accuracy_100(self):
        """Should detect ~100 BPM within ±10 BPM."""
        engine = HeartRateEngine(sample_rate=30)
        signal = make_synthetic_signal(bpm=100)
        for v in signal:
            engine.add_frame(v, v * 0.7, v * 0.4)
        result = engine.get_result()
        assert result is not None
        assert abs(result.bpm - 100) < 10, f"Expected ~100, got {result.bpm}"

    def test_spo2_in_valid_range(self):
        engine = HeartRateEngine(sample_rate=30)
        signal = make_synthetic_signal(bpm=72)
        for v in signal:
            engine.add_frame(v, v * 0.7, v * 0.4)
        result = engine.get_result()
        assert result is not None
        assert 90.0 <= result.spo2 <= 100.0

    def test_confidence_is_valid(self):
        engine = HeartRateEngine(sample_rate=30)
        signal = make_synthetic_signal(bpm=72)
        for v in signal:
            engine.add_frame(v, v * 0.7, v * 0.4)
        result = engine.get_result()
        assert result is not None
        assert 0.0 <= result.confidence <= 1.0

    def test_hrv_non_negative(self):
        engine = HeartRateEngine(sample_rate=30)
        signal = make_synthetic_signal(bpm=72)
        for v in signal:
            engine.add_frame(v, v * 0.7, v * 0.4)
        result = engine.get_result()
        assert result is not None
        assert result.hrv_ms >= 0.0

    def test_reset_clears_buffer(self):
        engine = HeartRateEngine(sample_rate=30)
        signal = make_synthetic_signal(bpm=72)
        for v in signal:
            engine.add_frame(v, v * 0.7, v * 0.4)
        engine.reset()
        assert engine.get_result() is None
        assert engine.get_buffer_progress() == 0.0

    def test_progress_increases(self):
        engine = HeartRateEngine(sample_rate=30)
        assert engine.get_buffer_progress() == 0.0
        for _ in range(75):
            engine.add_frame(180, 120, 60)
        assert engine.get_buffer_progress() == 0.5

    def test_signal_quality_field(self):
        engine = HeartRateEngine(sample_rate=30)
        signal = make_synthetic_signal(bpm=72)
        for v in signal:
            engine.add_frame(v, v * 0.7, v * 0.4)
        result = engine.get_result()
        assert result is not None
        assert result.signal_quality in ('excellent', 'good', 'poor')


class TestFrameExtractor:

    def test_finger_detected_on_reddish_frame(self):
        extractor = FrameExtractor()
        # Simulate reddish frame (finger over camera)
        channels = extractor._detect_finger(r=190, g=100, b=50)
        assert channels is True

    def test_no_finger_on_bright_frame(self):
        extractor = FrameExtractor()
        # Bright uniform frame (no finger)
        channels = extractor._detect_finger(r=220, g=210, b=200)
        assert channels is False

    def test_no_finger_on_dark_frame(self):
        extractor = FrameExtractor()
        # Dark frame
        channels = extractor._detect_finger(r=30, g=25, b=20)
        assert channels is False

    def test_extract_from_frame_shape(self):
        import numpy as np
        extractor = FrameExtractor()
        # Create a fake BGR frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, 2] = 180   # red channel
        frame[:, :, 1] = 100   # green channel
        frame[:, :, 0] = 50    # blue channel
        result = extractor.extract_from_frame(frame)
        assert abs(result.red - 180) < 5
        assert abs(result.green - 100) < 5
        assert abs(result.blue - 50) < 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])