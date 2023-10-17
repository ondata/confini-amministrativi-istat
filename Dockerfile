FROM python:3.11-slim AS environment

RUN apt-get update
RUN apt-get install -y \
    gdal-bin \
    sqlite3 \
    #libsqlite3-mod-spatialite \
    libsqlite3-dev \
    #liblwgeom-2.5-0 \
    python3-dev \
    build-essential \
    libxml2-dev \
    libproj-dev \
    libgeos-dev \
    zlib1g-dev \
    pkg-config \
    automake \
    autoconf \
    autotools-dev \
    #m4 \
    libtool \
    libminizip-dev

ARG LIBRTTOPO_VERSION=1.1.0
ADD https://git.osgeo.org/gitea/rttopo/librttopo/archive/librttopo-${LIBRTTOPO_VERSION}.tar.gz /tmp
RUN tar zxf /tmp/librttopo-${LIBRTTOPO_VERSION}.tar.gz -C /tmp && rm /tmp/librttopo-${LIBRTTOPO_VERSION}.tar.gz
RUN cd /tmp/librttopo && \
    ./autogen.sh && \
    ./configure && \
    make && \
    make check && \
    make install

ARG FREEXL_VERSION=2.0.0
ADD http://www.gaia-gis.it/gaia-sins/freexl-sources/freexl-${FREEXL_VERSION}.tar.gz /tmp
RUN tar zxf /tmp/freexl-${FREEXL_VERSION}.tar.gz -C /tmp && rm /tmp/freexl-${FREEXL_VERSION}.tar.gz
RUN cd /tmp/freexl-${FREEXL_VERSION} && \
    ./configure && \
    make && \
    make install

ARG LIBSPATIALITE_VERSION=5.1.0
ADD http://www.gaia-gis.it/gaia-sins/libspatialite-sources/libspatialite-${LIBSPATIALITE_VERSION}.tar.gz /tmp
RUN tar zxf /tmp/libspatialite-${LIBSPATIALITE_VERSION}.tar.gz -C /tmp && rm /tmp/libspatialite-${LIBSPATIALITE_VERSION}.tar.gz
RUN cd /tmp/libspatialite-${LIBSPATIALITE_VERSION} && \
    ./configure --enable-rttopo=yes --enable-gcp=yes && \
    make -j8 && \
    make install-strip

RUN /sbin/ldconfig -v

ARG MOD_SPATIALITE_VERSION=8.1.0
RUN ln -s /usr/local/lib/mod_spatialite.so.${MOD_SPATIALITE_VERSION} /usr/lib/mod_spatialite.so

FROM environment AS application

RUN mkdir -p /app
WORKDIR /app
ADD requirements.txt /app
RUN pip install -r requirements.txt
ADD main.py /app

VOLUME ["/app"]

CMD ["python", "main.py"]

