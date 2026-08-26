import { apiClient } from '../services/apiClient.js';
import { authStore } from '../core/authStore.js';

export class Integrations {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'integrations-view';
        this.connections = [];
        this.providersMatrix = null;
        this.preferredProvider = 'groq';
        this.oauthStatusMessage = null;
        this.oauthStatusType = null;
    }

    render() {
        this.element.innerHTML = `
            <!-- HEADER SECTION -->
            <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Integrations & External Services</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">
                        Connect Google Search Console, Google Business Profile, local AI (Ollama), and optional cloud AI providers to your workspace.
                    </p>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="btn-refresh-integrations" class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                        Refresh Integration Status
                    </button>
                </div>
            </div>

            <!-- OAUTH RETURN CONFIRMATION BANNER CONTAINER -->
            <div id="oauth-return-banner-container"></div>

            <!-- SECTION 1: GOOGLE ACCOUNT OAUTH INTEGRATION -->
            <div style="margin-bottom: 32px;">
                <div style="margin-bottom: 16px;">
                    <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Google Services Integration</h2>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin: 0;">
                        Connect your official Google account to fetch Search Console performance and Business Profile data.
                    </p>
                </div>
                <div id="google-integration-card-container"></div>
            </div>

            <!-- SECTION 2: AI PROVIDER SELECTION & MANAGER -->
            <div class="card" style="padding: 20px; margin-bottom: 28px; background: var(--bg-card); border-left: 4px solid var(--primary); border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em;">ACTIVE AI SERVICE MANAGER</div>
                        <h2 style="font-size: 17px; font-weight: 700; color: var(--text-primary); margin: 2px 0 4px 0;">Preferred AI Engine Selection</h2>
                        <div style="font-size: 13px; color: var(--text-secondary);">Select which configured AI service executes your automated SEO analysis.</div>
                    </div>
                    <div id="preferred-provider-pills" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>
                </div>
            </div>

            <!-- SECTION 3: PLATFORM & LOCAL AI -->
            <div style="margin-bottom: 32px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                    <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;">Platform Cloud & Local AI</h2>
                    <span style="font-size: 12px; color: var(--text-tertiary);">Zero setup required</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
                    <div id="platform-ai-container"></div>
                    <div id="local-ai-container"></div>
                </div>
            </div>

            <!-- SECTION 4: BRING YOUR OWN AI (BYO KEYS) -->
            <div style="margin-bottom: 32px;">
                <div style="margin-bottom: 16px;">
                    <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Bring Your Own AI (Optional)</h2>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin: 0;">
                        Connecting personal OpenAI, Anthropic (Claude), or Gemini API keys is completely optional.
                    </p>
                </div>
                <div id="customer-ai-container"></div>
            </div>

            <div id="integrations-modal-container"></div>
        `;
        return this.element;
    }

    async mounted() {
        this.checkOAuthUrlStatus();
        await this.loadIntegrations();
        
        const btnRefresh = this.element.querySelector('#btn-refresh-integrations');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => this.loadIntegrations());
        }
    }

    checkOAuthUrlStatus() {
        const urlParams = new URLSearchParams(window.location.search);
        const googleStatus = urlParams.get('google');
        const errParam = urlParams.get('error');

        if (googleStatus === 'connected' || urlParams.get('code')) {
            this.oauthStatusType = 'success';
            this.oauthStatusMessage = 'Google Account Connected — Your Google account was successfully connected. You can now use supported Google services.';
        } else if (googleStatus === 'failed' || errParam) {
            this.oauthStatusType = 'error';
            this.oauthStatusMessage = 'Google Connection Failed — We couldn\'t complete the Google connection. Your SEO account is still active. You can try connecting Google again.';
        }

        if (this.oauthStatusMessage) {
            const container = this.element.querySelector('#oauth-return-banner-container');
            if (container) {
                container.innerHTML = `
                    <div class="card" style="padding: 16px 20px; margin-bottom: 24px; background: ${this.oauthStatusType === 'success' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)'}; border: 1px solid ${this.oauthStatusType === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}; border-radius: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="font-size: 20px;">${this.oauthStatusType === 'success' ? '✓' : '✕'}</div>
                            <div>
                                <div style="font-size: 14px; font-weight: 700; color: ${this.oauthStatusType === 'success' ? '#10b981' : '#ef4444'};">${this.oauthStatusType === 'success' ? 'Google Account Connected' : 'Google Connection Failed'}</div>
                                <div style="font-size: 13px; color: var(--text-secondary);">${this.oauthStatusMessage}</div>
                            </div>
                        </div>
                        <button class="btn btn-secondary btn-sm" onclick="this.parentElement.style.display='none'">Dismiss</button>
                    </div>
                `;
            }
            // Clean URL query params without reloading
            const cleanUrl = window.location.pathname;
            window.history.replaceState({}, document.title, cleanUrl);
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

            this.renderGoogleCard();
            this.renderPreferredPills();
            this.renderPlatformAi();
            this.renderLocalAi();
            this.renderCustomerAi();
        } catch (e) {
            console.error('[INTEGRATIONS] Load error:', e);
        }
    }

    renderGoogleCard() {
        const container = this.element.querySelector('#google-integration-card-container');
        if (!container) return;

        const googleConn = this.connections.find(c => c.provider === 'google');
        const isConnected = !!(googleConn && googleConn.is_active);
        const accountEmail = googleConn ? (googleConn.account_identifier || (authStore.user ? authStore.user.email : 'Google Account')) : null;

        container.innerHTML = `
            <div class="card" style="padding: 28px; background: var(--bg-card); border-left: 4px solid ${isConnected ? '#10b981' : 'var(--primary)'}; border-radius: 14px; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);">
                
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(66, 133, 244, 0.08); display: flex; align-items: center; justify-content: center;">
                            <svg width="24" height="24" viewBox="0 0 24 24">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.62z"/>
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                            </svg>
                        </div>
                        <div>
                            <h3 style="font-size: 18px; font-weight: 700; margin: 0 0 2px 0; color: var(--text-primary);">Google Account</h3>
                            ${isConnected ? `<span style="font-size: 13px; color: var(--text-secondary); font-family: monospace;">${this.escapeHtml(accountEmail)}</span>` : '<span style="font-size: 13px; color: var(--text-secondary);">External Google Identity & APIs</span>'}
                        </div>
                    </div>

                    <span class="badge ${isConnected ? 'badge-success' : 'badge-secondary'}" style="font-size: 12px; padding: 5px 12px;">
                        ${isConnected ? 'Connected' : 'Not Connected'}
                    </span>
                </div>

                <p style="font-size: 14px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 20px;">
                    Connect your Google account to enable supported Google services and SEO data integrations. You can connect or disconnect your Google account at any time.
                </p>

                <!-- SUPPORTED CAPABILITIES GRID -->
                <div style="background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 20px;">
                    <div style="font-size: 11.5px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px;">SUPPORTED GOOGLE SERVICES</div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                        <div style="display: flex; align-items: center; gap: 8px; font-size: 13.5px; font-weight: 600; color: var(--text-primary);">
                            <span style="color: #10b981; font-weight: 800;">✓</span>
                            <span>Google Search Console</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px; font-size: 13.5px; font-weight: 600; color: var(--text-primary);">
                            <span style="color: #10b981; font-weight: 800;">✓</span>
                            <span>Google Business Profile</span>
                        </div>
                    </div>
                </div>

                <!-- ACTION BUTTONS -->
                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    ${isConnected ? `
                        <button id="btn-google-disconnect" class="btn btn-secondary" style="color: var(--critical);">
                            Disconnect Google
                        </button>
                    ` : `
                        <button id="btn-google-connect" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700;">
                            Connect Google
                        </button>
                    `}
                </div>

                <div id="google-oauth-status-text" style="display: none; margin-top: 12px; font-size: 13px; color: var(--primary); text-align: right;"></div>
            </div>
        `;

        const btnConnect = container.querySelector('#btn-google-connect');
        const btnDisconnect = container.querySelector('#btn-google-disconnect');
        const statusText = container.querySelector('#google-oauth-status-text');

        if (btnConnect) {
            btnConnect.addEventListener('click', async () => {
                btnConnect.disabled = true;
                if (statusText) {
                    statusText.style.display = 'block';
                    statusText.innerText = "Connecting Google... Opening Google's secure authorization page...";
                }
                try {
                    const authUrl = await authStore.getGoogleOAuthLoginUrl();
                    window.location.href = authUrl;
                } catch (err) {
                    btnConnect.disabled = false;
                    if (statusText) {
                        statusText.style.color = '#ef4444';
                        statusText.innerText = "Google Connection Failed. Please try again.";
                    }
                }
            });
        }

        if (btnDisconnect) {
            btnDisconnect.addEventListener('click', async () => {
                if (!confirm('Disconnect your Google account from this workspace?')) return;
                btnDisconnect.disabled = true;
                try {
                    await apiClient.post('/api/integrations/google/disconnect', {});
                    await this.loadIntegrations();
                } catch (err) {
                    btnDisconnect.disabled = false;
                    alert('Disconnect failed: ' + err.message);
                }
            });
        }
    }

    renderPreferredPills() {
        const container = this.element.querySelector('#preferred-provider-pills');
        if (!container || !this.providersMatrix) return;

        const available = this.providersMatrix.providers || [];
        container.innerHTML = available.map(p => {
            const isSelected = p.id === this.preferredProvider;
            return `
                <button class="btn btn-sm ${isSelected ? 'btn-primary' : 'btn-secondary'} btn-set-preferred" data-provider="${p.id}" ${!p.available ? 'disabled' : ''}>
                    ${isSelected ? '★ ' : ''}${p.name}
                    ${!p.available ? ' (Offline)' : ''}
                </button>
            `;
        }).join('');

        container.querySelectorAll('.btn-set-preferred').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const provider = e.currentTarget.getAttribute('data-provider');
                try {
                    await apiClient.post('/api/ai/set-provider', { provider });
                    this.preferredProvider = provider;
                    await this.loadIntegrations();
                } catch (err) {
                    alert('Failed to set active AI provider: ' + err.message);
                }
            });
        });
    }

    renderPlatformAi() {
        const container = this.element.querySelector('#platform-ai-container');
        if (!container) return;
        container.innerHTML = `
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Groq Cloud AI</h3>
                    <span class="badge badge-success">Connected</span>
                </div>
                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
                    Provided out of the box by the SEO Intelligence platform.
                </p>
                <div style="font-size: 12px; color: var(--text-tertiary);">Status: Active</div>
            </div>
        `;
    }

    renderLocalAi() {
        const container = this.element.querySelector('#local-ai-container');
        if (!container) return;
        const ollamaActive = this.providersMatrix && this.providersMatrix.providers ? (this.providersMatrix.providers.find(p => p.id === 'ollama')?.available) : false;
        container.innerHTML = `
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Ollama (Local AI)</h3>
                    <span class="badge ${ollamaActive ? 'badge-success' : 'badge-secondary'}">${ollamaActive ? 'Connected' : 'Not Connected'}</span>
                </div>
                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
                    Runs locally on localhost:11434. No API key required.
                </p>
                <div style="font-size: 12px; color: var(--text-tertiary);">${ollamaActive ? 'Status: Local Ollama instance running' : 'Status: Local Ollama instance offline'}</div>
            </div>
        `;
    }

    renderCustomerAi() {
        const container = this.element.querySelector('#customer-ai-container');
        if (!container) return;

        const aiProviders = [
            { id: 'openai', name: 'OpenAI (GPT-4o)', desc: 'Connect OpenAI to use your own OpenAI account/model for supported AI analysis.', optional: true },
            { id: 'anthropic', name: 'Anthropic (Claude)', desc: 'Connect Anthropic (Claude) to use your own Claude model for SEO analysis.', optional: true },
            { id: 'gemini', name: 'Google Gemini', desc: 'Connect Google Gemini to use your own Gemini API key for SEO analysis.', optional: true }
        ];

        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
                ${aiProviders.map(p => {
                    const conn = this.connections.find(c => c.provider === p.id);
                    const isConnected = !!(conn && conn.is_active);
                    return `
                        <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px; display: flex; flex-direction: column; justify-content: space-between;">
                            <div>
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">${p.name}</h3>
                                    <div style="display: flex; gap: 6px;">
                                        <span class="badge badge-warning" style="font-size: 10px; font-weight: 800;">Optional</span>
                                        <span class="badge ${isConnected ? 'badge-success' : 'badge-secondary'}">${isConnected ? 'Connected' : 'Not Connected'}</span>
                                    </div>
                                </div>
                                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; line-height: 1.5;">
                                    ${p.desc}
                                </p>
                            </div>
                            <div style="border-top: 1px solid var(--border); padding-top: 12px;">
                                ${isConnected ? `
                                    <button class="btn btn-secondary btn-sm btn-remove-customer-key" data-provider="${p.id}" style="width: 100%; color: var(--critical);">
                                        Remove Key
                                    </button>
                                ` : `
                                    <button class="btn btn-secondary btn-sm btn-add-customer-key" data-provider="${p.id}" data-name="${p.name}" style="width: 100%;">
                                        Connect ${p.id.toUpperCase()}
                                    </button>
                                `}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;

        this.bindCustomerEvents(container);
    }

    bindCustomerEvents(container) {
        container.querySelectorAll('.btn-add-customer-key').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const provider = e.currentTarget.getAttribute('data-provider');
                const name = e.currentTarget.getAttribute('data-name');
                this.openAddKeyModal(provider, name);
            });
        });

        container.querySelectorAll('.btn-remove-customer-key').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const provider = e.currentTarget.getAttribute('data-provider');
                if (!confirm(`Are you sure you want to remove your ${provider.toUpperCase()} API key?`)) return;
                try {
                    await apiClient.post(`/api/integrations/${provider}/disconnect`, {});
                    await this.loadIntegrations();
                } catch (err) {
                    alert(`Error removing key: ${err.message}`);
                }
            });
        });
    }

    openAddKeyModal(provider, name) {
        const container = this.element.querySelector('#integrations-modal-container');
        if (!container) return;

        container.innerHTML = `
            <div class="modal-overlay" style="position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6); display: flex; align-items: center; justify-content: center; z-index: 9999; padding: 20px;">
                <div class="card" style="width: 100%; max-width: 480px; padding: 28px; background: var(--bg-card); border-radius: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text-primary);">Connect ${this.escapeHtml(name)}</h3>
                        <button id="btn-modal-close" style="background: none; border: none; font-size: 20px; color: var(--text-tertiary); cursor: pointer;">&times;</button>
                    </div>

                    <form id="form-customer-key">
                        <div style="margin-bottom: 20px;">
                            <label style="display: block; font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">API Key</label>
                            <input type="password" id="input-api-key" placeholder="Enter your ${this.escapeHtml(name)} API key" required style="width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-subtle); color: var(--text-primary); font-size: 13.5px;" />
                        </div>

                        <div style="display: flex; justify-content: flex-end; gap: 10px;">
                            <button type="button" id="btn-modal-cancel" class="btn btn-secondary" style="padding: 8px 16px; font-size: 13px;">Cancel</button>
                            <button type="submit" id="btn-modal-submit" class="btn btn-primary" style="padding: 8px 16px; font-size: 13px;">Save Key</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        const closeModal = () => { container.innerHTML = ''; };
        container.querySelector('#btn-modal-close')?.addEventListener('click', closeModal);
        container.querySelector('#btn-modal-cancel')?.addEventListener('click', closeModal);

        container.querySelector('#form-customer-key')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const key = container.querySelector('#input-api-key')?.value;
            if (!key) return;

            try {
                await apiClient.post(`/api/integrations/${provider}/connect`, { api_key: key });
                closeModal();
                await this.loadIntegrations();
            } catch (err) {
                alert(`Error saving ${name} key: ` + err.message);
            }
        });
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
