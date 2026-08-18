import datetime
from typing import Optional, Union

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
except ImportError:
    date_parser = None


class DateHandler:
    TIMEZONE = _TIMEZONE

    @staticmethod
    def get_datetime_now() -> datetime.datetime:
        """Restituisce il datetime corrente nel timezone Europe/Rome."""
        return datetime.datetime.now(DateHandler.TIMEZONE)

    @staticmethod
    def parse_datetime(date_val: Optional[Union[str, datetime.datetime, Any]] = None) -> datetime.datetime:
        """Parsa una stringa, struct_time o datetime in un datetime object con timezone Europe/Rome, con fallback sicuro."""
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
                    parsed_datetime = date_parser.parse(str(date_val))
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


