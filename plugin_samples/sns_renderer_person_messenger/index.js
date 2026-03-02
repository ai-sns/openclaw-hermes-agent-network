const PersonMessengerPlugin = {
    info: {
        id: 'person-messenger',
        name: 'Person Messenger',
        version: '1.0.0',
        description: 'Send a map chat message to a person'
    },

    _container: null,

    async render(container, api) {
        this._container = container;
        container.innerHTML = `
            <div style="display:flex; flex-direction:column; gap:10px; padding:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-weight:600;">Person Messenger</div>
                    <button class="btn btn-secondary" id="pm_refresh_people" type="button">Refresh</button>
                </div>

                <div class="form-group">
                    <label>People</label>
                    <select class="form-input" id="pm_people_select">
                        <option value="">Loading...</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>Message</label>
                    <textarea class="form-input" id="pm_message" rows="4" placeholder="Type a message..."></textarea>
                </div>

                <div style="display:flex; gap:8px;">
                    <button class="btn btn-primary" id="pm_send" type="button" style="flex:1;">Send</button>
                </div>

                <div style="font-size:12px; color:var(--text-secondary,#666);" id="pm_status"></div>
            </div>
        `;

        const refreshBtn = container.querySelector('#pm_refresh_people');
        const select = container.querySelector('#pm_people_select');
        const msg = container.querySelector('#pm_message');
        const sendBtn = container.querySelector('#pm_send');
        const status = container.querySelector('#pm_status');

        const setStatus = (text) => {
            if (status) status.textContent = text ? String(text) : '';
        };

        const loadPeople = async () => {
            try {
                setStatus('Loading people...');
                if (select) select.innerHTML = '<option value="">Loading...</option>';

                const list = await api.sns.getJson('/api/get_people_list/');
                const people = Array.isArray(list) ? list : [];

                if (!people.length) {
                    if (select) select.innerHTML = '<option value="">No people found</option>';
                    setStatus('No people found.');
                    return;
                }

                if (select) {
                    select.innerHTML = '<option value="">Please select...</option>';
                    for (const p of people) {
                        const account = (p && (p.account || p.user_account)) ? String(p.account || p.user_account) : '';
                        const nick = (p && (p.nick_name || p.nickname)) ? String(p.nick_name || p.nickname) : '';
                        if (!account) continue;
                        const opt = document.createElement('option');
                        opt.value = account;
                        opt.textContent = nick ? `${nick} (${account})` : account;
                        select.appendChild(opt);
                    }
                }

                setStatus('Ready.');
            } catch (e) {
                if (select) select.innerHTML = '<option value="">Failed to load people</option>';
                setStatus(`Load failed: ${e && e.message ? e.message : String(e)}`);
            }
        };

        if (refreshBtn) refreshBtn.addEventListener('click', loadPeople);

        if (sendBtn) {
            sendBtn.addEventListener('click', async () => {
                const toUser = select ? String(select.value || '').trim() : '';
                const content = msg ? String(msg.value || '').trim() : '';

                if (!toUser) {
                    api.ui.toast('error', 'Please select a person.');
                    return;
                }
                if (!content) {
                    api.ui.toast('error', 'Message is empty.');
                    return;
                }

                try {
                    setStatus('Sending...');
                    const ok = api.map.postMessage({
                        type: 'snsPluginCommand',
                        command: 'sendImTo',
                        params: {
                            to_user: toUser,
                            content
                        }
                    });

                    if (ok) {
                        api.ui.toast('success', 'Message sent.');
                        setStatus('Message sent.');
                    } else {
                        api.ui.toast('error', 'Send failed: map iframe not ready.');
                        setStatus('Send failed: map iframe not ready.');
                    }
                } catch (e) {
                    api.ui.toast('error', `Send failed: ${e && e.message ? e.message : String(e)}`);
                    setStatus(`Send failed: ${e && e.message ? e.message : String(e)}`);
                }
            });
        }

        await loadPeople();
    }
};

export default PersonMessengerPlugin;
