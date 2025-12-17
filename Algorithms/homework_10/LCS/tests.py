import pytest
from main import lcs

def test_basic():
    assert lcs("AGGTAB", "GXTXAYB") == "GTAB"

def test_empty_s1():
    assert lcs("", "GXTXAYB") == ""

def test_empty_s2():
    assert lcs("AGGTAB", "") == ""

def test_both_empty():
    assert lcs("", "") == ""

def test_full_match():
    assert lcs("ABC", "ABC") == "ABC"

def test_no_common():
    assert lcs("ABC", "DEF") == ""

def test_subsequence_at_end():
    assert lcs("XYZABC", "ABC") == "ABC"

def test_subsequence_at_start():
    assert lcs("ABCXYZ", "ABC") == "ABC"

def test_repeated_characters():
    assert lcs("AABBA", "ABABA") == "ABBA"
