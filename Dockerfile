FROM python:3.11-slim

RUN apt-get update
RUN apt-get install -y \
    gdal-bin \
    sqlite3 \
    libsqlite3-mod-spatialite \
    python3-cairo \
    python3-pil \
    libwebp-dev

RUN mkdir -p /app
WORKDIR /app
ADD requirements.txt /app
RUN pip install -r requirements.txt
ADD templates /app
ADD main.py /app

VOLUME ["/app"]

CMD ["python", "main.py"]
