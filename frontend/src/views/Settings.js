import { projectStore } from '../core/projectStore.js';
import { authStore } from '../core/authStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class Settings {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'settings-view';
        this.activeTab = 'account';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Settings & Workspace Control</h1>
                <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Manage platform identity, external service integrations, workspace projects, and team access.</p>
            </div>

            <!-- SETTINGS NAVIGATION TABS -->
            <div class="settings-tabs-bar" style="display: flex; gap: 8px; border-bottom: 1px solid var(--border); margin-bottom: 24px;">
                <button class="settings-tab-btn active" data-tab="account" style="padding: 10px 18px; font-size: 14px; font-weight: 600; color: var(--primary); border: none; border-bottom: 2px solid var(--primary); background: transparent; cursor: pointer;">
                    Account & Security
                </button>
                <button class="settings-tab-btn" data-tab="integrations" style="padding: 10px 18px; font-size: 14px; font-weight: 600; color: var(--text-secondary); border: none; border-bottom: 2px solid transparent; background: transparent; cursor: pointer;">
                    Integrations & Services
                </button>
                <button class="settings-tab-btn" data-tab="workspace" style="padding: 10px 18px; font-size: 14px; font-weight: 600; color: var(--text-secondary); border: none; border-bottom: 2px solid transparent; background: transparent; cursor: pointer;">
                    Workspace & Team
                </button>
            </div>

            <div id="settings-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading settings...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('settings-content');
        if (!container) return;

        // Bind tab switching
        this.element.querySelectorAll('.settings-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetTab = e.currentTarget.getAttribute('data-tab');
                this.activeTab = targetTab;

                this.element.querySelectorAll('.settings-tab-btn').forEach(tb => {
                    tb.classList.remove('active');
                    tb.style.color = 'var(--text-secondary)';
                    tb.style.borderBottomColor = 'transparent';
                });

                e.currentTarget.classList.add('active');
                e.currentTarget.style.color = 'var(--primary)';
                e.currentTarget.style.borderBottomColor = 'var(--primary)';

                this.renderTabContent(container);
            });
        });

        await this.renderTabContent(container);
    }

    async renderTabContent(container) {
        try {
            await authStore.checkSession();
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            const projName = selectedProj ? selectedProj.name : 'No active project';
            const projDomain = selectedProj ? (selectedProj.domain || selectedProj.url) : 'https://example.com/';
            const userRole = selectedProj ? (selectedProj.user_role || 'OWNER') : 'OWNER';
            const isOwner = userRole === 'OWNER';

            const userEmail = authStore.user && authStore.user.email ? authStore.user.email : 'user@company.com';
            const userName = authStore.user && authStore.user.name ? authStore.user.name : 'SEO Platform User';

            if (this.activeTab === 'account') {
                container.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 20px; max-width: 720px;">
                        
                        <!-- PROFILE CARD -->
                        <div class="card" style="padding: 24px;">
                            <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 16px; color: var(--text-primary);">User Profile</h3>
                            <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 20px;">
                                <div style="width: 52px; height: 52px; border-radius: 50%; background: linear-gradient(135deg, var(--primary), #7c3aed); color: #fff; font-weight: 800; font-size: 20px; display: flex; align-items: center; justify-content: center;">
                                    ${userName.charAt(0).toUpperCase()}
                                </div>
                                <div>
                                    <strong style="font-size: 16px; color: var(--text-primary); display: block;">${userName}</strong>
                                    <span style="font-size: 13.5px; color: var(--text-secondary); font-family: monospace;">${userEmail}</span>
                                </div>
                            </div>
                            <div style="border-top: 1px solid var(--border); padding-top: 14px; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 12px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase;">PLATFORM IDENTITY</span>
                                    <span class="badge badge-success" style="margin-left: 8px;">Authenticated User</span>
                                </div>
                                <button id="btn-settings-logout" class="btn btn-secondary btn-sm" style="color: var(--critical);">Sign Out</button>
                            </div>
                        </div>

                        <!-- SECURITY & SESSION -->
                        <div class="card" style="padding: 24px;">
                            <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 12px; color: var(--text-primary);">Security & Active Session</h3>
                            <p style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 16px;">
                                Your workspace session is secured via signed JWT tokens and enterprise role-based authorization.
                            </p>
                            <div style="display: flex; gap: 12px; align-items: center;">
                                <span style="font-size: 12px; font-weight: 700; color: var(--success);">● Session Active</span>
                                <span style="font-size: 12px; color: var(--text-tertiary);">• Cryptographic Bearer Token Enabled</span>
                            </div>
                        </div>

                    </div>
                `;

                const logoutBtn = container.querySelector('#btn-settings-logout');
                if (logoutBtn) {
                    logoutBtn.addEventListener('click', () => {
                        if (confirm('Sign out of your SEO Platform session?')) {
                            authStore.logout();
                        }
                    });
                }

            } else if (this.activeTab === 'integrations') {
                container.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 20px; max-width: 840px;">
                        
                        <!-- INTEGRATIONS INTRODUCTION -->
                        <div class="card" style="padding: 24px;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                <div>
                                    <h3 style="font-size: 17px; font-weight: 700; margin: 0 0 4px; color: var(--text-primary);">External Account Connections</h3>
                                    <p style="font-size: 13.5px; color: var(--text-secondary); margin: 0;">
                                        Connect Google Search Console, Google Business Profile, and optional AI services to power your SEO workspace.
                                    </p>
                                </div>
                                <button onclick="window.location.href='/integrations'" class="btn btn-primary btn-sm">
                                    Open Integrations Directory &rarr;
                                </button>
                            </div>
                        </div>

                        <!-- GOOGLE INTEGRATION CARD -->
                        <div class="card" style="padding: 24px; border-left: 4px solid var(--primary);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                <div style="display: flex; align-items: center; gap: 12px;">
                                    <svg width="24" height="24" viewBox="0 0 24 24">
                                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                        <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.62z"/>
                                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                                    </svg>
                                    <div>
                                        <strong style="font-size: 16px; color: var(--text-primary); display: block;">Google Account</strong>
                                        <span style="font-size: 12.5px; color: var(--text-secondary);">Google Search Console & Business Profile</span>
                                    </div>
                                </div>
                                <button onclick="window.location.href='/integrations'" class="btn btn-secondary btn-sm">Configure Google</button>
                            </div>
                            <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
                                Connect your Google account to enable supported Google services and SEO data integrations.
                            </p>
                            <div style="font-size: 12px; color: var(--text-tertiary);">
                                Capabilities: ✓ Search Console &nbsp;•&nbsp; ✓ Business Profile
                            </div>
                        </div>

                    </div>
                `;

            } else if (this.activeTab === 'workspace') {
                const projects = projectStore.projects || [];

                if (projects.length === 0) {
                    container.innerHTML = `
                        <div class="card" style="padding: 40px 24px; text-align: center; max-width: 600px; margin: 32px auto; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                            <div style="width: 48px; height: 48px; border-radius: 50%; background: var(--bg-secondary); color: var(--text-tertiary); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; font-size: 22px;">
                                📁
                            </div>
                            <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No Accessible Projects</h3>
                            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; line-height: 1.5;">
                                You do not currently have access to any projects in this workspace. Create a project to start tracking SEO intelligence.
                            </p>
                            <div style="display: flex; gap: 12px; justify-content: center;">
                                <a href="/projects" class="btn btn-primary btn-sm">+ Create Project</a>
                            </div>
                        </div>
                    `;
                    return;
                }

                const projIndustry = selectedProj ? (selectedProj.industry || '') : '';
                const projServices = selectedProj ? (selectedProj.services || '') : '';
                const projServiceAreas = selectedProj ? (selectedProj.service_areas || '') : '';

                container.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 20px; max-width: 840px;">
                        
                        <!-- PROJECT DETAILS & BUSINESS CONTEXT -->
                        <div class="card" style="padding: 24px;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 4px; color: var(--text-primary);">Selected Project & Business Context</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 0;">
                                        Provide business niche, core services, and service locations to tailor AI recommendations and executive report narratives.
                                    </p>
                                </div>
                            </div>

                            <!-- PROJECT SELECTION DROPDOWN -->
                            <div style="margin-bottom: 18px;">
                                <label for="settings-project-select" style="display: block; font-size: 12px; font-weight: 600; margin-bottom: 6px; color: var(--text-secondary);">
                                    Active Project
                                </label>
                                <select id="settings-project-select" style="width: 100%; padding: 9px 12px; font-size: 13.5px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); color: var(--text-primary); cursor: pointer;">
                                    ${projects.map(p => `
                                        <option value="${this.escapeHtml(p.id)}" ${p.id === projectId ? 'selected' : ''}>
                                            ${this.escapeHtml(p.name)} — ${this.escapeHtml(p.domain || p.url || '')}
                                        </option>
                                    `).join('')}
                                </select>
                            </div>

                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 14px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border);">
                                <div>
                                    <span style="color: var(--text-tertiary); font-size: 11px; font-weight: 700; text-transform: uppercase; display: block; margin-bottom: 4px;">PROJECT NAME</span>
                                    <strong style="font-size: 16px; color: var(--text-primary);">${this.escapeHtml(projName)}</strong>
                                </div>
                                <div>
                                    <span style="color: var(--text-tertiary); font-size: 11px; font-weight: 700; text-transform: uppercase; display: block; margin-bottom: 4px;">TARGET DOMAIN</span>
                                    <a href="${this.escapeHtml(projDomain)}" target="_blank" style="color: var(--primary); font-weight: 600; text-decoration: none;">${this.escapeHtml(projDomain)}</a>
                                </div>
                            </div>

                            <!-- BUSINESS CONTEXT FORM -->
                            <form id="project-business-context-form" style="display: flex; flex-direction: column; gap: 14px;">
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                                    <div>
                                        <label style="display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; color: var(--text-secondary);">Industry / Business Niche</label>
                                        <input type="text" id="ctx-industry" value="${this.escapeHtml(projIndustry)}" placeholder="e.g. Electrical & Solar Contracting" style="width: 100%; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); color: var(--text-primary);"/>
                                    </div>
                                    <div>
                                        <label style="display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; color: var(--text-secondary);">Service Areas / Locations</label>
                                        <input type="text" id="ctx-service-areas" value="${this.escapeHtml(projServiceAreas)}" placeholder="e.g. Sydney, Brisbane, Gold Coast, Regional QLD" style="width: 100%; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); color: var(--text-primary);"/>
                                    </div>
                                </div>

                                <div>
                                    <label style="display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; color: var(--text-secondary);">Core Services / Topic Focus (Comma Separated)</label>
                                    <input type="text" id="ctx-services" value="${this.escapeHtml(projServices)}" placeholder="e.g. Level 2 Electrical, Solar Power Installation, Battery Storage, EV Chargers, Air Conditioning" style="width: 100%; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); color: var(--text-primary);"/>
                                </div>

                                <div id="ctx-save-status" style="display: none; font-size: 12.5px; padding: 8px 12px; border-radius: 6px;"></div>

                                ${isOwner ? `
                                    <div style="display: flex; justify-content: flex-end; margin-top: 4px;">
                                        <button type="submit" id="btn-save-context" class="btn btn-primary btn-sm">Save Business Context</button>
                                    </div>
                                ` : `
                                    <span style="font-size: 12px; color: var(--text-tertiary);">Only project owners can modify business context settings.</span>
                                `}
                            </form>
                        </div>

                        <!-- TEAM MANAGEMENT CONTAINER -->
                        <div id="settings-team-wrapper"></div>

                    </div>
                `;

                // Handle Project Switcher
                const projSelect = container.querySelector('#settings-project-select');
                if (projSelect) {
                    projSelect.addEventListener('change', async (e) => {
                        const newProjId = e.target.value;
                        if (newProjId && newProjId !== projectId) {
                            projectStore.setSelectedProjectId(newProjId);
                            const teamWrapper = container.querySelector('#settings-team-wrapper');
                            if (teamWrapper) {
                                teamWrapper.innerHTML = `
                                    <div class="card" style="padding: 24px; text-align: center; color: var(--text-secondary); margin-bottom: 20px;">
                                        Loading team members...
                                    </div>
                                `;
                            }
                            await this.renderTabContent(container);
                            window.dispatchEvent(new CustomEvent('project:selected', { detail: { projectId: newProjId } }));
                        }
                    });
                }

                const ctxForm = container.querySelector('#project-business-context-form');
                if (ctxForm && isOwner && projectId) {
                    ctxForm.addEventListener('submit', async (e) => {
                        e.preventDefault();
                        const statusBox = container.querySelector('#ctx-save-status');
                        const saveBtn = container.querySelector('#btn-save-context');
                        if (saveBtn) saveBtn.disabled = true;

                        try {
                            const indVal = (container.querySelector('#ctx-industry')?.value || '').trim();
                            const servVal = (container.querySelector('#ctx-services')?.value || '').trim();
                            const areasVal = (container.querySelector('#ctx-service-areas')?.value || '').trim();

                            await apiClient.put(`/api/projects/${projectId}`, {
                                industry: indVal,
                                services: servVal,
                                service_areas: areasVal
                            });

                            if (selectedProj) {
                                selectedProj.industry = indVal;
                                selectedProj.services = servVal;
                                selectedProj.service_areas = areasVal;
                            }

                            if (statusBox) {
                                statusBox.style.display = 'block';
                                statusBox.style.background = 'rgba(34, 197, 94, 0.1)';
                                statusBox.style.color = '#22c55e';
                                statusBox.style.border = '1px solid rgba(34, 197, 94, 0.3)';
                                statusBox.textContent = 'Business context saved successfully. Future reports will tailor AI recommendations with this context.';
                            }
                        } catch (err) {
                            if (statusBox) {
                                statusBox.style.display = 'block';
                                statusBox.style.background = 'rgba(239, 68, 68, 0.1)';
                                statusBox.style.color = '#ef4444';
                                statusBox.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                                statusBox.textContent = err.message || 'Failed to update business context.';
                            }
                        } finally {
                            if (saveBtn) saveBtn.disabled = false;
                        }
                    });
                }

                const teamWrapper = container.querySelector('#settings-team-wrapper');
                if (teamWrapper) {
                    if (projectId) {
                        await this.renderTeamSection(teamWrapper, projectId, isOwner, projName);
                    } else {
                        teamWrapper.innerHTML = `
                            <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary); margin-bottom: 20px;">
                                <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 8px; color: var(--text-primary);">No Project Selected</h3>
                                <p style="margin: 0; font-size: 13.5px;">Please select or create a website project to manage team access and teammate permissions.</p>
                            </div>
                        `;
                    }
                }
            }

        } catch (e) {
            console.error('[SETTINGS] Tab render error:', e);
            if (e.isNetworkError) {
                renderBackendOfflineState(container, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.renderTabContent(container));
            } else if (e.status === 401) {
                renderFeatureErrorState(container, "Session Expired", "Your session has expired. Please sign in again to access workspace settings.", () => window.location.href = '/login');
            } else if (e.status === 403) {
                renderFeatureErrorState(container, "Access Restricted", "You do not have permission to access these settings.", () => this.renderTabContent(container));
            } else {
                renderFeatureErrorState(container, "Settings Error", e.message || "Unable to load settings data.", () => this.renderTabContent(container));
            }
        }
    }

    async renderTeamSection(wrapper, projectId, isOwner, projName = 'this project') {
        try {
            wrapper.innerHTML = `
                <div class="card" style="padding: 24px; text-align: center; color: var(--text-secondary); margin-bottom: 20px;">
                    Loading team members...
                </div>
            `;
            const teamData = await apiClient.get(`/api/projects/${projectId}/team`);
            const members = teamData.members || [];
            const pendingInvites = teamData.pending_invitations || [];
            const memberCount = teamData.member_count || 0;
            const callerIsOwner = teamData.is_owner ?? isOwner;

            let pendingRows = pendingInvites.map(inv => `
                <tr>
                    <td style="padding: 12px 16px;">
                        <strong style="color: var(--text-primary); display: block;">${this.escapeHtml(inv.invited_email)}</strong>
                        <span style="font-size: 11px; color: var(--text-tertiary);">Internal Invitation</span>
                    </td>
                    <td style="padding: 12px 16px;">
                        <span class="badge badge-info" style="font-size: 11px;">${this.escapeHtml(inv.role || 'MEMBER')}</span>
                    </td>
                    <td style="padding: 12px 16px;">
                        <span class="badge badge-warning" style="font-size: 11px;">● Pending</span>
                    </td>
                    <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary);">
                        ${inv.created_at ? new Date(inv.created_at).toLocaleDateString() : 'Recent'}
                    </td>
                    <td style="padding: 12px 16px; text-align: right;">
                        ${callerIsOwner ? `
                            <button class="btn btn-secondary btn-sm btn-cancel-invitation" data-id="${inv.id}" style="font-size: 11px; color: var(--critical);">Cancel</button>
                        ` : '<span style="font-size: 11px; color: var(--text-tertiary);">-</span>'}
                    </td>
                </tr>
            `).join('');

            wrapper.innerHTML = `
                <div class="card" style="padding: 24px; margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <h3 style="font-size: 17px; font-weight: 700; margin: 0; color: var(--text-primary);">Project Team & Teammate Permissions</h3>
                            <p style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">
                                Invite registered SEO Intelligence Platform accounts to collaborate on this project. Each project supports 1 Lead + max 2 Team Members (${memberCount}/2 teammates active).
                            </p>
                        </div>
                        ${callerIsOwner && memberCount < 2 ? `
                            <button id="btn-show-invite-form" class="btn btn-primary btn-sm">+ Invite Teammate</button>
                        ` : (callerIsOwner ? `<span class="badge badge-warning">Team Member Limit Reached (2/2)</span>` : '')}
                    </div>

                    <!-- SEARCH & INVITE TEAMMATE FORM -->
                    <div id="invite-form-container" style="display: none; background: var(--bg-subtle); border-radius: 10px; padding: 20px; margin-bottom: 24px; border: 1px solid var(--border);">
                        <h4 style="font-size: 14px; font-weight: 700; margin: 0 0 6px; color: var(--text-primary);">Add Teammate (Internal Account Invitation)</h4>
                        <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 14px;">
                            Search for an existing SEO Intelligence Platform account. The invited recipient will receive an internal invitation inside their account.
                        </p>
                        
                        <form id="invite-teammate-form">
                            <div style="margin-bottom: 14px; position: relative;">
                                <label style="display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; color: var(--text-secondary);">Search Existing Account</label>
                                <input type="text" id="invite-account-search" placeholder="Type email or account name (e.g. john@example.com)..." autocomplete="off" required style="width: 100%; padding: 9px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); color: var(--text-primary);"/>
                                <div id="account-search-results" style="display: none; position: absolute; top: 100%; left: 0; right: 0; z-index: 100; background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-height: 180px; overflow-y: auto; margin-top: 4px;"></div>
                            </div>

                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px;">
                                <div>
                                    <label style="display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; color: var(--text-secondary);">Requested Role</label>
                                    <select id="invite-role-select" style="width: 100%; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); color: var(--text-primary);">
                                        <option value="MEMBER">Team Member (Editor)</option>
                                        <option value="ADMIN">Project Admin</option>
                                        <option value="VIEWER">Viewer (Read Only)</option>
                                    </select>
                                </div>
                                <div>
                                    <label style="display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; color: var(--text-secondary);">Assigned Permissions</label>
                                    <div style="display: flex; gap: 12px; font-size: 12px; flex-wrap: wrap; margin-top: 6px;">
                                        <label><input type="checkbox" checked disabled/> Can View</label>
                                        <label><input type="checkbox" id="perm-edit" checked/> Can Edit</label>
                                        <label><input type="checkbox" id="perm-crawl" checked/> Can Crawl</label>
                                    </div>
                                </div>
                            </div>

                            <div id="invite-error-box" style="display: none; padding: 10px 14px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; color: #ef4444; font-size: 12.5px; margin-bottom: 14px;"></div>

                            <div style="display: flex; gap: 10px;">
                                <button type="submit" class="btn btn-primary btn-sm">Send Team Invitation</button>
                                <button type="button" class="btn btn-secondary btn-sm" id="btn-cancel-invite-form">Cancel</button>
                            </div>
                        </form>
                    </div>

                    <!-- ACTIVE TEAM MEMBERS TABLE -->
                    <h4 style="font-size: 14px; font-weight: 700; margin: 0 0 10px; color: var(--text-primary);">Current Team Members (${members.length})</h4>
                    <div style="overflow-x: auto; margin-bottom: 24px;">
                        <table class="data-table" style="width: 100%;">
                            <thead>
                                <tr>
                                    <th style="padding: 10px 16px;">User Account</th>
                                    <th style="padding: 10px 16px;">Role</th>
                                    <th style="padding: 10px 16px;">Status</th>
                                    <th style="padding: 10px 16px; text-align: right;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${members.map(m => {
                                    const isCurrentLoggedInUser = authStore.user && (
                                        (authStore.user.email && (m.email === authStore.user.email || m.user_id === authStore.user.email)) ||
                                        (authStore.user.id && (m.user_id === authStore.user.id || m.email === authStore.user.id))
                                    );

                                    let actionHtml = '';
                                    if (callerIsOwner) {
                                        if (m.role === 'OWNER') {
                                            actionHtml = '<span style="font-size: 11px; color: var(--text-tertiary);">Owner</span>';
                                        } else {
                                            actionHtml = `
                                                <button class="btn btn-secondary btn-sm btn-remove-teammate" data-user="${this.escapeHtml(m.email || m.user_id)}" data-name="${this.escapeHtml(m.name || m.email || m.user_id)}" style="font-size: 11px; color: var(--critical);">Remove</button>
                                            `;
                                        }
                                    } else {
                                        if (isCurrentLoggedInUser && m.role !== 'OWNER') {
                                            actionHtml = `
                                                <button class="btn btn-secondary btn-sm btn-leave-project" data-id="${this.escapeHtml(projectId)}" data-project="${this.escapeHtml(projName)}" style="font-size: 11px; color: var(--critical);">Leave Project</button>
                                            `;
                                        } else if (m.role === 'OWNER') {
                                            actionHtml = '<span style="font-size: 11px; color: var(--text-tertiary);">Owner</span>';
                                        } else {
                                            actionHtml = '<span style="font-size: 11px; color: var(--text-tertiary);">-</span>';
                                        }
                                    }

                                    return `
                                        <tr>
                                            <td style="padding: 12px 16px;">
                                                <strong style="color: var(--text-primary); display: block;">${this.escapeHtml(m.name)}</strong>
                                                <span style="font-size: 11.5px; color: var(--text-secondary); font-family: monospace;">${this.escapeHtml(m.email || m.masked_email)}</span>
                                            </td>
                                            <td style="padding: 12px 16px;">
                                                <span class="badge ${m.role === 'OWNER' ? 'badge-success' : 'badge-info'}">${this.escapeHtml(m.role_label)}</span>
                                            </td>
                                            <td style="padding: 12px 16px;">
                                                <span style="color: var(--success); font-weight: 600; font-size: 12px;">● Active</span>
                                            </td>
                                            <td style="padding: 12px 16px; text-align: right;">
                                                ${actionHtml}
                                            </td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>

                    <!-- PENDING INVITATIONS TABLE -->
                    <h4 style="font-size: 14px; font-weight: 700; margin: 0 0 10px; color: var(--text-primary);">Pending Invitations (${pendingInvites.length})</h4>
                    <div style="overflow-x: auto;">
                        <table class="data-table" style="width: 100%;">
                            <thead>
                                <tr>
                                    <th style="padding: 10px 16px;">Invited Account</th>
                                    <th style="padding: 10px 16px;">Role</th>
                                    <th style="padding: 10px 16px;">Status</th>
                                    <th style="padding: 10px 16px;">Invited Date</th>
                                    <th style="padding: 10px 16px; text-align: right;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${pendingRows.length > 0 ? pendingRows : `<tr><td colspan="5" style="padding: 24px; text-align: center; color: var(--text-secondary);">No pending invitations.</td></tr>`}
                            </tbody>
                        </table>
                    </div>

                </div>
            `;

            this.bindTeamHandlers(wrapper, projectId, callerIsOwner, projName);
        } catch (err) {
            console.error('[SETTINGS] Team load error:', err);
            let errTitle = "Unable to Load Team";
            let errMsg = err.message || "Failed to load team data.";
            if (err.status === 401) {
                errTitle = "Session Expired";
                errMsg = "Your session has expired. Please sign in again.";
            } else if (err.status === 403) {
                errTitle = "Access Restricted";
                errMsg = "You do not have permission to view team members for this project.";
            } else if (err.status === 404) {
                errTitle = "Project Not Found";
                errMsg = "The requested project could not be found.";
            } else if (err.isNetworkError) {
                errTitle = "Connection Error";
                errMsg = `Unable to connect to the backend server at ${API_BASE_URL}.`;
            }

            renderFeatureErrorState(wrapper, errTitle, errMsg, () => this.renderTeamSection(wrapper, projectId, isOwner, projName));
        }
    }

    bindTeamHandlers(wrapper, projectId, isOwner, projName = 'this project') {
        const toggleBtn = wrapper.querySelector('#btn-show-invite-form');
        const inviteFormContainer = wrapper.querySelector('#invite-form-container');
        const cancelBtn = wrapper.querySelector('#btn-cancel-invite-form');
        const inviteForm = wrapper.querySelector('#invite-teammate-form');
        const searchInput = wrapper.querySelector('#invite-account-search');
        const searchResults = wrapper.querySelector('#account-search-results');
        const errorBox = wrapper.querySelector('#invite-error-box');

        if (toggleBtn && inviteFormContainer) {
            toggleBtn.addEventListener('click', () => {
                inviteFormContainer.style.display = inviteFormContainer.style.display === 'none' ? 'block' : 'none';
            });
        }
        if (cancelBtn && inviteFormContainer) {
            cancelBtn.addEventListener('click', () => {
                inviteFormContainer.style.display = 'none';
            });
        }

        // Live Account Search Autocomplete
        if (searchInput && searchResults) {
            let searchTimeout = null;
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.trim();
                if (searchTimeout) clearTimeout(searchTimeout);
                if (query.length < 2) {
                    searchResults.style.display = 'none';
                    return;
                }

                searchTimeout = setTimeout(async () => {
                    try {
                        const res = await apiClient.get(`/api/projects/users/search?q=${encodeURIComponent(query)}`);
                        const users = res.users || [];
                        if (users.length === 0) {
                            searchResults.innerHTML = `<div style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">No registered accounts found matching "${this.escapeHtml(query)}"</div>`;
                        } else {
                            searchResults.innerHTML = users.map(u => `
                                <div class="search-user-item" data-email="${this.escapeHtml(u.email)}" style="padding: 10px 14px; border-bottom: 1px solid var(--border); cursor: pointer;">
                                    <strong style="font-size: 13px; color: var(--text-primary); display: block;">${this.escapeHtml(u.name)}</strong>
                                    <span style="font-size: 11.5px; color: var(--text-secondary);">${this.escapeHtml(u.email)}</span>
                                </div>
                            `).join('');

                            searchResults.querySelectorAll('.search-user-item').forEach(item => {
                                item.addEventListener('click', () => {
                                    searchInput.value = item.dataset.email;
                                    searchResults.style.display = 'none';
                                });
                            });
                        }
                        searchResults.style.display = 'block';
                    } catch (err) {
                        console.error('[SEARCH USERS] Error:', err);
                    }
                }, 300);
            });
        }

        if (inviteForm) {
            inviteForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                if (errorBox) errorBox.style.display = 'none';
                const email = searchInput ? searchInput.value.trim() : '';
                const role = wrapper.querySelector('#invite-role-select')?.value || 'MEMBER';
                const permEdit = wrapper.querySelector('#perm-edit')?.checked ?? true;
                const permCrawl = wrapper.querySelector('#perm-crawl')?.checked ?? true;

                if (!email) return;

                try {
                    await apiClient.post(`/api/projects/${projectId}/team/invite`, {
                        email,
                        role,
                        permissions: { can_view: true, can_edit: permEdit, can_crawl: permCrawl }
                    });
                    await this.renderTeamSection(wrapper, projectId, isOwner, projName);
                    alert(`Team invitation sent successfully.`);
                } catch (err) {
                    if (errorBox) {
                        errorBox.textContent = err.message || err;
                        errorBox.style.display = 'block';
                    } else {
                        alert(`Failed to send invitation: ${err.message || err}`);
                    }
                }
            });
        }

        // Cancel Pending Invitation Buttons
        wrapper.querySelectorAll('.btn-cancel-invitation').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const invId = e.currentTarget.dataset.id;
                if (!invId) return;
                if (confirm('Cancel this pending project invitation?')) {
                    try {
                        await apiClient.post(`/api/projects/${projectId}/team/cancel-invite`, { invitation_id: invId });
                        await this.renderTeamSection(wrapper, projectId, isOwner, projName);
                    } catch (err) {
                        alert(`Failed to cancel invitation: ${err.message || err}`);
                    }
                }
            });
        });

        // Remove Teammate Buttons (Owner only)
        wrapper.querySelectorAll('.btn-remove-teammate').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const userEmail = e.currentTarget.dataset.user;
                const userName = e.currentTarget.dataset.name || userEmail;
                if (!userEmail) return;
                if (confirm(`Remove ${userName} from this project team?`)) {
                    try {
                        await apiClient.post(`/api/projects/${projectId}/team/remove`, { email: userEmail });
                        await this.renderTeamSection(wrapper, projectId, isOwner, projName);
                        alert(`Team member ${userName} has been removed.`);
                    } catch (err) {
                        alert(`Failed to remove teammate: ${err.message || err}`);
                    }
                }
            });
        });

        // Leave Project Buttons (Team Member self-leave)
        wrapper.querySelectorAll('.btn-leave-project').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const confirmed = confirm(
                    `Leave this project?\n\nYou will lose access to this project's website data, crawl history, keywords, rankings, links, reports, and team workspace.`
                );
                if (!confirmed) return;

                try {
                    await apiClient.post(`/api/projects/${projectId}/team/leave`);
                    await projectStore.fetchProjects();
                    const remainingProjects = projectStore.projects || [];
                    if (remainingProjects.length > 0) {
                        projectStore.setSelectedProjectId(remainingProjects[0].id);
                    } else {
                        projectStore.setSelectedProjectId(null);
                    }
                    window.dispatchEvent(new CustomEvent('project:selected', { detail: { projectId: projectStore.getSelectedProjectId() } }));
                    const container = document.getElementById('settings-content');
                    if (container) {
                        await this.renderTabContent(container);
                    }
                    alert('You have successfully left the project team.');
                } catch (err) {
                    alert(`Failed to leave project: ${err.message || err}`);
                }
            });
        });
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
