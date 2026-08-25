import { apiClient } from '../services/apiClient.js';

export class Integrations {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'integrations-view';
        this.connections = [];
        this.providersMatrix = null;
        this.preferredProvider = 'groq';
        this.selectedOllamaModel = '';
    }

    render() {
        this.element.innerHTML = `
            <!-- HEADER SECTION -->
            <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Integrations & AI Services</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 14px;">
                        Manage local AI (Ollama), Groq platform AI, customer BYO AI keys, and search engine services.
                    </p>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="btn-refresh-integrations" class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                        Refresh Providers
                    </button>
                </div>
            </div>

            <!-- ACTIVE PREFERRED PROVIDER SELECTOR BAR -->
            <div class="card" style="padding: 20px; margin-bottom: 28px; background: var(--bg-card); border-left: 4px solid var(--primary); border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em;">ACTIVE AI SERVICE MANAGER</div>
                        <h2 style="font-size: 17px; font-weight: 700; color: var(--text-primary); margin: 2px 0 4px 0;">Preferred AI Provider Selection</h2>
                        <div style="font-size: 13px; color: var(--text-secondary);">Select which configured AI service executes your SEO analysis prompts.</div>
                    </div>
                    <div id="preferred-provider-pills" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>
                </div>
            </div>

            <!-- SECTION 1: PLATFORM AI (GROQ) -->
            <div style="margin-bottom: 32px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                    <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;">Platform Cloud AI</h2>
                    <span style="font-size: 12px; color: var(--text-tertiary);">Provided by platform</span>
                </div>
                <div id="platform-ai-container"></div>
            </div>

            <!-- SECTION 2: LOCAL AI (OLLAMA) -->
            <div style="margin-bottom: 32px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                    <div>
                        <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 2px 0;">Local AI (Ollama)</h2>
                        <div style="font-size: 13px; color: var(--text-secondary);">Runs 100% locally on your computer. Zero external cloud API calls. No API key required.</div>
                    </div>
                </div>
                <div id="local-ai-container"></div>
            </div>

            <!-- SECTION 3: CUSTOMER AI INTEGRATIONS (BYO KEY) -->
            <div style="margin-bottom: 32px;">
                <div style="margin-bottom: 16px;">
                    <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Bring Your Own AI</h2>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin: 0;">
                        Connect your personal API key to use your own cloud AI account and usage limits.
                    </p>
                </div>

                <!-- FRIENDLY PROVIDER NOTICE BANNER -->
                <div style="background: rgba(59, 130, 246, 0.08); border-left: 4px solid var(--primary); padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
                    <div style="display: flex; gap: 12px; align-items: flex-start;">
                        <div style="font-size: 18px; line-height: 1;">💡</div>
                        <div>
                            <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">Your choice, your AI</div>
                            <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.5;">
                                AI features are available through Groq by default, and you can also use Ollama locally or connect your own OpenAI, Gemini, or Claude API key. Your custom AI connection is completely optional. If you disable or remove it, Groq can automatically become your cloud AI again.<br/>
                                <strong style="color: var(--text-primary);">You're always in control — connecting your own AI is completely optional.</strong>
                            </div>
                        </div>
                    </div>
                </div>

                <div id="customer-ai-container"></div>
            </div>

            <!-- SECTION 4: SEARCH & SOCIAL OAUTH CONNECTIONS -->
            <div style="margin-bottom: 32px;">
                <div style="margin-bottom: 16px;">
                    <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Search & Social Media OAuth Connections</h2>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin: 0;">
                        Connect Google Search Console and business accounts via OAuth 2.0.
                    </p>
                </div>
                <div id="oauth-connections-container"></div>
            </div>

            <div id="integrations-modal-container"></div>
        `;
        return this.element;
    }

    async mounted() {
        await this.loadIntegrations();
        
        const btnRefresh = this.element.querySelector('#btn-refresh-integrations');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => this.loadIntegrations());
        }
    }

    async loadIntegrations() {
        try {
            const [matrix, intData] = await Promise.all([
                apiClient.get('/api/ai/providers').catch(() => null),
                apiClient.get('/api/integrations').catch(() => ({ connections: [] }))
            ]);

            this.providersMatrix = matrix;
            this.connections = (intData && intData.connections) || [];
            
            if (matrix && matrix.active_provider) {
                this.preferredProvider = matrix.active_provider;
            }

            this.renderPreferredPills();
            this.renderPlatformAi();
            this.renderLocalAi();
            this.renderCustomerAi();
            this.renderOAuthConnections();
        } catch (e) {
            console.error('[INTEGRATIONS ERROR]', e);
        }
    }

    renderPreferredPills() {
        const container = this.element.querySelector('#preferred-provider-pills');
        if (!container) return;

        const providers = [
            { id: 'groq', name: 'Groq (Cloud)', available: this.providersMatrix?.providers?.groq?.available },
            { id: 'ollama', name: 'Ollama (Local)', available: this.providersMatrix?.providers?.ollama?.available },
            { id: 'openai', name: 'OpenAI', available: this.providersMatrix?.providers?.openai?.connected },
            { id: 'gemini', name: 'Gemini', available: this.providersMatrix?.providers?.gemini?.connected },
            { id: 'claude', name: 'Claude', available: this.providersMatrix?.providers?.claude?.connected }
        ];

        container.innerHTML = providers.map(p => `
            <button class="pill-btn ${this.preferredProvider === p.id ? 'active' : ''}" 
                    data-provider="${p.id}" 
                    ${!p.available ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}
                    style="padding: 6px 14px; font-size: 13px; font-weight: 600; border-radius: 20px;">
                ${p.name} ${p.available ? '✓' : '(Not Configured)'}
            </button>
        `).join('');

        container.querySelectorAll('.pill-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const prov = e.currentTarget.getAttribute('data-provider');
                if (prov) {
                    this.preferredProvider = prov;
                    this.renderPreferredPills();
                }
            });
        });
    }

    renderPlatformAi() {
        const container = this.element.querySelector('#platform-ai-container');
        if (!container) return;

        const groq = this.providersMatrix?.providers?.groq || { available: false, model: 'openai/gpt-oss-120b', available_models: [] };
        const isAvailable = groq.available;
        const models = groq.available_models || [];
        const currentModel = this.selectedGroqModel || groq.model || (models[0] ? models[0].id : 'openai/gpt-oss-120b');

        container.innerHTML = `
            <div class="card" style="padding: 24px; background: var(--bg-card); border: 1px solid ${isAvailable ? '#10b981' : 'var(--border)'}; border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(16, 185, 129, 0.15); display: flex; align-items: center; justify-content: center; font-weight: 800; color: #10b981; font-size: 20px;">
                            ⚡
                        </div>
                        <div>
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                                <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Groq AI</h3>
                                <span class="badge ${isAvailable ? 'badge-success' : 'badge-danger'}">${isAvailable ? '✓ Connected' : '✕ Connection Failed'}</span>
                                <span style="font-size: 11px; background: var(--bg-subtle); padding: 2px 8px; border-radius: 12px; color: var(--text-secondary);">Platform Default</span>
                            </div>
                            <p style="font-size: 13px; color: var(--text-secondary); margin: 0 0 4px 0;">
                                Groq is provided automatically by the platform. High-speed cloud LLM inference powered by Groq LPU hardware.
                            </p>
                        </div>
                    </div>

                    <div style="display: flex; align-items: center; gap: 10px;">
                        ${isAvailable ? `
                            <button type="button" id="btn-test-groq" class="btn btn-secondary" style="font-size: 13px; display: inline-flex; align-items: center; gap: 6px;">
                                ⚡ Test Connection
                            </button>
                        ` : `
                            <button type="button" class="btn btn-secondary" disabled style="font-size: 13px; opacity: 0.6; cursor: not-allowed;">
                                Configured Server-Side (.env)
                            </button>
                        `}
                    </div>
                </div>

                <!-- MODEL SELECTION ROW -->
                <div style="display: flex; align-items: center; gap: 16px; background: var(--bg-subtle); padding: 12px 16px; border-radius: 8px; flex-wrap: wrap;">
                    <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
                        <span>Detected Model:</span>
                    </div>
                    ${models.length > 0 ? `
                        <select id="select-groq-model" class="form-control" style="font-size: 13px; padding: 6px 12px; width: auto; max-width: 320px; border-radius: 6px;">
                            ${models.map(m => `
                                <option value="${this.escapeHtml(m.id)}" ${m.id === currentModel ? 'selected' : ''}>
                                    ${this.escapeHtml(m.id)} (${this.escapeHtml(m.owned_by || 'Groq')})
                                </option>
                            `).join('')}
                        </select>
                    ` : `
                        <span style="font-size: 13px; font-weight: 700; color: var(--primary); background: rgba(59, 130, 246, 0.1); padding: 4px 10px; border-radius: 6px;">
                            ${this.escapeHtml(currentModel)}
                        </span>
                    `}
                </div>

                <div id="groq-test-status" style="margin-top: 12px; font-size: 13px; display: none;"></div>
            </div>
        `;

        const selectModel = container.querySelector('#select-groq-model');
        if (selectModel) {
            selectModel.addEventListener('change', (e) => {
                this.selectedGroqModel = e.target.value;
            });
        }

        const btnTestGroq = container.querySelector('#btn-test-groq');
        const statusBox = container.querySelector('#groq-test-status');

        if (btnTestGroq) {
            btnTestGroq.addEventListener('click', async () => {
                btnTestGroq.disabled = true;
                btnTestGroq.innerText = 'Testing...';
                if (statusBox) {
                    statusBox.style.display = 'none';
                    statusBox.className = '';
                }

                try {
                    const targetModel = this.selectedGroqModel || currentModel;
                    const res = await apiClient.post('/api/ai/groq/test', { model: targetModel });
                    if (statusBox) {
                        statusBox.style.display = 'block';
                        statusBox.style.padding = '10px 14px';
                        statusBox.style.borderRadius = '6px';
                        statusBox.style.background = 'rgba(16, 185, 129, 0.1)';
                        statusBox.style.border = '1px solid #10b981';
                        statusBox.style.color = '#10b981';
                        statusBox.innerHTML = `✓ <strong>Groq Connected Successfully!</strong> Active Model: <code>${this.escapeHtml(res.model)}</code> &bull; ${this.escapeHtml(res.message || '')}`;
                    }
                } catch (err) {
                    if (statusBox) {
                        statusBox.style.display = 'block';
                        statusBox.style.padding = '10px 14px';
                        statusBox.style.borderRadius = '6px';
                        statusBox.style.background = 'rgba(239, 68, 68, 0.1)';
                        statusBox.style.border = '1px solid #ef4444';
                        statusBox.style.color = '#ef4444';
                        const msg = err.response?.data?.detail?.message || err.message || 'Groq connection failed.';
                        statusBox.innerHTML = `✕ <strong>Groq Connection Error:</strong> ${this.escapeHtml(msg)}`;
                    }
                } finally {
                    btnTestGroq.disabled = false;
                    btnTestGroq.innerText = '⚡ Test Connection';
                }
            });
        }
    }

    renderLocalAi() {
        const container = this.element.querySelector('#local-ai-container');
        if (!container) return;

        const ollama = this.providersMatrix?.providers?.ollama || { available: false };
        const isAvailable = ollama.available;
        const models = ollama.installed_models || [];

        container.innerHTML = `
            <div class="card" style="padding: 24px; background: var(--bg-card); border: 1px solid ${isAvailable ? 'var(--primary)' : 'var(--border)'}; border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 16px;">
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(59, 130, 246, 0.15); display: flex; align-items: center; justify-content: center; font-weight: 800; color: var(--primary); font-size: 20px;">
                            🦙
                        </div>
                        <div>
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                                <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Ollama Local AI</h3>
                                <span class="badge ${isAvailable ? 'badge-success' : 'badge-secondary'}">${isAvailable ? '● Available' : '○ Not Available'}</span>
                                ${isAvailable ? `<span class="badge badge-info" style="font-size: 11px;">${this.escapeHtml(ollama.hardware_badge || 'Suitable for this computer')}</span>` : ''}
                            </div>
                            <p style="font-size: 13px; color: var(--text-secondary); margin: 0 0 4px 0;">
                                Default endpoint: <code>${this.escapeHtml(ollama.base_url || 'http://localhost:11434')}</code> &bull; ${this.escapeHtml(ollama.description || '')}
                            </p>
                            <div style="font-size: 12px; color: var(--text-tertiary);">
                                💡 Hardware recommendation: <strong>1B–4B models recommended</strong> for 8GB RAM / MX110 GPU footprint.
                            </div>
                        </div>
                    </div>

                    <div style="display: flex; gap: 8px;">
                        <button type="button" id="btn-detect-ollama" class="btn btn-secondary" style="font-size: 13px;">
                            Detect Ollama
                        </button>
                        ${isAvailable ? `
                            <button type="button" id="btn-test-ollama" class="btn btn-primary" style="font-size: 13px;">
                                ⚡ Test Ollama
                            </button>
                        ` : ''}
                    </div>
                </div>

                ${isAvailable ? `
                    <div style="background: var(--bg-subtle); padding: 16px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; margin-top: 12px;">
                        <div>
                            <label style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">Selected Local Model</label>
                            <select id="select-ollama-model" style="padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); color: var(--text-primary); min-width: 240px; cursor: pointer;">
                                ${models.length > 0 ? models.map(m => `
                                    <option value="${this.escapeHtml(m.name)}" ${m.name === ollama.selected_model ? 'selected' : ''}>
                                        ${this.escapeHtml(m.name)} (${m.size_mb} MB) ${m.recommended ? '★ Suitable' : '⚠️ Large'}
                                    </option>
                                `).join('') : `<option value="${this.escapeHtml(ollama.selected_model)}">${this.escapeHtml(ollama.selected_model)} (Default)</option>`}
                            </select>
                        </div>
                        <div style="font-size: 12.5px; color: var(--text-secondary); max-width: 400px;">
                            ${ollama.hardware_detail ? `<span>ℹ️ ${this.escapeHtml(ollama.hardware_detail)}</span>` : ''}
                        </div>
                    </div>
                ` : `
                    <div style="background: rgba(245, 158, 11, 0.08); border-left: 4px solid #f59e0b; padding: 14px 16px; border-radius: 6px; font-size: 13px; color: var(--text-secondary); margin-top: 12px;">
                        <strong style="color: var(--text-primary);">Ollama isn't running on this device.</strong><br/>
                        Install and start Ollama to use local AI. Your SEO crawling and auditing will continue to work normally without it.
                        <a href="https://ollama.com" target="_blank" rel="noopener" style="color: var(--primary); text-decoration: underline; margin-left: 8px; font-weight: 600;">Download Ollama &rarr;</a>
                    </div>
                `}
            </div>
        `;

        const btnDetect = container.querySelector('#btn-detect-ollama');
        if (btnDetect) {
            btnDetect.addEventListener('click', async () => {
                btnDetect.disabled = true;
                btnDetect.innerText = 'Detecting...';
                await this.loadIntegrations();
            });
        }

        const btnTest = container.querySelector('#btn-test-ollama');
        if (btnTest) {
            btnTest.addEventListener('click', async () => {
                btnTest.disabled = true;
                btnTest.innerText = 'Testing...';
                try {
                    const modelSel = container.querySelector('#select-ollama-model')?.value || '';
                    const res = await apiClient.post('/api/ai/ollama/test', { model: modelSel });
                    alert(res.status === 'connected' ? `✓ Ollama Local AI Connected!\nModel: ${res.model}\nHardware Rating: ${res.hardware_fit} (${res.hardware_badge})\nMessage: ${res.message}` : `✕ Ollama Error: ${res.message}`);
                } catch (err) {
                    alert(`✕ Error testing Ollama: ${err.message}`);
                } finally {
                    btnTest.disabled = false;
                    btnTest.innerText = '⚡ Test Ollama';
                }
            });
        }
    }

    renderCustomerAi() {
        const container = this.element.querySelector('#customer-ai-container');
        if (!container) return;

        const providers = [
            { provider: 'openai', name: 'OpenAI / ChatGPT', model_info: 'GPT-4o & Mini models', privacy: 'Sent to OpenAI using your API key.' },
            { provider: 'gemini', name: 'Google Gemini', model_info: 'Gemini Flash & Pro models', privacy: 'Sent to Google Gemini using your API key.' },
            { provider: 'claude', name: 'Anthropic Claude', model_info: 'Claude 3.5 Sonnet', privacy: 'Sent to Anthropic Claude using your API key.' }
        ];

        const cards = providers.map(p => {
            const statusObj = this.providersMatrix?.providers?.[p.provider] || {};
            return {
                ...p,
                connected: statusObj.connected || false,
                enabled: statusObj.enabled || false,
                masked_key: statusObj.masked_key || ''
            };
        });

        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px;">
                ${cards.map(c => this.renderCustomerCardHtml(c)).join('')}
            </div>
        `;

        this.bindCustomerEvents(container);
    }

    renderCustomerCardHtml(c) {
        const isConnected = c.connected;
        const isEnabled = c.enabled;
        const initial = c.name.charAt(0);

        return `
            <div class="card provider-card" style="padding: 24px; background: var(--bg-card); border: 1px solid ${isConnected ? (isEnabled ? 'var(--primary)' : '#f59e0b') : 'var(--border)'}; border-radius: 12px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--bg-subtle); display: flex; align-items: center; justify-content: center; font-weight: 800; color: var(--primary); font-size: 18px;">
                                ${initial}
                            </div>
                            <div>
                                <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 2px 0; color: var(--text-primary);">${this.escapeHtml(c.name)}</h3>
                                <span style="font-size: 11.5px; color: var(--text-tertiary);">${this.escapeHtml(c.model_info)}</span>
                            </div>
                        </div>
                        <span class="badge ${isConnected ? (isEnabled ? 'badge-success' : 'badge-warning') : 'badge-secondary'}">
                            ${isConnected ? (isEnabled ? 'Connected' : 'Disabled') : 'Not Connected'}
                        </span>
                    </div>

                    ${isConnected ? `
                        <div style="background: var(--bg-subtle); padding: 8px 12px; border-radius: 6px; font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; font-family: monospace; display: flex; justify-content: space-between; align-items: center;">
                            <span>Key: ${this.escapeHtml(c.masked_key)}</span>
                            <span style="font-size: 11px; color: var(--text-tertiary); font-family: sans-serif;">Customer API</span>
                        </div>
                    ` : `
                        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;">
                            Connect your personal API key to use your custom account and usage limits.
                        </p>
                    `}

                    <div style="font-size: 11.5px; color: var(--text-tertiary); margin-bottom: 16px;">
                        <em>${this.escapeHtml(c.privacy)}</em>
                    </div>
                </div>

                <div style="border-top: 1px solid var(--border); padding-top: 14px; display: flex; gap: 8px; flex-wrap: wrap;">
                    ${isConnected ? `
                        <button type="button" class="btn btn-secondary btn-sm btn-test-customer-key" data-provider="${c.provider}" style="flex: 1; font-size: 12px;">
                            Test
                        </button>
                        <button type="button" class="btn btn-secondary btn-sm btn-toggle-customer-key" data-provider="${c.provider}" style="flex: 1; font-size: 12px;">
                            ${isEnabled ? 'Disable' : 'Enable'}
                        </button>
                        <button type="button" class="btn btn-danger btn-sm btn-remove-customer-key" data-provider="${c.provider}" style="font-size: 12px;">
                            Remove
                        </button>
                    ` : `
                        <button type="button" class="btn btn-primary btn-add-customer-key" data-provider="${c.provider}" data-name="${this.escapeHtml(c.name)}" style="width: 100%; padding: 8px; font-size: 13px;">
                            + Add API Key
                        </button>
                    `}
                </div>
            </div>
        `;
    }

    renderOAuthConnections() {
        const container = this.element.querySelector('#oauth-connections-container');
        if (!container) return;

        const oauthProviders = [
            { id: 'google', name: 'Google Search Console & Business Profile', desc: 'Fetch verified search traffic, query impressions, and location data via Google OAuth 2.0.' }
        ];

        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px;">
                ${oauthProviders.map(p => {
                    const conn = this.connections.find(c => c.provider === p.id);
                    const isConnected = conn && conn.status === 'CONNECTED';
                    return `
                        <div class="card" style="padding: 24px; background: var(--bg-card); border: 1px solid ${isConnected ? 'var(--primary)' : 'var(--border)'}; border-radius: 12px; display: flex; flex-direction: column; justify-content: space-between;">
                            <div>
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">${p.name}</h3>
                                    <span class="badge ${isConnected ? 'badge-success' : 'badge-secondary'}">${isConnected ? '✓ Connected' : 'Not Connected'}</span>
                                </div>
                                <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 16px;">
                                    ${p.desc}
                                </p>
                            </div>
                            <div style="border-top: 1px solid var(--border); padding-top: 14px;">
                                ${isConnected ? `
                                    <button class="btn btn-secondary btn-disconnect-oauth" data-provider="${p.id}" style="width: 100%; font-size: 13px;">
                                        Disconnect Account
                                    </button>
                                ` : `
                                    <button class="btn btn-primary btn-connect-oauth" data-provider="${p.id}" style="width: 100%; font-size: 13px;">
                                        Connect Google Account
                                    </button>
                                `}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;

        this.bindOAuthEvents(container);
    }

    bindCustomerEvents(container) {
        container.querySelectorAll('.btn-add-customer-key').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const provider = e.currentTarget.getAttribute('data-provider');
                const name = e.currentTarget.getAttribute('data-name');
                this.openAddKeyModal(provider, name);
            });
        });

        container.querySelectorAll('.btn-test-customer-key').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const provider = e.currentTarget.getAttribute('data-provider');
                btn.disabled = true;
                btn.innerText = 'Testing...';
                try {
                    const res = await apiClient.post(`/api/integrations/${provider}/test`, {});
                    alert(`✓ ${provider.toUpperCase()} API key test successful!\nMessage: ${res.result ? res.result.message : 'Connected'}`);
                } catch (err) {
                    alert(`✕ Error testing ${provider} API key: ${err.message}`);
                } finally {
                    btn.disabled = false;
                    btn.innerText = 'Test';
                }
            });
        });

        container.querySelectorAll('.btn-toggle-customer-key').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const provider = e.currentTarget.getAttribute('data-provider');
                btn.disabled = true;
                try {
                    await apiClient.post(`/api/integrations/${provider}/toggle`, {});
                    await this.loadIntegrations();
                } catch (err) {
                    alert(`✕ Error toggling ${provider}: ${err.message}`);
                    btn.disabled = false;
                }
            });
        });

        container.querySelectorAll('.btn-remove-customer-key').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const provider = e.currentTarget.getAttribute('data-provider');
                if (!confirm(`Are you sure you want to remove your ${provider.toUpperCase()} API key? Groq platform AI will automatically resume.`)) return;
                btn.disabled = true;
                try {
                    await apiClient.post(`/api/integrations/${provider}/disconnect`, {});
                    await this.loadIntegrations();
                } catch (err) {
                    alert(`✕ Error removing key: ${err.message}`);
                    btn.disabled = false;
                }
            });
        });
    }

    bindOAuthEvents(container) {
        container.querySelectorAll('.btn-connect-oauth').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const provider = e.currentTarget.getAttribute('data-provider');
                try {
                    const res = await apiClient.get(`/api/integrations/${provider}/connect`);
                    if (res && res.authorization_url) {
                        window.location.href = res.authorization_url;
                    }
                } catch (err) {
                    alert(`✕ Could not start OAuth login: ${err.message}`);
                }
            });
        });

        container.querySelectorAll('.btn-disconnect-oauth').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const provider = e.currentTarget.getAttribute('data-provider');
                if (!confirm(`Disconnect ${provider.toUpperCase()} account?`)) return;
                try {
                    await apiClient.post(`/api/integrations/${provider}/disconnect`, {});
                    await this.loadIntegrations();
                } catch (err) {
                    alert(`✕ Disconnect error: ${err.message}`);
                }
            });
        });
    }

    openAddKeyModal(provider, name) {
        const container = this.element.querySelector('#integrations-modal-container');
        if (!container) return;

        container.innerHTML = `
            <div class="modal-overlay" style="position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6); display: flex; align-items: center; justify-content: center; z-index: 9999; padding: 20px;">
                <div class="card" style="width: 100%; max-width: 480px; padding: 28px; background: var(--bg-card); border-radius: 12px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text-primary);">Connect ${this.escapeHtml(name)}</h3>
                        <button id="btn-modal-close" style="background: none; border: none; font-size: 20px; color: var(--text-tertiary); cursor: pointer;">&times;</button>
                    </div>

                    <form id="form-customer-key">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Provider</label>
                            <input type="text" value="${this.escapeHtml(name)}" readonly style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-subtle); color: var(--text-secondary); font-size: 13.5px;" />
                        </div>

                        <div style="margin-bottom: 20px;">
                            <label style="display: block; font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">API Key</label>
                            <input type="password" id="input-api-key" placeholder="Enter your ${this.escapeHtml(name)} API key" required style="width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-subtle); color: var(--text-primary); font-size: 13.5px;" />
                            <div style="font-size: 11.5px; color: var(--text-tertiary); margin-top: 4px;">
                                Your key is encrypted at rest and never shown again in plaintext.
                            </div>
                        </div>

                        <div id="modal-error-msg" style="display: none; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 10px 12px; border-radius: 6px; font-size: 12.5px; margin-bottom: 16px;"></div>

                        <div style="display: flex; justify-content: flex-end; gap: 10px;">
                            <button type="button" id="btn-modal-cancel" class="btn btn-secondary" style="padding: 8px 16px; font-size: 13px;">Cancel</button>
                            <button type="submit" id="btn-modal-submit" class="btn btn-primary" style="padding: 8px 16px; font-size: 13px;">Test & Save Key</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        const closeModal = () => { container.innerHTML = ''; };

        container.querySelector('#btn-modal-close').addEventListener('click', closeModal);
        container.querySelector('#btn-modal-cancel').addEventListener('click', closeModal);

        const form = container.querySelector('#form-customer-key');
        const inputKey = container.querySelector('#input-api-key');
        const btnSubmit = container.querySelector('#btn-modal-submit');
        const errorDiv = container.querySelector('#modal-error-msg');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const rawKey = (inputKey.value || '').trim();
            if (!rawKey) return;

            btnSubmit.disabled = true;
            btnSubmit.innerText = 'Verifying with Provider...';
            errorDiv.style.display = 'none';

            try {
                await apiClient.post(`/api/integrations/${provider}/key`, { api_key: rawKey });
                closeModal();
                await this.loadIntegrations();
            } catch (err) {
                errorDiv.style.display = 'block';
                errorDiv.innerText = `Unable to connect. ${err.message || 'The API key could not be verified.'}`;
                btnSubmit.disabled = false;
                btnSubmit.innerText = 'Test & Save Key';
            }
        });
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}
