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
                container.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 20px; max-width: 840px;">
                        
                        <!-- PROJECT DETAILS -->
                        <div class="card" style="padding: 24px;">
                            <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 16px; color: var(--text-primary);">Selected Project Configuration</h3>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 14px;">
                                <div>
                                    <span style="color: var(--text-tertiary); font-size: 11px; font-weight: 700; text-transform: uppercase; display: block;">PROJECT NAME</span>
                                    <strong style="font-size: 16px; color: var(--text-primary);">${projName}</strong>
                                </div>
                                <div>
                                    <span style="color: var(--text-tertiary); font-size: 11px; font-weight: 700; text-transform: uppercase; display: block;">TARGET DOMAIN</span>
                                    <a href="${projDomain}" target="_blank" style="color: var(--primary); font-weight: 600; text-decoration: none;">${projDomain}</a>
                                </div>
                            </div>
                        </div>

                        <!-- TEAM MANAGEMENT CONTAINER -->
                        <div id="settings-team-wrapper"></div>

                    </div>
                `;

                const teamWrapper = container.querySelector('#settings-team-wrapper');
                if (teamWrapper && projectId) {
                    await this.renderTeamSection(teamWrapper, projectId, isOwner);
                }
            }

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.renderTabContent(container));
            } else {
                renderFeatureErrorState(container, "Settings Error", e.message || "Unable to load settings data.", () => this.renderTabContent(container));
            }
        }
    }

    async renderTeamSection(wrapper, projectId, isOwner) {
        try {
            const teamData = await apiClient.get(`/api/projects/${projectId}/team`);
            const members = teamData.members || [];
            const pendingInvites = teamData.pending_invitations || [];
            const memberCount = teamData.member_count || 0;

            wrapper.innerHTML = `
                <div class="card" style="padding: 24px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <h3 style="font-size: 17px; font-weight: 700; margin: 0; color: var(--text-primary);">Project Team & Teammate Permissions</h3>
                            <p style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">
                                Each project supports 1 Lead + max 2 Team Members (${memberCount}/2 teammates active). Access is project-specific.
                            </p>
                        </div>
                        ${isOwner && memberCount < 2 ? `
                            <button id="btn-show-invite-form" class="btn btn-primary btn-sm">+ Invite Teammate</button>
                        ` : (isOwner ? `<span class="badge badge-warning">Team Member Limit Reached (2/2)</span>` : '')}
                    </div>

                    <!-- INVITE TEAMMATE FORM -->
                    <div id="invite-form-container" style="display: none; background: var(--bg-subtle); border-radius: 10px; padding: 18px; margin-bottom: 20px; border: 1px solid var(--border);">
                        <h4 style="font-size: 14px; font-weight: 700; margin: 0 0 8px; color: var(--text-primary);">Invite Teammate</h4>
                        <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 12px;">
                            Enter your teammate's email address. They will gain access upon signing into the SEO platform.
                        </p>
                        <form id="invite-teammate-form" style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <input type="email" id="invite-google-email" placeholder="e.g. teammate@company.com" required style="flex: 1; min-width: 240px; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); color: var(--text-primary);"/>
                            <button type="submit" class="btn btn-primary btn-sm">Send Invitation</button>
                            <button type="button" class="btn btn-secondary btn-sm" id="btn-cancel-invite-form">Cancel</button>
                        </form>
                    </div>

                    <!-- ACTIVE TEAM MEMBERS TABLE -->
                    <div style="overflow-x: auto; margin-bottom: 16px;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th style="padding: 10px 16px;">User Account</th>
                                    <th style="padding: 10px 16px;">Role</th>
                                    <th style="padding: 10px 16px;">Status</th>
                                    <th style="padding: 10px 16px; text-align: right;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${members.map(m => `
                                    <tr>
                                        <td style="padding: 12px 16px;">
                                            <strong style="color: var(--text-primary); display: block;">${m.name}</strong>
                                            <span style="font-size: 11.5px; color: var(--text-secondary); font-family: monospace;">${m.email || m.masked_email}</span>
                                        </td>
                                        <td style="padding: 12px 16px;">
                                            <span class="badge ${m.role === 'OWNER' ? 'badge-success' : 'badge-info'}">${m.role_label}</span>
                                        </td>
                                        <td style="padding: 12px 16px;">
                                            <span style="color: var(--success); font-weight: 600; font-size: 12px;">● Active</span>
                                        </td>
                                        <td style="padding: 12px 16px; text-align: right;">
                                            ${isOwner && m.role !== 'OWNER' ? `
                                                <button class="btn btn-secondary btn-sm btn-remove-teammate" data-user="${m.email}" style="font-size: 11px; color: var(--critical);">Remove Access</button>
                                            ` : '<span style="font-size: 11px; color: var(--text-tertiary);">Owner</span>'}
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>

                </div>
            `;

            this.bindTeamHandlers(wrapper, projectId);
        } catch (err) {
            console.error('[SETTINGS] Team load error:', err);
        }
    }

    bindTeamHandlers(wrapper, projectId) {
        const toggleBtn = wrapper.querySelector('#btn-show-invite-form');
        const inviteFormContainer = wrapper.querySelector('#invite-form-container');
        const cancelBtn = wrapper.querySelector('#btn-cancel-invite-form');
        const inviteForm = wrapper.querySelector('#invite-teammate-form');

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

        if (inviteForm) {
            inviteForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const emailInput = wrapper.querySelector('#invite-google-email');
                const email = emailInput ? emailInput.value.trim() : '';

                if (!email) return;

                try {
                    await apiClient.post(`/api/projects/${projectId}/team/invite`, { email });
                    await this.renderTeamSection(wrapper, projectId, true);
                    alert(`Invitation sent to ${email}.`);
                } catch (err) {
                    alert(`Failed to invite teammate: ${err.message || err}`);
                }
            });
        }
    }
}
