import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState } from '../components/ErrorState.js';

window.fetchAutocompleteIdeas = async () => {
    const input = document.getElementById('autocomplete-input');
    const resultsContainer = document.getElementById('autocomplete-results');
    if (!input || !input.value.trim()) return;

    resultsContainer.style.display = 'block';
    resultsContainer.innerHTML = '<span style="color: var(--text-secondary); font-size: 13px;">Fetching live Google search suggestions...</span>';

    try {
        const res = await fetch(`${API_BASE_URL}/api/projects/${projectStore.getSelectedProjectId()}/keywords/autocomplete?q=${encodeURIComponent(input.value.trim())}`);
        const data = await res.json();
        
        if (data.suggestions && data.suggestions.length > 0) {
            const items = data.suggestions.map(s => `
                <div style="padding: 8px 12px; background: var(--bg-subtle); border-radius: 6px; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>${s}</span>
                    <span class="badge badge-info" style="font-size: 10px;">Google Suggestion</span>
                </div>
            `).join('');
            resultsContainer.innerHTML = `<div style="display: flex; flex-direction: column; gap: 8px;">${items}</div>`;
        } else {
            resultsContainer.innerHTML = '<span style="color: var(--text-secondary); font-size: 13px;">No suggestions returned for this term.</span>';
        }
    } catch(e) {
        resultsContainer.innerHTML = '<span style="color: red; font-size: 13px;">Failed to reach autocomplete API.</span>';
    }
};

export class Keywords {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'keywords-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Keyword & Topic Intelligence</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Content-extracted topics, entity terms, and live Google autocomplete suggestions.</p>
            </div>
            <div id="keywords-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading keyword intelligence...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('keywords-content');
        if (!container) return;

        try {
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();
            
            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select or create a project workspace.</div>`;
                return;
            }

            const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/keywords`);
            if (!res.ok) throw new Error("API response error");
            const data = await res.json();

            const terms = data.content_keywords || [];
            
            let tableHtml = '';
            if (terms.length === 0) {
                tableHtml = `
                    <div class="empty-state" style="margin-top: 24px;">
                        <div class="empty-state-title">No Crawled Content Topics Found</div>
                        <div class="empty-state-desc">Run a website crawl to automatically extract page topics, entity phrases, and content keywords.</div>
                    </div>
                `;
            } else {
                const rows = terms.map(t => `
                    <tr>
                        <td style="font-weight: 600;">${t.keyword}</td>
                        <td><span class="badge badge-info">${t.source}</span></td>
                        <td>${t.type}</td>
                        <td style="font-weight: 600;">${t.frequency}</td>
                        <td>${t.pages_found} page(s)</td>
                    </tr>
                `).join('');

                tableHtml = `
                    <div class="card" style="padding: 0; overflow: hidden; margin-top: 24px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="font-size: 15px; font-weight: 600;">Extracted Page Topics & Content Terms (${data.total_extracted_terms || terms.length})</h3>
                            <span style="font-size: 12px; color: var(--text-secondary);">${data.source || 'Local NLP Engine'}</span>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Topic / Keyword</th>
                                    <th style="padding: 12px;">Source</th>
                                    <th style="padding: 12px;">Type</th>
                                    <th style="padding: 12px;">Occurrence Count</th>
                                    <th style="padding: 12px 20px;">Pages Found</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                `;
            }

            container.innerHTML = `
                <!-- LIVE GOOGLE AUTOCOMPLETE GENERATOR -->
                <div class="card" style="padding: 24px; background: linear-gradient(to right, var(--bg-card), var(--bg-subtle));">
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">Google Autocomplete Keyword Ideas</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 16px;">Generate real-time keyword variations directly from Google Search suggestions.</p>
                    <div style="display: flex; gap: 12px; max-width: 600px;">
                        <input id="autocomplete-input" type="text" placeholder="e.g. solar panels brisbane" style="flex: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-card); color: var(--text-primary);" onkeypress="if(event.key==='Enter') window.fetchAutocompleteIdeas()">
                        <button class="btn btn-primary" onclick="window.fetchAutocompleteIdeas()">Get Suggestions</button>
                    </div>
                    <div id="autocomplete-results" style="display: none; margin-top: 16px; max-width: 600px;">
                    </div>
                </div>

                ${tableHtml}
            `;

        } catch (e) {
            renderBackendOfflineState(container, "Unable to load keyword intelligence from backend.");
        }
    }
}
