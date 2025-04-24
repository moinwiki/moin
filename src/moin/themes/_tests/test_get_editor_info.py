import pytest
from moin.themes import get_editor_info

def test_get_editor_info_anonymous():
    meta = {}  # Simulate revision with no USERID or ADDRESS
    result = get_editor_info(meta)
    assert result["text"] == "anonymous"
    assert result["title"] == ""
    assert result["css"] == "editor"
    assert result["name"] is None

def test_get_editor_info_with_address():
    meta = {"address": "192.168.1.1"}
    result = get_editor_info(meta)
    assert result["text"] == "192.168.1.1"
    assert result["title"] == "[192.168.1.1]"
    assert result["css"] == "editor ip"

def test_get_editor_info_invalid_user(monkeypatch):
    # Simulate a USERID but make user.User(userid) raise an Exception
    class DummyUser:
        def __init__(self, userid):
            raise ValueError("Simulated broken profile")

    from moin import themes
    from moin import user as real_user_module

    monkeypatch.setattr(themes.user, "User", DummyUser)

    meta = {"userid": "fake-id"}
    result = get_editor_info(meta)

    assert result["text"] == "anonymous"
    assert result["title"] == "Unknown User"
    assert result["css"] == "editor unknown"
    assert result["name"] == "Unknown"
