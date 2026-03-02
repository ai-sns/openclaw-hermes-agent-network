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
                <div style="font-weight:600;">Nearest Place</div>

                <div style="display:flex; gap:8px;">
                    <div class="form-group" style="flex:1;">
                        <label>Lng</label>
                        <input class="form-input" id="np_lng" placeholder="116.3974" />
                    </div>
                    <div class="form-group" style="flex:1;">
                        <label>Lat</label>
                        <input class="form-input" id="np_lat" placeholder="39.9093" />
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

        if (openBtn) {
            openBtn.addEventListener('click', () => {
                if (!lastUrl) return;
                api.ui.openUrl(lastUrl);
            });
        }

        if (queryBtn) {
            queryBtn.addEventListener('click', async () => {
                const lng = Number(String(lngEl ? lngEl.value : '').trim());
                const lat = Number(String(latEl ? latEl.value : '').trim());

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
