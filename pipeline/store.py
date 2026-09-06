"""Merge each week's scrape into the running dataset.

This file is the actual product. Scrapers can break and be fixed; if this
logic is wrong, "new this week" lies to people and they stop trusting the app.

Two rules that must never be violated:
  1. first_seen is written once and never overwritten.
  2. A source failing is not the same as its listings disappearing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import Opportunity

# How many consecutive runs a listing can go unseen before we hide it.
# 2 means a listing survives one flaky scrape without vanishing from the site.
GRACE_RUNS = 2


@dataclass
class MergeReport:
    run_date: str
    new: list[Opportunity]
    returning: list[Opportunity]
    expired: list[Opportunity]
    total_open: int
    sources_ok: list[str]
    sources_failed: list[str]

    def summary(self) -> str:
        lines = [
            f"run {self.run_date}",
            f"  new         {len(self.new)}",
            f"  returning   {len(self.returning)}",
            f"  expired     {len(self.expired)}",
            f"  open total  {self.total_open}",
            f"  sources ok  {', '.join(self.sources_ok) or 'none'}",
        ]
        if self.sources_failed:
            lines.append(f"  FAILED      {', '.join(self.sources_failed)}")
        return "\n".join(lines)


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.opportunities: dict[str, Opportunity] = {}
        self.runs: list[str] = []
        self.load()

    # ------------------------------------------------------------------
    def load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text())
        self.runs = data.get("runs", [])
        for raw in data.get("opportunities", []):
            opp = Opportunity.from_dict(raw)
            self.opportunities[opp.id] = opp

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": self.runs[-1] if self.runs else None,
            "runs": self.runs[-12:],  # keep a quarter of history, no more
            "opportunities": [
                o.to_dict()
                for o in sorted(
                    self.opportunities.values(),
                    key=lambda o: (o.first_seen or "", o.title),
                    reverse=True,
                )
            ],
        }
        # Stable formatting keeps git diffs readable week to week.
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    # ------------------------------------------------------------------
    def merge(
        self,
        scraped: Iterable[Opportunity],
        run_date: str,
        sources_ok: list[str],
        sources_failed: list[str],
    ) -> MergeReport:
        scraped = list(scraped)
        new, returning = [], []

        for opp in scraped:
            existing = self.opportunities.get(opp.id)
            if existing is None:
                opp.first_seen = run_date
                opp.last_seen = run_date
                opp.status = "open"
                self.opportunities[opp.id] = opp
                new.append(opp)
            else:
                was_expired = existing.status == "expired"
                # Refresh mutable content, preserve lifecycle fields.
                first_seen = existing.first_seen
                opp.first_seen = first_seen
                opp.last_seen = run_date
                opp.status = "open"
                self.opportunities[opp.id] = opp
                if was_expired:
                    returning.append(opp)

        expired = self._expire(run_date, sources_ok)

        self.runs.append(run_date)
        open_count = sum(1 for o in self.opportunities.values() if o.status == "open")

        return MergeReport(
            run_date=run_date,
            new=new,
            returning=returning,
            expired=expired,
            total_open=open_count,
            sources_ok=sources_ok,
            sources_failed=sources_failed,
        )

    def _expire(self, run_date: str, sources_ok: list[str]) -> list[Opportunity]:
        """Hide listings we haven't seen in GRACE_RUNS runs.

        Only considers sources that scraped successfully this run. If
        fremont_gov 500s, its listings are left alone rather than being
        silently marked dead -- otherwise one bad Tuesday wipes the board.
        """
        history = (self.runs + [run_date])[-GRACE_RUNS:]
        cutoff = history[0]
        expired = []
        for opp in self.opportunities.values():
            if opp.source not in sources_ok:
                continue
            if opp.status == "expired":
                continue
            if (opp.last_seen or "") < cutoff:
                opp.status = "expired"
                expired.append(opp)
        return expired

    # ------------------------------------------------------------------
    def new_since(self, run_date: str) -> list[Opportunity]:
        return [
            o
            for o in self.opportunities.values()
            if o.first_seen == run_date and o.status == "open"
        ]
