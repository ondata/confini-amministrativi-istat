# OnData - Confini amministrativi italiani - Homepage

The homepage of the project is a static webpage built using [ParcelJS](https://parceljs.org/).

Tech stack includes [NodeJS](https://nodejs.org/en) (lts version recommended), [ParcelJS](https://parceljs.org/),
[TailwindCSS](https://tailwindcss.com/), [React](https://react.dev/), [React Select](https://react-select.com/).

All dependencies are listed in the `package.json` file.

## Getting started

Clone this repo and enter the `src/app` folder.
Then install all dependencies with `npm i` and build the page with `npm run build`.

Built files will be emitted in `dist/` folder.
You can serve them locally on http://localhost:8080
running `bash run.sh serve` from the root directory.

## Development

Just run the development server with `npm run start`,
every changes in source code will fire a live reload of the page at http://localhost:1234.

Please note you must serve the static files in `dist/api/` running `bash run.sh serve`
from the root directory to have a fully working application.

Available scripts:
- `npm run start` starts the development server
- `npm run clean` cleans the `dist/` folder
- `npm run build` calls clean script and builds the page in `dist/` folder
