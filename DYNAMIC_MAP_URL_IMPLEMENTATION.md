# Dynamic Map URL Loading Implementation

## Overview
Modified the Electron main process to dynamically load the appropriate map URL based on the user's map configuration instead of hardcoding the Baidu map URL.

## Changes Made

### electron/main.js

#### Modified `createMapWindow()` function:
1. **Changed to async function** - Now fetches map configuration before loading the window
2. **Fetches map configuration** - Calls the backend API endpoint `/api/sns/map-config`
3. **Dynamic URL selection**:
   - If `map_type === '0'`: Loads Google Map (`googlemap3d.html`)
   - If `map_type === '1'`: Loads Baidu Map (`map.html`)
   - Default: Baidu Map (if API call fails or no config found)
4. **Error handling** - Falls back to Baidu map if the API call fails

#### Updated function calls:
- Added `.catch()` handlers to both `createMapWindow()` calls to prevent unhandled promise rejections
- Locations:
  - Tray menu "地图" click handler (line 177)
  - IPC handler for 'open-map-window' (line 237)

## Implementation Details

### API Call
```javascript
const response = await fetch(`${API_BASE_URL}/api/sns/map-config`);
const result = await response.json();
```

### URL Selection Logic
```javascript
let mapUrl = `${API_BASE_URL}/scripts/map.html`; // Default: Baidu

if (result.success && result.data) {
    const mapType = result.data.map_type;
    if (mapType === '0') {
        mapUrl = `${API_BASE_URL}/scripts/googlemap3d.html`; // Google
    }
}
```

### Error Handling
- Try-catch block wraps the API call
- On error, logs to console and falls back to Baidu map
- Promise rejection handlers added to all `createMapWindow()` calls

## Benefits
1. **User preference respected** - Map window loads the user's selected map type
2. **Seamless integration** - Works with the map configuration dialog
3. **Robust error handling** - Falls back gracefully if API is unavailable
4. **No breaking changes** - Maintains backward compatibility with default Baidu map

## Testing
1. Set map type to Google in the map configuration dialog
2. Open the map window (via tray menu or IPC)
3. Verify Google Map loads
4. Change to Baidu Map in configuration
5. Close and reopen map window
6. Verify Baidu Map loads

## Related Files
- `backend/modules/sns/router.py` - API endpoint `/api/sns/map-config`
- `backend/modules/sns/service.py` - `get_map_config()` method
- `renderer/js/modules/sns/SNSMapConfigDialog.js` - Map configuration UI
