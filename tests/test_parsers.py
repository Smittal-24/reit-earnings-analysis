import pytest

from extraction.parsers import extract_text


def test_extract_text_plain_txt():
    assert extract_text(b"hello world", "note.txt") == "hello world"


def test_extract_text_unsupported_extension():
    with pytest.raises(ValueError):
        extract_text(b"data", "file.xyz")