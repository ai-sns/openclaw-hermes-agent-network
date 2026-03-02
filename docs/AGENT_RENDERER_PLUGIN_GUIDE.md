# Agent Renderer Plugin Development Guide

This guide explains how to build and import **renderer (UI) plugins** for the Agent module. Agent renderer plugins are loaded dynamically into the Agent settings panel as new tabs.

## 1. Quick Start (Zip Import)

- Create a plugin folder with:
  - `plugin.json`
  - your entry module (e.g. `index.js`)
- Zip the folder contents.
- In the Agent page, click:
  - the `Add` button in the input toolbar
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
  "id": "agent-hello-panel",
  "name": "Agent Hello Panel",
  "version": "1.0.0",
  "description": "A minimal Agent renderer plugin example.",
  "entry": "index.js"
}
```

Fields:

- **id**
  - Optional but recommended.
  - Stored as `alias_name` in DB.
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
    description: 'My first Agent plugin'
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

The Agent host passes an `api` object to `render(container, api)`.

### 4.1 api.ui

- `api.ui.toast(type, message)`
  - type: `info|success|warning|error`
- `api.ui.openUrl(url)`

### 4.2 api.sns

This naming is historical. In the Agent module it still points to the same backend API base:

- `api.sns.getJson(path)`
- `api.sns.postJson(path, body)`
- `api.sns.jsonrpc(method, params)`
  - Calls backend `/jsonrpc`.

## 5. Notes & Limitations

- Renderer plugins run in the Electron renderer context.
- Do not assume Node APIs are available.
- Keep UI text/logs in English.
- Keep resource usage small; release timers/listeners in `dispose()`.

## 6. Sample Plugins

Two sample Agent renderer plugins are provided under `plugin_samples/`:

- `plugin_samples/agent_renderer_hello_panel`
- `plugin_samples/agent_renderer_jsonrpc_tester`

To import a sample plugin:

1. Zip the folder contents (must include `plugin.json` at the root of the zip or within the shortest path inside it).
2. Import it using the Agent Plugins dialog.
