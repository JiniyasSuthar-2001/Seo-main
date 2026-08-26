import { apiClient } from '../services/apiClient.js';
import { projectStore } from '../core/projectStore.js';

export class AIAnchorModal {
    static async show(sourceUrl, targetUrl) {
        let modal = document.getElementById('ai-anchor-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'ai-anchor-modal';
            document.body.appendChild(modal);
        }

        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.75); display: flex; align-items: center; justify-content: center; z-index: 10000; backdrop-filter: blur(4px);';

        // Render Loading State
        modal.innerHTML = `
            <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color, #334155); border-radius: 14px; max-width: 680px; width: 92%; padding: 28px; color: var(--text-primary);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <h3 style="font-size: 18px; font-weight: 700; margin: 0;">✨ AI Suggested Anchors</h3>
                        <span class="badge-ai-analysis" style="font-size: 10px; padding: 2px 6px;">AI Analysis</span>
                    </div>
                    <button class="btn btn-secondary btn-sm" id="btn-close-anchor-modal">✕</button>
                </div>

                <div style="padding: 24px; text-align: center; color: var(--text-secondary);">
                    <div style="font-size: 24px; margin-bottom: 12px; animation: spin 1s linear infinite; display: inline-block;">⟳</div>
                    <div style="font-weight: 600; font-size: 15px; color: var(--text-primary); margin-bottom: 12px;">Analyzing Source & Destination Page Context...</div>
                    <div style="font-size: 12.5px; line-height: 1.8; text-align: left; max-width: 400px; margin: 0 auto; background: rgba(0,0,0,0.2); padding: 12px 18px; border-radius: 8px;">
                        <div>✓ Loading page crawl context</div>
                        <div>✓ Extracting destination title & H1 headings</div>
                        <div>✓ Mapping existing internal link anchor graph</div>
                        <div style="color: var(--primary);">⟳ Generating evidence-grounded recommendations...</div>
                    </div>
                </div>
            </div>
            <style>
                @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            </style>
        `;

        document.getElementById('btn-close-anchor-modal')?.addEventListener('click', () => {
            if (document.body.contains(modal)) document.body.removeChild(modal);
        });

        // Fetch AI suggestions
        await projectStore.ensureInitialized();
        const projectId = projectStore.getSelectedProjectId();

        try {
            const res = await apiClient.post(`/api/projects/${projectId}/internal-links/anchor-suggestions`, {
                source_url: sourceUrl,
                target_url: targetUrl,
                refresh: false
            });

            AIAnchorModal.renderContent(modal, projectId, sourceUrl, targetUrl, res);
        } catch (err) {
            AIAnchorModal.renderError(modal, err.message || "Failed to generate AI anchor suggestions.");
        }
    }

    static renderContent(modal, projectId, sourceUrl, targetUrl, data) {
        const suggestions = data.suggestions || [];
        const evidence = data.evidence || {};
        const warning = data.diversity_warning;
        const status = data.status;

        modal.innerHTML = `
            <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color, #334155); border-radius: 14px; max-width: 720px; width: 92%; max-height: 88vh; overflow-y: auto; padding: 24px; color: var(--text-primary);">
                <!-- HEADER -->
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <h3 style="font-size: 19px; font-weight: 700; margin: 0;">✨ AI Suggested Anchors</h3>
                            <span class="badge-ai-analysis" style="font-size: 10px; padding: 2px 6px;">AI Analysis</span>
                            <span style="font-size: 10px; padding: 2px 6px; border-radius: 4px; background: rgba(59,130,246,0.15); color: #60a5fa; font-weight: 700;">Crawled Data</span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                            Recommendations derived from verified page content and site link graph structure.
                        </div>
                    </div>
                    <button class="btn btn-secondary btn-sm" id="btn-close-anchor-modal">✕</button>
                </div>

                <!-- SOURCE & DESTINATION BADGES -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; font-size: 12.5px;">
                    <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-color); padding: 10px 14px; border-radius: 8px;">
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;">Source Page</div>
                        <div style="font-family: monospace; font-size: 12px; color: var(--primary); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${AIAnchorModal.escapeHtml(sourceUrl)}</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-color); padding: 10px 14px; border-radius: 8px;">
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;">Destination Page</div>
                        <div style="font-family: monospace; font-size: 12px; color: var(--primary); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${AIAnchorModal.escapeHtml(targetUrl)}</div>
                    </div>
                </div>

                <!-- DIVERSITY WARNING ALERT -->
                ${warning ? `
                    <div style="background: rgba(245, 158, 11, 0.1); border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 13px; color: var(--text-secondary);">
                        <strong style="color: #f59e0b;">⚠️ ${warning}</strong>
                    </div>
                ` : ''}

                <!-- SUGGESTIONS LIST -->
                <div style="margin-bottom: 24px;">
                    <div style="font-size: 13px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 10px;">
                        AI Recommended Anchors (${suggestions.length})
                    </div>

                    ${suggestions.length === 0 ? `
                        <div style="background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); padding: 24px; border-radius: 10px; text-align: center; color: var(--text-secondary);">
                            <div style="font-size: 18px; margin-bottom: 6px;">ℹ️</div>
                            <strong style="color: var(--text-primary);">${AIAnchorModal.escapeHtml(data.message || "No reliable anchor suggestions available.")}</strong>
                        </div>
                    ` : suggestions.map((s, idx) => `
                        <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 10px; padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
                            <div>
                                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                                    <span style="font-size: 15px; font-weight: 700; color: var(--text-primary); font-family: monospace;">"${AIAnchorModal.escapeHtml(s.anchor)}"</span>
                                    <span style="font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 4px; background: ${s.confidence === 'High' ? 'rgba(34,197,94,0.15)' : 'rgba(234,179,8,0.15)'}; color: ${s.confidence === 'High' ? '#22c55e' : '#eab308'};">
                                        ${s.confidence} Confidence
                                    </span>
                                </div>
                                <div style="font-size: 12.5px; color: var(--text-secondary);">${AIAnchorModal.escapeHtml(s.reason)}</div>
                            </div>
                            <button class="btn btn-secondary btn-sm btn-copy-anchor" data-anchor="${AIAnchorModal.escapeHtml(s.anchor)}" style="flex-shrink: 0;">
                                Copy
                            </button>
                        </div>
                    `).join('')}
                </div>

                <!-- EVIDENCE SUMMARY BOX -->
                <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-color); border-radius: 10px; padding: 16px; margin-bottom: 20px; font-size: 12.5px;">
                    <div style="font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 10px;">
                        Audited Evidence Package
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <div style="color: var(--text-tertiary);">Destination Title:</div>
                            <div style="font-weight: 600; color: var(--text-primary);">${AIAnchorModal.escapeHtml(evidence.destination_title || '-')}</div>
                        </div>
                        <div>
                            <div style="color: var(--text-tertiary);">Destination Primary H1:</div>
                            <div style="font-weight: 600; color: var(--text-primary);">${AIAnchorModal.escapeHtml(evidence.destination_h1 || '-')}</div>
                        </div>
                    </div>

                    ${evidence.existing_anchor_usage && evidence.existing_anchor_usage.length > 0 ? `
                        <div style="margin-top: 12px; border-top: 1px solid var(--border-color); padding-top: 10px;">
                            <div style="color: var(--text-tertiary); margin-bottom: 6px;">Existing Internal Anchor Usage:</div>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                                ${evidence.existing_anchor_usage.map(a => `
                                    <span style="background: rgba(255,255,255,0.05); border: 1px solid var(--border-color); padding: 2px 8px; border-radius: 4px; font-size: 11.5px;">
                                        "${AIAnchorModal.escapeHtml(a.anchor)}": <strong>${a.count} links</strong>
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>

                <!-- MODAL ACTIONS -->
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <button class="btn btn-secondary btn-sm" id="btn-refresh-anchors">🔄 Regenerate Suggestions</button>
                    <button class="btn btn-primary btn-sm" id="btn-close-anchor-modal-footer">Close</button>
                </div>
            </div>
        `;

        const closeModal = () => {
            if (document.body.contains(modal)) document.body.removeChild(modal);
        };

        document.getElementById('btn-close-anchor-modal')?.addEventListener('click', closeModal);
        document.getElementById('btn-close-anchor-modal-footer')?.addEventListener('click', closeModal);

        modal.querySelectorAll('.btn-copy-anchor').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const text = btn.getAttribute('data-anchor');
                if (text) {
                    navigator.clipboard.writeText(text);
                    btn.innerText = 'Anchor copied!';
                    setTimeout(() => { btn.innerText = 'Copy'; }, 2000);
                }
            });
        });

        document.getElementById('btn-refresh-anchors')?.addEventListener('click', async () => {
            modal.innerHTML = `<div style="color: var(--text-primary); text-align: center; padding: 40px;">Regenerating suggestions...</div>`;
            try {
                const res = await apiClient.post(`/api/projects/${projectId}/internal-links/anchor-suggestions`, {
                    source_url: sourceUrl,
                    target_url: targetUrl,
                    refresh: true
                });
                AIAnchorModal.renderContent(modal, projectId, sourceUrl, targetUrl, res);
            } catch (err) {
                AIAnchorModal.renderError(modal, err.message);
            }
        });
    }

    static renderError(modal, message) {
        modal.innerHTML = `
            <div style="background: var(--bg-card, #1e293b); border: 1px solid #ef4444; border-radius: 14px; max-width: 500px; width: 90%; padding: 24px; color: var(--text-primary);">
                <h3 style="font-size: 18px; font-weight: 700; color: #ef4444; margin-bottom: 8px;">Unable to Generate AI Anchor Suggestions</h3>
                <p style="color: var(--text-secondary); font-size: 13.5px; margin-bottom: 20px;">${AIAnchorModal.escapeHtml(message)}</p>
                <div style="display: flex; justify-content: flex-end;">
                    <button class="btn btn-secondary" id="btn-close-err-modal">Close</button>
                </div>
            </div>
        `;
        document.getElementById('btn-close-err-modal')?.addEventListener('click', () => {
            if (document.body.contains(modal)) document.body.removeChild(modal);
        });
    }

    static escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}
