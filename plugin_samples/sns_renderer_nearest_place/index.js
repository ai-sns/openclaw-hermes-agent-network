const NearestPlacePlugin = {
    info: {
        id: 'nearest-place',
        name: 'Nearest Place',
        version: '1.0.0',
        description: 'Query nearest place by coordinates'
    },

    async render(container, api) {
        container.innerHTML = `
            <div style="display:flex; flex-direction:column; gap:10px; padding:12px;">
                <div style="font-weight:700; font-size:16px;">Nearest Place</div>

                <div style="display:grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 42px; gap:8px;">
                    <div class="form-group" style="min-width:0;">
                        <label>Lng</label>
                        <input class="form-input" id="np_lng" placeholder="-121.97535981852862" />
                    </div>
                    <div class="form-group" style="min-width:0;">
                        <label>Lat</label>
                        <input class="form-input" id="np_lat" placeholder="37.342402884898505" />
                    </div>
                    <div class="form-group" style="flex:0 0 auto; margin-bottom:0;">
                        <label style="visibility:hidden;">Go</label>
                        <a href="javascript:void(0)" id="np_go" title="Go to coordinates" aria-label="Go to coordinates" style="display:inline-block; width:42px; padding:10px 0; font-size:16px; font-weight:700; line-height:1.5; letter-spacing:0.5px; text-transform:uppercase; text-align:center; text-decoration:underline; color:var(--color-primary,#1a73e8); user-select:none;">GO</a>
                    </div>
                </div>

                <div style="display:flex; gap:8px;">
                    <button class="btn btn-primary" id="np_query" type="button" style="flex:1;">Query</button>
                    <button class="btn btn-secondary" id="np_open" type="button" style="min-width:120px;" disabled>Open URL</button>
                </div>

                <div style="font-size:12px; color:var(--text-secondary,#666);" id="np_status"></div>
                <pre style="white-space:pre-wrap; word-break:break-word; background: var(--bg-secondary,#f5f5f5); padding:10px; border-radius:6px;" id="np_result"></pre>
            </div>
        `;

        const lngEl = container.querySelector('#np_lng');
        const latEl = container.querySelector('#np_lat');
        const goBtn = container.querySelector('#np_go');
        const queryBtn = container.querySelector('#np_query');
        const openBtn = container.querySelector('#np_open');
        const status = container.querySelector('#np_status');
        const resultEl = container.querySelector('#np_result');

        let lastUrl = '';

        const setStatus = (t) => {
            if (status) status.textContent = t ? String(t) : '';
        };

        const setResult = (obj) => {
            if (!resultEl) return;
            try {
                resultEl.textContent = JSON.stringify(obj, null, 2);
            } catch (e) {
                resultEl.textContent = String(obj);
            }
        };

        const setOpenEnabled = (enabled) => {
            if (!openBtn) return;
            openBtn.disabled = !enabled;
        };

        const parsePastedCoordinates = (text) => {
            const raw = (text === undefined || text === null) ? '' : String(text);
            const normalized = raw.replace(/[\r\n\t]/g, ' ').trim();
            const delim = normalized.includes(',') ? ',' : (normalized.includes('，') ? '，' : '');
            if (!delim) return null;

            const parts = normalized.split(delim).map(s => String(s || '').trim()).filter(Boolean);
            if (parts.length < 2) return null;
            return { a: parts[0], b: parts[1] };
        };

        if (lngEl) {
            lngEl.addEventListener('paste', (e) => {
                try {
                    const text = e && e.clipboardData ? e.clipboardData.getData('text') : '';
                    const parsed = parsePastedCoordinates(text);
                    if (!parsed) return;
                    if (e && typeof e.preventDefault === 'function') e.preventDefault();
                    lngEl.value = parsed.a;
                    if (latEl) latEl.value = parsed.b;
                } catch (err) {
                }
            });
        }

        if (latEl) {
            latEl.addEventListener('paste', (e) => {
                try {
                    const text = e && e.clipboardData ? e.clipboardData.getData('text') : '';
                    const parsed = parsePastedCoordinates(text);
                    if (!parsed) return;
                    if (e && typeof e.preventDefault === 'function') e.preventDefault();
                    latEl.value = parsed.a;
                    if (lngEl) lngEl.value = parsed.b;
                } catch (err) {
                }
            });
        }

        const getCoordinates = () => {
            const lng = Number(String(lngEl ? lngEl.value : '').trim());
            const lat = Number(String(latEl ? latEl.value : '').trim());
            return { lng, lat };
        };

        const goToCoordinates = () => {
            const { lng, lat } = getCoordinates();

            if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
                api.ui.toast('error', 'Lng/Lat must be numbers.');
                return false;
            }

            try {
                const ok = api.map && typeof api.map.postMessage === 'function'
                    ? api.map.postMessage({
                        type: 'mapGoTo',
                        data: {
                            lng,
                            lat,
                            zoom: 17
                        }
                    })
                    : false;

                if (!ok) {
                    api.ui.toast('error', 'Map is not ready.');
                    return false;
                }
            } catch (e) {
                api.ui.toast('error', `Go failed: ${e && e.message ? e.message : String(e)}`);
                return false;
            }

            return true;
        };

        if (goBtn) {
            goBtn.addEventListener('click', (e) => {
                if (e && typeof e.preventDefault === 'function') e.preventDefault();
                goToCoordinates();
            });
        }

        if (openBtn) {
            openBtn.addEventListener('click', () => {
                if (!lastUrl) return;
                if (api.ui && typeof api.ui.openPlaceIntro === 'function') {
                    api.ui.openPlaceIntro(lastUrl);
                    return;
                }
                api.ui.openUrl(lastUrl);
            });
        }

        if (queryBtn) {
            queryBtn.addEventListener('click', async () => {
                const { lng, lat } = getCoordinates();

                if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
                    api.ui.toast('error', 'Lng/Lat must be numbers.');
                    return;
                }

                setStatus('Querying...');
                setOpenEnabled(false);
                lastUrl = '';

                try {
                    const resp = await api.sns.jsonrpc('update_location_and_get_nearest_place', {
                        lng,
                        lat,
                        max_distance_m: 1000
                    });

                    setResult(resp);

                    const result = resp && resp.result ? resp.result : resp;
                    const data = result && result.data ? result.data : {};
                    const urlCandidates = [
                        data && data.url ? String(data.url) : '',
                        data && data.place && data.place.url ? String(data.place.url) : ''
                    ].map(x => String(x || '').trim()).filter(Boolean);

                    const url = urlCandidates.length ? urlCandidates[0] : '';
                    if (url) {
                        lastUrl = url;
                        setOpenEnabled(true);
                        setStatus('Found a place URL.');
                    } else {
                        setStatus('No URL returned.');
                    }
                } catch (e) {
                    setStatus(`Query failed: ${e && e.message ? e.message : String(e)}`);
                }
            });
        }

        setStatus('Enter coordinates and click Query.');
        setResult({});
    }
};

export default NearestPlacePlugin;
