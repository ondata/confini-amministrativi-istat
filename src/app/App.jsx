import { useEffect, useRef, useState } from 'react';
import Select from 'react-select';

export function App() {
    const initialCenter = [42.5206995, 13.2275392];
    const initialZoom = 6;

    let map;
    let mapLayer;

    function ControlsItem({ id, label, children }) {
        return (
            <li className="flex flex-col gap-2">
                <label className="capitalize" htmlFor={id}>
                    {label}
                </label>
                {children}
            </li>
        );
    }

    function Controls() {
        const selectRefs = useRef({});
        const downloadRef = useRef();

        const firstResource = `${window.API_DOMAIN}/api/v2/index.json`;
        const geoResourceType = 'application/geo+json';
        const labels = [
            'country',
            'release',
            'division',
            'territory',
            'subdivision',
        ];
        const profiles = labels.map((s) => `/api/v2/hal-${s}.schema.json`);

        const [options, setOptions] = useState({});
        const [resources, setResources] = useState([]);
        const [downloadPath, setDownloadPath] = useState('#');

        async function loadOptions(src) {
            if (!src) return;

            const res = await fetch(src);
            const data = await res.json();
            const items = data._links.item ?? [];
            const enclosures = data._links.enclosure ?? [];
            const geoResource =
                enclosures.length &&
                enclosures.find((e) => e.type === geoResourceType)?.href;

            if (items.length) {
                const target = items[0].profile;
                const targetIndex = profiles.findIndex((p) => p === target);

                setOptions((oldOptions) => ({
                    ...oldOptions,
                    [target]: items.map((item) => ({
                        value: `${window.API_DOMAIN}${item.href}`,
                        label: item.title,
                    })),
                    ...profiles.slice(targetIndex + 1).reduce(
                        (options, target) => ({
                            ...options,
                            [target]: [],
                        }),
                        {}
                    ),
                }));

                profiles
                    .slice(targetIndex)
                    .forEach((p) => selectRefs.current[p]?.clearValue?.());
            }

            updateMap(geoResource ? `${window.API_DOMAIN}${geoResource}` : '');
            setResources(
                enclosures.length
                    ? enclosures.map((e) => ({ value: e.href, label: e.title }))
                    : []
            );
            downloadRef.current?.clearValue?.();
            setDownloadPath('#');
        }

        async function updateMap(geoResource) {
            if (geoResource) {
                // Fetch GeoJSON data
                const res = await fetch(geoResource);
                const geojson = await res.json();

                // Remove previous layer
                mapLayer && map.removeLayer(mapLayer);

                // Add new layer
                mapLayer = L.geoJson(geojson, {
                    style: () => ({
                        color: '#eb593c',
                        weight: 2,
                        fillColor: '#2e85d1',
                        fillOpacity: 0.66,
                    }),
                })
                    .bindPopup(
                        (layer) => `
                    <table>
                        ${Object.entries(layer.feature.properties)
                            .sort(([a], [b]) => a.localeCompare(b))
                            .map(
                                ([k, v]) =>
                                    `<tr><th>${k}</th><td>${v}</td></tr>`
                            )
                            .join('\n')}
                    </table>
                `
                    )
                    .addTo(map);

                // Adapt map zoom and pan
                map.fitBounds(mapLayer.getBounds());
            } else {
                mapLayer && map.removeLayer(mapLayer);
                map.setView(initialCenter, initialZoom);
            }
        }

        useEffect(() => {
            loadOptions(firstResource);
        }, []);

        return (
            <>
                <ol className="flex flex-col gap-6">
                    {profiles.map((p, i) => (
                        <ControlsItem key={p} id={p} label={labels[i]}>
                            <Select
                                id={p}
                                ref={(el) => (selectRefs.current[p] = el)}
                                name={p}
                                placeholder={`Select a ${labels[i]}...`}
                                isDisabled={!options[p]?.length}
                                options={options[p] ?? []}
                                onChange={(e) => loadOptions(e?.value)}
                            />
                        </ControlsItem>
                    ))}
                </ol>

                {resources.length > 0 && (
                    <ol className="flex flex-col gap-6">
                        <ControlsItem key="format" id="format" label="Format">
                            <Select
                                id="format"
                                ref={downloadRef}
                                name="format"
                                placeholder="Select a file format..."
                                isDisabled={!resources.length}
                                options={resources}
                                onChange={(e) => setDownloadPath(e?.value ?? '#')}
                            />
                        </ControlsItem>

                        
                        <li key="download" className="flex flex-col gap-2">
                            {downloadPath !== '#' ? (
                                <a
                                    className="bg-ored text-oblue-dark font-bold py-2 px-4 rounded inline-flex items-center justify-between"
                                    target="_blank"
                                    href={`${window.API_DOMAIN}${downloadPath}`}
                                    download={`ondata_confini_amministrativi_${downloadPath
                                        .replace(/^\//, '')
                                        .replace(/\//g, '_')}`}>
                                    <span>Download</span>
                                    <svg
                                        className="fill-current w-4 h-4 mr-2"
                                        xmlns="http://www.w3.org/2000/svg"
                                        viewBox="0 0 20 20">
                                        <path d="M13 8V2H7v6H2l8 8 8-8h-5zM0 18h20v2H0v-2z" />
                                    </svg>
                                </a>
                            ) : (
                                <button className="bg-oblue-dark text-oblue-light border-oblue-dark font-bold py-2 px-4 rounded inline-flex items-center justify-between opacity-50 cursor-not-allowed">
                                    <span>Download</span>
                                    <svg
                                        className="fill-current w-4 h-4 mr-2"
                                        xmlns="http://www.w3.org/2000/svg"
                                        viewBox="0 0 20 20">
                                        <path d="M13 8V2H7v6H2l8 8 8-8h-5zM0 18h20v2H0v-2z" />
                                    </svg>
                                </button>
                            )}
                        </li>
                    </ol>
                )}
            </>
        );
    }

    function Map() {
        const mapRef = useRef(null);

        useEffect(() => {
            // Setup map
            map = L.map(mapRef.current, { scrollWheelZoom: false }).setView(
                initialCenter,
                initialZoom
            );

            // Setup tiles
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution:
                    '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            }).addTo(map);

            // Add watermark
            L.control.watermark({ position: 'bottomleft' }).addTo(map);

            return () => map.remove();
        }, []);

        return (
            <div
                ref={mapRef}
                className="grow overflow-hidden max-sm:hidden"></div>
        );
    }

    return (
        <main className="min-h-screen bg-oblue-light text-oblue-dark flex flex-row justify-center">
            <section className="p-6 max-w-sm flex flex-col justify-between">
                <Controls />
            </section>
            <Map />
        </main>
    );
}
