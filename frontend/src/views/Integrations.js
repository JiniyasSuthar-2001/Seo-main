import { apiClient } from '../services/apiClient.js';
import { authStore } from '../core/authStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';

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
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Connected Accounts</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">
                        Connect your Google account, AI Assistant provider, and data services.
                    </p>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="btn-refresh-integrations" class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                        Refresh Connection Status
                    </button>
                </div>
            </div>

            <!-- OAUTH RETURN CONFIRMATION BANNER CONTAINER -->
            <div id="oauth-return-banner-container"></div>

            <!-- SECTION 1: GOOGLE ACCOUNT OAUTH INTEGRATION -->
            <div style="margin-bottom: 32px;">
                <div style="margin-bottom: 16px;">
                    <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Google Account Connection</h2>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin: 0;">
                        Connect your Google account for Google Search Console and Google Business Profile access.
                    </p>
                </div>
                <div id="google-integration-card-container"></div>
            </div>

            <!-- SECTION 2: AI PROVIDER SELECTION & MANAGER -->
            <div class="card" style="padding: 20px; margin-bottom: 28px; background: var(--bg-card); border-left: 4px solid var(--primary); border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em;">AI ASSISTANT ENGINE</div>
                        <h2 style="font-size: 17px; font-weight: 700; color: var(--text-primary); margin: 2px 0 4px 0;">Preferred AI Engine Selection</h2>
                        <div style="font-size: 13px; color: var(--text-secondary);">Select which configured AI service executes your website analysis.</div>
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

        if (googleStatus === 'success') {
            this.oauthStatusMessage = 'Google account connected successfully!';
            this.oauthStatusType = 'success';
            window.history.replaceState({}, document.title, window.location.pathname);
        } else if (googleStatus === 'error' || errParam) {
            this.oauthStatusMessage = `We couldn't connect your Google account right now. Please try again.`;
            this.oauthStatusType = 'error';
            window.history.replaceState({}, document.title, window.location.pathname);
        }

        const bannerContainer = this.element.querySelector('#oauth-return-banner-container');
        if (bannerContainer && this.oauthStatusMessage) {
            const isSuccess = this.oauthStatusType === 'success';
            bannerContainer.innerHTML = `
                <div style="background: ${isSuccess ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'}; border: 1px solid ${isSuccess ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}; color: ${isSuccess ? '#10b981' : '#ef4444'}; padding: 14px 18px; border-radius: 10px; margin-bottom: 24px; font-size: 13.5px; font-weight: 600; display: flex; justify-content: space-between; align-items: center;">
                    <div>${isSuccess ? '✓' : '⚠️'} ${this.escapeHtml(this.oauthStatusMessage)}</div>
                    <button onclick="this.parentElement.remove()" style="background: none; border: none; font-size: 18px; cursor: pointer; color: inherit;">&times;</button>
                </div>
            `;
        }
    }

    async loadIntegrations() {
        try {
            const [intData, matrix] = await Promise.all([
                apiClient.get('/api/integrations').catch(() => null),
                apiClient.get('/api/ai/providers-matrix').catch(() => null)
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
        const isConnected = !!(googleConn && (googleConn.status === 'CONNECTED' || googleConn.status === 'ACTIVE' || googleConn.is_active));
        const accountEmail = googleConn ? (googleConn.provider_email || googleConn.provider_account_name || googleConn.account_identifier || (authStore.user ? authStore.user.email : 'Google Account')) : null;

        container.innerHTML = `
            <div class="card" style="padding: 28px; background: var(--bg-card); border-left: 4px solid ${isConnected ? '#10b981' : 'var(--primary)'}; border-radius: 14px;">
                
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
                            ${isConnected ? `<span style="font-size: 13px; color: var(--text-secondary); font-family: monospace;">${this.escapeHtml(accountEmail)}</span>` : '<span style="font-size: 13px; color: var(--text-secondary);">Google OAuth Connection</span>'}
                        </div>
                    </div>

                    <span class="badge ${isConnected ? 'badge-success' : 'badge-secondary'}" style="font-size: 12px; padding: 5px 12px;">
                        ${isConnected ? 'Google Account Connected' : 'Not Connected'}
                    </span>
                </div>

                <p style="font-size: 14px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 20px;">
                    ${isConnected ? 
                        '<strong>Google Account Connected.</strong> Your Google account is connected. Search performance data will appear here once the required data integration is available.' : 
                        'Connect your Google account to enable Google Search Console and Google Business Profile integrations. You can connect or disconnect at any time.'
                    }
                </p>

                <!-- ACTION BUTTONS -->
                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    ${isConnected ? `
                        <button id="btn-google-disconnect" class="btn btn-secondary" style="color: var(--critical);">
                            Disconnect Google
                        </button>
                    ` : `
                        <button id="btn-google-connect" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700;">
                            Connect Google Source
                        </button>
                    `}
                </div>
            </div>
        `;

        const btnConnect = container.querySelector('#btn-google-connect');
        const btnDisconnect = container.querySelector('#btn-google-disconnect');

        if (btnConnect) {
            btnConnect.addEventListener('click', async () => {
                try {
                    btnConnect.disabled = true;
                    btnConnect.innerText = 'Connecting...';
                    const res = await apiClient.get('/api/oauth/google/authorize');
                    if (res && res.authorization_url) {
                        window.location.href = res.authorization_url;
                    } else {
                        alert("Failed to initialize Google OAuth authorization URL.");
                        btnConnect.disabled = false;
                        btnConnect.innerText = 'Connect Google Source';
                    }
                } catch (err) {
                    alert("Google OAuth Error: " + err.message);
                    btnConnect.disabled = false;
                    btnConnect.innerText = 'Connect Google Source';
                }
            });
        }

        if (btnDisconnect) {
            btnDisconnect.addEventListener('click', async () => {
                if (!confirm("Are you sure you want to disconnect your Google account?")) return;
                try {
                    btnDisconnect.disabled = true;
                    await apiClient.post('/api/integrations/google/disconnect', {});
                    await this.loadIntegrations();
                } catch (err) {
                    alert("Disconnect error: " + err.message);
                    btnDisconnect.disabled = false;
                }
            });
        }
    }

    renderPreferredPills() {
        const container = this.element.querySelector('#preferred-provider-pills');
        if (!container) return;

        const matrix = this.providersMatrix || {};
        const available = matrix.available_providers || ['groq', 'ollama'];

        container.innerHTML = available.map(p => `
            <button class="btn btn-sm ${this.preferredProvider === p ? 'btn-primary' : 'btn-secondary'}" 
                    style="text-transform: uppercase; font-size: 11.5px; font-weight: 700;"
                    onclick="window.switchPreferredAi('${p}')">
                ${p}
            </button>
        `).join('');

        window.switchPreferredAi = async (p) => {
            try {
                await apiClient.post(`/api/ai/set-active-provider?provider=${p}`, {});
                this.preferredProvider = p;
                await this.loadIntegrations();
            } catch (err) {
                alert("Failed to switch AI engine: " + err.message);
            }
        };
    }

    renderPlatformAi() {
        const container = this.element.querySelector('#platform-ai-container');
        if (!container) return;
        container.innerHTML = `
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px;">
                <div style="font-weight: 700; font-size: 15px; color: var(--text-primary); margin-bottom: 4px;">Platform Managed Cloud AI (Groq Llama 3)</div>
                <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5;">High-speed cloud AI engine for audit analysis. Ready to use.</div>
            </div>
        `;
    }

    renderLocalAi() {
        const container = this.element.querySelector('#local-ai-container');
        if (!container) return;
        container.innerHTML = `
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px;">
                <div style="font-weight: 700; font-size: 15px; color: var(--text-primary); margin-bottom: 4px;">Local AI (Ollama)</div>
                <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5;">Run private AI analysis locally on your computer.</div>
            </div>
        `;
    }

    renderCustomerAi() {
        const container = this.element.querySelector('#customer-ai-container');
        if (!container) return;
        container.innerHTML = `
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px; color: var(--text-secondary); font-size: 13px;">
                Personal API keys (OpenAI, Anthropic, Gemini) can be configured here if desired.
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
