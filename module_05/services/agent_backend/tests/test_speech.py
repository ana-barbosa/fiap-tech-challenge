from unittest.mock import MagicMock

import pytest
from openai import OpenAIError

from src import speech
from src.speech import SpeechError, transcribe


def test_transcribe_returns_stripped_text(monkeypatch):
    fake_result = MagicMock()
    fake_result.text = "  quero alugar um apê  "
    fake_client = MagicMock()
    fake_client.audio.transcriptions.create.return_value = fake_result
    monkeypatch.setattr(speech, "_client", fake_client)

    result = transcribe("voice.ogg", b"fake-audio-bytes")

    assert result == "quero alugar um apê"
    fake_client.audio.transcriptions.create.assert_called_once_with(
        model="whisper-1", file=("voice.ogg", b"fake-audio-bytes"), language="pt"
    )


def test_transcribe_raises_speech_error_on_openai_error(monkeypatch):
    fake_client = MagicMock()
    fake_client.audio.transcriptions.create.side_effect = OpenAIError("boom")
    monkeypatch.setattr(speech, "_client", fake_client)

    with pytest.raises(SpeechError):
        transcribe("voice.ogg", b"fake-audio-bytes")
