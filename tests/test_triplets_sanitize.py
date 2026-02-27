import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from triplets_to_neo4js import _sanitize_rel_type


def test_valid_relationship_types():
    assert _sanitize_rel_type("mentioned") == "MENTIONED"
    assert _sanitize_rel_type("mentioned_on") == "MENTIONED_ON"
    assert _sanitize_rel_type("referenced on") == "REFERENCED_ON"


def test_rejects_injection_attempts():
    with pytest.raises(ValueError, match="Unsafe"):
        _sanitize_rel_type("MENTIONED]->(x) DELETE x //")

    with pytest.raises(ValueError, match="Unsafe"):
        _sanitize_rel_type("a{b}")
