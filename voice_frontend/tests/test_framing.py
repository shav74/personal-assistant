import numpy as np

from voice_frontend.audio.framing import FrameAccumulator


def _int16_bytes(*samples: int) -> bytes:
    return np.array(samples, dtype=np.int16).tobytes()


def test_push_returns_no_frames_below_frame_length():
    acc = FrameAccumulator(frame_length=4)
    frames = acc.push(_int16_bytes(1, 2, 3))
    assert frames == []


def test_push_returns_complete_frames_and_buffers_remainder():
    acc = FrameAccumulator(frame_length=4)
    frames = acc.push(_int16_bytes(1, 2, 3, 4, 5, 6))
    assert len(frames) == 1
    assert list(frames[0]) == [1, 2, 3, 4]

    # the remaining [5, 6] should still be buffered
    more_frames = acc.push(_int16_bytes(7, 8))
    assert len(more_frames) == 1
    assert list(more_frames[0]) == [5, 6, 7, 8]


def test_push_handles_multiple_complete_frames_in_one_chunk():
    acc = FrameAccumulator(frame_length=2)
    frames = acc.push(_int16_bytes(1, 2, 3, 4, 5, 6))
    assert len(frames) == 3
    assert [list(f) for f in frames] == [[1, 2], [3, 4], [5, 6]]


def test_reset_drops_buffered_remainder():
    acc = FrameAccumulator(frame_length=4)
    acc.push(_int16_bytes(1, 2, 3))  # partial, buffered
    acc.reset()
    frames = acc.push(_int16_bytes(4, 5, 6, 7))
    assert len(frames) == 1
    assert list(frames[0]) == [4, 5, 6, 7]  # not [1,2,3,4]
