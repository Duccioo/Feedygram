import datetime
from typing import Optional, Union, Any

try:
    from zoneinfo import ZoneInfo
    _TIMEZONE = ZoneInfo("Europe/Rome")
except Exception:
    try:
        import pytz
        _TIMEZONE = pytz.timezone("Europe/Rome")
    except Exception:
        _TIMEZONE = datetime.timezone.utc

try:
    from dateutil import parser as date_parser
    from dateutil.parser import UnknownTimezoneWarning
except ImportError:
    date_parser = None
    UnknownTimezoneWarning = Warning


_COMMON_TZINFOS = {
    "EST": -5 * 3600,
    "EDT": -4 * 3600,
    "CST": -6 * 3600,
    "CDT": -5 * 3600,
    "MST": -7 * 3600,
    "MDT": -6 * 3600,
    "PST": -8 * 3600,
    "PDT": -7 * 3600,
    "UT": 0,
    "UTC": 0,
    "GMT": 0,
    "Z": 0,
    "CET": 3600,
    "CEST": 7200,
}


class DateHandler:
    TIMEZONE = _TIMEZONE

    @staticmethod
    def get_datetime_now() -> datetime.datetime:
        """Returns current datetime in Europe/Rome timezone."""
        return datetime.datetime.now(DateHandler.TIMEZONE)

    @staticmethod
    def parse_datetime(date_val: Optional[Union[str, datetime.datetime, Any]] = None) -> datetime.datetime:
        """Parses a string, struct_time, or datetime object into a timezone-aware datetime with Europe/Rome timezone and safe fallback."""
        if date_val is None or (isinstance(date_val, str) and not date_val.strip()):
            return DateHandler.get_datetime_now()


        if isinstance(date_val, datetime.datetime):
            parsed_datetime = date_val
        elif hasattr(date_val, "tm_year"):
            try:
                parsed_datetime = datetime.datetime(*date_val[:6])
            except Exception:
                return DateHandler.get_datetime_now()
        else:
            parsed_datetime = None
            if date_parser is not None:
                try:
                    import warnings

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UnknownTimezoneWarning)
                        parsed_datetime = date_parser.parse(str(date_val), tzinfos=_COMMON_TZINFOS)
                except Exception:
                    pass
            if parsed_datetime is None:
                try:
                    parsed_datetime = datetime.datetime.fromisoformat(str(date_val))
                except Exception:
                    return DateHandler.get_datetime_now()

        if parsed_datetime.tzinfo is None:
            if hasattr(DateHandler.TIMEZONE, "localize"):
                localized_datetime = DateHandler.TIMEZONE.localize(parsed_datetime)
            else:
                localized_datetime = parsed_datetime.replace(tzinfo=DateHandler.TIMEZONE)
        else:
            localized_datetime = parsed_datetime.astimezone(DateHandler.TIMEZONE)

        return localized_datetime


if __name__ == "__main__":
    print(DateHandler.parse_datetime("2026-08-18 12:00:00"))


