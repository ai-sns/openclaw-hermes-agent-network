/**
 * SNS Map Configuration Dialog
 */

export class SNSMapConfigDialog {
    constructor() {
        this.dialog = null;
        this.originalMapType = null; // Store original map type
    }

    async show() {
        // Create dialog HTML
        const dialogHTML = `
            <div class="modal-overlay" id="snsMapConfigDialog">
                <div class="modal-dialog" style="max-width: 700px;">
                    <div class="modal-header">
                        <h3>地图配置</h3>
                        <button class="modal-close" onclick="document.getElementById('snsMapConfigDialog').remove()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="map-config-container">
                            <!-- Google Map Section -->
                            <div class="map-section">
                                <h4>Google Map</h4>
                                <div class="form-group">
                                    <label for="googleMapApiKey">地图API Key:</label>
                                    <input type="text" id="googleMapApiKey" class="form-control" placeholder="请输入Google地图API Key">
                                </div>
                                <div class="form-group">
                                    <label for="googleMapId">地图ID:</label>
                                    <input type="text" id="googleMapId" class="form-control" placeholder="请输入Google地图ID">
                                </div>
                            </div>

                            <!-- Baidu Map Section -->
                            <div class="map-section">
                                <h4>Baidu Map</h4>
                                <div class="form-group">
                                    <label for="baiduMapApiKey">地图API Key:</label>
                                    <input type="text" id="baiduMapApiKey" class="form-control" placeholder="请输入百度地图API Key">
                                </div>
                                <div class="form-group">
                                    <label for="baiduMapId">地图ID:</label>
                                    <input type="text" id="baiduMapId" class="form-control" placeholder="请输入百度地图ID">
                                </div>
                            </div>

                            <!-- Map Selection Section -->
                            <div class="map-section">
                                <h4>Select a map to use</h4>
                                <div class="map-selection">
                                    <label class="radio-label">
                                        <input type="radio" name="mapType" value="0" id="googleMapRadio">
                                        <span>Google Map</span>
                                    </label>
                                    <label class="radio-label">
                                        <input type="radio" name="mapType" value="1" id="baiduMapRadio">
                                        <span>Baidu Map</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="document.getElementById('snsMapConfigDialog').remove()">取消</button>
                        <button class="btn btn-primary" id="saveMapConfigBtn">保存</button>
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
            const response = await fetch('http://localhost:8788/api/sns/map-config');
            const result = await response.json();

            if (result.success && result.data) {
                const data = result.data;

                // Store original map type for comparison
                this.originalMapType = data.map_type;

                // Parse API keys and Map IDs
                const apiKeys = data.map_api_key ? data.map_api_key.split(',') : ['', ''];
                const mapIds = data.map_id ? data.map_id.split(',') : ['', ''];

                // Set Google Map values
                document.getElementById('googleMapApiKey').value = apiKeys[0] || '';
                document.getElementById('googleMapId').value = mapIds[0] || '';

                // Set Baidu Map values
                document.getElementById('baiduMapApiKey').value = apiKeys[1] || '';
                document.getElementById('baiduMapId').value = mapIds[1] || '';

                // Set map type selection
                if (data.map_type === '1') {
                    document.getElementById('baiduMapRadio').checked = true;
                } else {
                    document.getElementById('googleMapRadio').checked = true;
                }
            }
        } catch (error) {
            console.error('Error loading map config:', error);
        }
    }

    setupEventListeners() {
        // Save button
        document.getElementById('saveMapConfigBtn').addEventListener('click', () => {
            this.saveConfiguration();
        });
    }

    async saveConfiguration() {
        try {
            // Get form values
            const googleApiKey = document.getElementById('googleMapApiKey').value.trim() || 'N/A';
            const googleMapId = document.getElementById('googleMapId').value.trim() || 'N/A';
            const baiduApiKey = document.getElementById('baiduMapApiKey').value.trim() || 'N/A';
            const baiduMapId = document.getElementById('baiduMapId').value.trim() || 'N/A';
            const mapType = document.querySelector('input[name="mapType"]:checked')?.value || '0';

            // Validate required fields based on selected map
            if (mapType === '0') {
                // Google Map selected
                if (googleApiKey === 'N/A' || !googleApiKey) {
                    alert('Google地图的API Key为必填项，不能为空');
                    return;
                }
                if (googleMapId === 'N/A' || !googleMapId) {
                    alert('Google地图的地图ID为必填项，不能为空');
                    return;
                }
            } else {
                // Baidu Map selected
                if (baiduApiKey === 'N/A' || !baiduApiKey) {
                    alert('百度地图的API Key为必填项，不能为空');
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
            const response = await fetch('http://localhost:8788/api/sns/map-config', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(configData)
            });

            const result = await response.json();
            if (result.success) {
                alert('地图配置保存成功！');

                // Check if map type changed
                if (this.originalMapType !== mapType) {
                    console.log('Map type changed from', this.originalMapType, 'to', mapType, '- reloading map');
                    this.reloadMap();
                }

                this.dialog.remove();
            } else {
                alert('保存失败：' + (result.message || '未知错误'));
            }
        } catch (error) {
            console.error('Error saving map configuration:', error);
            alert('保存失败：' + error.message);
        }
    }

    reloadMap() {
        // Remove existing iframe
        const mapContainer = document.getElementById('mapContainer');
        if (mapContainer) {
            const existingIframe = mapContainer.querySelector('iframe');
            if (existingIframe) {
                existingIframe.remove();
                console.log('Removed existing map iframe');
            }

            // Trigger map reload by dispatching a custom event
            window.dispatchEvent(new CustomEvent('reloadMap'));
        }
    }
}
