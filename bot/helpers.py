from collections import namedtuple
from datetime import datetime, timedelta
from typing import Iterable


class YearWeek(namedtuple("_", ("year", "week"))):
    @classmethod
    def from_string(cls, s: str) -> "YearWeek":
        """ Parse year-week pair into a named YearWeek tuple.

        Yearweek string is expected to be in yyyy-Www

        :param string: Year-week pair as string
        :return: Year-week pair as YearWeek
        """
        year, sep, week = s.partition("-W")
        if not sep:
            raise ValueError("invalid format")
        return cls(int(year), int(week))

    def __str__(self):
        """Return YearWeek in format suitable for use with YearWeek.from_string

        >>> yw = YearWeek.now()
        >>> assert yw == YearWeek.from_string(str(yw))
        """
        return f"{self.year}-W{self.week:02}"

    @classmethod
    def now(cls) -> "YearWeek":
        "Construct YearWeek from current time"
        t = datetime.now()
        return cls.from_datetime(t)

    @classmethod
    def from_datetime(cls, t: datetime) -> "YearWeek":
        "Construct YearWeek from given datetime"
        year, week, _ = t.isocalendar()
        return cls(year, week)

    def valid(self) -> bool:
        "Check if the YearWeek is valid"
        try:
            self.next_week()
        except ValueError:
            return False
        return True

    def __add__(self, delta: timedelta) -> "YearWeek":
        "Return the YearWeek delta from self"
        t = datetime.fromisocalendar(*self, 1)
        return self.from_datetime(t + delta)

    def next_week(self) -> "YearWeek":
        "Return the next YearWeek from self"
        return self + timedelta(weeks=1)

    def iter_weeks(self) -> Iterable["YearWeek"]:
        """ Yield next YearWeeks starting from self

        >>> yw = YearWeek(2021, 12)
        >>> it = yw.iter_weeks()
        >>> assert next(it) == yw
        >>> assert next(it) == YearWeek(2021, 13)
        """
        while True:
            yield self
            self = self.next_week()


def debug_printer(item="Nothing was given to log.", sign="#"):
    """
    This function is for debugging purposes.
    :param item: item or message to be printed.
    :param sign: The character or string with which the message in this instance is highlighted.
    :return: None
    """
    print()
    print(sign * 6)
    print(sign * 6)
    print(item)
    print(sign * 6)
    print(sign * 6)
