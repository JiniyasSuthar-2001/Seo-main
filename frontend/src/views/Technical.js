import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

window.exportTechnicalCSV = () => {
    const table = document.querySelector('table');
    if (!table) return;
    let csv = [];
    for (let i = 0; i < table.rows.length; i++) {
        let row = [], cols = table.rows[i].querySelectorAll('td, th');
        for (let j = 0; j < cols.length; j++) 
            row.push('"' + cols[j].innerText.replace(/"/g, '""') + '"');
        csv.push(row.join(','));
    }
    const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'technical_seo_issues.csv';
    a.click();
};

export class Technical {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'technical-view';
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600;">Technical SEO Audit</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Automated deterministic rules and evidence-based SEO issue detection.</p>
                </div>
                <div id="technical-actions" style="display: flex; gap: 10px;">
                </div>
            </div>

            <div id="technical-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading technical audit issues...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('technical-content');
        const actionsContainer = document.getElementById('technical-actions');
        if (!container) return;

        try {
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select or create a project workspace.</div>`;
                return;
            }

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <a href="${API_BASE_URL}/api/projects/${projectId}/technical/report.pdf" target="_blank" class="btn btn-secondary btn-sm">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Download PDF
                    </a>
                    <a href="${API_BASE_URL}/api/projects/${projectId}/technical/export.csv" target="_blank" class="btn btn-secondary btn-sm">Export CSV</a>
                `;
            }

            const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/technical?limit=200&offset=0`);
            if (!res.ok) throw new Error("API response error");
            const rawIssues = await res.json();

            // Extract severity query param e.g. /technical?severity=critical
            const urlParams = new URLSearchParams(window.location.search);
            const activeSeverityFilter = (urlParams.get('severity') || '').toLowerCase();

            const hasCrawled = selectedProj.has_crawled || (selectedProj.pages_count && selectedProj.pages_count > 0);

            if (!hasCrawled && (!rawIssues || rawIssues.length === 0)) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                        </div>
                        <div class="empty-state-title">Technical SEO Has Not Been Analyzed Yet</div>
                        <div class="empty-state-desc">No crawl snapshot exists for <strong>${selectedProj.name}</strong>. Run a website crawl from the header or Dashboard to detect technical SEO findings.</div>
                        <button class="btn btn-primary" onclick="window.location.href='/'">Run Website Crawl</button>
                    </div>
                `;
                return;
            }

            if (hasCrawled && (!rawIssues || rawIssues.length === 0)) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon" style="color: var(--success);">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        </div>
                        <div class="empty-state-title">No Technical Issues Detected</div>
                        <div class="empty-state-desc">Your website crawl snapshot for <strong>${selectedProj.name}</strong> completed with zero detected technical SEO issues.</div>
                    </div>
                `;
                return;
            }

            const criticals = rawIssues.filter(i => (i.severity || '').toLowerCase() === 'critical');
            const warnings = rawIssues.filter(i => (i.severity || '').toLowerCase() === 'warning');
            const notices = rawIssues.filter(i => (i.severity || '').toLowerCase() === 'notice');

            let filteredIssues = rawIssues;
            if (activeSeverityFilter === 'critical') {
                filteredIssues = criticals;
            } else if (activeSeverityFilter === 'warning') {
                filteredIssues = warnings;
            } else if (activeSeverityFilter === 'notice') {
                filteredIssues = notices;
            }

            let rows = filteredIssues.map(iss => {
                let badgeClass = 'badge-info';
                const sev = (iss.severity || '').toLowerCase();
                if (sev === 'critical') badgeClass = 'badge-critical';
                else if (sev === 'warning') badgeClass = 'badge-warning';

                return `
                    <tr>
                        <td><span class="badge ${badgeClass}">${iss.severity}</span></td>
                        <td style="font-weight: 600;">${iss.issue_type}</td>
                        <td style="font-family: monospace; font-size: 12px; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            <a href="${iss.affected_url}" target="_blank" style="color: var(--primary); text-decoration: none;">${iss.affected_url}</a>
                        </td>
                        <td style="font-size: 13px;">${iss.details}</td>
                        <td style="font-size: 12px; color: var(--text-secondary); background: var(--bg-subtle); padding: 8px 12px; border-radius: 4px;">${iss.recommendation}</td>
                    </tr>
                `;
            }).join('');

            container.innerHTML = `
                <!-- SUMMARY KPI CARDS & SEVERITY FILTER TOGGLES -->
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
                    <a href="/technical" data-link class="kpi-card" style="text-decoration: none; cursor: pointer; border: 1px solid ${!activeSeverityFilter ? 'var(--primary)' : 'var(--border)'};">
                        <div class="kpi-label">TOTAL ISSUES</div>
                        <div class="kpi-value">${rawIssues.length}</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">Show All</div>
                    </a>
                    <a href="/technical?severity=critical" data-link class="kpi-card" style="text-decoration: none; cursor: pointer; border: 1px solid ${activeSeverityFilter === 'critical' ? 'var(--critical)' : 'var(--border)'};">
                        <div class="kpi-label">CRITICAL</div>
                        <div class="kpi-value" style="color: var(--critical);">${criticals.length}</div>
                        <div style="font-size: 11px; color: var(--critical); margin-top: 4px;">Filter Critical &rarr;</div>
                    </a>
                    <a href="/technical?severity=warning" data-link class="kpi-card" style="text-decoration: none; cursor: pointer; border: 1px solid ${activeSeverityFilter === 'warning' ? 'var(--warning)' : 'var(--border)'};">
                        <div class="kpi-label">WARNINGS</div>
                        <div class="kpi-value" style="color: var(--warning);">${warnings.length}</div>
                        <div style="font-size: 11px; color: var(--warning); margin-top: 4px;">Filter Warnings &rarr;</div>
                    </a>
                    <a href="/technical?severity=notice" data-link class="kpi-card" style="text-decoration: none; cursor: pointer; border: 1px solid ${activeSeverityFilter === 'notice' ? 'var(--primary)' : 'var(--border)'};">
                        <div class="kpi-label">NOTICES</div>
                        <div class="kpi-value">${notices.length}</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">Filter Notices &rarr;</div>
                    </a>
                </div>

                <!-- ISSUES TABLE -->
                <div class="card" style="padding: 0; overflow: hidden;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="font-size: 15px; font-weight: 600;">
                            Evidence-Backed Findings (${filteredIssues.length})
                            ${activeSeverityFilter ? `<span class="badge badge-info" style="margin-left: 8px; text-transform: uppercase;">Filter: ${activeSeverityFilter}</span>` : ''}
                        </h3>
                        <span style="font-size: 12px; color: var(--text-secondary);">Rule Engine Output</span>
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Severity</th>
                                    <th style="padding: 12px;">Issue Category</th>
                                    <th style="padding: 12px;">Affected Page</th>
                                    <th style="padding: 12px;">Evidence Details</th>
                                    <th style="padding: 12px 20px;">Actionable Recommendation</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows.length > 0 ? rows : `<tr><td colspan="5" style="padding: 24px; text-align: center; color: var(--text-secondary);">No issues found for filter '${activeSeverityFilter}'.</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend API server at http://127.0.0.1:8020.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Technical Audit Error", e.message || "Unable to load technical audit issues.", () => this.mounted());
            }
        }
    }
}
