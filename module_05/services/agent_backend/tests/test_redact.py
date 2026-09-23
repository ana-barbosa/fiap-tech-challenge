from src import redact


def test_redact_masks_email():
    text = "Meu e-mail é joao.silva@example.com, pode me chamar."
    result = redact.redact(text)
    assert "joao.silva@example.com" not in result
    assert redact.EMAIL_PLACEHOLDER in result


def test_redact_masks_phone_number():
    text = "Meu telefone é (12) 99876-5432."
    result = redact.redact(text)
    assert "99876-5432" not in result
    assert redact.PHONE_PLACEHOLDER in result


def test_redact_scrubs_known_pii_values():
    text = "O cliente se chama João Pereira e quer ser contatado."
    result = redact.redact(text, known_pii=["João Pereira"])
    assert "João Pereira" not in result
    assert redact.NAME_PLACEHOLDER in result


def test_redact_leaves_unrelated_text_untouched():
    text = "Quero um apartamento de 2 quartos em Taubaté por até R$300000."
    assert redact.redact(text) == text


def test_redact_handles_none():
    assert redact.redact(None) is None
