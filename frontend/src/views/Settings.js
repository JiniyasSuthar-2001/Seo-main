import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { Integrations } from './Integrations.js';

export class Settings {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'settings-view';
        this.integrationsSubView = new Integrations();
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary);">Project Settings & Team Access</h1>
                <p style="color: var(--text-secondary); margin-top: 4px; font-size: 13.5px;">Manage project details, team invitations, access roles, and connected Google integrations.</p>
            </div>

            <div id="settings-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading settings & team permissions...
                </div>
            </div>

            <!-- TEAM MANAGEMENT SECTION -->
            <div id="settings-team-wrapper" style="margin-top: 32px;"></div>

            <!-- INTEGRATIONS SUB-SECTION -->
            <div id="settings-integrations-wrapper" style="margin-top: 40px; border-top: 1px solid var(--border); padding-top: 32px;"></div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('settings-content');
        const teamWrapper = this.element.querySelector('#settings-team-wrapper') || document.getElementById('settings-team-wrapper');
        const integrationsWrapper = this.element.querySelector('#settings-integrations-wrapper') || document.getElementById('settings-integrations-wrapper');
        if (!container) return;

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            const projName = selectedProj ? selectedProj.name : 'No active project';
            const projDomain = selectedProj ? (selectedProj.domain || selectedProj.url) : 'https://example.com/';
            const userRole = selectedProj ? (selectedProj.user_role || 'OWNER') : 'OWNER';
            const isOwner = userRole === 'OWNER';

            container.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 28px;">
                    <!-- ACTIVE PROJECT INFO -->
                    <div class="card" style="padding: 24px;">
                        <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 16px; color: var(--text-primary);">Selected Project Details</h3>
                        <div style="display: flex; flex-direction: column; gap: 12px; font-size: 14px;">
                            <div>
                                <span style="color: var(--text-tertiary); font-size: 11px; font-weight: 700; text-transform: uppercase; display: block;">PROJECT NAME</span>
                                <strong style="font-size: 16px; color: var(--text-primary);">${projName}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-tertiary); font-size: 11px; font-weight: 700; text-transform: uppercase; display: block;">TARGET DOMAIN</span>
                                <a href="${projDomain}" target="_blank" style="color: var(--primary); font-weight: 600; text-decoration: none;">${projDomain}</a>
                            </div>
                            <div>
                                <span style="color: var(--text-tertiary); font-size: 11px; font-weight: 700; text-transform: uppercase; display: block;">YOUR PROJECT ROLE</span>
                                <span class="badge ${isOwner ? 'badge-success' : 'badge-info'}" style="margin-top: 2px;">${isOwner ? 'Lead (Owner)' : 'Team Member'}</span>
                            </div>
                        </div>
                    </div>

                    <!-- LOCAL PRIVACY & DATA ISOLATION -->
                    <div class="card" style="padding: 24px;">
                        <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 12px; color: var(--text-primary);">Data Isolation & Security</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 16px;">
                            SEO crawl data and audit findings are stored once and shared securely among authorized project members. Teammates must be explicitly invited via Google OAuth identity.
                        </p>
                        <span class="badge badge-success">Backend Project Access Control Active</span>
                    </div>
                </div>
            `;

            // Load Team Management Section
            if (teamWrapper && projectId) {
                await this.renderTeamSection(teamWrapper, projectId, isOwner);
            }

            // Mount Integrations Subview
            if (integrationsWrapper) {
                integrationsWrapper.appendChild(this.integrationsSubView.render());
                await this.integrationsSubView.mounted();
            }

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Settings Error", e.message || "Unable to load settings data.", () => this.mounted());
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
                                Each project supports 1 Lead + max 2 Team Members (${memberCount}/2 teammates active).
                            </p>
                        </div>
                        ${isOwner && memberCount < 2 ? `
                            <button id="btn-show-invite-form" class="btn btn-primary btn-sm">+ Invite Teammate</button>
                        ` : (isOwner ? `<span class="badge badge-warning">Team Member Limit Reached (2/2)</span>` : '')}
                    </div>

                    <!-- INVITE TEAMMATE FORM (HIDDEN BY DEFAULT UNLESS TOGGLED) -->
                    <div id="invite-form-container" style="display: none; background: var(--bg-subtle); border-radius: 10px; padding: 18px; margin-bottom: 20px; border: 1px solid var(--border);">
                        <h4 style="font-size: 14px; font-weight: 700; margin: 0 0 8px; color: var(--text-primary);">Invite Teammate via Google Account</h4>
                        <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 12px;">
                            Enter your teammate's Google email address. They will gain access upon signing in with Google.
                        </p>
                        <form id="invite-teammate-form" style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <input type="email" id="invite-google-email" placeholder="e.g. teammate@gmail.com" required style="flex: 1; min-width: 240px; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); color: var(--text-primary);"/>
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
                                            <span style="font-size: 11.5px; color: var(--text-secondary); font-family: monospace;">${m.masked_email}</span>
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

                    <!-- PENDING INVITATIONS LIST -->
                    ${pendingInvites.length > 0 ? `
                        <div style="margin-top: 20px; border-top: 1px dashed var(--border); padding-top: 16px;">
                            <h4 style="font-size: 13.5px; font-weight: 700; margin: 0 0 10px; color: var(--text-primary);">Pending Teammate Invitations</h4>
                            <div style="display: flex; flex-direction: column; gap: 8px;">
                                ${pendingInvites.map(inv => `
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--bg-subtle); border-radius: 8px; font-size: 12.5px; border: 1px solid var(--border);">
                                        <div>
                                            <strong style="color: var(--text-primary);">${inv.invited_email}</strong>
                                            <span style="font-size: 11px; color: var(--text-tertiary); margin-left: 8px;">Pending Acceptance</span>
                                        </div>
                                        ${isOwner ? `
                                            <button class="btn btn-secondary btn-sm btn-cancel-invite" data-id="${inv.id}" style="font-size: 11px; padding: 3px 9px;">Cancel Invitation</button>
                                        ` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

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
                    alert(`Invitation sent to Google account ${email}.`);
                } catch (err) {
                    alert(`Failed to invite teammate: ${err.message || err}`);
                }
            });
        }

        // Remove teammate buttons
        const removeBtns = wrapper.querySelectorAll('.btn-remove-teammate');
        removeBtns.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const targetEmail = e.currentTarget.getAttribute('data-user');
                if (confirm(`Remove project access for ${targetEmail}?\nThis user will no longer be able to access this project's SEO data.`)) {
                    try {
                        await apiClient.post(`/api/projects/${projectId}/team/remove`, { email: targetEmail });
                        await this.renderTeamSection(wrapper, projectId, true);
                    } catch (err) {
                        alert(`Failed to remove access: ${err.message || err}`);
                    }
                }
            });
        });

        // Cancel invite buttons
        const cancelInviteBtns = wrapper.querySelectorAll('.btn-cancel-invite');
        cancelInviteBtns.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const invitationId = e.currentTarget.getAttribute('data-id');
                try {
                    await apiClient.post(`/api/projects/${projectId}/team/cancel-invite`, { invitation_id: invitationId });
                    await this.renderTeamSection(wrapper, projectId, true);
                } catch (err) {
                    alert(`Failed to cancel invitation: ${err.message || err}`);
                }
            });
        });
    }
}
