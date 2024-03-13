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
    // Leaflet map initialization
    let layer;
    const initialCentroid = [42.5206995, 13.2275392];
    const initialZoom = 6;
    const map = L.map('map', { scrollWheelZoom: false }).setView(initialCentroid, initialZoom);

    // Tile layer loading
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    // Watermark
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

    L.control.watermark({ position: 'bottomleft' }).addTo(map);

    window.updateMap = async (geoResource) => {
        if (geoResource) {
            // Fetch GeoJSON data
            const response = await fetch(geoResource);
            const geojson = await response.json();

            // Layer loading
            layer && map.removeLayer(layer);
            layer = L.geoJson(
                geojson,
                {
                    style: function (feature) {
                        return {
                            color: "#EB593C",
                            weight: 2,
                            fillColor: "#2E85D1",
                            fillOpacity: 0.66
                        };
                    }
                }
            ).bindPopup(layer => `
                <table>
                    ${Object.entries(layer.feature.properties).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join("\n")}
                </table>
            `).addTo(map);

            // Adapt map zoom and pan
            map.fitBounds(layer.getBounds());
        } else {
            layer && map.removeLayer(layer);
            map.setView(initialCentroid, initialZoom);
        }
    };
})();

// React
const container = document.getElementById("controls");
const root = createRoot(container);
root.render(<App />);
