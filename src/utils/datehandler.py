import pytz
import datetime
from dateutil import parser


class DateHandler:
    # Utilizzo di una costante di classe per il timezone per evitare ripetizioni
    TIMEZONE = pytz.timezone("Europe/Rome")

    @staticmethod
    def get_datetime_now() -> datetime.datetime:
        """Restituisce il datetime corrente nel timezone Europe/Rome."""
        # Ottenimento diretto del datetime nel timezone specificato (ottimizzazione)
        return datetime.datetime.now(DateHandler.TIMEZONE)

    @staticmethod
    def parse_datetime(date_string: str) -> datetime.datetime:
        """Parsa una stringa in un datetime object con timezone Europe/Rome."""
        parsed_datetime = parser.parse(date_string)

        if parsed_datetime.tzinfo is None:
            # Assunzione che le datetime naive siano nel timezone locale (Europe/Rome)
            localized_datetime = DateHandler.TIMEZONE.localize(parsed_datetime)
        else:
            # Conversione esplicita al timezone target se la datetime è aware
            localized_datetime = parsed_datetime.astimezone(DateHandler.TIMEZONE)

        return localized_datetime


if __name__ == "__main__":
    print(DateHandler.parse_datetime("15-10-2022"))
