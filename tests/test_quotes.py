"""Straight quotes in the manuscript; curly ones in the export; the conversion of existing files; spelling of contractions."""
import pytest

from storywheel import quotes


@pytest.mark.parametrize("text,expected", [
    ("couldn't I've we'll", "couldn’t I’ve we’ll"),
    ('"Hello," she said.', "“Hello,” she said."),
    ("He said, \"don't go.\"", "He said, “don’t go.”"),
    ("'Hello,' he said.", "‘Hello,’ he said."),
    ("She said 'no' twice.", "She said ‘no’ twice."),
    ("rock 'n' roll and 'em and 'til dawn", "rock ’n’ roll and ’em and ’til dawn"),
    ("the '90s were loud", "the ’90s were loud"),
    ("the dogs' bowls", "the dogs’ bowls"),
    ("(\"quoted\")", "(“quoted”)"),
    ('*"italic quote"* after', "*“italic quote”* after"),
    ('"I\'m sure," he said, "it\'s fine."', "“I’m sure,” he said, “it’s fine.”"),
    ('word—"dash"', "word—“dash”"),
    ("", ""),
])
def test_smarten(text, expected):
    assert quotes.smarten(text) == expected


def test_straighten_undoes_every_curly_mark():
    assert quotes.straighten("“don’t” ‘x’") == "\"don't\" 'x'"
    assert quotes.straighten("plain 'text'") == "plain 'text'"
    assert quotes.count_curly("“a” ’") == 3


def test_smarten_then_straighten_is_the_identity_for_ordinary_prose():
    text = 'She said, "I can\'t, and they\'re leaving," then \'left\'.'
    assert quotes.straighten(quotes.smarten(text)) == text
