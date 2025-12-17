import pytest
from main import kmp_search

def test_basic():
    text = "abracadabra"
    pattern = "abra"
    assert kmp_search(text, pattern) == [0, 7]

def test_no_match():
    text = "abcdefg"
    pattern = "hij"
    assert kmp_search(text, pattern) == []

def test_full_match():
    text = "aaa"
    pattern = "aaa"
    assert kmp_search(text, pattern) == [0]

def test_overlap():
    text = "aaaaa"
    pattern = "aa"
    assert kmp_search(text, pattern) == [0, 1, 2, 3]

def test_pattern_longer_than_text():
    text = "abc"
    pattern = "abcd"
    assert kmp_search(text, pattern) == []

def test_empty_pattern():
    text = "abc"
    pattern = ""
    assert kmp_search(text, pattern) == []

def test_empty_text():
    text = ""
    pattern = "a"
    assert kmp_search(text, pattern) == []

def test_single_char_match():
    text = "a"
    pattern = "a"
    assert kmp_search(text, pattern) == [0]

def test_multiple_non_overlapping():
    text = "abababab"
    pattern = "ab"
    assert kmp_search(text, pattern) == [0, 2, 4, 6]

def test_unicode_characters():
    text = "абвгдабв"
    pattern = "абв"
    assert kmp_search(text, pattern) == [0, 5]
