# Confini Amministrativi ISTAT

[![Data and open data on forum.italia.it](https://img.shields.io/badge/Forum-Dati%20e%20open%20data-blue.svg)](https://forum.italia.it/c/dati)
[![Confini Amministrativi ISTAT on forum.italia.it](https://img.shields.io/badge/Thread-%5BCall%20for%20ideas%5D%20Confini%20amministrativi%20ISTAT-blue.svg)](https://forum.italia.it/t/call-for-ideas-confini-amministrativi-istat/12224)

Collezione di utilities per facilitare il riuso dei dati [ISTAT](https://www.istat.it/it/archivio/222527) e [ANPR](https://www.anpr.interno.it/) sui confini amministrativi italiani. Per approfondimenti e discussione è aperto un [thread dedicato su Forum Italia](https://forum.italia.it/t/call-for-ideas-confini-amministrativi-istat/12224).

> Work in progress, al momento l'output completo è pubblicato in versione di prova su [dev.ondata.it/confini-amministrativi-istat/v1](https://dev.ondata.it/confini-amministrativi-istat/).

## Contenuto del repository

Nel file `sources.json` ci sono i link a tutti gli shapefile rilasciati da ISTAT dal 2001 elencati in [questa tabella](https://www.istat.it/it/archivio/222527)
e il link all'[archivio dei comuni di ANPR](https://www.anpr.interno.it/portale/anpr-archivio-comuni.csv).

Lo script `main.py` scarica gli archivi zip dal sito ISTAT, li decomprime e li elabora in cartelle nominate con la data di rilascio: `v1/YYYYMMDD/`.
Scarica anche il file di ANPR e lo arricchisce con i dati ISTAT contenuti negli shapefile.

Al momento sono supportati i seguenti formati di output:

* [ESRI shapefile](https://it.wikipedia.org/wiki/Shapefile) nella cartella `shp/` (formato originale)
* [Comma-separated values](https://it.wikipedia.org/wiki/Comma-separated_values) nella cartella `csv/`
* [Javascript Object Notation](https://it.wikipedia.org/wiki/JavaScript_Object_Notation) nella cartella `json/`
* [Geojson](https://it.wikipedia.org/wiki/GeoJSON) nella cartella `geojson/`
* [Geopackage](https://en.wikipedia.org/wiki/GeoPackage) nella cartella `geopkg/`
* [Topojson](https://it.wikipedia.org/wiki/GeoJSON#TopoJSON) nella cartella `topojson/`
* ~~[Geobuf](https://github.com/pygeobuf/pygeobuf) nella cartella `geobuf/`~~

Il file di ANPR è quello originale arricchito delle denominazioni e dell'indicazione degli shapefile in cui i comuni sono presenti.

> Avvertenza: al momento è inserita nel repository solo la cartella di output risultante dall'esecuzione dell'applicazione relativa al file ISTAT più recente.

## Come eseguire l'applicazione

Si consiglia caldamente di usare la versione dockerizzata.

> Avvertenza: al momento la conversione in geobuf è commentata perché va in errore

### Versione dockerizzata

> Modalità consigliata

Clona questo repository con [Git](https://git-scm.com/): `git clone https://github.com/teamdigitale/confini-amministrativi-istat.git`.
Entra nella cartella appena creata: `cd confini-amministrativi-istat/`.

Effettua la build delle immagini: `docker build --target application -t ondata-conf-amm-istat .`.
Puoi usare l'utility `bash run.sh build`.

Esegui il container per ogni tipologia di confine amministrativo e per tutte le versioni (`docker run --rm -v $PWD:/app ondata-conf-amm-istat:latest`)
oppure indicando la singola versione di interesse: `docker run --rm -e SOURCE_NAME=YYYYMMDD -v $PWD:/app ondata-conf-amm-istat:latest`.
Puoi usare l'utility `bash run.sh generate [YYYYMMDD]`.

> Avvertenza: l'esecuzione può richiedere diversi minuti, o anche ore nel caso dell'elaborazione di tutte le versioni.

### Esecuzione diretta

> Modalità altamente **sconsigliata**, le dipendenze indirette sono molte e si reggono su un equilibrio precario tra le versioni di ogni libreria.

Clona questo repository con [Git](https://git-scm.com/): `git clone https://github.com/teamdigitale/confini-amministrativi-istat.git`.
Entra nella cartella appena creata: `cd confini-amministrativi-istat/`.

Il file `requirements.txt` elenca tutte le dipendenze necessarie a eseguire l'applicazione.
Si consiglia di operare sempre in un ambiente isolato creando un apposito *virtual environment*.
Con [pipenv](https://pipenv.kennethreitz.org/en/latest/) è sufficiente entrare nel virtualenv con `pipenv shell` e la prima volta installare le dipendenze con `pipenv install`.

Infine, per eseguire l'applicazione ed elaborare tutte le versioni: `python main.py`. Per specificare una singola versione di interesse: `SOURCE_NAME=YYYYMMDD python main.py`.

## Come contribuire

Ogni contributo è benvenuto, puoi aprire una issue oppure proporre una pull request, così come partecipare alla [discussione su Forum Italia](https://forum.italia.it/t/call-for-ideas-confini-amministrativi-istat/12224).

## Ringraziamenti

Ringraziamo il [Team per la Trasformazione Digitale](https://teamdigitale.governo.it/) per aver ospitato questo progetto nella sua primissima fase di ideazione e realizzazione.
Un ringraziamento anche a [Datafactor Agrigento](https://www.datafactor.it/) per il supporto e il prezioso contributo di finalizzazione del file di configurazione `sources.json`.

## Licenza
L'uso di questo software è concesso sotto licenza [GNU Affero General Public License](https://github.com/ondata/confini-amministrativi-istat/blob/develop/LICENSE).
