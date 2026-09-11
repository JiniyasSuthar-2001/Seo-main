import { apiClient } from '../services/apiClient.js';
import { authStore } from '../core/authStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { ApiKeyModal } from '../components/ApiKeyModal.js';

export class Integrations {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'integrations-view';
        this.data = null;
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
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Connected Accounts & Data Providers</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">
                        Manage your individual Google service connections, external SEO providers, and AI Assistant engines.
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

            <!-- SECTION 1: GOOGLE INTEGRATIONS (INDIVIDUAL PRODUCTS) -->
            <div style="margin-bottom: 36px;">
                <div style="margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <svg width="18" height="18" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.62z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                        </svg>
                        <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;">Google Services & Products</h2>
                    </div>
                    <p style="font-size: 13px; color: var(--text-secondary); margin: 4px 0 0 0;">
                        Individual service connections for search analytics, local business visibility, and advertising data.
                    </p>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px;">
                    <!-- CARD 1: GOOGLE SEARCH CONSOLE -->
                    <div id="gsc-card-container"></div>
                    <!-- CARD 2: GOOGLE BUSINESS PROFILE -->
                    <div id="gbp-card-container"></div>
                    <!-- CARD 3: GOOGLE ADS -->
                    <div id="gads-card-container"></div>
                </div>
            </div>

            <!-- SECTION 2: RANK TRACKING & SERP PROVIDER -->
            <div style="margin-bottom: 36px;">
                <div style="margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 16px;">🎯</span>
                        <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;">Rank Tracking & SERP Data</h2>
                    </div>
                    <p style="font-size: 13px; color: var(--text-secondary); margin: 4px 0 0 0;">
                        External SERP provider integration for live keyword ranking position evaluation.
                    </p>
                </div>
                <div id="serp-card-container"></div>
            </div>

            <!-- SECTION 3: BACKLINK INTELLIGENCE PROVIDER -->
            <div style="margin-bottom: 36px;">
                <div style="margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 16px;">🔗</span>
                        <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;">Backlink Intelligence</h2>
                    </div>
                    <p style="font-size: 13px; color: var(--text-secondary); margin: 4px 0 0 0;">
                        External backlink provider for referring domains, inbound backlinks, and link equity metrics.
                    </p>
                </div>
                <div id="backlink-card-container"></div>
            </div>

            <!-- SECTION 4: AI PROVIDER SELECTION & MANAGER (PRESERVED) -->
            <div class="card" style="padding: 20px; margin-bottom: 24px; background: var(--bg-card); border-left: 4px solid var(--primary); border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em;">AI ASSISTANT ENGINE</div>
                        <h2 style="font-size: 17px; font-weight: 700; color: var(--text-primary); margin: 2px 0 4px 0;">Preferred AI Engine Selection</h2>
                        <div style="font-size: 13px; color: var(--text-secondary);">Select which configured AI service executes your website analysis and recommendations.</div>
                    </div>
                    <div id="preferred-provider-pills" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>
                </div>
            </div>

            <!-- SECTION 5: PLATFORM, LOCAL & CUSTOMER AI (PRESERVED) -->
            <div style="margin-bottom: 32px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                    <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;">AI Engine Configurations</h2>
                    <span style="font-size: 12px; color: var(--text-tertiary);">Platform Cloud, Local Ollama & BYOK</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 20px;">
                    <div id="platform-ai-container"></div>
                    <div id="local-ai-container"></div>
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
        const googleStatus = urlParams.get('google') || urlParams.get('integration');
        const errParam = urlParams.get('error');
        const msgParam = urlParams.get('msg');

        if (googleStatus === 'success') {
            this.oauthStatusMessage = 'Google account authorization completed successfully!';
            this.oauthStatusType = 'success';
            window.history.replaceState({}, document.title, window.location.pathname);
        } else if (googleStatus === 'error' || errParam) {
            this.oauthStatusMessage = msgParam || `We couldn't complete the authorization right now. Please try again.`;
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

            this.data = intData || {};
            this.providersMatrix = matrix;
            
            if (matrix && matrix.active_provider) {
                this.preferredProvider = matrix.active_provider;
            }

            this.renderGoogleCards();
            this.renderSerpCard();
            this.renderBacklinkCard();
            this.renderPreferredPills();
            this.renderPlatformAi();
            this.renderLocalAi();
            this.renderCustomerAi();
        } catch (e) {
            console.error('[INTEGRATIONS] Load error:', e);
        }
    }

    // ============================================================
    // RENDER INDIVIDUAL GOOGLE PRODUCT CARDS
    // ============================================================

    renderGoogleCards() {
        const gscContainer = this.element.querySelector('#gsc-card-container');
        const gbpContainer = this.element.querySelector('#gbp-card-container');
        const gadsContainer = this.element.querySelector('#gads-card-container');

        const gsc = this.data.google_search_console || { status: 'NOT_CONNECTED' };
        const gbp = this.data.google_business_profile || { status: 'NOT_CONNECTED' };
        const gads = this.data.google_ads || { status: 'NOT_CONNECTED' };

        // 1. Google Search Console Card
        if (gscContainer) {
            const isGscConnected = gsc.status === 'CONNECTED';
            const isGscAuthReq = gsc.status === 'AUTHORIZATION_REQUIRED';
            gscContainer.innerHTML = `
                <div class="card" style="padding: 24px; background: var(--bg-card); border-left: 4px solid ${isGscConnected ? '#10b981' : (isGscAuthReq ? '#f59e0b' : 'var(--border)')}; border-radius: 12px; display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; gap: 8px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(66, 133, 244, 0.1); display: flex; align-items: center; justify-content: center; font-size: 18px;">
                                    🔍
                                </div>
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Google Search Console</h3>
                                    <span style="font-size: 11.5px; color: var(--text-tertiary);">${gsc.connected_account ? this.escapeHtml(gsc.connected_account) : 'Search Performance Data'}</span>
                                </div>
                            </div>
                            <span class="badge ${isGscConnected ? 'badge-success' : (isGscAuthReq ? 'badge-warning' : 'badge-secondary')}" style="font-size: 11px; padding: 4px 8px;">
                                ${isGscConnected ? 'Connected' : (isGscAuthReq ? 'Scope Required' : 'Not Connected')}
                            </span>
                        </div>
                        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 0 0 14px 0;">
                            ${gsc.description || 'Connect Google Search Console to import search performance data for your verified websites.'}
                        </p>
                        <div style="margin-bottom: 16px;">
                            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); margin-bottom: 6px; letter-spacing: 0.05em;">Includes Data For:</div>
                            <ul style="margin: 0; padding-left: 18px; font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
                                <li>Organic clicks, impressions & CTR</li>
                                <li>Average search ranking position</li>
                                <li>Top performing search queries & pages</li>
                            </ul>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: flex-end; gap: 8px; pt: 12px; border-top: 1px solid var(--border);">
                        ${isGscConnected ? `
                            <button class="btn btn-secondary btn-sm btn-gsc-disconnect" style="color: var(--critical);">Disconnect</button>
                        ` : `
                            <button class="btn btn-primary btn-sm btn-google-oauth-connect">
                                ${isGscAuthReq ? 'Grant Permissions' : 'Connect Search Console'}
                            </button>
                        `}
                    </div>
                </div>
            `;
        }

        // 2. Google Business Profile Card
        if (gbpContainer) {
            const isGbpConnected = gbp.status === 'CONNECTED';
            const isGbpAuthReq = gbp.status === 'AUTHORIZATION_REQUIRED';
            gbpContainer.innerHTML = `
                <div class="card" style="padding: 24px; background: var(--bg-card); border-left: 4px solid ${isGbpConnected ? '#10b981' : (isGbpAuthReq ? '#f59e0b' : 'var(--border)')}; border-radius: 12px; display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; gap: 8px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(52, 168, 83, 0.1); display: flex; align-items: center; justify-content: center; font-size: 18px;">
                                    🏢
                                </div>
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Google Business Profile</h3>
                                    <span style="font-size: 11.5px; color: var(--text-tertiary);">${gbp.connected_account ? this.escapeHtml(gbp.connected_account) : 'Local Search & Business Info'}</span>
                                </div>
                            </div>
                            <span class="badge ${isGbpConnected ? 'badge-success' : (isGbpAuthReq ? 'badge-warning' : 'badge-secondary')}" style="font-size: 11px; padding: 4px 8px;">
                                ${isGbpConnected ? 'Connected' : (isGbpAuthReq ? 'Scope Required' : 'Not Connected')}
                            </span>
                        </div>
                        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 0 0 14px 0;">
                            ${gbp.description || 'Access local business profile data, local search visibility, and customer interaction insights.'}
                        </p>
                        <div style="margin-bottom: 16px;">
                            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); margin-bottom: 6px; letter-spacing: 0.05em;">Includes Data For:</div>
                            <ul style="margin: 0; padding-left: 18px; font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
                                <li>Business profile verification status</li>
                                <li>Maps & local search performance signals</li>
                                <li>Customer interaction trend tracking</li>
                            </ul>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: flex-end; gap: 8px; pt: 12px; border-top: 1px solid var(--border);">
                        ${isGbpConnected ? `
                            <button class="btn btn-secondary btn-sm btn-gbp-disconnect" style="color: var(--critical);">Disconnect</button>
                        ` : `
                            <button class="btn btn-primary btn-sm btn-google-oauth-connect">
                                ${isGbpAuthReq ? 'Grant Permissions' : 'Connect Business Profile'}
                            </button>
                        `}
                    </div>
                </div>
            `;
        }

        // 3. Google Ads Card
        if (gadsContainer) {
            const isGadsConnected = gads.status === 'CONNECTED';
            const isGadsConfigReq = gads.status === 'CONFIGURATION_REQUIRED';
            gadsContainer.innerHTML = `
                <div class="card" style="padding: 24px; background: var(--bg-card); border-left: 4px solid ${isGadsConnected ? '#10b981' : (isGadsConfigReq ? '#f59e0b' : 'var(--border)')}; border-radius: 12px; display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; gap: 8px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(251, 188, 5, 0.15); display: flex; align-items: center; justify-content: center; font-size: 18px;">
                                    📊
                                </div>
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Google Ads</h3>
                                    <span style="font-size: 11.5px; color: var(--text-tertiary);">${gads.developer_token_configured ? 'Developer Token Configured' : 'CPC & Keyword Insights'}</span>
                                </div>
                            </div>
                            <span class="badge ${isGadsConnected ? 'badge-success' : (isGadsConfigReq ? 'badge-warning' : 'badge-secondary')}" style="font-size: 11px; padding: 4px 8px;">
                                ${isGadsConnected ? 'Connected' : (isGadsConfigReq ? 'Config Required' : 'Not Connected')}
                            </span>
                        </div>
                        <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; font-size: 11.5px; color: #b45309;">
                            <strong>Note:</strong> Requires Google Ads Developer Token approval.
                        </div>
                        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 0 0 14px 0;">
                            ${gads.description || 'Synchronize search keyword volume, cost-per-click (CPC) data, and ad campaign search terms.'}
                        </p>
                        ${gads.developer_token_configured ? `
                            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
                                Token: <code style="background: var(--bg-subtle); padding: 2px 6px; border-radius: 4px;">${this.escapeHtml(gads.masked_developer_token || 'Configured')}</code>
                            </div>
                        ` : ''}
                    </div>
                    <div style="display: flex; justify-content: flex-end; gap: 8px; pt: 12px; border-top: 1px solid var(--border);">
                        <button class="btn btn-secondary btn-sm btn-configure-google-ads">
                            ${gads.developer_token_configured ? 'Edit Token' : 'Configure Token'}
                        </button>
                        ${isGadsConnected ? `
                            <button class="btn btn-secondary btn-sm btn-gads-disconnect" style="color: var(--critical);">Disconnect</button>
                        ` : `
                            <button class="btn btn-primary btn-sm btn-google-oauth-connect">Connect Google</button>
                        `}
                    </div>
                </div>
            `;
        }

        // Bind Google OAuth Buttons
        this.element.querySelectorAll('.btn-google-oauth-connect').forEach(btn => {
            btn.addEventListener('click', async () => {
                try {
                    btn.disabled = true;
                    btn.innerText = 'Connecting...';
                    const res = await apiClient.get('/api/oauth/google/authorize');
                    if (res && res.authorization_url) {
                        window.location.href = res.authorization_url;
                    } else {
                        alert("Failed to initialize Google OAuth authorization URL.");
                        btn.disabled = false;
                        btn.innerText = 'Connect Google';
                    }
                } catch (err) {
                    alert("Google OAuth Error: " + err.message);
                    btn.disabled = false;
                    btn.innerText = 'Connect Google';
                }
            });
        });

        // Bind Google Disconnect buttons
        const btnGscDisc = this.element.querySelector('.btn-gsc-disconnect');
        if (btnGscDisc) {
            btnGscDisc.addEventListener('click', async () => {
                if (confirm('Disconnect Google Search Console?')) {
                    await apiClient.post('/api/integrations/google/disconnect', {});
                    await this.loadIntegrations();
                }
            });
        }

        const btnGbpDisc = this.element.querySelector('.btn-gbp-disconnect');
        if (btnGbpDisc) {
            btnGbpDisc.addEventListener('click', async () => {
                if (confirm('Disconnect Google Business Profile?')) {
                    await apiClient.post('/api/integrations/google/disconnect', {});
                    await this.loadIntegrations();
                }
            });
        }

        const btnGadsDisc = this.element.querySelector('.btn-gads-disconnect');
        if (btnGadsDisc) {
            btnGadsDisc.addEventListener('click', async () => {
                if (confirm('Disconnect Google Ads configuration?')) {
                    await apiClient.post('/api/integrations/google_ads/disconnect', {});
                    await this.loadIntegrations();
                }
            });
        }

        const btnConfGads = this.element.querySelector('.btn-configure-google-ads');
        if (btnConfGads) {
            btnConfGads.addEventListener('click', () => {
                const gads = this.data.google_ads || { status: 'NOT_CONNECTED' };
                ApiKeyModal.open({
                    provider: 'google_ads',
                    isConnected: gads.status === 'CONNECTED',
                    maskedKey: gads.masked_developer_token || '',
                    onSuccess: () => this.loadIntegrations()
                });
            });
        }
    }

    // ============================================================
    // RENDER SERP / RANK TRACKING PROVIDER CARD
    // ============================================================

    renderSerpCard() {
        const container = this.element.querySelector('#serp-card-container');
        if (!container) return;

        const serp = this.data.serp_provider || { status: 'NOT_CONFIGURED' };
        const isConnected = serp.status === 'CONNECTED';

        container.innerHTML = `
            <div class="card" style="padding: 24px; background: var(--bg-card); border-left: 4px solid ${isConnected ? '#10b981' : 'var(--border)'}; border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; margin-bottom: 14px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(59, 130, 246, 0.1); display: flex; align-items: center; justify-content: center; font-size: 20px;">
                            🎯
                        </div>
                        <div>
                            <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">SERP & Rank Tracking Provider</h3>
                            <span style="font-size: 12px; color: var(--text-secondary);">${serp.provider_type || 'SerpApi / DataForSEO / Custom SERP Provider'}</span>
                        </div>
                    </div>
                    <span class="badge ${isConnected ? 'badge-success' : 'badge-secondary'}" style="font-size: 11px; padding: 4px 10px;">
                        ${isConnected ? 'Provider Connected' : 'Not Configured'}
                    </span>
                </div>
                <p style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.5; margin: 0 0 16px 0;">
                    ${serp.description || 'Modular SERP tracking provider abstraction for authentic live keyword ranking position tracking.'}
                </p>
                ${isConnected ? `
                    <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 16px;">
                        API Key: <code style="background: var(--bg-subtle); padding: 2px 6px; border-radius: 4px;">${this.escapeHtml(serp.masked_key || 'Configured')}</code>
                    </div>
                ` : ''}
                <div id="serp-feedback-banner" style="display: none; margin-bottom: 14px; padding: 8px 12px; border-radius: 6px; font-size: 12.5px;"></div>
                <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border); padding-top: 14px;">
                    ${isConnected ? `
                        <button class="btn btn-secondary btn-sm btn-test-serp">Test Connection</button>
                        <button class="btn btn-secondary btn-sm btn-disconnect-serp" style="color: var(--critical);">Disconnect</button>
                    ` : ''}
                    <button class="btn btn-primary btn-sm btn-configure-serp">
                        ${isConnected ? 'Edit Provider Key' : 'Configure SERP Provider'}
                    </button>
                </div>
            </div>
        `;

        const btnConf = container.querySelector('.btn-configure-serp');
        if (btnConf) {
            btnConf.addEventListener('click', () => {
                ApiKeyModal.open({
                    provider: 'serp',
                    isConnected,
                    maskedKey: serp.masked_key || '',
                    existingName: serp.provider_type || 'SerpApi',
                    onSuccess: () => this.loadIntegrations()
                });
            });
        }

        const btnTest = container.querySelector('.btn-test-serp');
        const feedbackBanner = container.querySelector('#serp-feedback-banner');
        if (btnTest) {
            btnTest.addEventListener('click', async () => {
                try {
                    btnTest.disabled = true;
                    btnTest.innerText = 'Testing...';
                    const res = await apiClient.post('/api/integrations/serp/test', {});
                    if (feedbackBanner) {
                        feedbackBanner.style.display = 'block';
                        feedbackBanner.style.background = 'var(--success-bg, rgba(16, 185, 129, 0.1))';
                        feedbackBanner.style.color = 'var(--success, #10b981)';
                        feedbackBanner.style.border = '1px solid var(--success-border, rgba(16, 185, 129, 0.25))';
                        feedbackBanner.innerText = res.message || '✓ SERP connection verified successfully!';
                    }
                } catch (e) {
                    if (feedbackBanner) {
                        feedbackBanner.style.display = 'block';
                        feedbackBanner.style.background = 'var(--critical-bg, rgba(239, 68, 68, 0.1))';
                        feedbackBanner.style.color = 'var(--critical, #ef4444)';
                        feedbackBanner.style.border = '1px solid var(--critical-border, rgba(239, 68, 68, 0.25))';
                        feedbackBanner.innerText = '⚠️ ' + (e.message || 'SERP connection test failed.');
                    }
                } finally {
                    btnTest.disabled = false;
                    btnTest.innerText = 'Test Connection';
                }
            });
        }

        const btnDisc = container.querySelector('.btn-disconnect-serp');
        if (btnDisc) {
            btnDisc.addEventListener('click', async () => {
                if (confirm('Disconnect SERP Provider?')) {
                    await apiClient.post('/api/integrations/serp/disconnect', {});
                    await this.loadIntegrations();
                }
            });
        }
    }

    // ============================================================
    // RENDER BACKLINK DATA PROVIDER CARD
    // ============================================================

    renderBacklinkCard() {
        const container = this.element.querySelector('#backlink-card-container');
        if (!container) return;

        const backlink = this.data.backlink_provider || { status: 'NOT_CONFIGURED' };
        const isConnected = backlink.status === 'CONNECTED';

        container.innerHTML = `
            <div class="card" style="padding: 24px; background: var(--bg-card); border-left: 4px solid ${isConnected ? '#10b981' : 'var(--border)'}; border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; margin-bottom: 14px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(139, 92, 246, 0.1); display: flex; align-items: center; justify-content: center; font-size: 20px;">
                            🔗
                        </div>
                        <div>
                            <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">External Backlink Data Provider</h3>
                            <span style="font-size: 12px; color: var(--text-secondary);">${backlink.provider_type || 'Ahrefs / Moz / OpenLink / Custom Backlink API'}</span>
                        </div>
                    </div>
                    <span class="badge ${isConnected ? 'badge-success' : 'badge-secondary'}" style="font-size: 11px; padding: 4px 10px;">
                        ${isConnected ? 'Provider Connected' : 'Not Configured'}
                    </span>
                </div>
                <p style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.5; margin: 0 0 16px 0;">
                    ${backlink.description || 'External backlink intelligence provider for inbound link metrics, referring domains, and link equity analysis.'}
                </p>
                ${isConnected ? `
                    <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 16px;">
                        API Key: <code style="background: var(--bg-subtle); padding: 2px 6px; border-radius: 4px;">${this.escapeHtml(backlink.masked_key || 'Configured')}</code>
                    </div>
                ` : ''}
                <div id="backlink-feedback-banner" style="display: none; margin-bottom: 14px; padding: 8px 12px; border-radius: 6px; font-size: 12.5px;"></div>
                <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border); padding-top: 14px;">
                    ${isConnected ? `
                        <button class="btn btn-secondary btn-sm btn-test-backlink">Test Connection</button>
                        <button class="btn btn-secondary btn-sm btn-disconnect-backlink" style="color: var(--critical);">Disconnect</button>
                    ` : ''}
                    <button class="btn btn-primary btn-sm btn-configure-backlink">
                        ${isConnected ? 'Edit Provider Key' : 'Configure Backlink Provider'}
                    </button>
                </div>
            </div>
        `;

        const btnConf = container.querySelector('.btn-configure-backlink');
        if (btnConf) {
            btnConf.addEventListener('click', () => {
                ApiKeyModal.open({
                    provider: 'backlink',
                    isConnected,
                    maskedKey: backlink.masked_key || '',
                    existingName: backlink.provider_type || 'Ahrefs / Backlink API',
                    onSuccess: () => this.loadIntegrations()
                });
            });
        }

        const btnTest = container.querySelector('.btn-test-backlink');
        const feedbackBanner = container.querySelector('#backlink-feedback-banner');
        if (btnTest) {
            btnTest.addEventListener('click', async () => {
                try {
                    btnTest.disabled = true;
                    btnTest.innerText = 'Testing...';
                    const res = await apiClient.post('/api/integrations/backlink/test', {});
                    if (feedbackBanner) {
                        feedbackBanner.style.display = 'block';
                        feedbackBanner.style.background = 'var(--success-bg, rgba(16, 185, 129, 0.1))';
                        feedbackBanner.style.color = 'var(--success, #10b981)';
                        feedbackBanner.style.border = '1px solid var(--success-border, rgba(16, 185, 129, 0.25))';
                        feedbackBanner.innerText = res.message || '✓ Backlink connection verified successfully!';
                    }
                } catch (e) {
                    if (feedbackBanner) {
                        feedbackBanner.style.display = 'block';
                        feedbackBanner.style.background = 'var(--critical-bg, rgba(239, 68, 68, 0.1))';
                        feedbackBanner.style.color = 'var(--critical, #ef4444)';
                        feedbackBanner.style.border = '1px solid var(--critical-border, rgba(239, 68, 68, 0.25))';
                        feedbackBanner.innerText = '⚠️ ' + (e.message || 'Backlink connection test failed.');
                    }
                } finally {
                    btnTest.disabled = false;
                    btnTest.innerText = 'Test Connection';
                }
            });
        }

        const btnDisc = container.querySelector('.btn-disconnect-backlink');
        if (btnDisc) {
            btnDisc.addEventListener('click', async () => {
                if (confirm('Disconnect Backlink Provider?')) {
                    await apiClient.post('/api/integrations/backlink/disconnect', {});
                    await this.loadIntegrations();
                }
            });
        }
    }

    // ============================================================
    // PRESERVED AI PROVIDER CARDS & SWITCHING
    // ============================================================

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
                console.error("Failed to switch AI engine:", err);
            }
        };
    }

    renderPlatformAi() {
        const container = this.element.querySelector('#platform-ai-container');
        if (!container) return;
        container.innerHTML = `
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px;">
                <div style="font-weight: 700; font-size: 15px; color: var(--text-primary); margin-bottom: 4px;">Platform Managed Cloud AI (Groq Llama 3.3)</div>
                <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5;">High-speed cloud AI engine for audit analysis and smart recommendations. Ready to use.</div>
            </div>
        `;
    }

    renderLocalAi() {
        const container = this.element.querySelector('#local-ai-container');
        if (!container) return;
        container.innerHTML = `
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px;">
                <div style="font-weight: 700; font-size: 15px; color: var(--text-primary); margin-bottom: 4px;">Local AI (Ollama)</div>
                <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5;">Run private AI analysis locally on your computer with local models.</div>
            </div>
        `;
    }

    renderCustomerAi() {
        const container = this.element.querySelector('#customer-ai-container');
        if (!container) return;

        const customerAiList = this.data.customer_ai || [];
        const cardsHtml = customerAiList.map(ai => {
            const isConnected = ai.connected;
            return `
                <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px; border-left: 4px solid ${isConnected ? '#10b981' : 'var(--border)'}; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div style="font-weight: 700; font-size: 15px; color: var(--text-primary);">${this.escapeHtml(ai.name)}</div>
                                <span class="badge ${isConnected ? 'badge-success' : 'badge-secondary'}" style="font-size: 11px;">
                                    ${isConnected ? 'Connected' : 'Not Connected'}
                                </span>
                            </div>
                            <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">${this.escapeHtml(ai.model_info || '')}</div>
                            ${isConnected ? `<div style="font-size: 11.5px; color: var(--text-tertiary); margin-top: 4px;">Key: <code style="background: var(--bg-subtle); padding: 1px 5px; border-radius: 4px;">${this.escapeHtml(ai.masked_key || 'Configured')}</code></div>` : ''}
                        </div>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            ${isConnected ? `
                                <button class="btn btn-secondary btn-sm" id="btn-test-ai-${ai.provider}" onclick="window.testAiKey('${ai.provider}')">Test Connection</button>
                                <button class="btn btn-secondary btn-sm" onclick="window.configureAiKey('${ai.provider}', true, '${this.escapeHtml(ai.masked_key || '')}')">Update Key</button>
                                <button class="btn btn-secondary btn-sm" style="color: var(--critical);" onclick="window.disconnectAiKey('${ai.provider}')">Disconnect</button>
                            ` : `
                                <button class="btn btn-primary btn-sm" onclick="window.configureAiKey('${ai.provider}', false, '')">Connect ${this.escapeHtml(ai.name)}</button>
                            `}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <div style="margin-bottom: 12px;">
                <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Bring Your Own AI Keys (Optional)</h3>
                <p style="font-size: 13px; color: var(--text-secondary); margin: 0 0 12px 0;">Connecting personal API keys is completely optional. Platform default is available automatically.</p>
                <div id="ai-test-global-feedback" style="display: none; margin-bottom: 14px; padding: 10px 14px; border-radius: 8px; font-size: 13px;"></div>
                ${cardsHtml}
            </div>
        `;

        window.configureAiKey = (provider, isConnected = false, maskedKey = '') => {
            ApiKeyModal.open({
                provider: provider,
                isConnected: isConnected,
                maskedKey: maskedKey,
                onSuccess: () => this.loadIntegrations()
            });
        };

        window.testAiKey = async (provider) => {
            const btn = document.getElementById(`btn-test-ai-${provider}`);
            const banner = document.getElementById('ai-test-global-feedback');
            const originalText = btn ? btn.innerText : 'Test Connection';

            try {
                const res = await apiClient.post(`/api/integrations/${provider}/test`, {});
                if (banner) {
                    banner.style.display = 'block';
                    banner.style.background = 'var(--success-bg, rgba(16, 185, 129, 0.1))';
                    banner.style.color = 'var(--success, #10b981)';
                    banner.style.border = '1px solid var(--success-border, rgba(16, 185, 129, 0.25))';
                    banner.innerHTML = `✓ <strong>${provider.toUpperCase()} Test Successful:</strong> ${res.result?.message || 'Connection verified successfully.'}`;
                }
            } catch (err) {
                if (banner) {
                    banner.style.display = 'block';
                    banner.style.background = 'var(--critical-bg, rgba(239, 68, 68, 0.1))';
                    banner.style.color = 'var(--critical, #ef4444)';
                    banner.style.border = '1px solid var(--critical-border, rgba(239, 68, 68, 0.25))';
                    banner.innerHTML = `⚠️ <strong>${provider.toUpperCase()} Test Failed:</strong> ${err.message || 'Unable to connect.'}`;
                }
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerText = originalText;
                }
            }
        };

        window.disconnectAiKey = async (provider) => {
            if (confirm(`Disconnect ${provider.toUpperCase()} API key?`)) {
                try {
                    await apiClient.post(`/api/integrations/${provider}/disconnect`, {});
                    await this.loadIntegrations();
                } catch (err) {
                    console.error('Failed to disconnect:', err);
                }
            }
        };
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
