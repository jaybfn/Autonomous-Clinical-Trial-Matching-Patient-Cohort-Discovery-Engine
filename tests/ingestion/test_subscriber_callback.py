"""TDD: subscriber callback ack/nack wiring."""

from __future__ import annotations

from trialmatch.ingestion.handlers import HandleDisposition, HandleResult
from trialmatch.ingestion.subscriber import on_pubsub_message


class _Msg:
    def __init__(self, data: bytes, message_id: str = "m1") -> None:
        self.data = data
        self.message_id = message_id
        self.attributes = {"k": "v"}
        self.acked = False
        self.nacked = False

    def ack(self) -> None:
        self.acked = True

    def nack(self) -> None:
        self.nacked = True


class _Handler:
    def __init__(self, disposition: HandleDisposition) -> None:
        self.disposition = disposition

    def handle(self, **kwargs):  # type: ignore[no-untyped-def]
        return HandleResult(
            disposition=self.disposition,
            status="ok" if self.disposition == HandleDisposition.ACK else "retry",
            correlation_id=kwargs["message_id"],
        )


def test_callback_acks_on_ack_disposition() -> None:
    msg = _Msg(b"{}")
    on_pubsub_message(_Handler(HandleDisposition.ACK), subscription="sub", message=msg)  # type: ignore[arg-type]
    assert msg.acked is True
    assert msg.nacked is False


def test_callback_nacks_on_nack_disposition() -> None:
    msg = _Msg(b"{}")
    on_pubsub_message(_Handler(HandleDisposition.NACK), subscription="sub", message=msg)  # type: ignore[arg-type]
    assert msg.nacked is True
    assert msg.acked is False
