"""Pure unit tests for the PaddleOCR result parser (no PaddleOCR needed)."""

from app.providers.ocr.paddle import _extract_lines, _poly_to_bbox


def test_extract_lines_paddleocr_3x():
    res = {
        "rec_texts": ["Hello", "World"],
        "rec_scores": [0.99, 0.95],
        "rec_polys": [
            [[0, 0], [10, 0], [10, 5], [0, 5]],
            [[0, 6], [10, 6], [10, 11], [0, 11]],
        ],
    }
    texts, scores, polys = _extract_lines(res)
    assert texts == ["Hello", "World"]
    assert scores == [0.99, 0.95]
    assert len(polys) == 2


def test_extract_lines_3x_without_polys_pads_with_none():
    res = {"rec_texts": ["A", "B"], "rec_scores": [0.5, 0.6]}
    texts, _scores, polys = _extract_lines(res)
    assert texts == ["A", "B"]
    assert polys == [None, None]


def test_extract_lines_paddleocr_2x_fallback():
    res = [
        [[[0, 0], [10, 0], [10, 5], [0, 5]], ("Hello", 0.99)],
        [[[0, 6], [10, 6], [10, 11], [0, 11]], ("World", 0.95)],
    ]
    texts, scores, polys = _extract_lines(res)
    assert texts == ["Hello", "World"]
    assert scores == [0.99, 0.95]
    assert len(polys) == 2


def test_poly_to_bbox():
    assert _poly_to_bbox([[1, 2], [9, 2], [9, 8], [1, 8]]) == (1, 2, 9, 8)
    assert _poly_to_bbox(None) is None
