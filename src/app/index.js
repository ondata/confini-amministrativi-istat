import { createRoot } from "react-dom/client";
import { App } from "./App";

// Constants
window.API_DOMAIN = process.env.NODE_ENV !== 'production' ? 'http://localhost:8080' : '';

// Current year
(function () {
    document.getElementById('year').innerText = (new Date()).getFullYear();
})();

// Swagger UI
(function () {
    window.ui = SwaggerUIBundle({
        url: `${window.API_DOMAIN}/api/v2/openapi.v2.yml`,
        dom_id: '#docs',
        deepLinking: true,
        presets: [
            SwaggerUIBundle.presets.apis,
            SwaggerUIStandalonePreset
        ],
        plugins: [
            SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "BaseLayout"
    });
})();

// Leaflet
(function () {
    // Register watermark control
    L.Control.Watermark = L.Control.extend({
        onAdd: () => {
            var img = L.DomUtil.create('img');
            img.src = 'https://www.ondata.it/wp-content/uploads/2022/03/logo-onData-corretto-trasparente.png';
            img.style.width = '125px';
            return img;
        }
    });

    L.control.watermark = function (opts) {
        return new L.Control.Watermark(opts);
    }
})();

// React
const appRoot = createRoot(document.getElementById('app'));
appRoot.render(<App />);
