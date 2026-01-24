# SNS Sidebar Tab Implementation

## Changes Made

### 1. Removed "Contact List" Header
- Removed the `<div class="contact-header">Contact List</div>` to make the sidebar more compact vertically

### 2. Added Tab Functionality
- Added two tabs: "Chat" and "Trade"
- Clicking tabs switches between contact list and trade list
- Tab switching is handled by `setupTabSwitching()` method

### 3. Updated HTML Structure (SNSSidebar.js)

#### Added Tab Buttons
```html
<div class="sns-sidebar-tabs">
    <button class="sidebar-tab active" data-tab="chat">Chat</button>
    <button class="sidebar-tab" data-tab="trade">Trade</button>
</div>
```

#### Added Tab Content Sections
```html
<!-- Contact List -->
<div class="contact-section tab-content active" data-content="chat">
    ...
</div>

<!-- Trade List -->
<div class="trade-section tab-content" data-content="trade">
    <div class="trade-list" id="tradeList"></div>
</div>
```

### 4. Added JavaScript Methods (SNSSidebar.js)

#### Data Properties
- `trades: []` - Stores trade list data
- `currentTab: 'chat'` - Tracks current active tab

#### Methods Added
- `loadTrades()` - Loads trade data from `/api/map/trades`
- `renderTrades()` - Renders trade list in UI
- `setupTabSwitching()` - Sets up tab click event handlers

#### Trade Item Display
Each trade shows:
- Title and pay amount
- Detail description
- Trade partner name
- Status (Pending/Completed)

### 5. Added CSS Styles (sns.css)

#### Tab Styles
- `.sns-sidebar-tabs` - Tab container with flexbox layout
- `.sidebar-tab` - Individual tab button styling
- `.sidebar-tab.active` - Active tab with blue background
- `.tab-content` - Hidden by default
- `.tab-content.active` - Visible when active

#### Trade List Styles
- `.trade-section` - Trade list container with scrolling
- `.trade-item` - Individual trade card with hover effects
- `.trade-header` - Title and pay amount row
- `.trade-detail` - Description text
- `.trade-footer` - Partner name and status
- `.empty-message` - Message when no trades available

### 6. Added Backend API Endpoint (backend/modules/map/router.py)

#### New Endpoint: GET /api/map/trades
```python
@router.get("/trades")
async def get_trades():
    """Get all trades from map_trade table"""
```

Returns array of trade objects with:
- id, trade_id, trade_type
- title, detail, link
- trade_with_name, trade_with_account, trade_with_company
- pay, pay_method, status
- create_time

### 7. Made Sidebar More Compact
- Reduced padding in `.user-stats-panel` from 12px to 8px
- Reduced margin-bottom from 12px to 8px
- Removed contact list header to save vertical space

## How It Works

1. **Initial Load**: Both contact list and trade list are loaded on init
2. **Tab Switching**: Clicking a tab:
   - Removes `active` class from all tabs and content
   - Adds `active` class to clicked tab and corresponding content
   - Updates `currentTab` property
3. **Display**: Only the active tab content is visible (CSS `display: block`)

## Testing

1. Start the API server:
```bash
python3 api_server.py
```

2. Open the Electron app and navigate to SNS module

3. You should see:
   - Two tabs: "Chat" and "Trade"
   - Chat tab shows contact list (default)
   - Trade tab shows trade list from database

4. Click between tabs to switch views

## Database

Trade data is loaded from the `map_trade` table with columns:
- trade_id, trade_type, title, detail, link
- trade_with_name, trade_with_account, trade_with_company
- pay, pay_method, status
- create_time, is_delete
