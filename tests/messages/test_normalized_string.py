import pytest

from babel.messages.pofile import _NormalizedString


def test_normalized_string():
    ab = _NormalizedString('"a"', '"b"')
    ac = _NormalizedString('"a"', '"c"')
    z = _NormalizedString()
    assert ab < ac  # __lt__
    assert ac > ab  # __gt__
    assert ab != ac  # __ne__
    assert not z  # __nonzero__ / __bool__
    assert sorted([ac, ab, z]) == [z, ab, ac] # sorted() is stable


@pytest.mark.parametrize(
    "original, denormalized",
    (
        ('""', ""),
        ('"a"', "a"),
        ('"a\\n"', "a\n"),
        ('"a\\r"', "a\r"),
        ('"a\\t"', "a\t"),
        ('"a\\""', 'a"'),
        ('"a\\\\"', "a\\"),
    ),
)
def test_denormalized_simple_normalized_string(original, denormalized):
    assert denormalized == _NormalizedString(original).denormalize()

@pytest.mark.parametrize(
    "originals, denormalized",
    (
        (('"a"', '"b"'), "ab"),
        (('"a"', '"b"'), "ab"),
        (('"ab"', '""'), "ab"),
        (('"ab"', '"c"'), "abc"),
        (('"a"', '"bc"'), "abc"),
    ),
)
def test_denormalized_multi_normalized_string(originals, denormalized):
    assert denormalized == _NormalizedString(*originals).denormalize()
