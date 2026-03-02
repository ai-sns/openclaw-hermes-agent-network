const AgentJsonRpcTester = {
  info: {
    id: 'agent-jsonrpc-tester',
    name: 'Agent JSON-RPC Tester',
    version: '1.0.0',
    description: 'Call backend /jsonrpc from the Agent UI and inspect the response.'
  },

  async render(container, api) {
    const root = document.createElement('div');
    root.style.padding = '12px';
    root.style.display = 'flex';
    root.style.flexDirection = 'column';
    root.style.gap = '10px';

    const title = document.createElement('div');
    title.textContent = 'JSON-RPC Tester';
    title.style.fontWeight = '600';

    const form = document.createElement('div');
    form.style.display = 'flex';
    form.style.flexDirection = 'column';
    form.style.gap = '8px';

    const methodLabel = document.createElement('div');
    methodLabel.textContent = 'Method';
    methodLabel.style.fontSize = '12px';

    const methodInput = document.createElement('input');
    methodInput.type = 'text';
    methodInput.className = 'form-input';
    methodInput.value = 'ping';

    const paramsLabel = document.createElement('div');
    paramsLabel.textContent = 'Params (JSON)';
    paramsLabel.style.fontSize = '12px';

    const paramsInput = document.createElement('textarea');
    paramsInput.className = 'form-input';
    paramsInput.style.minHeight = '90px';
    paramsInput.value = '{\n  "message": "hello"\n}';

    const row = document.createElement('div');
    row.style.display = 'flex';
    row.style.gap = '8px';
    row.style.flexWrap = 'wrap';

    const runBtn = document.createElement('button');
    runBtn.type = 'button';
    runBtn.className = 'btn btn-secondary';
    runBtn.textContent = 'Call JSON-RPC';

    const openDocsBtn = document.createElement('button');
    openDocsBtn.type = 'button';
    openDocsBtn.className = 'btn btn-secondary';
    openDocsBtn.textContent = 'Open docs';

    row.appendChild(runBtn);
    row.appendChild(openDocsBtn);

    const output = document.createElement('pre');
    output.style.whiteSpace = 'pre-wrap';
    output.style.fontSize = '11px';
    output.style.padding = '10px';
    output.style.borderRadius = '6px';
    output.style.background = 'rgba(0,0,0,0.25)';
    output.textContent = 'Ready.';

    form.appendChild(methodLabel);
    form.appendChild(methodInput);
    form.appendChild(paramsLabel);
    form.appendChild(paramsInput);
    form.appendChild(row);

    root.appendChild(title);
    root.appendChild(form);
    root.appendChild(output);

    container.innerHTML = '';
    container.appendChild(root);

    const safeParse = (text) => {
      const raw = String(text || '').trim();
      if (!raw) return {};
      try {
        return JSON.parse(raw);
      } catch (e) {
        throw new Error('Params must be valid JSON');
      }
    };

    const callRpc = async () => {
      if (!api || !api.sns || typeof api.sns.jsonrpc !== 'function') {
        output.textContent = 'Host API not available: api.sns.jsonrpc';
        return;
      }

      const method = String(methodInput.value || '').trim();
      if (!method) {
        output.textContent = 'Method is required.';
        return;
      }

      let params;
      try {
        params = safeParse(paramsInput.value);
      } catch (e) {
        output.textContent = e && e.message ? e.message : String(e);
        return;
      }

      output.textContent = 'Calling...';
      try {
        const resp = await api.sns.jsonrpc(method, params);
        output.textContent = JSON.stringify(resp, null, 2);
        if (api.ui && typeof api.ui.toast === 'function') {
          api.ui.toast('success', 'JSON-RPC call finished');
        }
      } catch (e) {
        output.textContent = e && e.message ? e.message : String(e);
        if (api.ui && typeof api.ui.toast === 'function') {
          api.ui.toast('error', 'JSON-RPC call failed');
        }
      }
    };

    runBtn.addEventListener('click', callRpc);
    openDocsBtn.addEventListener('click', () => {
      if (api && api.ui && typeof api.ui.openUrl === 'function') {
        api.ui.openUrl('https://www.jsonrpc.org/specification');
      }
    });

    this._dispose = () => {
      try {
        runBtn.replaceWith(runBtn.cloneNode(true));
        openDocsBtn.replaceWith(openDocsBtn.cloneNode(true));
      } catch (e) {
      }
    };
  },

  dispose() {
    try {
      if (typeof this._dispose === 'function') this._dispose();
    } catch (e) {
    }
    this._dispose = null;
  }
};

export default AgentJsonRpcTester;
