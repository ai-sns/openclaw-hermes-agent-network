# Map Configuration Implementation Summary

## Overview
Added a fourth configuration button "地图配置" (Map Config) to the SNS page's Process tab, allowing users to configure Google Map and Baidu Map settings.

## Changes Made

### 1. Frontend Changes

#### renderer/js/modules/sns/SNSPage.js
- Added a fourth config button with ID `snsMapConfigBtn` after the social role button
- Icon: Map icon (SVG path for map visualization)
- Label: "地图配置"

#### renderer/js/modules/sns/SNSMapConfigDialog.js (NEW FILE)
- Created new dialog component following the same pattern as SNSAvatarDialog
- Features:
  - Google Map section with API Key and Map ID inputs
  - Baidu Map section with API Key and Map ID inputs
  - Radio button selection for choosing which map to use
  - Validation: Required fields based on selected map type
  - Loads current configuration from backend
  - Saves configuration to backend

#### renderer/js/modules/sns/snsHandlers.js
- Imported SNSMapConfigDialog
- Added event listener for `snsMapConfigBtn` that opens the dialog

### 2. Backend Changes

#### backend/modules/sns/service.py
Added three new methods:

1. **get_map_config()**
   - Retrieves map configuration from aichat_cfg table
   - Returns: map_api_key, map_id, map_type

2. **update_map_config(data)**
   - Updates map configuration in database
   - Handles map type switching with position data preservation
   - Stores old position data in memo field when switching map types
   - Resets route fields when map type changes
   - Calls file replacement method

3. **_replace_map_config_in_files(old_api_keys, old_map_ids, new_api_keys, new_map_ids)**
   - Replaces API keys and Map IDs in actual HTML/JS files
   - Google Map files:
     - scripts/googlemap3d.html
     - scripts/js/google/map_common.js
   - Baidu Map files:
     - scripts/map.html
   - Uses regex patterns to find and replace values

#### backend/modules/sns/router.py
Added two new API endpoints:

1. **GET /api/sns/map-config**
   - Returns current map configuration

2. **PUT /api/sns/map-config**
   - Updates map configuration
   - Request body:
     ```json
     {
       "google_api_key": "string",
       "google_map_id": "string",
       "baidu_api_key": "string",
       "baidu_map_id": "string",
       "map_type": "0" or "1"
     }
     ```

## Implementation Details

### Database Fields Used (aichat_cfg table)
- `map_api_key`: Comma-separated string "google_key,baidu_key"
- `map_id`: Comma-separated string "google_id,baidu_id"
- `map_type`: "0" for Google, "1" for Baidu
- `memo`: JSON field storing position data for each map type
- Position fields: `home_position`, `positionx`, `positiony`, `positionz`
- Route fields: `route_start`, `route_end`, `route_current_position`, `route`, `route_status`

### Map Type Switching Logic
When switching between map types:
1. Current position data is saved to memo field under the old map type key
2. Route fields are reset
3. Position data for the new map type is loaded from memo (if exists)
4. This allows users to maintain separate positions for each map type

### File Replacement Logic
The implementation follows the same pattern as aimapcfgdialog.py:
- Uses regex patterns to find API keys and Map IDs in files
- Only replaces non-empty, non-"N/A" values
- Handles different file formats (Google vs Baidu)
- Logs all replacements for debugging

## Testing
To test the implementation:
1. Start the backend: `python api_server.py`
2. Start the Electron app
3. Navigate to SNS page
4. Click on the "地图配置" button in the Process tab
5. Fill in the map configuration details
6. Select a map type
7. Click "保存" to save

## Reference Implementation
The implementation closely follows the pattern established in:
- `aimapcfgdialog.py` - For database updates and file replacement logic
- `SNSAvatarDialog.js` - For frontend dialog structure
- Existing SNS config dialogs - For consistent UI/UX
