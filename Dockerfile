FROM python:3.10-alpine3.16

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

RUN apk update \
    # && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add --virtual build-deps gcc musl-dev \
    # && apk add postgresql \
    # && apk add postgresql-dev \
    # && pip install psycopg2 \
    && apk add jpeg-dev zlib-dev libjpeg \
    && pip install Pillow 
    # && apk del build-deps

COPY requirements.txt .
RUN python -m pip install -r requirements.txt


# VOLUME /app
WORKDIR /app

COPY . /app

CMD [ "python", "src/bot.py"]