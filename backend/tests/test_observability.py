import sentry_sdk

from config.observability import init_sentry


def test_sin_dsn_no_se_activa_sentry(monkeypatch):
    llamadas = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: llamadas.append(kw))
    assert init_sentry("") is False
    assert llamadas == []


def test_con_dsn_solo_envia_errores_sin_datos_personales(monkeypatch):
    llamadas = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: llamadas.append(kw))
    assert init_sentry("https://clave@o0.ingest.sentry.io/1", environment="staging") is True
    config = llamadas[0]
    assert config["send_default_pii"] is False
    assert config["max_request_body_size"] == "never"
    assert config["traces_sample_rate"] == 0.0
    assert config["environment"] == "staging"
