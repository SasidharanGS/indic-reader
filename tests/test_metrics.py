from app.bench.metrics import cer, edit_distance, real_time_factor


def test_edit_distance():
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance("abc", "abc") == 0
    assert edit_distance("", "abc") == 3
    assert edit_distance("abc", "") == 3


def test_cer():
    assert cer("abc", "abc") == 0.0
    assert cer("hello", "hallo") == 0.2  # one substitution / 5 chars
    assert cer("", "") == 0.0
    assert cer("", "spurious") == 1.0
    assert cer("abc", "") == 1.0


def test_real_time_factor():
    assert real_time_factor(2.0, 4.0) == 0.5
    assert real_time_factor(8.0, 4.0) == 2.0
    assert real_time_factor(1.0, 0) == float("inf")
