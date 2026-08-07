"""Unit tests for Streamlit demo API client (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from streamlit_app.api_client import TrialMatchApiError, healthz, match_patient


def test_healthz_ok() -> None:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"status": "ok", "service": "trialmatch-api"}
    with patch("streamlit_app.api_client.requests.get", return_value=response) as get:
        body = healthz("http://example:18080")
    assert body["status"] == "ok"
    get.assert_called_once()
    assert get.call_args.args[0] == "http://example:18080/healthz"


def test_match_patient_posts_json() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "status": "ok",
        "patient_id": "p-1",
        "matches": [],
        "correlation_id": "c1",
    }
    with patch("streamlit_app.api_client.requests.post", return_value=response) as post:
        body = match_patient(
            "http://example:18080/",
            patient_id=" p-1 ",
            note_text=" diabetes ",
        )
    assert body["status"] == "ok"
    post.assert_called_once()
    assert post.call_args.kwargs["json"] == {
        "patient_id": "p-1",
        "note_text": "diabetes",
    }


def test_match_patient_timeout_raises() -> None:
    import requests

    with patch(
        "streamlit_app.api_client.requests.post",
        side_effect=requests.Timeout(),
    ):
        with pytest.raises(TrialMatchApiError, match="timed out"):
            match_patient("http://example:18080", patient_id="p", note_text="n")
