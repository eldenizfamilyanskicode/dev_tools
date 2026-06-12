from __future__ import annotations

from typed_time_provider import (
    SecondPrecisionFormattedTimestamp,
    Seconds,
    TimeFormatter,
    TimePrecision,
    WallClock,
)


class TimestampService:
    def __init__(
        self,
        wall_clock: WallClock[Seconds],
        time_formatter: TimeFormatter[SecondPrecisionFormattedTimestamp],
    ) -> None:
        self.wall_clock = wall_clock
        self.time_formatter = time_formatter

    def build_current_timestamp(self) -> str:
        current_timestamp: Seconds = self.wall_clock.now_unix(Seconds)
        formatted_timestamp: SecondPrecisionFormattedTimestamp
        formatted_timestamp = self.time_formatter.format_unix_to_human(
            unix_timestamp=current_timestamp,
            user_timezone_name="UTC",
            return_precision=TimePrecision.SECOND,
        )
        return str(formatted_timestamp)
