# Change Log

All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## [2.0] - 2024-04-08

### Added

- deploy to https://www.confini-amministrativi.it/
- homepage with interactive map and OpenAPI specs
- new resource formats: GeoParquet, SVG, PNG, JPG, WEBP
- JSON-HAL resources (index.json)
- interactive maps (index.html)
- subdivision resources
- reprojection to [EPSG:4326](https://epsg.io/?q=4326)
- releases 20240101, 20230101, 20220101

### Changed

- new API path: `/v1/YYYYMMDD/.../DIVISION.FILE_FORMAT` (BREAKING CHANGE!)
- full incremental execution (no generation if destination file exists)
- new and simpler Dockerfile
- update documentation

## [1.1] - 2021-04-21

### Added

- deploy to http://dev.ondata.it/confini-amministrativi-istat/
- new ANPR permalink

## [1.0] - 2021-04-19

### Added

- static API with path `/v1/YYYYMMDD/FILE_FORMAT/DIVISION/`


[2.0]: https://github.com/ondata/confini-amministrativi-istat/compare/v1.1...v2.0
[1.1]: https://github.com/ondata/confini-amministrativi-istat/compare/v1.0...v1.1
[1.0]: https://github.com/ondata/confini-amministrativi-istat/releases/tag/v1.0
