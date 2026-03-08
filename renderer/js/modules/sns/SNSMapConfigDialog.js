/**
 * SNS Map Configuration Dialog
 */

export class SNSMapConfigDialog {
    constructor() {
        this.dialog = null;
        this.originalMapType = null; // Store original map type
    }

    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    }

    async show() {
        const existing = document.getElementById('snsMapConfigDialog');
        if (existing) {
            try {
                existing.remove();
            } catch (e) {
            }
        }

        // Create dialog HTML
        const dialogHTML = `
            <div class="modal-overlay" id="snsMapConfigDialog">
                <div class="modal-dialog" style="max-width: 700px;">
                    <div class="modal-header">
                        <h3>Map Configuration</h3>
                        <button class="modal-close" id="snsMapConfigDialogCloseBtn">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="map-config-container">
                            <!-- Google Map Section -->
                            <div class="map-section">
                                <h4>Google Map</h4>
                                <div class="form-group">
                                    <label for="googleMapApiKey">API Key:</label>
                                    <input type="text" id="googleMapApiKey" class="form-control" placeholder="Enter Google Maps API key">
                                </div>
                                <div class="form-group">
                                    <label for="googleMapId">Map ID:</label>
                                    <input type="text" id="googleMapId" class="form-control" placeholder="Enter Google map ID">
                                </div>
                            </div>

                            <!-- Baidu Map Section -->
                            <div class="map-section">
                                <h4>Baidu Map</h4>
                                <div class="form-group">
                                    <label for="baiduMapApiKey">API Key:</label>
                                    <input type="text" id="baiduMapApiKey" class="form-control" placeholder="Enter Baidu Maps API key">
                                </div>
                                <div class="form-group">
                                    <label for="baiduMapId">Map ID:</label>
                                    <input type="text" id="baiduMapId" class="form-control" placeholder="Enter Baidu map ID (optional)">
                                </div>
                            </div>

                            <!-- Map Selection Section -->
                            <div class="map-section">
                                <h4>Select a map to use</h4>
                                <div class="map-selection">
                                    <label class="profession-label">
                                        <input type="radio" name="mapType" value="0" id="googleMapRadio" checked>
                                        <span>Google Map</span>
                                    </label>
                                    <label class="profession-label">
                                        <input type="radio" name="mapType" value="1" id="baiduMapRadio">
                                        <span>Baidu Map</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" id="snsMapConfigDialogCancelBtn">Cancel</button>
                        <button class="btn btn-primary" id="saveMapConfigBtn">Save</button>
                    </div>
                </div>
            </div>
        `;

        // Add to DOM
        document.body.insertAdjacentHTML('beforeend', dialogHTML);
        this.dialog = document.getElementById('snsMapConfigDialog');

        // Load current configuration
        await this.loadMapConfig();

        // Setup event listeners
        this.setupEventListeners();
    }

    async loadMapConfig() {
        try {
            const response = await fetch(this.resolve('/api/sns/map-config'));
            const result = await response.json();

            if (result.success && result.data) {
                const data = result.data;

                const normalize = (v) => {
                    const s = (v === null || v === undefined) ? '' : String(v);
                    const t = s.trim();
                    return (t && t !== 'N/A') ? t : '';
                };

                // Store original map type for comparison
                this.originalMapType = normalize(data.map_type);

                // Parse API keys and Map IDs
                const apiKeys = data.map_api_key ? String(data.map_api_key).split(',') : ['', ''];
                const mapIds = data.map_id ? String(data.map_id).split(',') : ['', ''];

                // Set Google Map values
                document.getElementById('googleMapApiKey').value = normalize(apiKeys[0]);
                document.getElementById('googleMapId').value = normalize(mapIds[0]);

                // Set Baidu Map values
                document.getElementById('baiduMapApiKey').value = normalize(apiKeys[1]);
                document.getElementById('baiduMapId').value = normalize(mapIds[1]);

                // Set map type selection
                const mapType = normalize(data.map_type);
                if (mapType === '1') {
                    document.getElementById('baiduMapRadio').checked = true;
                } else {
                    document.getElementById('googleMapRadio').checked = true;
                }
            }
        } catch (error) {
            console.error('Failed to load map config:', error);
        }
    }

    setupEventListeners() {
        const closeBtn = document.getElementById('snsMapConfigDialogCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                try {
                    if (this.dialog) this.dialog.remove();
                } catch (e) {
                }
            });
        }

        const cancelBtn = document.getElementById('snsMapConfigDialogCancelBtn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                try {
                    if (this.dialog) this.dialog.remove();
                } catch (e) {
                }
            });
        }

        // Save button
        document.getElementById('saveMapConfigBtn').addEventListener('click', () => {
            this.saveConfiguration();
        });
    }

    async saveConfiguration() {
        try {
            // Get form values
            const googleApiKey = document.getElementById('googleMapApiKey').value.trim();
            const googleMapId = document.getElementById('googleMapId').value.trim();
            const baiduApiKey = document.getElementById('baiduMapApiKey').value.trim();
            const baiduMapId = document.getElementById('baiduMapId').value.trim();
            const mapType = document.querySelector('input[name="mapType"]:checked')?.value || '0';

            // Validate required fields based on selected map
            if (mapType === '0') {
                // Google Map selected
                if (!googleApiKey) {
                    alert('Google Maps API key is required.');
                    return;
                }
                if (!googleMapId) {
                    alert('Google map ID is required.');
                    return;
                }
            } else {
                // Baidu Map selected
                if (!baiduApiKey) {
                    alert('Baidu Maps API key is required.');
                    return;
                }
            }

            // Prepare data
            const configData = {
                google_api_key: googleApiKey,
                google_map_id: googleMapId,
                baidu_api_key: baiduApiKey,
                baidu_map_id: baiduMapId,
                map_type: mapType
            };

            // Send to backend
            const response = await fetch(this.resolve('/api/sns/map-config'), {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(configData)
            });

            const result = await response.json();
            if (result.success) {
                alert('Map configuration saved successfully.');

                try {
                    localStorage.setItem('sns_map_type', String(mapType));
                } catch (e) {
                }

                // Check if map type changed
                if (String(this.originalMapType) !== String(mapType)) {
                    console.log('Map type changed from', this.originalMapType, 'to', mapType, '- reloading map iframe');
                    this.reloadMap();
                }

                this.dialog.remove();
            } else {
                alert('Save failed: ' + (result.message || 'Unknown error'));
            }
        } catch (error) {
            console.error('Failed to save map configuration:', error);
            alert('Save failed: ' + error.message);
        }
    }

    reloadMap() {
        // Dispatch reloadMap event and let loadMapIframe(true) handle
        // stopping the engine, removing the old iframe, and creating a new one.
        // Do NOT remove the iframe here — loadMapIframe needs to find it
        // so it can call stopEngineIfActiveForMapReload before removal.
        console.log('Map config changed - dispatching reloadMap event');
        window.dispatchEvent(new CustomEvent('reloadMap'));
    }
}
