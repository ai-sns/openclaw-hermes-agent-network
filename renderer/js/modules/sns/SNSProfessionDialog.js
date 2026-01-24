/**
 * SNS Profession Selection Dialog
 */

export class SNSProfessionDialog {
    constructor() {
        this.dialog = null;
        this.selectedProfession = null;
        this.currentMoney = 0;
    }

    async show() {
        // Load current configuration
        await this.loadCurrentConfig();

        // Create dialog HTML
        const dialogHTML = `
            <div class="modal-overlay" id="snsProfessionDialog">
                <div class="modal-dialog" style="max-width: 600px;">
                    <div class="modal-header">
                        <h3>职业选择</h3>
                        <button class="modal-close" onclick="document.getElementById('snsProfessionDialog').remove()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="profession-config-container">
                            <!-- Current Balance -->
                            <div class="balance-display">
                                <h4>当前资金: <span id="currentBalance">${this.currentMoney.toFixed(2)}</span>元</h4>
                            </div>

                            <!-- Professions with Cost -->
                            <div class="profession-section">
                                <h4>需要开办费的职业</h4>
                                <div class="profession-list" id="professionListCost">
                                    <div class="loading">加载中...</div>
                                </div>
                            </div>

                            <!-- Professions without Cost -->
                            <div class="profession-section">
                                <h4>其他职业选项</h4>
                                <div class="profession-list" id="professionListFree">
                                    <div class="loading">加载中...</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="document.getElementById('snsProfessionDialog').remove()">取消</button>
                        <button class="btn btn-primary" id="saveProfessionBtn">确定</button>
                    </div>
                </div>
            </div>
        `;

        // Add to DOM
        document.body.insertAdjacentHTML('beforeend', dialogHTML);
        this.dialog = document.getElementById('snsProfessionDialog');

        // Load professions
        await this.loadProfessions();

        // Setup event listeners
        this.setupEventListeners();
    }

    async loadCurrentConfig() {
        try {
            const response = await fetch('http://localhost:8788/api/sns/user-stats');
            const stats = await response.json();
            this.currentMoney = stats.money || 0;
        } catch (error) {
            console.error('Error loading current config:', error);
            this.currentMoney = 0;
        }
    }

    async loadProfessions() {
        try {
            const response = await fetch('http://localhost:8788/api/sns/professions');
            const professions = await response.json();

            const costList = document.getElementById('professionListCost');
            const freeList = document.getElementById('professionListFree');

            costList.innerHTML = '';
            freeList.innerHTML = '';

            professions.forEach(profession => {
                const item = document.createElement('div');
                item.className = 'profession-item';
                item.dataset.name = profession.name;
                item.dataset.cost = profession.cost || 0;

                const costText = profession.cost ? `(*需要${profession.cost}元开办费)` : '';
                const disabled = profession.cost && profession.cost > this.currentMoney ? 'disabled' : '';

                item.innerHTML = `
                    <label class="profession-label ${disabled}">
                        <input type="radio" name="profession" value="${profession.name}" ${disabled}>
                        <span>${profession.name} ${costText}</span>
                    </label>
                `;

                if (profession.cost) {
                    costList.appendChild(item);
                } else {
                    freeList.appendChild(item);
                }
            });
        } catch (error) {
            console.error('Error loading professions:', error);
            document.getElementById('professionListCost').innerHTML = '<div class="error">加载失败</div>';
            document.getElementById('professionListFree').innerHTML = '<div class="error">加载失败</div>';
        }
    }

    setupEventListeners() {
        // Save button
        document.getElementById('saveProfessionBtn').addEventListener('click', () => {
            this.saveConfiguration();
        });

        // Radio button change
        document.querySelectorAll('input[name="profession"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.selectedProfession = e.target.value;
            });
        });
    }

    async saveConfiguration() {
        if (!this.selectedProfession) {
            alert('请选择一个职业');
            return;
        }

        try {
            const response = await fetch('http://localhost:8788/api/sns/config', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    profession: this.selectedProfession
                })
            });

            const result = await response.json();
            if (result.success) {
                alert('职业设置成功！');
                this.dialog.remove();
            } else {
                alert('保存失败：' + result.message);
            }
        } catch (error) {
            console.error('Error saving profession:', error);
            alert('保存失败：' + error.message);
        }
    }
}
