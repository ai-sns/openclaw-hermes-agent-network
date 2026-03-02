# SNS Renderer Plugin Development Guide

This guide explains how to build and import **renderer (UI) plugins** for the SNS module. Renderer plugins are loaded dynamically into the SNS right status panel as new tabs.

## 1. Quick Start (Zip Import)

- Create a plugin folder with:
  - `plugin.json`
  - your entry module (e.g. `index.js`)
- Zip the folder contents.
- In the SNS page, click:
  - `Plugin` (bottom action bar)
  - `Import zip`
  - Choose the `.zip`
  - Select the imported plugin and click `Load`

The backend will extract files into:

- `uploads/plugins/<plugin_id>/...`

## 2. plugin.json Manifest

A renderer plugin zip must include a `plugin.json` file.

Example:

```json
{
  "id": "person-messenger",
  "name": "Person Messenger",
  "version": "1.0.0",
  "description": "Send a map chat message to a person.",
  "entry": "index.js"
}
```

Fields:

- **id**
  - Optional but recommended.
  - Used as `alias_name` in DB.
- **name**
  - Required.
  - Used as the tab title.
- **version**
  - Optional, default `1.0.0`.
- **description**
  - Optional.
- **entry**
  - Required.
  - Relative path to the plugin entry module.
  - Must not contain `..` and must not be an absolute path.

## 3. Entry Module Contract

Your entry module must export a default object with:

- `info: { id, name, version, description }`
- `render(container, api)`
- optional: `dispose()`

Example:

```js
const MyPlugin = {
  info: {
    id: 'my-plugin',
    name: 'My Plugin',
    version: '1.0.0',
    description: 'My first SNS plugin'
  },

  async render(container, api) {
    container.innerHTML = '<div>Hello from plugin</div>';
  },

  dispose() {
    // Optional cleanup
  }
};

export default MyPlugin;
```

## 4. Plugin API (Host-Provided)

The SNS host passes an `api` object to `render(container, api)`.

### 4.1 api.ui

- `api.ui.toast(type, message)`
  - type: `info|success|warning|error`
- `api.ui.openUrl(url)`

### 4.2 api.sns

- `api.sns.getJson(path)`
- `api.sns.postJson(path, body)`
- `api.sns.jsonrpc(method, params)`
  - Calls backend `/jsonrpc`.

### 4.3 api.map

- `api.map.postMessage(payload)`
  - Sends a `postMessage` to the map iframe.

The map iframe supports a minimal command channel for SNS renderer plugins:

- `type: 'snsPluginCommand'`

Currently supported commands:

- `sendImTo`
  - Sends a map chat message using the current map user's account as `from_user`.

Example:

```js
api.map.postMessage({
  type: 'snsPluginCommand',
  command: 'sendImTo',
  params: {
    to_user: 'target_account',
    content: 'Hello'
  }
});
```

## 5. Notes & Limitations

- Renderer plugins run in the Electron renderer context.
- Do not assume Node APIs are available.
- Keep UI text/logs in English.
- Keep resource usage small; release timers/listeners in `dispose()`.
