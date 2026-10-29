from calendar_reconcile_core.errors import BoundsError
from calendar_reconcile_core.normalize import jaccard, normalize_title


def test_unicode_punctuation_and_stopwords_are_deterministic():
    assert normalize_title("The Cafe\u0301: game!") == ("café", "game")
    assert normalize_title("Max's concert") == ("concert", "maxs")
    assert normalize_title("Practice") == ("practice",)
    assert jaccard((), ()) == 0.0


def test_domain_specific_words_remain_part_of_titles():
    assert normalize_title("Soccer practice") != normalize_title("Soccer game")


def test_token_limit_fails_closed():
    try:
        normalize_title(" ".join(str(i) for i in range(65)), max_tokens=64)
    except BoundsError:
        pass
    else:
        raise AssertionError("too many tokens must fail")
