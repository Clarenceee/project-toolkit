from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

DateRangeName = Literal[
    "latest",
    "last_days",
    "last_months",
    "last_week",
    "this_month",
    "last_month",
    "this_year",
    "last_year",
    "this_quarter",
    "last_quarter",
    "year_to_date",
    "default",
]


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date
    end: date
    name: DateRangeName

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("Date range start must not be after end")


@dataclass(frozen=True, slots=True)
class TemporalQuery:
    query: str
    date_range: DateRange | None
    matched_text: str | None = None


def _shift_months(value: date, months: int) -> date:
    absolute = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(absolute, 12)
    month = month_index + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _month_end(value: date) -> date:
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])


def _quarter_start(value: date) -> date:
    month = ((value.month - 1) // 3) * 3 + 1
    return date(value.year, month, 1)


class RelativeDateParser:
    def __init__(self, *, default_months: int | None = None) -> None:
        if default_months is not None and default_months < 1:
            raise ValueError("default_months must be positive")
        self._default_months = default_months

    def parse(self, query: str, *, now: date | datetime) -> TemporalQuery:
        today = now.date() if isinstance(now, datetime) else now
        dynamic_patterns = (
            (
                re.compile(
                    r"\b(?:last|past|over the last)\s+(\d+)\s+days?\b",
                    re.IGNORECASE,
                ),
                self._last_days,
            ),
            (
                re.compile(
                    r"\b(?:last|past|over the last)\s+(\d+)\s+months?\b",
                    re.IGNORECASE,
                ),
                self._last_months,
            ),
        )
        for pattern, handler in dynamic_patterns:
            match = pattern.search(query)
            if match:
                return self._result(query, match, handler(today, int(match.group(1))))

        fixed = self._fixed_ranges(today)
        patterns = (
            (r"\b(?:latest|recent)\b", "latest"),
            (r"\blast week\b", "last_week"),
            (r"\b(?:this|current) month\b", "this_month"),
            (r"\blast month\b", "last_month"),
            (r"\b(?:this|current) year\b", "this_year"),
            (r"\b(?:last|previous) year\b", "last_year"),
            (r"\b(?:this|current) quarter\b", "this_quarter"),
            (r"\blast quarter\b", "last_quarter"),
            (r"\b(?:year to date|ytd)\b", "year_to_date"),
        )
        for expression, name in patterns:
            match = re.search(expression, query, re.IGNORECASE)
            if match:
                return self._result(query, match, fixed[name])
        if self._default_months is None:
            return TemporalQuery(query=query, date_range=None)
        return TemporalQuery(
            query=query,
            date_range=self._last_months(today, self._default_months, "default"),
        )

    @staticmethod
    def _result(query: str, match: re.Match[str], date_range: DateRange) -> TemporalQuery:
        cleaned = (query[: match.start()] + query[match.end() :]).strip()
        return TemporalQuery(
            query=re.sub(r"\s+", " ", cleaned),
            date_range=date_range,
            matched_text=match.group(0),
        )

    @staticmethod
    def _last_days(today: date, count: int) -> DateRange:
        if count < 1:
            raise ValueError("Day count must be positive")
        return DateRange(today - timedelta(days=count - 1), today, "last_days")

    @staticmethod
    def _last_months(today: date, count: int, name: DateRangeName = "last_months") -> DateRange:
        if count < 1:
            raise ValueError("Month count must be positive")
        return DateRange(_shift_months(today, -count) + timedelta(days=1), today, name)

    @staticmethod
    def _fixed_ranges(today: date) -> dict[str, DateRange]:
        this_month = _month_start(today)
        previous_month = _shift_months(this_month, -1)
        this_quarter = _quarter_start(today)
        previous_quarter_end = this_quarter - timedelta(days=1)
        previous_quarter_start = _quarter_start(previous_quarter_end)
        this_week = today - timedelta(days=today.weekday())
        return {
            "latest": DateRange(this_month, today, "latest"),
            "last_week": DateRange(
                this_week - timedelta(days=7),
                this_week - timedelta(days=1),
                "last_week",
            ),
            "this_month": DateRange(this_month, today, "this_month"),
            "last_month": DateRange(previous_month, _month_end(previous_month), "last_month"),
            "this_year": DateRange(date(today.year, 1, 1), today, "this_year"),
            "last_year": DateRange(
                date(today.year - 1, 1, 1),
                date(today.year - 1, 12, 31),
                "last_year",
            ),
            "this_quarter": DateRange(this_quarter, today, "this_quarter"),
            "last_quarter": DateRange(previous_quarter_start, previous_quarter_end, "last_quarter"),
            "year_to_date": DateRange(date(today.year, 1, 1), today, "year_to_date"),
        }
