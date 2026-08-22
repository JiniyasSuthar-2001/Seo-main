import { apiClient } from '../services/apiClient.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';

export class Integrations {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'integrations-view';
        this.connections = [];
        this.searchQuery = '';
        this.activeCategory = 'All'; // 'All', 'Connected', 'AI & Automation', 'Search & Analytics', 'Social & Marketing'
        this.selectedManageConn = null;
    }

    render() {
        this.element.innerHTML = `
            <!-- HEADER SECTION -->
            <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px 0;">Integrations & External Accounts</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 14px;">
                        Connect your favorite AI services, search engines, and social platforms to power your SEO workspace.
                    </p>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="btn-refresh-integrations" class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                        Refresh Connections
                    </button>
                </div>
            </div>

            <!-- SECURITY DISCLOSURE BANNER -->
            <div class="card" style="padding: 16px 20px; border-left: 4px solid var(--primary); background: rgba(59, 130, 246, 0.08); margin-bottom: 24px;">
                <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                    <div style="width: 34px; height: 34px; border-radius: 50%; background: rgba(59, 130, 246, 0.2); color: var(--primary); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                    </div>
                    <div style="flex: 1; min-width: 240px;">
                        <div style="font-size: 14px; font-weight: 600; color: var(--text-primary);">User-Owned Credentials & AI Independence</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                            ✨ <strong>AI Integration is 100% Optional.</strong> All core SEO crawling, technical audits, link graphs, keyword tracking, and ranking analytics operate fully without connecting an AI account. Credentials are encrypted at rest using Fernet AES-256.
                        </div>
                    </div>
                </div>
            </div>


            <!-- URL STATUS ALERT BANNER -->
            <div id="url-status-banner" style="display: none; margin-bottom: 24px;"></div>

            <!-- SEARCH & CATEGORY FILTER BAR -->
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; flex-wrap: wrap;">
                <!-- SEARCH INPUT -->
                <div style="position: relative; flex: 1; min-width: 240px; max-width: 420px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary);">
                        <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    <input type="text" id="integrations-search-input" placeholder="Search integrations by name or service..." style="width: 100%; padding: 10px 12px 10px 36px; border: 1px solid var(--border); border-radius: 8px; font-size: 13.5px; background: var(--bg-card); color: var(--text-primary);">
                </div>

                <!-- CATEGORY PILL TABS -->
                <div id="category-pills" style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <button class="pill-btn active" data-cat="All">All</button>
                    <button class="pill-btn" data-cat="Connected">Connected</button>
                    <button class="pill-btn" data-cat="AI & Automation">AI & Automation</button>
                    <button class="pill-btn" data-cat="Search & Analytics">Search & Analytics</button>
                </div>
            </div>


            <!-- MAIN INTEGRATIONS GRID CONTENT -->
            <div id="integrations-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading connected accounts...
                </div>
            </div>

            <!-- MODAL CONTAINER -->
            <div id="integrations-modal-container"></div>

            <style>
                .pill-btn {
                    padding: 6px 14px;
                    border-radius: 20px;
                    border: 1px solid var(--border);
                    background: var(--bg-card);
                    color: var(--text-secondary);
                    font-size: 12.5px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.15s ease;
                }
                .pill-btn:hover {
                    background: var(--bg-subtle);
                    color: var(--text-primary);
                }
                .pill-btn.active {
                    background: var(--primary);
                    color: #ffffff;
                    border-color: var(--primary);
                    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
                }
            </style>
        `;

        return this.element;
    }

    async mounted() {
        this.checkUrlStatusParams();
        await this.loadConnections();
        
        const btnRefresh = this.element.querySelector('#btn-refresh-integrations');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => this.loadConnections());
        }

        // Search bar listener
        const searchInput = this.element.querySelector('#integrations-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = (e.target.value || '').toLowerCase().trim();
                this.renderFilteredGrid();
            });
        }

        // Category pills listeners
        const categoryPills = this.element.querySelectorAll('.pill-btn');
        categoryPills.forEach(pill => {
            pill.addEventListener('click', (e) => {
                categoryPills.forEach(p => p.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.activeCategory = e.currentTarget.getAttribute('data-cat');
                this.renderFilteredGrid();
            });
        });
    }

    checkUrlStatusParams() {
        const urlParams = new URLSearchParams(window.location.search);
        const status = urlParams.get('integration');
        const provider = urlParams.get('provider');
        const msg = urlParams.get('msg');
        const banner = this.element.querySelector('#url-status-banner');
        
        if (!banner) return;

        if (status === 'success') {
            banner.style.display = 'block';
            banner.innerHTML = `
                <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #10b981; padding: 12px 16px; border-radius: 8px; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>✓ Successfully connected your <strong>${(provider || 'external').toUpperCase()}</strong> account.</span>
                    <button onclick="this.parentElement.parentElement.style.display='none'" style="background: none; border: none; color: inherit; cursor: pointer; font-size: 16px;">&times;</button>
                </div>
            `;
            window.history.replaceState({}, '', window.location.pathname);
        } else if (status === 'error') {
            banner.style.display = 'block';
            banner.innerHTML = `
                <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 12px 16px; border-radius: 8px; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>✕ Failed to connect ${(provider || 'external').toUpperCase()}: ${this.escapeHtml(msg || 'Authorization cancelled.')}</span>
                    <button onclick="this.parentElement.parentElement.style.display='none'" style="background: none; border: none; color: inherit; cursor: pointer; font-size: 16px;">&times;</button>
                </div>
            `;
            window.history.replaceState({}, '', window.location.pathname);
        }
    }


    async loadConnections() {
        const container = this.element.querySelector('#integrations-content');
        if (!container) return;

        try {
            const data = await apiClient.get('/api/integrations');
            this.connections = (data && data.connections) || [];
            this.renderFilteredGrid();
        } catch (e) {
            if (e.status === 401) {
                renderFeatureErrorState(
                    container,
                    "Authentication Required",
                    "Connected external accounts belong strictly to your authenticated application user. Please sign in or provide a valid user session to manage integrations.",
                    () => this.loadConnections()
                );
            } else if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.loadConnections());
            } else {
                renderFeatureErrorState(container, "Connected Accounts Error", e.message || "Unable to load integrations status.", () => this.loadConnections());
            }
        }

    }

    getProviderCatalog() {
        return [
            {
                id: 'google',
                name: 'Google',
                category: 'Search & Analytics',
                desc: 'Google Search Console, Google Business Profile & Analytics.',
                type: 'oauth',
                badge: 'OAuth 2.0',
                scopesInfo: ['Profile & Email', 'Search Console Read-Only', 'Business Profile']
            },
            {
                id: 'openai',
                name: 'OpenAI',
                category: 'AI & Automation',
                desc: 'GPT-4o, GPT-3.5-Turbo & Text Embeddings for AI audit reasoning.',
                type: 'oauth',
                badge: 'Account Connection'
            },
            {
                id: 'gemini',
                name: 'Google Gemini',
                category: 'AI & Automation',
                desc: 'Gemini 1.5 Pro & Flash multimodal AI reasoning models via Google Account.',
                type: 'oauth',
                badge: 'Google OAuth 2.0'
            },
            {
                id: 'claude',
                name: 'Claude AI (Anthropic)',
                category: 'AI & Automation',
                desc: 'Claude 3.5 Sonnet, Claude 3 Opus & Haiku AI models.',
                type: 'oauth',
                badge: 'Account Connection'
            }
        ];
    }


    renderFilteredGrid() {
        const container = this.element.querySelector('#integrations-content');
        if (!container) return;

        const catalog = this.getProviderCatalog();

        let filtered = catalog.filter(p => {
            const matchesSearch = !this.searchQuery || p.name.toLowerCase().includes(this.searchQuery) || p.desc.toLowerCase().includes(this.searchQuery);
            const conn = this.connections.find(c => c.provider === p.id);
            const isConnected = conn && conn.status === 'CONNECTED';

            if (!matchesSearch) return false;

            if (this.activeCategory === 'All') return true;
            if (this.activeCategory === 'Connected') return isConnected;
            return p.category === this.activeCategory;
        });

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 40px; text-align: center; color: var(--text-secondary);">
                    <div style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">No Integrations Match '${this.escapeHtml(this.searchQuery || this.activeCategory)}'</div>
                    <div style="font-size: 13px;">Try selecting a different filter category or search keyword.</div>
                </div>
            `;
            return;
        }

        // Group into Connected and Available if 'All' tab is active
        const connectedProviders = filtered.filter(p => this.connections.some(c => c.provider === p.id && c.status === 'CONNECTED'));
        const availableProviders = filtered.filter(p => !this.connections.some(c => c.provider === p.id && c.status === 'CONNECTED'));

        let gridHtml = '';

        if (this.activeCategory === 'All' && connectedProviders.length > 0) {
            gridHtml += `
                <div style="margin-bottom: 32px;">
                    <div style="font-size: 11px; font-weight: 700; color: #10b981; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 12px;">CONNECTED ACCOUNTS (${connectedProviders.length})</div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px;">
                        ${connectedProviders.map(p => this.renderCardHtml(p)).join('')}
                    </div>
                </div>
            `;
        }

        const remainingToDisplay = (this.activeCategory === 'All' && connectedProviders.length > 0) ? availableProviders : filtered;

        if (remainingToDisplay.length > 0) {
            gridHtml += `
                <div>
                    ${(this.activeCategory === 'All' && connectedProviders.length > 0) ? `<div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 12px;">AVAILABLE INTEGRATIONS (${remainingToDisplay.length})</div>` : ''}
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px;">
                        ${remainingToDisplay.map(p => this.renderCardHtml(p)).join('')}
                    </div>
                </div>
            `;
        }

        container.innerHTML = gridHtml;
        this.bindEvents(container);
    }

    renderCardHtml(p) {
        const conn = this.connections.find(c => c.provider === p.id);
        const isConnected = conn && (conn.status === 'CONNECTED' || conn.status === 'HEALTHY');
        const isReauth = conn && conn.status === 'REAUTH_REQUIRED';
        
        let statusBadge = '<span class="badge badge-secondary">Not Connected</span>';
        if (isConnected) {
            statusBadge = '<span class="badge badge-success" style="box-shadow: 0 0 8px rgba(16, 185, 129, 0.3);">✓ Connected</span>';
        } else if (isReauth) {
            statusBadge = '<span class="badge badge-warning">⚠ Reauth Required</span>';
        }

        return `
            <div class="card provider-card" style="padding: 24px; background: var(--bg-card); border: 1px solid ${isConnected ? 'var(--primary)' : 'var(--border)'}; border-radius: 12px; display: flex; flex-direction: column; justify-content: space-between; transition: all 0.2s ease;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="width: 36px; height: 36px; border-radius: 8px; background: var(--bg-subtle); display: flex; align-items: center; justify-content: center; font-weight: 700; color: var(--primary); font-size: 16px;">
                                ${p.name.charAt(0)}
                            </div>
                            <div>
                                <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 2px 0; color: var(--text-primary);">${p.name}</h3>
                                <span style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase;">${p.badge}</span>
                            </div>
                        </div>
                        ${statusBadge}
                    </div>

                    <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 16px; min-height: 38px;">
                        ${p.desc}
                    </p>

                    ${isConnected ? `
                        <div style="background: var(--bg-subtle); border-radius: 8px; padding: 12px; font-size: 12px; margin-bottom: 16px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="color: var(--text-secondary);">Account:</span>
                                <strong style="color: var(--text-primary); max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${this.escapeHtml(conn.provider_account_name || conn.provider_email || 'Connected User')}</strong>
                            </div>
                            ${conn.provider_email ? `
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="color: var(--text-secondary);">Email:</span>
                                    <span style="color: var(--text-primary); font-family: monospace;">${this.escapeHtml(conn.provider_email)}</span>
                                </div>
                            ` : ''}
                            ${conn.masked_key ? `
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="color: var(--text-secondary);">Encrypted Key:</span>
                                    <code style="color: var(--primary); font-size: 11px;">${conn.masked_key}</code>
                                </div>
                            ` : ''}
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-secondary);">Status:</span>
                                <span style="color: #10b981; font-weight: 600;">● ${conn.status}</span>
                            </div>
                        </div>
                    ` : ''}
                </div>

                <div style="display: flex; gap: 8px; margin-top: 8px; border-top: 1px solid var(--border); padding-top: 14px;">
                    ${!isConnected ? `
                        ${p.type === 'oauth' ? `
                            <button class="btn btn-primary btn-confirm-oauth" data-provider="${p.id}" style="flex: 1; padding: 8px; font-size: 13px;">
                                Connect ${p.name.split(' ')[0]}
                            </button>
                        ` : `
                            <button class="btn btn-primary btn-connect-key" data-provider="${p.id}" style="flex: 1; padding: 8px; font-size: 13px;">
                                Register ${p.name.split(' ')[0]} Key
                            </button>
                        `}
                    ` : `
                        <button class="btn btn-secondary btn-manage-conn" data-id="${conn.id}" style="font-size: 12px; padding: 6px 10px;">Manage</button>
                        ${p.type === 'key' ? `
                            <button class="btn btn-secondary btn-connect-key" data-provider="${p.id}" style="font-size: 12px; padding: 6px 10px;">Update Key</button>
                        ` : ''}
                        <button class="btn btn-secondary btn-disconnect" data-id="${conn.id}" data-provider="${p.name}" style="flex: 1; font-size: 12px; padding: 6px 10px; color: #ef4444;">
                            Disconnect
                        </button>
                    `}
                </div>
            </div>
        `;
    }

    bindEvents(container) {
        // Pre-connect OAuth confirmation modal
        const oauthBtns = container.querySelectorAll('.btn-confirm-oauth');
        oauthBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const providerId = e.currentTarget.getAttribute('data-provider');
                const provider = this.getProviderCatalog().find(p => p.id === providerId);
                if (provider) this.openOAuthConfirmModal(provider);
            });
        });

        // Key modal
        const keyBtns = container.querySelectorAll('.btn-connect-key');
        keyBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const providerId = e.currentTarget.getAttribute('data-provider');
                const provider = this.getProviderCatalog().find(p => p.id === providerId);
                if (provider) this.openKeyModal(provider);
            });
        });

        // Manage Drawer / Modal
        const manageBtns = container.querySelectorAll('.btn-manage-conn');
        manageBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                const conn = this.connections.find(c => c.id === id);
                if (conn) this.openManageModal(conn);
            });
        });

        // Disconnect buttons
        const disBtns = container.querySelectorAll('.btn-disconnect');
        disBtns.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                const pName = e.currentTarget.getAttribute('data-provider');
                if (confirm(`Are you sure you want to disconnect your ${pName} account?\nStored credentials and access tokens will be removed.`)) {
                    await this.disconnectAccount(id);
                }
            });
        });
    }

    openOAuthConfirmModal(provider) {
        const modalContainer = this.element.querySelector('#integrations-modal-container');
        if (!modalContainer) return;

        const scopesList = (provider.scopesInfo || ['Basic Profile', 'Email Address']).map(s => `
            <div style="display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-primary); margin-bottom: 6px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <span>${s}</span>
            </div>
        `).join('');

        const isGoogleOrGemini = provider.id === 'google' || provider.id === 'gemini';

        modalContainer.innerHTML = `
            <div class="modal-backdrop" style="position: fixed; inset: 0; background: rgba(15, 23, 42, 0.7); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 9999; padding: 20px;">
                <div class="card" style="width: 100%; max-width: 500px; padding: 28px; background: var(--bg-card); border-radius: 12px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <h3 style="font-size: 18px; font-weight: 600; margin: 0; color: var(--text-primary);">Connect ${provider.name} Account</h3>
                        <button id="btn-close-oauth-modal" style="background: none; border: none; font-size: 20px; color: var(--text-secondary); cursor: pointer;">&times;</button>
                    </div>
                    <p style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 16px;">
                        ${isGoogleOrGemini 
                            ? `Connect your Google account to grant authorization for ${provider.name} features. You will be redirected to official Google OAuth consent.` 
                            : `Official third-party OAuth account login for ${provider.name} is not currently supported by the provider API. AI integration is 100% optional, and all core SEO features remain fully operational.`}
                    </p>

                    ${isGoogleOrGemini ? `
                        <div style="background: var(--bg-subtle); border-radius: 8px; padding: 14px; margin-bottom: 20px;">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase; margin-bottom: 8px;">APPROVED PERMISSIONS</div>
                            ${scopesList}
                        </div>
                    ` : `
                        <div style="background: rgba(59, 130, 246, 0.08); border-left: 4px solid var(--primary); border-radius: 6px; padding: 12px 16px; margin-bottom: 20px; font-size: 13px; color: var(--text-secondary);">
                            ℹ️ <strong>Optional Integration:</strong> Core SEO crawling, site audits, keyword rankings, and PDF reports operate 100% reliably without connecting an AI account.
                        </div>
                    `}

                    <div style="font-size: 12px; color: var(--text-tertiary); margin-bottom: 20px;">
                        🔒 Your passwords and sensitive credentials are NEVER requested or stored by this application.
                    </div>

                    <div style="display: flex; justify-content: flex-end; gap: 10px;">
                        <button type="button" id="btn-cancel-oauth-modal" class="btn btn-secondary">Close</button>
                        ${isGoogleOrGemini ? `
                            <button type="button" id="btn-start-oauth-flow" class="btn btn-primary">Continue to Google OAuth</button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;

        const btnClose = modalContainer.querySelector('#btn-close-oauth-modal');
        const btnCancel = modalContainer.querySelector('#btn-cancel-oauth-modal');
        const btnStart = modalContainer.querySelector('#btn-start-oauth-flow');
        const closeModal = () => { modalContainer.innerHTML = ''; };

        if (btnClose) btnClose.addEventListener('click', closeModal);
        if (btnCancel) btnCancel.addEventListener('click', closeModal);
        if (btnStart) {
            btnStart.addEventListener('click', async () => {
                btnStart.disabled = true;
                btnStart.innerText = 'Redirecting to Provider...';
                await this.initiateOAuthFlow(provider.id);
            });
        }
    }

    openManageModal(conn) {

        const modalContainer = this.element.querySelector('#integrations-modal-container');
        if (!modalContainer) return;

        modalContainer.innerHTML = `
            <div class="modal-backdrop" style="position: fixed; inset: 0; background: rgba(15, 23, 42, 0.7); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 9999; padding: 20px;">
                <div class="card" style="width: 100%; max-width: 520px; padding: 28px; background: var(--bg-card); border-radius: 12px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <h3 style="font-size: 18px; font-weight: 600; margin: 0; color: var(--text-primary);">${conn.provider.toUpperCase()} Connection Details</h3>
                        <button id="btn-close-manage-modal" style="background: none; border: none; font-size: 20px; color: var(--text-secondary); cursor: pointer;">&times;</button>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 12px; font-size: 13px; margin-bottom: 20px; background: var(--bg-subtle); padding: 16px; border-radius: 8px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: var(--text-secondary);">Account Name:</span>
                            <strong style="color: var(--text-primary);">${this.escapeHtml(conn.provider_account_name || 'User Account')}</strong>
                        </div>
                        ${conn.provider_email ? `
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-secondary);">Email:</span>
                                <span style="color: var(--text-primary); font-family: monospace;">${this.escapeHtml(conn.provider_email)}</span>
                            </div>
                        ` : ''}
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: var(--text-secondary);">Status:</span>
                            <span style="color: #10b981; font-weight: 600;">● ${conn.status}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: var(--text-secondary);">Connected On:</span>
                            <span style="color: var(--text-tertiary);">${conn.created_at ? conn.created_at.split('T')[0] : 'Active'}</span>
                        </div>
                        ${conn.masked_key ? `
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-secondary);">Encrypted Key:</span>
                                <code style="color: var(--primary);">${conn.masked_key}</code>
                            </div>
                        ` : ''}
                    </div>

                    <div id="modal-test-status" style="display: none; margin-bottom: 16px; font-size: 12px; padding: 10px; border-radius: 6px;"></div>

                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; border-top: 1px solid var(--border); padding-top: 16px;">
                        <button id="btn-test-connection" class="btn btn-secondary btn-sm">Test Connection</button>
                        <div style="display: flex; gap: 8px;">
                            <button id="btn-close-manage" class="btn btn-secondary btn-sm">Close</button>
                            <button id="btn-disconnect-manage" class="btn btn-secondary btn-sm" style="color: #ef4444;">Disconnect</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const btnCloseX = modalContainer.querySelector('#btn-close-manage-modal');
        const btnClose = modalContainer.querySelector('#btn-close-manage');
        const btnTest = modalContainer.querySelector('#btn-test-connection');
        const btnDis = modalContainer.querySelector('#btn-disconnect-manage');
        const testStatusDiv = modalContainer.querySelector('#modal-test-status');

        const closeModal = () => { modalContainer.innerHTML = ''; };

        if (btnCloseX) btnCloseX.addEventListener('click', closeModal);
        if (btnClose) btnClose.addEventListener('click', closeModal);

        if (btnTest) {
            btnTest.addEventListener('click', async () => {
                btnTest.disabled = true;
                btnTest.innerText = 'Testing...';
                testStatusDiv.style.display = 'block';
                testStatusDiv.className = 'card';
                testStatusDiv.style.background = 'var(--bg-subtle)';
                testStatusDiv.innerText = 'Ping provider API...';

                try {
                    const res = await apiClient.post(`/api/integrations/${conn.id}/test`);
                    testStatusDiv.style.background = 'rgba(16, 185, 129, 0.15)';
                    testStatusDiv.style.color = '#10b981';
                    testStatusDiv.innerText = `✓ ${res.message || 'Connection test successful. Status: HEALTHY.'}`;
                } catch (err) {
                    testStatusDiv.style.background = 'rgba(239, 68, 68, 0.15)';
                    testStatusDiv.style.color = '#ef4444';
                    testStatusDiv.innerText = `✕ ${err.message || 'Connection test failed.'}`;
                } finally {
                    btnTest.disabled = false;
                    btnTest.innerText = 'Test Connection';
                }
            });
        }

        if (btnDis) {
            btnDis.addEventListener('click', async () => {
                if (confirm(`Disconnect ${conn.provider.toUpperCase()} account?`)) {
                    closeModal();
                    await this.disconnectAccount(conn.id);
                }
            });
        }
    }

    async initiateOAuthFlow(provider) {
        try {
            const res = await apiClient.get(`/api/integrations/${provider}/connect`);
            if (res && res.authorization_url) {
                window.location.href = res.authorization_url;
            } else {
                alert(`Could not initiate OAuth flow for ${provider}.`);
            }
        } catch (e) {
            alert(`OAuth Initiation Failed: ${e.message || e}`);
        }
    }

    async disconnectAccount(connectionId) {
        try {
            await apiClient.post(`/api/integrations/${connectionId}/disconnect`);
            await this.loadConnections();
        } catch (e) {
            alert(`Failed to disconnect: ${e.message || e}`);
        }
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
