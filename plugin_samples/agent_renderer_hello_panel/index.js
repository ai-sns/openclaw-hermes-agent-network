const AgentHelloPanel = {
  info: {
    id: 'agent-hello-panel',
    name: 'Agent Hello Panel',
    version: '1.0.0',
    description: 'A minimal Agent renderer plugin example with a counter and toast messages.'
  },

  async render(container, api) {
    const root = document.createElement('div');
    root.style.padding = '12px';
    root.style.display = 'flex';
    root.style.flexDirection = 'column';
    root.style.gap = '10px';

    const title = document.createElement('div');
    title.textContent = 'Hello from Agent plugin';
    title.style.fontWeight = '600';

    const note = document.createElement('div');
    note.textContent = 'This plugin runs inside the Agent settings panel.';
    note.style.fontSize = '12px';
    note.style.opacity = '0.85';

    const counterRow = document.createElement('div');
    counterRow.style.display = 'flex';
    counterRow.style.alignItems = 'center';
    counterRow.style.gap = '8px';

    const counterLabel = document.createElement('span');
    counterLabel.style.fontSize = '12px';

    const incBtn = document.createElement('button');
    incBtn.type = 'button';
    incBtn.className = 'btn btn-secondary';
    incBtn.textContent = 'Increment';

    const toastBtn = document.createElement('button');
    toastBtn.type = 'button';
    toastBtn.className = 'btn btn-secondary';
    toastBtn.textContent = 'Toast';

    counterRow.appendChild(counterLabel);
    counterRow.appendChild(incBtn);
    counterRow.appendChild(toastBtn);

    root.appendChild(title);
    root.appendChild(note);
    root.appendChild(counterRow);

    container.innerHTML = '';
    container.appendChild(root);

    let count = 0;
    const renderCount = () => {
      counterLabel.textContent = `Counter: ${count}`;
    };

    renderCount();

    incBtn.addEventListener('click', () => {
      count += 1;
      renderCount();
      if (api && api.ui && typeof api.ui.toast === 'function') {
        api.ui.toast('success', `Counter is now ${count}`);
      }
    });

    toastBtn.addEventListener('click', () => {
      if (api && api.ui && typeof api.ui.toast === 'function') {
        api.ui.toast('info', 'Hello from AgentHelloPanel');
      }
    });

    this._dispose = () => {
      try {
        incBtn.replaceWith(incBtn.cloneNode(true));
        toastBtn.replaceWith(toastBtn.cloneNode(true));
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

export default AgentHelloPanel;
