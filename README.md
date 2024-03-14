# OnData - Confini amministrativi italiani

[![Made with ♥ by OnData](https://img.shields.io/badge/Made_with_%E2%99%A5_by-OnData-EB593C.svg)](https://www.ondata.it)
[![v2](https://img.shields.io/badge/Release-v2-green.svg)](https://github.com/ondata/confini-amministrativi-istat/releases/tag/v2)

[![Data and open data on forum.italia.it](https://img.shields.io/badge/Forum-Dati%20e%20open%20data-blue.svg)](https://forum.italia.it/c/dati)
[![Confini Amministrativi ISTAT on forum.italia.it](https://img.shields.io/badge/Thread-%5BCall%20for%20ideas%5D%20Confini%20amministrativi%20ISTAT-blue.svg)](https://forum.italia.it/t/call-for-ideas-confini-amministrativi-istat/12224)

[![Thanks to ISTAT](https://img.shields.io/badge/Thanks_to-ISTAT-d22630.svg)](https://www.istat.it)
[![Thanks to ANPR](https://img.shields.io/badge/Thanks_to-ANPR-0066cc.svg)](https://www.istat.it)
[![Thanks to OntoPiA](https://img.shields.io/badge/Thanks_to-OntoPiA-0066cc.svg)](https://schema.gov.it)

Collezione di dati e utilities per facilitare il riuso dei dati [ISTAT](https://www.istat.it/it/archivio/222527) e [ANPR](https://www.anpr.interno.it/) sui confini amministrativi italiani (versione generalizzata meno dettagliata).

Per approfondimenti e discussione è aperto un [thread dedicato su Forum Italia](https://forum.italia.it/t/call-for-ideas-confini-amministrativi-istat/12224).

Sito ufficiale: https://www.confini-amministrativi.it.

## Contenuto del repository

Nel file `sources.json` ci sono i link a tutti gli shapefile rilasciati da ISTAT dal 1991 elencati in [questa tabella](https://www.istat.it/it/archivio/222527), il link all'[archivio storico dei comuni di ANPR](https://www.anpr.interno.it/portale/anpr-archivio-comuni.csv) e le risorse Linked Open Data del [progetto OntoPiA](https://schema.gov.it/).

Lo script `main.py` scarica gli archivi zip dal sito ISTAT, li decomprime e li elabora in cartelle nominate con la data di rilascio: `dist/api/v2/it/YYYYMMDD/`. Scarica anche il file di ANPR e lo arricchisce con i dati ISTAT contenuti negli shapefile.

Al momento sono supportati i seguenti formati di output:

* [ESRI shapefile (ZIP)](https://it.wikipedia.org/wiki/Shapefile), il formato originario in cui l'ISTAT pubblica i dati ufficiali, ma con le geometrie corrette, la normalizzazione del charset a UTF-8 e la proiezione a [EPSG:4326](https://epsg.io/?q=4326).
* [Comma-separated values (CSV)](https://it.wikipedia.org/wiki/Comma-separated_values) con la tabella dei dati arricchiti dei territori (UTF-8, virgola come separatore, doppie virgolette come delimitatori di stringa, new line come separatore di riga)
* [JavaScript Object Notation (JSON)](https://it.wikipedia.org/wiki/JavaScript_Object_Notation) con gli stessi dati del CSV
* [GeoJSON](https://it.wikipedia.org/wiki/GeoJSON) con gli stessi dati dello shapefile
* [TopoJSON](https://it.wikipedia.org/wiki/GeoJSON#TopoJSON) con gli stessi dati dello shapefile
* [GeoPackage](https://en.wikipedia.org/wiki/GeoPackage) con gli stessi dati dello shapefile
* [GeoParquet](https://geoparquet.org/) con gli stessi dati dello shapefile
* [Geobuf](https://github.com/cubao/geobuf-cpp) con gli stessi dati dello shapefile
* [SVG](https://developer.mozilla.org/en-US/docs/Web/SVG) con i contorni in grafica vettoriale dello shapefile (linee nere e bianche, sfondo trasparente)
* [PNG](https://en.wikipedia.org/wiki/PNG) con i contorni in grafica raster dello shapefile (linee nere e bianche, sfondo trasparente)
* [WEBP](https://en.wikipedia.org/wiki/WebP) con i contorni in grafica raster dello shapefile (linee nere e bianche, sfondo trasparente)
* [JPEG](https://en.wikipedia.org/wiki/JPEG) con i contorni in grafica raster dello shapefile (linee nere su sfondo bianco e bianche su sfondo nero)

Il file di ANPR è quello originale arricchito delle denominazioni e dell'indicazione degli shapefile in cui i comuni sono presenti.

> Avvertenza: nel repository è incluso solo il codice sorgente dell'applicazione e non i file generati.

## Design e stack tecnologico

L'obiettivo di questo progetto è automatizzare completamente la generazione di risorse geografiche italiane utili in diversi ambiti di mapping e GIS a partire dai dati storici ufficiali rilasciati da ISTAT e ANPR. I task includono il download, l'omogeneizzazione di codifiche e formati, la correzione di errori di geometrie, la generazione di raggruppamenti di territori a tutti i livelli (es. i comuni di una regione), la conversione in diversi formati geografici e la generazione di mappe interattive per una fruizione semplificata di ognuno di essi.

La struttura dell'albero di cartelle di output è conforme allo standard [REST delle Web API](https://en.wikipedia.org/wiki/REST), per cui il risultato finale è effettivamente una API statica, descritta mediante lo [standard OpenAPI](./dist/api/v2/openapi.v2.yml).

Tutte le risorse disponibili sono automaticamente raggiungibili grazie alla presenza di file `index.json` in ogni cartella conformi alla specifica [Hypertext Application Language (HAL)](https://en.wikipedia.org/wiki/Hypertext_Application_Language).

Tutte le cartelle mostrano una preview dei dati geografici che contengono in una mappa interattiva gestita da [LeafletJS](https://leafletjs.com).

Lo script di generazione è scritto in Python (v3.11) e le sue dipendenze dirette sono elencate nel file `requirements.txt`.

Oltre a queste si richiede che alcune librerie siano installate nel sistema,
in particolare [GDAL](https://gdal.org/index.html) e [SQLite](https://www.sqlite.org/index.html)
con l'estensione [Spatialite](https://www.gaia-gis.it/fossil/libspatialite/index).

Per semplificare la portabilità dello script è possibile (e conveniente) eseguirlo in un container Docker, per cui è fornito un Dockerfile con cui fare la build dell'immagine.

## Come eseguire l'applicazione

Si consiglia caldamente di usare la versione containerizzata con [Docker](https://www.docker.com/).

### Versione dockerizzata

> Modalità consigliata

Clona questo repository con [Git](https://git-scm.com/): `git clone https://github.com/teamdigitale/confini-amministrativi-istat.git`.
Entra nella cartella appena creata: `cd confini-amministrativi-istat/`.

L'utility `run.sh` contiene degli shortcut per gestire più facilmente l'immagine docker dell'applicazione (in ambiente windows si raccomanda l'uso di [Git Bash](https://gitforwindows.org/)).
Per l'elenco di tutti i comandi supportati: `bash run.sh help`.

Effettua la build delle immagini: `bash run.sh build` (usa `rebuild` per non fare uso della cache).

Esegui il container per ogni tipologia di confine amministrativo e per tutte le versioni con `bash run.sh generate` oppure indicando la singola versione di interesse con `bash run.sh generate YYYYMMDD`.

> Avvertenza: l'esecuzione può richiedere alcune ore o anche molte nel caso dell'elaborazione di tutte le versioni.

Naviga le API e la loro documentazione eseguendo un web server in locale: `bash run.sh serve [PORT]`, la porta di default è la `8080`.

### Esecuzione diretta

> Modalità altamente **sconsigliata**, le dipendenze indirette sono molte e si reggono su un equilibrio precario tra le versioni di ogni libreria.

Clona questo repository con [Git](https://git-scm.com/): `git clone https://github.com/teamdigitale/confini-amministrativi-istat.git`.
Entra nella cartella appena creata: `cd confini-amministrativi-istat/`.

Il file `requirements.txt` elenca tutte le dipendenze necessarie a eseguire l'applicazione.
Si consiglia di operare sempre in un ambiente isolato creando un apposito *virtual environment*.

Con [Poetry](https://python-poetry.org/) è sufficiente entrare nel virtualenv con `poetry shell` e la prima volta installare le dipendenze con `poetry install` come descritte nel file `pyproject.toml`.

Infine, per eseguire l'applicazione ed elaborare tutte le versioni: `python main.py`.
Per specificare una singola versione di interesse: `SOURCE_NAME=YYYYMMDD python main.py`.

### Specifiche OpenAPI

Il file `dist/api/v2/openapi.v2.yml` contiene le specifiche conformi allo standard [OpenAPI v3.1](https://www.openapis.org/).

Con `bash run.sh serve` puoi navigare la documentazione in maniera interattiva sia dalla homepage (http://localhost:8080), sia come pagina standalone (http://localhost:8080/api/v2/).

### Homepage

L'homepage del sito offre una preview dei dati su mappa interattiva (solo desktop) e la possibiltà di scaricare la risorsa scelta mediante form.
Contiene anche la documentazione completa dell'API e la possibilità di navigarla interattivamente grazie a [Swagger UI](https://swagger.io/tools/swagger-ui/).

Per il codice sorgente dell'homepage si rimanda al [README dedicato](src/app/README.md).

## Sviluppo

Con `bash run.sh dev YYYYMMDD` è possibile eseguire lo script `main.py` all'interno di un container senza effettuare una nuova build dell'immagine.

Per lo sviluppo dell'homepage si rimanda al [README dedicato](src/app/README.md).

## Come contribuire

Ogni contributo è benvenuto, puoi aprire una issue oppure proporre una pull request, così come partecipare alla [discussione su Forum Italia](https://forum.italia.it/t/call-for-ideas-confini-amministrativi-istat/12224). Per favore leggi interamente e con attenzione il [Codice di Condotta](./CODE_OF_CONDUCT.md) e le [Regole di Contribuzione](./CONTRIBUTING.md) prima di farlo.

## Ringraziamenti

Ringraziamo il [Team per la Trasformazione Digitale](https://teamdigitale.governo.it/) per aver ospitato questo progetto nella sua primissima fase di ideazione e realizzazione.

Un ringraziamento anche a [Datafactor Agrigento](https://www.datafactor.it/) per il supporto e il prezioso contributo di finalizzazione del file di configurazione `sources.json`.

Ringraziamo anche [Dataninja srl](https://www.dataninja.it) per il [lavoro pionieristico](https://github.com/dataninja/geo-shapes) sul tema, [Density Design](https://densitydesign.org/) che con [RAWGraphs](http://rawgraphs.io/) ha fatto emergere per la prima volta l'[esigenza di un'API](https://groups.google.com/g/densitydesign-raw/c/-MIAUtSjkzk) di questo tipo e [SparkFabrik srl](https://www.sparkfabrik.com/) per aver reso possibile la finalizzazione del progetto.

## Licenza

L'uso di questo software è concesso sotto licenza [GNU Affero General Public License](https://github.com/ondata/confini-amministrativi-istat/blob/main/LICENSE).
