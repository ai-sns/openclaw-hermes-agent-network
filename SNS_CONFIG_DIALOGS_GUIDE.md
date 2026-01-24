# SNS Configuration Dialogs - Integration Guide

## Overview
Three new configuration dialogs have been created for the SNS module:
1. Avatar Configuration Dialog (upload + 3D avatar selection)
2. Profession Selection Dialog
3. Social Role Configuration Dialog

## Files Created

### Backend Files
1. **Backend API Endpoints** - `/backend/modules/sns/router.py`
   - `GET /api/sns/config` - Get AI chat configuration
   - `PUT /api/sns/config` - Update AI chat configuration
   - `POST /api/sns/config/upload-avatar` - Upload avatar image
   - `GET /api/sns/avatars3d` - Get list of 3D avatars
   - `GET /api/sns/professions` - Get list of professions
   - `GET /api/sns/social-roles` - Get social roles (SNS prompts)

2. **Backend Schemas** - `/backend/modules/sns/schemas.py`
   - `AIChatConfigResponse`
   - `AIChatConfigUpdateRequest`
   - `Avatar3DItem`
   - `ProfessionItem`
   - `SocialRoleItem`

3. **Backend Service** - `/backend/modules/sns/service.py`
   - `get_ai_chat_config()`
   - `update_ai_chat_config()`
   - `upload_avatar()`
   - `get_social_roles()`

### Frontend Files
1. **Dialog Components**
   - `/renderer/js/modules/sns/SNSAvatarDialog.js`
   - `/renderer/js/modules/sns/SNSProfessionDialog.js`
   - `/renderer/js/modules/sns/SNSSocialRoleDialog.js`

2. **Styles**
   - `/renderer/css/sns-config-dialogs.css`

3. **Integration**
   - `/renderer/js/modules/sns/snsHandlers.js` (updated with dialog imports and init methods)

## How to Use

### 1. Include CSS in index.html
Add this line to `/renderer/index.html` in the `<head>` section:
```html
<link rel="stylesheet" href="css/sns-config-dialogs.css">
```

### 2. Add Configuration Buttons to SNS UI
Add these buttons to the SNS status panel (in `/renderer/js/modules/sns/SNSPage.js`):

```html
<!-- Add this section in the Process tab, before Current Status -->
<div class="status-section">
    <div class="status-section-title">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
            <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
        </svg>
        Configuration
    </div>
    <div class="config-buttons">
        <button class="config-btn" id="snsAvatarConfigBtn">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
            <span>头像配置</span>
        </button>
        <button class="config-btn" id="snsProfessionConfigBtn">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z"/>
            </svg>
            <span>职业选择</span>
        </button>
        <button class="config-btn" id="snsSocialRoleConfigBtn">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
            </svg>
            <span>社交角色</span>
        </button>
    </div>
</div>
```

### 3. Add Button Styles to sns.css
Add these styles to `/renderer/css/sns.css`:

```css
/* Configuration Buttons */
.config-buttons {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px 0;
}

.config-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 15px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 14px;
    font-weight: 500;
}

.config-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.config-btn svg {
    flex-shrink: 0;
}
```

## Usage Examples

### Opening Dialogs Programmatically

```javascript
// Avatar configuration
import { SNSAvatarDialog } from './modules/sns/SNSAvatarDialog.js';
const avatarDialog = new SNSAvatarDialog();
await avatarDialog.show();

// Profession selection
import { SNSProfessionDialog } from './modules/sns/SNSProfessionDialog.js';
const professionDialog = new SNSProfessionDialog();
await professionDialog.show();

// Social role configuration
import { SNSSocialRoleDialog } from './modules/sns/SNSSocialRoleDialog.js';
const socialRoleDialog = new SNSSocialRoleDialog();
await socialRoleDialog.show();
```

## Features

### Avatar Configuration Dialog
- Upload custom avatar images
- Select from 31 pre-made 3D avatars
- Preview avatars before saving
- Saves to `aichat_cfg.avatar` and `aichat_cfg.avatar3d` fields

### Profession Selection Dialog
- Shows current balance
- Lists professions with startup costs
- Disables professions user can't afford
- Groups professions by cost requirement
- Saves to `aichat_cfg.profession` field

### Social Role Configuration Dialog
- Lists all prompts tagged with "SNS"
- Shows role details and content
- Preview role before selection
- Emits `social-role-selected` event when saved

## Database Schema

### aichat_cfg Table Fields Used
- `avatar` (Text) - Base64 encoded avatar image
- `avatar3d` (Text) - Selected 3D avatar name
- `profession` (String) - Selected profession name
- `money` (Float) - Current balance (for profession validation)

### prompts Table
- Filtered by `tags LIKE '%SNS%'`
- Returns: id, title, content, question, tags

## API Testing

Test the backend APIs:

```bash
# Get configuration
curl http://localhost:8788/api/sns/config

# Update configuration
curl -X PUT http://localhost:8788/api/sns/config \
  -H "Content-Type: application/json" \
  -d '{"profession": "医生", "avatar3d": "cbot_0_0_0_0_1_0"}'

# Get 3D avatars
curl http://localhost:8788/api/sns/avatars3d

# Get professions
curl http://localhost:8788/api/sns/professions

# Get social roles
curl http://localhost:8788/api/sns/social-roles
```

## Notes

1. The dialogs are already integrated into `snsHandlers.js` via the `initConfigButtons()` method
2. The CSS file needs to be included in `index.html`
3. The configuration buttons need to be added to the SNS UI (SNSPage.js)
4. All backend endpoints are ready and functional
5. Avatar uploads are stored in `uploads/avatars/` directory
6. 3D avatar previews are served from `scripts/avatar3d/` directory

## Troubleshooting

If dialogs don't appear:
1. Check browser console for import errors
2. Verify CSS file is loaded
3. Ensure button IDs match: `snsAvatarConfigBtn`, `snsProfessionConfigBtn`, `snsSocialRoleConfigBtn`
4. Check that backend API server is running on port 8788
