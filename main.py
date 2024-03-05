import json
import logging
import os
import re
import subprocess
from io import BytesIO, StringIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile, ZIP_DEFLATED
from PIL import Image

import warnings
warnings.filterwarnings('ignore', message=r'.*due to too larger number with respect to field.*')

from jinja2 import Environment, PackageLoader, select_autoescape
tpl_env = Environment(
    loader=PackageLoader("main"),
    autoescape=select_autoescape()
)
index_tpl = tpl_env.get_template("map.html.j2")

from pybind11_geobuf import Encoder
geobuf = Encoder(max_precision=int(10**8))
import geopandas as gpd
import pandas as pd
import topojson
from dbfread import DBF

DIST_DIR = os.getenv("DIST_DIR", "dist")
API_DIR = os.getenv("API_DIR", "api")
VERSION_DIR = os.getenv("VERSION_DIR", "v1")
PUBLIC_DIR = os.getenv("PUBLIC_DIR", f"{API_DIR}/{VERSION_DIR}")
COUNTRY_CODE = os.getenv("COUNTRY_CODE", "it")
COUNTRY_NAME = os.getenv("COUNTRY_NAME", "Italia")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", f"{DIST_DIR}/{PUBLIC_DIR}/{COUNTRY_CODE}")
SOURCE_FILE = os.getenv("SOURCE_FILE", "sources.json")
SOURCE_NAME = os.getenv("SOURCE_NAME")
SHAPEFILE_ENCODING = "UTF-8"
SHAPEFILE_PROJECTION = "EPSG:4326" # WGS84 World: https://epsg.io/?q=4326
SHAPEFILE_EXTENSIONS = [".dbf", ".prj", ".shp", ".shx", ".cpg"]
MIME_TYPES = [
    ("Shapefile (ZIP)", "zip", "application/zip"),
    ("GeoJSON", "geo.json", "application/geo+json"),
    ("TopoJSON", "topo.json", "application/json"),
    ("GeoPackage", "gpkg", "application/geopackage+vnd.sqlite3"),
    ("GeoParquet", "geo.parquet", "application/vnd.apache.parquet"),
    ("Geobuf", "geo.pbf", "application/x-protobuf"),

    ("JSON", "json", "application/json"),
    ("CSV", "csv", "text/csv"),

    ("SVG (light)", "light.svg", "image/svg+xml"),
    ("SVG (dark)", "dark.svg", "image/svg+xml"),
    ("PNG (light)", "light.png", "image/png"),
    ("PNG (dark)", "dark.png", "image/png"),
    ("JPEG (light)", "light.jpg", "image/jpeg"),
    ("JPEG (dark)", "dark.jpg", "image/jpeg"),
    ("WEBP (light)", "light.webp", "image/webp"),
    ("WEBP (dark)", "dark.webp", "image/webp"),

    ("Shapefile (SHP)", "shp", "application/vnd.shp"),
    ("Shapefile (DBF)", "dbf", "application/vnd.dbf"),
    ("Shapefile (SHX)", "shx", "application/vnd.shx"),
    ("Shapefile (PRJ)", "prj", "text/plain"),
    ("Shapefile (CPG)", "cpg", "text/plain"),
]

logging.basicConfig(level=logging.INFO)

# Apro il file con tutte le risorse
with open(SOURCE_FILE) as f:
    # Carico le risorse (JSON)
    sources = json.load(f)
    # Ciclo su tutte le risorse ISTAT
    for release in sources["istat"]:
        # Trasforma la lista di divisioni amministrative (comuni, province, ecc.) in un dizionario indicizzato
        release["divisions"] = {
            division["name"]: division for division in release.get("divisions", [])
        }
    # Trasforma la lista di divisioni amministrative (comuni, province, ecc.) in un dizionario indicizzato
    sources["ontopia"]["divisions"] = {
        division["name"]: division
        for division in sources["ontopia"].get("divisions", [])
    }

# ISTAT - Unità territoriali originali
logging.info("+++ ISTAT +++")
# Ciclo su tutte le risorse ISTAT
for release in sources["istat"]: # noqa: C901

    if SOURCE_NAME and release["name"] != SOURCE_NAME:
        continue

    logging.info(f"Processing {release['name']}...")

    # Cartella di output
    output_release = Path(OUTPUT_DIR, release["name"])

    # Se non esiste...
    if not output_release.exists():
        # ... la creo
        output_release.mkdir(parents=True, exist_ok=True)

        logging.info(f"Downloading source data...")

        # Scarico la risorsa remota
        with urlopen(release["url"]) as res:
            # La leggo come archivio zip
            with ZipFile(BytesIO(res.read())) as zfile:
                # Ciclo su ogni file e cartella nell'archivio
                for zip_info in zfile.infolist():
                    # Elimino la cartella root dal percorso di ogni file e cartella
                    zip_info.filename = zip_info.filename.replace(release["rootdir"], "")
                    # Ciclo sulle divisioni amministrative
                    for division in release["divisions"].values():
                        # Rinomino le sottocartelle con il nome normalizzato delle divisioni
                        zip_info.filename = zip_info.filename.replace(
                            f"{division['dirname']}/", ""
                        ).replace(
                            f"{division['filename']}.", f"{division['name']}."
                        )
                    # Estraggo file e cartelle con un percorso non vuoto
                    if zip_info.filename:
                        zfile.extract(zip_info, output_release)

        logging.info(f"Correcting shapefiles...")

        # SHP (Shapefile) - Corrected shapefile
        # Per ogni divisione amministrativa...
        for division in release["divisions"].values():
            # Database spaziale temporaneo
            output_sqlite = Path(output_release, division["name"]).with_suffix(".sqlite")
            # Shapefile di output
            shp_filename = output_sqlite.with_suffix(".shp")
            # Creo il db sqlite e poi lo inizializzo come db spaziale
            subprocess.run(
                [
                    "sqlite3",
                    output_sqlite,
                    "\n".join(
                        [
                            "SELECT load_extension('mod_spatialite');",
                            "SELECT InitSpatialMetadata(1);",
                        ]
                    ),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Analizzo lo shapefile originale
            subprocess.run(
                [
                    "sqlite3",
                    output_sqlite,
                    "\n".join(
                        [
                            "SELECT load_extension('mod_spatialite');",
                            # "-- importa shp come tabella virtuale",
                            f"CREATE VIRTUAL TABLE \"{division['name']}\" USING VirtualShape('{Path(output_release, division['name'])}',{release['charset']},{release['srid']});",
                            # "-- crea tabella con output check geometrico",
                            f"CREATE TABLE \"{division['name']}_check\" AS SELECT PKUID,GEOS_GetLastWarningMsg() msg,ST_AsText(GEOS_GetCriticalPointFromMsg()) punto FROM \"{division['name']}\" WHERE ST_IsValid(geometry) <> 1;",
                        ]
                    ),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Conto gli errori rilevati
            errors = int(subprocess.check_output(
                [
                    "sqlite3",
                    output_sqlite,
                    "\n".join([f"SELECT count(*) FROM \"{division['name']}_check\""]),
                ],
                stderr=subprocess.DEVNULL,
            ))
            if errors > 0:
                logging.warning(f"!!! Errori {division['name']}: {errors} geometrie corrette")
            # Creo una nuova tabella con geometrie eventualmente corrette
            subprocess.run(
                [
                    "sqlite3",
                    output_sqlite,
                    "\n".join(
                        [
                            "SELECT load_extension('mod_spatialite');",
                            f"CREATE table \"{division['name']}_clean\" AS SELECT * FROM \"{division['name']}\";",
                            f"SELECT RecoverGeometryColumn('{division['name']}_clean','geometry',{release['srid']},'MULTIPOLYGON','XY');",
                            f"UPDATE \"{division['name']}_clean\" SET geometry = MakeValid(geometry) WHERE ST_IsValid(geometry) <> 1;",
                        ]
                    ),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Creo uno shapefile con geometrie corrette e proiezione normalizzata
            subprocess.run(
                [
                    "ogr2ogr",
                    shp_filename,
                    "-t_srs", SHAPEFILE_PROJECTION,
                    "-lco", f"ENCODING={SHAPEFILE_ENCODING}",
                    output_sqlite,
                    f"{division['name']}_clean",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    logging.info(f"Creating nested shapefiles...")

    # SHP (Shapefile) - Nested shapefile
    # Per ogni divisione amministrativa...
    for division in release["divisions"].values():
        # Cartella di output
        output_div = Path(output_release, division["name"])
        output_div.mkdir(parents=True, exist_ok=True)
        # Ricavo tutti gli id dei territori
        dbf_filename = output_div.with_suffix(".dbf")
        division_territories = [
            (
                str(row[division["keys"]["id"].lower()]),
                str(row[division["keys"]["label"].lower()])
            )
            for row in DBF(dbf_filename, encoding=SHAPEFILE_ENCODING)
        ]
        # Per ogni territorio individuo le suddivisioni amministrative inferiori
        for territory_id, territory_label in division_territories:
            # Creazione cartella
            output_territory = Path(output_div, territory_id)
            output_territory.mkdir(parents=True, exist_ok=True)
            # File di output
            shp_filename = output_territory.with_suffix(".shp")
            # Estrazione del singolo territorio
            if not shp_filename.exists():
                subprocess.run(
                    [
                        "ogr2ogr",
                        shp_filename,
                        "-t_srs", SHAPEFILE_PROJECTION,
                        "-lco", f"ENCODING={SHAPEFILE_ENCODING}",
                        Path(output_release, division["name"]).with_suffix(".sqlite"),
                        f"{division['name']}_clean",
                        "-where", f"{division['keys']['id'].lower()}=\"{territory_id}\""
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            for subdivision_name in division.get("children", []):
                # Creazione cartella
                output_subdivision = Path(output_territory, subdivision_name)
                output_subdivision.mkdir(parents=True, exist_ok=True)
                # File di output
                shp_filename = output_subdivision.with_suffix(".shp")
                # Estrazione delle suddivisioni amministrative del singolo territorio
                if not shp_filename.exists():
                    subprocess.run(
                        [
                            "ogr2ogr",
                            shp_filename,
                            "-t_srs", SHAPEFILE_PROJECTION,
                            "-lco", f"ENCODING={SHAPEFILE_ENCODING}",
                            Path(output_release, subdivision_name).with_suffix(".sqlite"),
                            f"{subdivision_name}_clean",
                            "-where", f"{division['keys']['id'].lower()}=\"{territory_id}\"",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                # JSON-HAL - https://stateless.group/hal_specification.html
                # File di output
                hal_filename = Path(output_subdivision, "index").with_suffix(".json")
                with open(hal_filename, 'w') as f:
                    json.dump({
                        "_links": {
                            "self": {
                                "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}/{territory_id}/{subdivision_name}/index.json",
                                "hreflang": COUNTRY_CODE,
                                "name": subdivision_name,
                                "title": f"{territory_label} / {release['divisions'][subdivision_name]['title']}",
                                "type": "application/hal+json",
                                "profile": f"/{PUBLIC_DIR}/hal-subdivision.schema.json"
                            },
                            "up": {
                                "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}/{territory_id}/index.json",
                                "hreflang": COUNTRY_CODE,
                                "name": territory_id,
                                "title": territory_label,
                                "type": "application/hal+json",
                                "profile": f"/{PUBLIC_DIR}/hal-territory.schema.json"
                            },
                            "enclosure": [
                                {
                                    "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}/{territory_id}/{subdivision_name}.{mime_extension}",
                                    "hreflang": "it",
                                    "name": f"{subdivision_name}.{mime_extension}",
                                    "title": mime_label,
                                    "type": mime_type
                                }
                                for mime_label, mime_extension, mime_type in MIME_TYPES
                            ]
                        }
                    }, f)

            # JSON-HAL - https://stateless.group/hal_specification.html
            # File di output
            hal_filename = Path(output_territory, "index").with_suffix(".json")
            with open(hal_filename, 'w') as f:
                json.dump({
                    "_links": {
                        "self": {
                            "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}/{territory_id}/index.json",
                            "hreflang": COUNTRY_CODE,
                            "name": territory_id,
                            "title": territory_label,
                            "type": "application/hal+json",
                            "profile": f"/{PUBLIC_DIR}/hal-territory.schema.json"
                        },
                        "up": {
                            "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}/index.json",
                            "hreflang": COUNTRY_CODE,
                            "name": division['name'],
                            "title": division['title'],
                            "type": "application/hal+json",
                            "profile": f"/{PUBLIC_DIR}/hal-division.schema.json"
                        },
                        "item": [
                            {
                                "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}/{territory_id}/{subdivision_name}/index.json",
                                "hreflang": COUNTRY_CODE,
                                "name": subdivision_name,
                                "title": release["divisions"][subdivision_name]["title"],
                                "type": "application/hal+json",
                                "profile": f"/{PUBLIC_DIR}/hal-subdivision.schema.json"
                            }
                            for subdivision_name in division.get("children", [])
                        ],
                        "enclosure": [
                            {
                                "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}/{territory_id}.{mime_extension}",
                                "hreflang": "it",
                                "name": f"{territory_id}.{mime_extension}",
                                "title": mime_label,
                                "type": mime_type
                            }
                            for mime_label, mime_extension, mime_type in MIME_TYPES
                        ]
                    }
                }, f)

        # JSON-HAL - https://stateless.group/hal_specification.html
        # File di output
        hal_filename = Path(output_div, "index").with_suffix(".json")
        with open(hal_filename, 'w') as f:
            json.dump({
                "_links": {
                    "self": {
                        "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}/index.json",
                        "hreflang": COUNTRY_CODE,
                        "name": division["name"],
                        "title": division["title"],
                        "type": "application/hal+json",
                        "profile": f"/{PUBLIC_DIR}/hal-division.schema.json"
                    },
                    "up": {
                        "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/index.json",
                        "hreflang": COUNTRY_CODE,
                        "name": release['name'],
                        "title": release['name'],
                        "type": "application/hal+json",
                        "profile": f"/{PUBLIC_DIR}/hal-release.schema.json"
                    },
                    "item": [
                        {
                            "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}/{territory_id}/index.json",
                            "hreflang": COUNTRY_CODE,
                            "name": territory_id,
                            "title": territory_label,
                            "type": "application/hal+json",
                            "profile": f"/{PUBLIC_DIR}/hal-territory.schema.json"
                        }
                        for territory_id, territory_label in division_territories
                    ],
                    "enclosure": [
                        {
                            "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}.{mime_extension}",
                            "hreflang": "it",
                            "name": f"{division['name']}.{mime_extension}",
                            "title": mime_label,
                            "type": mime_type
                        }
                        for mime_label, mime_extension, mime_type in MIME_TYPES
                    ]
                }
            }, f)

    logging.info(f"Creating CSV and JSON files...")

    # CSV (Comma Separated Values)
    # Ciclo su tutti i file DBF
    for dbf_filename in output_release.glob("**/*.dbf"):
        # File di output (CSV e JSON)
        csv_filename = dbf_filename.with_suffix(".csv")
        json_filename = csv_filename.with_suffix(".json")
        # Per ogni divisione amministrativa superiore a quella corrente
        if not csv_filename.exists() or not json_filename.exists():
            # Carico il DBF come dataframe
            df_dbf = DBF(dbf_filename, encoding=SHAPEFILE_ENCODING)
            df = pd.DataFrame(
                iter(df_dbf),
                columns=df_dbf.field_names,
                dtype=str,
            ).rename(columns=str.lower)
            # Individuo il nome della suddivisione di appartenenza
            division = dbf_filename.stem if dbf_filename.stem in release["divisions"] else dbf_filename.parent.stem
            for parent in (
                release["divisions"][division_id]
                for division_id in release["divisions"][division].get(
                    "parents", []
                )
            ):
                # Carico il DBF come dataframe
                jdf_dbf = DBF(Path(output_release, parent["name"]).with_suffix(".dbf"), encoding=SHAPEFILE_ENCODING)
                jdf = pd.DataFrame(
                    iter(jdf_dbf),
                    columns=jdf_dbf.field_names,
                    dtype=str,
                ).rename(columns=str.lower)
                # Faccio il join selezionando le colonne che mi interessano
                df = pd.merge(
                    df,
                    jdf[[parent["keys"]["id"].lower()] + [field.lower() for field in parent["fields"]]],
                    on=parent["keys"]["id"].lower(),
                    how="left",
                )
            # Sostituisco tutti i NaN con stringhe vuote
            df.fillna("", inplace=True)
            # Aggiungo l'URI di OntoPiA
            if "key" in sources["ontopia"]["divisions"][division]:
                df["ontopia"] = df[
                    sources["ontopia"]["divisions"][division].get("key").lower()
                ].apply(
                    lambda x: "{host:s}/{path:s}/{code:0{digits:d}d}".format(
                        host=sources["ontopia"].get("url", ""),
                        path=sources["ontopia"]["divisions"][division].get("url", ""),
                        code=int(x),
                        digits=sources["ontopia"]["divisions"][division].get("digits", 1),
                    )
                )
            # Salvo il file arricchito
            df.to_csv(csv_filename, index=False)
            # JSON (JavaScript Object Notation)
            df.to_json(json_filename, orient="records")

    logging.info(f"Converting shapefiles...")

    # Ciclo su tutti gli shapefile
    for shp_filename in output_release.glob("**/*.shp"):
        # Individuo il nome della suddivisione di appartenenza
        division = shp_filename.stem if shp_filename.stem in release["divisions"] else shp_filename.parent.stem

        # Carico lo shapefile come geodataframe
        gdf = gpd.read_file(shp_filename, encoding=SHAPEFILE_ENCODING)
        # Carico i dati arricchiti precedentemente
        df = pd.read_json(shp_filename.with_suffix(".json"))
        # Arricchisco lo shapefile e lo salvo
        if len(df.columns.difference(gdf.columns)) > 0:
            gdf = gdf.merge(df[df.columns.difference(gdf.columns).union(["pkuid"])], on="pkuid")
            gdf.to_file(shp_filename, encoding=SHAPEFILE_ENCODING)

        # ZIP - Archives of corrected shapefiles
        # Comprimo i file di ogni divisione amministrativa
        zip_filename = shp_filename.with_suffix(".zip")
        if not zip_filename.exists():
            with ZipFile(shp_filename.with_suffix(".zip"), "w", ZIP_DEFLATED, compresslevel=9) as zf:
                for item in shp_filename.parent.iterdir():
                    if item.is_file() and item.stem == division and item.suffix in SHAPEFILE_EXTENSIONS:
                        zf.write(item, arcname=item.name)

        # Geojson - https://geojson.org/
        # File di output
        geojson_filename = shp_filename.with_suffix(".geo.json")
        # Converto in GEOJSON e salvo il file
        if not geojson_filename.exists():
            gdf.to_file(geojson_filename, driver="GeoJSON")

        # Geopackage - https://www.geopackage.org/
        # File di output
        geopkg_filename = shp_filename.with_suffix(".gpkg")
        # Converto in GeoPackage e salvo il file
        if not geopkg_filename.exists():
            gdf.to_file(geopkg_filename, driver="GPKG")

        # GeoParquet - https://geoparquet.org/
        # File di output
        geoparquet_filename = shp_filename.with_suffix(".geo.parquet")
        # Converto in GeoParquet e salvo il file
        if not geoparquet_filename.exists():
            gdf.to_parquet(geoparquet_filename)

        # Topojson - https://github.com/topojson/topojson
        # File di output
        topojson_filename = shp_filename.with_suffix(".topo.json")
        # Converto in TOPOJSON
        if not topojson_filename.exists():
            tj = topojson.Topology(gdf, prequantize=False, topology=True)
            # Salvo il file
            with open(topojson_filename, 'w') as f:
                f.write(tj.to_json())

        # Geobuf - https://github.com/cubao/geobuf-cpp
        # File di output
        geobuf_filename = shp_filename.with_suffix('.geo.pbf')
        # Carico il GEOJSON e lo converto in GEOBUF
        if not geobuf_filename.exists() and geojson_filename.exists():
            with open(geojson_filename) as f:
                pbf = geobuf.encode(geojson=f.read())
            # Salvo il file
            with open(geobuf_filename, 'wb') as f:
                f.write(pbf)

        # SVG - https://developer.mozilla.org/en-US/docs/Web/SVG
        # File di output
        svg_filename = shp_filename.with_suffix('.svg')
        # Carico lo SHAPEFILE e lo converto in SVG
        # Black lines
        if not svg_filename.with_suffix('.light.svg').exists() and shp_filename.exists():
            subprocess.run(
                [
                    "svgis", "draw",
                    "--crs", release["srid"],
                    "--id-field", release["divisions"][division]["keys"]["id"],
                    "--data-fields", ",".join([
                        release["divisions"][division]["keys"]["id"],
                        release["divisions"][division]["keys"]["label"]
                    ]),
                    "--simplify", "75",
                    "--precision", "3",
                    "--style", r"polyline,line,rect,path,polygon,.polygon{fill:none;stroke:#000;stroke-width:10px;stroke-linejoin:round;}",
                    "--scale", "100",
                    "--no-inline",
                    "-o", svg_filename.with_suffix('.light.svg'),
                    shp_filename,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        # White lines
        if not svg_filename.with_suffix('.dark.svg').exists() and shp_filename.exists():
            subprocess.run(
                [
                    "svgis", "draw",
                    "--crs", release["srid"],
                    "--id-field", release["divisions"][division]["keys"]["id"],
                    "--data-fields", ",".join([
                        release["divisions"][division]["keys"]["id"],
                        release["divisions"][division]["keys"]["label"]
                    ]),
                    "--simplify", "75",
                    "--precision", "3",
                    "--style", r"polyline,line,rect,path,polygon,.polygon{fill:none;stroke:#fff;stroke-width:10px;stroke-linejoin:round;}",
                    "--scale", "100",
                    "--no-inline",
                    "-o", svg_filename.with_suffix('.dark.svg'),
                    shp_filename,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # PNG - https://en.wikipedia.org/wiki/PNG
        # File di output
        png_filename = shp_filename.with_suffix('.png')
        # Carico l'SVG e lo converto in PNG
        # Light mode
        if not png_filename.with_suffix('.light.png').exists() and svg_filename.with_suffix('.light.svg').exists():
            subprocess.run(
                [
                    "cairosvg",
                    "--output-height", "2160", # 4K
                    "-o", png_filename.with_suffix('.light.png'),
                    svg_filename.with_suffix('.light.svg')
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        # Dark mode
        if not png_filename.with_suffix('.dark.png').exists() and svg_filename.with_suffix('.dark.svg').exists():
            subprocess.run(
                [
                    "cairosvg",
                    "--output-height", "2160", # 4K
                    "--output", png_filename.with_suffix('.dark.png'),
                    svg_filename.with_suffix('.dark.svg')
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # WEBP - https://en.wikipedia.org/wiki/WebP
        # File di output
        webp_filename = shp_filename.with_suffix('.webp')
        # Carico il PNG e lo converto in WEBP
        # Light mode
        if not webp_filename.with_suffix('.light.webp').exists() and png_filename.with_suffix('.light.png').exists():
            Image.open(png_filename.with_suffix('.light.png')).save(webp_filename.with_suffix('.light.webp'), 'WEBP')
        # Dark mode
        if not webp_filename.with_suffix('.dark.webp').exists() and png_filename.with_suffix('.dark.png').exists():
            Image.open(png_filename.with_suffix('.dark.png')).save(webp_filename.with_suffix('.dark.webp'), 'WEBP')

        # JPG - https://en.wikipedia.org/wiki/JPEG
        # File di output
        jpg_filename = shp_filename.with_suffix('.jpg')
        # Carico il PNG e lo converto in JPG
        # Light mode
        if not jpg_filename.with_suffix('.light.jpg').exists() and png_filename.with_suffix('.light.png').exists():
            png = Image.open(png_filename.with_suffix('.light.png')).convert('RGBA')
            bg = Image.new('RGBA', png.size, (255, 255, 255))
            alpha_composite = Image.alpha_composite(bg, png).convert('RGB')
            alpha_composite.save(jpg_filename.with_suffix('.light.jpg'), 'JPEG', quality=80)
        # Dark mode
        if not jpg_filename.with_suffix('.dark.jpg').exists() and png_filename.with_suffix('.dark.png').exists():
            png = Image.open(png_filename.with_suffix('.dark.png')).convert('RGBA')
            bg = Image.new('RGBA', png.size, (0, 0, 0))
            alpha_composite = Image.alpha_composite(bg, png).convert('RGB')
            alpha_composite.save(jpg_filename.with_suffix('.dark.jpg'), 'JPEG', quality=80)

        # HTML - https://leafletjs.com/
        # File di output
        html_filename = Path(shp_filename.parent, shp_filename.stem, "index").with_suffix(".html")
        # Compilo il template e salvo il file
        if not html_filename.exists():
            html_filename.parent.mkdir(parents=True, exist_ok=True)
            with open(html_filename, 'w') as f:
                f.write(index_tpl.render(
                    lang=COUNTRY_CODE,
                    filename=geojson_filename.name,
                    path=geojson_filename,
                    key=release["divisions"][division]["keys"]["label"].lower(),
                    downloads=[
                        { "name": "Shapefile", "filename": zip_filename.name },
                        { "name": "GeoJSON", "filename": geojson_filename.name },
                        { "name": "TopoJSON", "filename": topojson_filename.name },
                        { "name": "GeoPKG", "filename": geopkg_filename.name },
                        { "name": "GeoParquet", "filename": geoparquet_filename.name },
                        { "name": "Geobuf", "filename": geobuf_filename.name }
                    ]
                ))

    logging.info(f"Cleaning temporary files...")

    # Pulizia dei file temporanei
    for sqlite_filename in output_release.glob("**/*.sqlite"):
        os.remove(sqlite_filename)

    # JSON-HAL - https://stateless.group/hal_specification.html
    # File di output
    hal_filename = Path(output_release, "index").with_suffix(".json")
    with open(hal_filename, 'w') as f:
        json.dump({
            "_links": {
                "self": {
                    "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/index.json",
                    "hreflang": COUNTRY_CODE,
                    "name": release["name"],
                    "title": release["name"],
                    "type": "application/hal+json",
                    "profile": f"/{PUBLIC_DIR}/hal-release.schema.json"
                },
                "up": {
                    "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/index.json",
                    "hreflang": COUNTRY_CODE,
                    "name": COUNTRY_CODE,
                    "title": COUNTRY_NAME,
                    "type": "application/hal+json",
                    "profile": f"/{PUBLIC_DIR}/hal-country.schema.json"
                },
                "item": [
                    {
                        "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release['name']}/{division['name']}/index.json",
                        "hreflang": COUNTRY_CODE,
                        "name": division["name"],
                        "title": division["title"],
                        "type": "application/hal+json",
                        "profile": f"/{PUBLIC_DIR}/hal-division.schema.json"
                    }
                    for division in release["divisions"].values()
                ]
            }
        }, f)

    # File di output
    hal_filename = Path(OUTPUT_DIR, "index").with_suffix(".json")
    with open(hal_filename, 'w') as f:
        json.dump({
            "_links": {
                "self": {
                    "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/index.json",
                    "hreflang": COUNTRY_CODE,
                    "name": COUNTRY_CODE,
                    "title": COUNTRY_NAME,
                    "type": "application/hal+json",
                    "profile": f"/{PUBLIC_DIR}/hal-country.schema.json"
                },
                "up": {
                    "href": f"/{PUBLIC_DIR}/index.json",
                    "name": VERSION_DIR,
                    "title": VERSION_DIR,
                    "type": "application/hal+json",
                    "profile": f"/{PUBLIC_DIR}/hal-version.schema.json"
                },
                "item": sorted([
                    {
                        "href": f"/{PUBLIC_DIR}/{COUNTRY_CODE}/{release.name}/index.json",
                        "hreflang": COUNTRY_CODE,
                        "name": release.name,
                        "title": release.name,
                        "type": "application/hal+json",
                        "profile": f"/{PUBLIC_DIR}/hal-release.schema.json"
                    }
                    for release in Path(OUTPUT_DIR).glob('*') if release.is_dir()
                ], key=lambda item: item["name"], reverse=True)
            }
        }, f)


# Arricchisce anche i dati ANPR solo se si tratta di un'elaborazione completa
if not SOURCE_NAME:

    # ANPR - Archivio dei comuni
    logging.info("+++ ANPR +++")
    # Scarico il file dal permalink di ANPR
    with urlopen(sources["anpr"]["url"]) as res:

        # Nome del file
        csv_filename = Path(OUTPUT_DIR, sources["anpr"]["name"]).with_suffix(".csv")
        # Carico come dataframe
        try:
            df = pd.read_csv(StringIO(res.read().decode(sources["anpr"]["charset"])), dtype=str)
        except pd.errors.ParserError as e:
            logging.warning(f"!!! ANPR aggiornato non disponibile, uso la cache: {e}")
            try:
                df = pd.read_csv(
                    Path(os.path.basename(sources["anpr"]["url"])).with_suffix(".csv"),
                    encoding=sources["anpr"]["charset"],
                    dtype=str,
                )
            except FileNotFoundError as e:
                logging.error(f"!!! ANPR non disponibile: {e}")
                exit(1)

        # Ciclo su tutte le risorse istat
        for source in sources["istat"]:

            if SOURCE_NAME and source["name"] != SOURCE_NAME:
                continue

            # Divisione amministrativa utile per arricchire ANPR (quella comunale)
            division = source["divisions"].get(sources["anpr"]["division"]["name"])
            if division:

                logging.info(f"Processing {source['name']}...")

                # Carico i dati ISTAT come dataframe
                jdf = pd.read_csv(
                    Path(
                        OUTPUT_DIR,
                        source["name"],
                        division["name"],
                    ).with_suffix(".csv"),
                    dtype=str,
                )
                # Aggiungo un suffisso a tutte le colonne uguale al nome della fonte ISTAT (_YYYYMMDD)
                jdf.rename(
                    columns={
                        col: f"{col}_{source['name']}"
                        for col in jdf.columns
                    },
                    inplace=True,
                )
                # Aggiungo una colonna GEO_YYYYMMDD con valore costante YYYYMMDD
                jdf[f"GEO_{source['name']}"] = source["name"]
                # Faccio il join tra ANPR e fonte ISTAT selezionando solo le colonne che mi interessano
                df = pd.merge(
                    df,
                    jdf[
                        [f"{division['keys']['id'].lower()}_{source['name']}"]
                        + [
                            f"{col.lower()}_{source['name']}"
                            for col in division["fields"]
                        ]
                        + [f"GEO_{source['name']}"]
                    ],
                    left_on=sources["anpr"]["division"]["key"],
                    right_on=f"{division['keys']['id'].lower()}_{source['name']}",
                    how="left",
                )
                # Elimino tutte le colonne duplicate (identici valori su tutte le righe)
                df = df.loc[:, ~df.T.duplicated(keep="first")]

        # Sostituisco tutti i NaN con stringhe vuote
        df.fillna("", inplace=True)
        # Concateno tutte le colonne GEO_YYYYMMDD in un'unica colonna GEO
        df["GEO"] = df[[col for col in df.columns if "GEO_" in col]].apply(
            lambda l: ",".join([str(x) for x in l if x]), axis=1
        )
        # Elimino le colonne temporanee GEO_YYYYMMDD
        df.drop(columns=[col for col in df.columns if "GEO_" in col], inplace=True)
        # Elimino i suffissi _YYYYMMDD da tutte le colonne
        df.rename(
            columns={col: re.sub(r"_\d+", "", col) for col in df.columns}, inplace=True
        )
        # Aggiungo la colonna di collegamento con OntoPiA
        df["ONTOPIA"] = df.apply(
            lambda row: "{host:s}/{code:0{digits:d}d}".format(
                host=sources["anpr"]["division"].get("url", ""),
                code=int(row["CODISTAT"]),
                digits=sources["anpr"]["division"].get("digits", 1),
            ),
            axis=1,
        )
        # Salvo il file arricchito
        df.to_csv(csv_filename, index=False)
