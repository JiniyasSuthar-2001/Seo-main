import { technicalService } from '../services/technical.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState } from '../components/ErrorState.js';

export class Technical {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'technical-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Technical SEO Issue Center</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Audit findings detected from actual HTML evidence and HTTP responses.</p>
            </div>
            <div id="technical-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading technical issues...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('technical-content');
        if (!container) return;

        try {
            const issues = await technicalService.getIssues(projectStore.getSelectedProjectId(), 100, 0);

            if (!issues || issues.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon" style="background: var(--success-bg); color: var(--success);">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        </div>
                        <div class="empty-state-title">No Technical Issues Detected</div>
                        <div class="empty-state-desc">Your website passed all technical SEO rule evaluations with zero detected audit findings!</div>
                        <button class="btn btn-primary" onclick="window.location.href='/'">Run New Crawl Audit</button>
                    </div>
                `;
                return;
            }

            const criticals = issues.filter(i => i.severity === 'Critical');
            const warnings = issues.filter(i => i.severity === 'Warning');
            const notices = issues.filter(i => i.severity === 'Notice');

            let issueCards = issues.map(iss => {
                let badgeClass = 'badge-info';
                let borderStyle = 'border-left: 4px solid var(--info);';
                if (iss.severity === 'Critical') { badgeClass = 'badge-critical'; borderStyle = 'border-left: 4px solid var(--critical);'; }
                else if (iss.severity === 'Warning') { badgeClass = 'badge-warning'; borderStyle = 'border-left: 4px solid var(--warning);'; }

                return `
                    <div class="card" style="padding: 20px; ${borderStyle}">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <span style="font-weight: 600; font-size: 15px; color: var(--text-primary);">${iss.issue_type}</span>
                            <span class="badge ${badgeClass}">${iss.severity}</span>
                        </div>
                        <div style="font-size: 13px; font-family: monospace; color: var(--text-secondary); margin-bottom: 10px; word-break: break-all;">
                            Affected URL: <a href="${iss.affected_url}" target="_blank" style="color: var(--primary); text-decoration: none;">${iss.affected_url}</a>
                        </div>
                        <div style="font-size: 14px; color: var(--text-primary); margin-bottom: 10px;">
                            ${iss.details}
                        </div>
                        <div style="font-size: 13px; color: var(--text-secondary); background: var(--bg-subtle); padding: 10px 12px; border-radius: 6px;">
                            <strong>Actionable Recommendation:</strong> ${iss.recommendation}
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px;">
                    <div class="card" style="padding: 20px; text-align: center; border-top: 3px solid var(--critical);">
                        <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">CRITICAL ISSUES</span>
                        <div style="font-size: 28px; font-weight: 700; color: var(--critical); margin-top: 4px;">${criticals.length}</div>
                    </div>
                    <div class="card" style="padding: 20px; text-align: center; border-top: 3px solid var(--warning);">
                        <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">WARNINGS</span>
                        <div style="font-size: 28px; font-weight: 700; color: var(--warning); margin-top: 4px;">${warnings.length}</div>
                    </div>
                    <div class="card" style="padding: 20px; text-align: center; border-top: 3px solid var(--info);">
                        <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">NOTICES</span>
                        <div style="font-size: 28px; font-weight: 700; color: var(--info); margin-top: 4px;">${notices.length}</div>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 16px;">
                    ${issueCards}
                </div>
            `;
        } catch (e) {
            renderBackendOfflineState(container, "Unable to load technical audit issues.");
        }
    }
}
