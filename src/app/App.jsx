import { useEffect, useRef, useState } from "react";
import Select from "react-select";

export function App() {
    const selectRefs = useRef({});
    const downloadRef = useRef();

    const firstResource = `${window.API_DOMAIN}/api/v2/index.json`;
    const geoResourceType = "application/geo+json";
    const labels = ["country", "release", "division", "territory", "subdivision"];
    const profiles = labels.map(s => `/api/v2/hal-${s}.schema.json`);

    const [options, setOptions] = useState({});
    const [resources, setResources] = useState([]);
    const [downloadPath, setDownloadPath] = useState('#');

    function loadOptions(src) {
        if (src) {
            fetch(src)
                .then(res => res.json())
                .then(data => {
                    const items = data._links.item ?? [];
                    const enclosures = data._links.enclosure ?? [];
                    const geoResource = enclosures.length && enclosures.find(e => e.type === geoResourceType)?.href;

                    if (items.length > 0) {
                        const target = items[0].profile;
                        const targetIndex = profiles.findIndex(p => p === target);

                        setOptions(oldOptions => ({
                            ...oldOptions,
                            [target]: items.map(item => ({
                                value: `${window.API_DOMAIN}${item.href}`,
                                label: item.title
                            })),
                            ...profiles.slice(targetIndex + 1).reduce((options, target) => ({
                                ...options,
                                [target]: []
                            }), {})
                        }));

                        profiles.slice(targetIndex).forEach(p => selectRefs.current[p]?.clearValue?.());
                    }

                    window.updateMap(geoResource ? `${window.API_DOMAIN}${geoResource}` : '');
                    setResources(enclosures.length ? enclosures.map(e => ({ value: e.href, label: e.title })) : []);
                    downloadRef.current?.clearValue?.();
                    setDownloadPath('#');
                });
        }
    }

    useEffect(() => {
        loadOptions(firstResource);
    }, []);

    return (
        <ol className="flex flex-col gap-6 mb-12">
            {
                profiles.map((p, i) => (
                    <li key={p} className="flex flex-col gap-2">
                        <label className="capitalize" htmlFor={p}>{labels[i]}</label>
                        <Select
                            id={p}
                            ref={el => (selectRefs.current[p] = el)}
                            name={p}
                            placeholder={`Select a ${labels[i]}...`}
                            isDisabled={!options[p]?.length}
                            options={options[p] ?? []}
                            onChange={e => loadOptions(e?.value)}
                        />
                    </li>
                ))
            }

            <li key="format" className="flex flex-col gap-2">
                <label className="capitalize" htmlFor="format">Format</label>
                <Select
                    id="format"
                    ref={downloadRef}
                    name="format"
                    placeholder="Select a file format..."
                    isDisabled={!resources.length}
                    options={resources}
                    onChange={e => setDownloadPath(e?.value ?? '#')}
                />
            </li>

            <li key="download" className="flex flex-col gap-2">
                {resources.length > 0 && downloadPath !== '#'
                    ? (
                        <a
                            className="bg-ored text-oblue-dark font-bold py-2 px-4 rounded inline-flex items-center justify-between"
                            target="_blank"
                            href={`${window.API_DOMAIN}${downloadPath}`}
                            download={`ondata_confini_amministrativi_${downloadPath.replace(/^\//, '').replace(/\//g, '_')}`}
                        >
                            <span>Download</span>
                            <svg className="fill-current w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                                <path d="M13 8V2H7v6H2l8 8 8-8h-5zM0 18h20v2H0v-2z" />
                            </svg>
                        </a>
                    )
                    : (
                        <button className="bg-oblue-dark text-oblue-light border-oblue-dark font-bold py-2 px-4 rounded inline-flex items-center justify-between opacity-50 cursor-not-allowed">
                            <span>Download</span>
                            <svg className="fill-current w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                                <path d="M13 8V2H7v6H2l8 8 8-8h-5zM0 18h20v2H0v-2z" />
                            </svg>
                        </button>
                    )
                }
            </li>
        </ol>
    );
}
