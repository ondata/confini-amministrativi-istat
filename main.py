import json
import csv
import logging
import os
import re
import subprocess
from io import BytesIO, StringIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile, ZIP_DEFLATED

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

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "dist/api/v1/it")
SOURCE_FILE = os.getenv("SOURCE_FILE", "sources.json")
SOURCE_NAME = os.getenv("SOURCE_NAME")
SHAPEFILE_EXTENSIONS = [".dbf", ".prj", ".shp", ".shx"]

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
for release in sources["istat"]:  # noqa: C901

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
                            f"CREATE VIRTUAL TABLE \"{division['name']}\" USING VirtualShape('{Path(output_release, division['name'])}', UTF-8, 32632);",
                            # "-- crea tabella con output check geometrico",
                            f"CREATE TABLE \"{division['name']}_check\" AS SELECT PKUID,GEOS_GetLastWarningMsg() msg,ST_AsText(GEOS_GetCriticalPointFromMsg()) punto FROM \"{division['name']}\" WHERE ST_IsValid(geometry) <> 1;",
                        ]
                    ),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Conto gli errori rilevati
            errori = subprocess.check_output(
                [
                    "sqlite3",
                    output_sqlite,
                    "\n".join([f"SELECT count(*) FROM \"{division['name']}_check\""]),
                ],
                stderr=subprocess.DEVNULL,
            )
            # Se ci sono errori creo una nuova tabella con geometrie corrette
            logging.warning(f"!!! Errori {division['name']}: {int(errori)} geometrie corrette")
            if int(errori) > 0:
                subprocess.run(
                    [
                        "sqlite3",
                        output_sqlite,
                        "\n".join(
                            [
                                "SELECT load_extension('mod_spatialite');",
                                f"CREATE table \"{division['name']}_clean\" AS SELECT * FROM \"{division['name']}\";",
                                f"SELECT RecoverGeometryColumn('{division['name']}_clean','geometry',32632,'MULTIPOLYGON','XY');",
                                f"UPDATE \"{division['name']}_clean\" SET geometry = MakeValid(geometry) WHERE ST_IsValid(geometry) <> 1;",
                            ]
                        ),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            # Creo uno shapefile con geometrie corrette
            subprocess.run(
                [
                    "ogr2ogr",
                    shp_filename,
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
        division_ids = [str(row[division["keys"]["id"].lower()]) for row in DBF(dbf_filename)]
        # Per ogni territorio individuo le suddivisioni amministrative inferiori
        for division_id in division_ids:
            # Creazione cartella
            output_division_id = Path(output_div, division_id)
            # File di output
            shp_filename = output_division_id.with_suffix(".shp")
            # Estrazione del singolo territorio
            if not shp_filename.exists():
                subprocess.run(
                    [
                        "ogr2ogr",
                        shp_filename,
                        Path(output_release, division["name"]).with_suffix(".sqlite"),
                        f"{division['name']}_clean",
                        "-where", f"{division['key']}=\"{division_id}\""
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            for sub_division_name in division.get("children", []):
                # File di output
                shp_filename = Path(output_division_id, sub_division_name).with_suffix(".shp")
                # Estrazione delle suddivisioni amministrative del singolo territorio
                if not shp_filename.exists():
                    subprocess.run(
                        [
                            "ogr2ogr",
                            shp_filename,
                            Path(output_release, sub_division_name).with_suffix(".sqlite"),
                            f"{sub_division_name}_clean",
                            "-where", f"{division['key']}=\"{division_id}\""
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

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
            df = pd.DataFrame(
                iter(DBF(
                    dbf_filename,
                    encoding=release["encoding"]),
                ),
                dtype=str,
            ).rename(columns=str.upper)
            # Individuo il nome della suddivisione di appartenenza
            division = dbf_filename.stem if dbf_filename.stem in release["divisions"] else dbf_filename.parent.stem
            for parent in (
                release["divisions"][division_id]
                for division_id in release["divisions"][division].get(
                    "parents", []
                )
            ):
                # Carico il DBF come dataframe
                jdf = pd.DataFrame(
                    iter(DBF(
                        Path(output_release, parent["name"]).with_suffix(".dbf"),
                        encoding=release["encoding"]),
                    ),
                    dtype=str,
                ).rename(columns=str.upper)
                # Faccio il join selezionando le colonne che mi interessano
                df = pd.merge(
                    df,
                    jdf[[parent["keys"]["id"]] + parent["fields"]],
                    on=parent["keys"]["id"],
                    how="left",
                )
            # Sostituisco tutti i NaN con stringhe vuote
            df.fillna("", inplace=True)
            # Aggiungo l'URI di OntoPiA
            if "key" in sources["ontopia"]["divisions"][division]:
                df["ONTOPIA"] = df[
                    sources["ontopia"]["divisions"][division].get("key")
                ].apply(
                    lambda x: "{host:s}/{path:s}/{code:0{digits:d}d}".format(
                        host=sources["ontopia"].get("url", ""),
                        path=sources["ontopia"]["divisions"][division].get("url", ""),
                        code=int(x),
                        digits=sources["ontopia"]["divisions"][division].get("digits", 1),
                    )
                )
            # Salvo il file arricchito
            df.to_csv(
                csv_filename,
                index=False,
                columns=[
                    col
                    for col in df.columns
                    if "shape_" not in col.lower() and "pkuid" not in col.lower()
                ],
            )
            # JSON (JavaScript Object Notation)
            df.to_json(json_filename, orient="records")

    logging.info(f"Converting shapefiles...")

    # Ciclo su tutti gli shapefile
    for shp_filename in output_release.glob("**/*.shp"):
        # Individuo il nome della suddivisione di appartenenza
        division = shp_filename.stem if shp_filename.stem in release["divisions"] else shp_filename.parent.stem

        # ZIP - Archives of corrected shapefiles
        # Comprimo i file di ogni divisione amministrativa
        zip_filename = shp_filename.with_suffix(".zip")
        if not zip_filename.exists():
            with ZipFile(shp_filename.with_suffix(".zip"), "w", ZIP_DEFLATED, compresslevel=9) as zf:
                for item in shp_filename.parent.iterdir():
                    if item.is_file() and item.stem == division and item.suffix in SHAPEFILE_EXTENSIONS:
                        zf.write(item, arcname=item.name)

        # Carico gli shapefile come geodataframe
        gdf = gpd.read_file(shp_filename)

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
        geoparquet_filename = shp_filename.with_suffix(".parquet")
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
        geobuf_filename = shp_filename.with_suffix('.pbf')
        # Carico il GEOJSON e lo converto in GEOBUF
        if not geobuf_filename.exists() and geojson_filename.exists():
            with open(geojson_filename) as f:
                pbf = geobuf.encode(geojson=f.read())
            # Salvo il file
            with open(geobuf_filename, 'wb') as f:
                f.write(pbf)

        # HTML - https://leafletjs.com/
        # File di output
        html_filename = Path(shp_filename.parent, shp_filename.stem, "index").with_suffix(".html")
        # Compilo il template e salvo il file
        if not html_filename.exists():
            html_filename.parent.mkdir(parents=True, exist_ok=True)
            with open(html_filename, 'w') as f:
                f.write(index_tpl.render(
                    filename=geojson_filename.name,
                    path=geojson_filename,
                    key=release["divisions"][division]["keys"]["label"].lower(),
                    downloads=[
                        { "name": "Shapefile", "filename": zip_filename.name },
                        { "name": "GeoJSON", "filename": geojson_filename.name },
                        { "name": "GeoPKG", "filename": geopkg_filename.name },
                        { "name": "GeoParquet", "filename": geoparquet_filename.name },
                        { "name": "TopoJSON", "filename": topojson_filename.name },
                        { "name": "GeoBUF", "filename": geobuf_filename.name }
                    ]
                ))

    logging.info(f"Cleaning temporary files...")

    # Pulizia dei file temporanei
    for sqlite_filename in output_release.glob("**/*.sqlite"):
        os.remove(sqlite_filename)


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
            df = pd.read_csv(StringIO(res.read().decode(sources["anpr"]["encoding"])), dtype=str)
        except pd.errors.ParserError as e:
            logging.warning(f"!!! ANPR aggiornato non disponibile, uso la cache: {e}")
            try:
                df = pd.read_csv(
                    Path(os.path.basename(sources["anpr"]["url"])).with_suffix(".csv"),
                    encoding=sources["anpr"]["encoding"],
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
                        "csv",
                        division["name"],
                        f"{division['name']}.csv",
                    ),
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
                        [f"{division['key']}_{source['name']}"]
                        + [
                            f"{col}_{source['name']}"
                            for col in division["fields"]
                        ]
                        + [f"GEO_{source['name']}"]
                    ],
                    left_on=sources["anpr"]["division"]["key"],
                    right_on=f"{division['key']}_{source['name']}",
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
