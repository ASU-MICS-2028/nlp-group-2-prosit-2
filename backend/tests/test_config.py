from backend.config import DEFAULT_ORIGINS, allowed_origins


def test_defaults_are_the_local_frontend(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    assert allowed_origins() == DEFAULT_ORIGINS.split(",")


def test_reads_a_comma_separated_list_and_trims_spaces(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", " https://a.example , https://b.example ")

    assert allowed_origins() == ["https://a.example", "https://b.example"]


def test_empty_value_means_nobody_is_allowed(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "")

    assert allowed_origins() == []
