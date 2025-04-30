FROM python:3.11-slim

RUN apt-get update
RUN apt-get install -y \
    build-essential \
    gdal-bin \
    libgdal-dev \
    sqlite3 \
    libsqlite3-mod-spatialite \
    python3-cairo \
    python3-pil \
    libxml2-dev \
    libxslt-dev \
    libwebp-dev

RUN mkdir -p /app
WORKDIR /app
ADD requirements.txt /app
RUN pip install -r requirements.txt
ADD templates /app
ADD main.py /app

VOLUME ["/app"]

CMD ["python", "main.py"]
