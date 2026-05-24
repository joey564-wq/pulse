"""Alert state tracking and notification."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

from pulse.logging import get_logger
from pulse.models import CheckResult, Service, _utcnow

AlertKind = Literal["failing", "recovered"]


@dataclass(frozen=True, slots=True)
class AlertEvent:
    url: str
    kind: AlertKind
    consecutive_failures: int
    at: datetime


@dataclass
class AlertTracker:
    """Stateful tracker — one instance per monitor run."""
    consecutive_failures: dict[str, int] = field(default_factory=dict)
    alerts_active: set[str] = field(default_factory=set)

    def record(self, service: Service, result: CheckResult) -> AlertEvent | None:
        """Update state; return an event if one should fire, else None."""
        url = service.url
        if result.ok:
            self.consecutive_failures[url] = 0
            if url in self.alerts_active:
                self.alerts_active.discard(url)
                return AlertEvent(
                    url=url, kind="recovered",
                    consecutive_failures=0, at=_utcnow(),
                )
            return None

        n = self.consecutive_failures.get(url, 0) + 1
        self.consecutive_failures[url] = n
        if n >= service.alert_after_failures and url not in self.alerts_active:
            self.alerts_active.add(url)
            return AlertEvent(
                url=url, kind="failing",
                consecutive_failures=n, at=_utcnow(),
            )
        return None


class Notifier(Protocol):
    def notify(self, event: AlertEvent) -> None: ...


class LogNotifier:
    """Logs alerts loudly via structlog."""
    def __init__(self) -> None:
        self._log = get_logger(__name__)

    def notify(self, event: AlertEvent) -> None:
        if event.kind == "failing":
            self._log.error(
                "ALERT_FAILING",
                url=event.url,
                consecutive_failures=event.consecutive_failures,
            )
        else:
            self._log.warning("ALERT_RECOVERED", url=event.url)


class FileNotifier:
    """Appends alert events to a file (one JSON line per event)."""
    def __init__(self, path: Path) -> None:
        self.path = path

    def notify(self, event: AlertEvent) -> None:
        import json
        line = json.dumps({
            "at": event.at.isoformat(),
            "url": event.url,
            "kind": event.kind,
            "consecutive_failures": event.consecutive_failures,
        })
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


class CompositeNotifier:
    """Fans out to multiple notifiers. Useful for log + file."""
    def __init__(self, *notifiers: Notifier) -> None:
        self._notifiers = notifiers

    def notify(self, event: AlertEvent) -> None:
        for n in self._notifiers:
            n.notify(event)