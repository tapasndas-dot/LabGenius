"""Calendar-based Stability Pull date calculation."""

import calendar
from datetime import date, timedelta

from app.core.exceptions import ValidationException


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def calculate_pull_date(start_date: date, timepoint) -> date:
    if timepoint.is_initial:
        return start_date
    value = timepoint.interval_value
    unit = timepoint.interval_unit
    if value is None or value <= 0:
        raise ValidationException("A non-initial Timepoint requires a positive interval.")
    if unit == "DAY":
        return start_date + timedelta(days=value)
    if unit == "WEEK":
        return start_date + timedelta(weeks=value)
    if unit == "MONTH":
        return _add_months(start_date, value)
    if unit == "YEAR":
        return _add_months(start_date, value * 12)
    raise ValidationException("Unsupported Stability Timepoint interval unit.")
