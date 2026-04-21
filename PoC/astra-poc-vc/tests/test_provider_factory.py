import importlib


def test_email_provider_prefers_explicit_mike_email_provider(monkeypatch):
    monkeypatch.setenv("DATA_PROVIDER", "mock")
    monkeypatch.setenv("MIKE_EMAIL_PROVIDER", "zoho")

    import providers.factory as factory

    importlib.reload(factory)

    assert factory._email_provider_name() == "zoho"


def test_email_provider_falls_back_to_data_provider(monkeypatch):
    monkeypatch.setenv("DATA_PROVIDER", "google")
    monkeypatch.delenv("MIKE_EMAIL_PROVIDER", raising=False)

    import providers.factory as factory

    importlib.reload(factory)

    assert factory._email_provider_name() == "google"
