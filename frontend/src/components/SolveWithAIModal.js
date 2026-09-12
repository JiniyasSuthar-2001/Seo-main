/**
 * Solve With AI Modal Component
 * Renders an evidence-grounded, implementation-ready solution modal
 * for fixing specific SEO issues on affected pages.
 */
import { apiClient } from '../services/apiClient.js';
import { projectStore } from '../core/projectStore.js';

export class SolveWithAIModal {
    static open({
        projectId,
        ruleId,
        title,
        category,
        severity,
        description,
        recommendation,
        affectedUrl,
        evidenceText,
        existingSolution
    }) {
        const existing = document.getElementById('solve-with-ai-modal-root');
        if (existing) existing.remove();

        let targetProjectId = projectId || projectStore.getSelectedProjectId();
        if (!targetProjectId) {
            const match = window.location.pathname.match(/\/projects\/([^\/]+)/);
            if (match) targetProjectId = match[1];
        }
        if (!targetProjectId) {
            targetProjectId = localStorage.getItem('seo_selected_project_id') || localStorage.getItem('active_project_id') || localStorage.getItem('selected_project_id');
        }

        let solution = existingSolution || null;
        let isLoading = !solution;
        let isError = false;
        let errorMessage = '';

        const modalRoot = document.createElement('div');
        modalRoot.id = 'solve-with-ai-modal-root';
        modalRoot.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(5px); display: flex; align-items: center;
            justify-content: center; z-index: 10000; padding: 20px;
        `;

        const renderModal = () => {
            let sevBadgeStyle = 'background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3);';
            const sevLower = (severity || solution?.severity || '').toLowerCase();
            if (sevLower === 'warning') sevBadgeStyle = 'background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3);';
            else if (sevLower === 'notice') sevBadgeStyle = 'background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3);';

            let bodyHtml = '';

            if (isLoading) {
                bodyHtml = `
                    <div style="padding: 48px 24px; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px;">
                        <div class="crawl-spinner" style="width: 32px; height: 32px; border: 3px solid var(--primary); border-top-color: transparent; border-radius: 50%;"></div>
                        <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">Analyzing crawl evidence with AI...</div>
                        <div style="font-size: 12.5px; color: var(--text-secondary); max-width: 420px; line-height: 1.5;">
                            Evaluating page title, metadata, headings, content structure, and technical signals to produce an actionable fix.
                        </div>
                    </div>
                `;
            } else if (isError || !solution) {
                bodyHtml = `
                    <div style="padding: 36px 24px; text-align: center;">
                        <div style="font-size: 28px; margin-bottom: 8px;">⚠️</div>
                        <div style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">AI solution temporarily unavailable</div>
                        <div style="font-size: 13px; color: var(--text-secondary); max-width: 480px; margin: 0 auto 18px auto; line-height: 1.5;">
                            ${escapeHtml(errorMessage || 'The detected problem and existing recommended action are still available. Please check your connection or retry.')}
                        </div>
                        <div style="display: flex; justify-content: center; gap: 10px;">
                            <button id="btn-retry-solve" class="btn btn-primary btn-sm">Try Again</button>
                            <button id="btn-close-error" class="btn btn-secondary btn-sm">Close</button>
                        </div>
                    </div>
                `;
            } else {
                const charCount = solution.character_count || (solution.replacement_value ? solution.replacement_value.length : 0);
                const showCharCount = charCount > 0 && (title.toLowerCase().includes('meta') || title.toLowerCase().includes('title') || title.toLowerCase().includes('description') || title.toLowerCase().includes('h1'));
                const showCurrent = solution.current_value && solution.current_value !== 'Not configured' && solution.current_value !== '(Missing meta description)' && solution.current_value !== '(Missing <title> tag)' && solution.current_value !== '(No H1 Tag)';

                bodyHtml = `
                    <div style="padding: 20px 24px; display: flex; flex-direction: column; gap: 18px; overflow-y: auto; max-height: calc(85vh - 140px);">
                        
                        <!-- AFFECTED PAGE -->
                        <div style="background: var(--bg-subtle); padding: 12px 16px; border-radius: 10px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px;">Affected Page</div>
                            <a href="${escapeHtml(solution.affected_url || affectedUrl)}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); font-family: monospace; font-size: 13px; font-weight: 600; text-decoration: none; word-break: break-all;">
                                ${escapeHtml(solution.affected_url || affectedUrl)} ↗
                            </a>
                        </div>

                        <!-- WHAT WE FOUND -->
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">WHAT WE FOUND</div>
                            <div style="background: var(--bg-card); border: 1px solid var(--border); padding: 12px 16px; border-radius: 8px; font-size: 13px; color: var(--text-primary); line-height: 1.5;">
                                ${escapeHtml(solution.what_we_found || evidenceText || description || title)}
                            </div>
                        </div>

                        <!-- AI RECOMMENDED SOLUTION -->
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">AI RECOMMENDED SOLUTION</div>
                            
                            <div style="display: flex; flex-direction: column; gap: 10px; background: rgba(59, 130, 246, 0.04); border: 1px solid rgba(59, 130, 246, 0.25); padding: 16px; border-radius: 10px;">
                                
                                ${showCurrent ? `
                                    <div>
                                        <div style="font-size: 11.5px; font-weight: 700; color: var(--text-secondary); margin-bottom: 4px;">Current:</div>
                                        <div style="background: var(--bg-card); border: 1px solid var(--border); padding: 10px 12px; border-radius: 6px; font-size: 12.5px; color: var(--text-secondary); line-height: 1.4; word-break: break-word;">
                                            "${escapeHtml(solution.current_value)}"
                                        </div>
                                    </div>
                                ` : ''}

                                <div>
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                        <span style="font-size: 11.5px; font-weight: 700; color: var(--success);">Replace with:</span>
                                        ${showCharCount ? `
                                            <span class="badge badge-success" style="font-size: 11px; font-weight: 700;">
                                                Character Count: ${charCount}
                                            </span>
                                        ` : ''}
                                    </div>
                                    <div style="background: var(--bg-card); border: 1.5px solid var(--success); padding: 12px 14px; border-radius: 8px; font-size: 13.5px; font-weight: 600; color: var(--text-primary); line-height: 1.5; word-break: break-word;">
                                        ${escapeHtml(solution.replacement_value || solution.recommended_fix || solution.ai_solution)}
                                    </div>
                                </div>

                            </div>
                        </div>

                        <!-- WHY THIS FIX -->
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">WHY THIS FIX</div>
                            <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.55;">
                                ${escapeHtml(solution.why_this_fix || solution.ai_solution || 'Addresses identified audit finding to improve search crawler interpretation.')}
                            </div>
                        </div>

                        <!-- IMPLEMENTATION -->
                        ${solution.implementation ? `
                            <div>
                                <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">IMPLEMENTATION CODE</div>
                                <pre style="background: #0f172a; color: #38bdf8; padding: 12px 16px; border-radius: 8px; font-size: 12px; font-family: monospace; overflow-x: auto; margin: 0; line-height: 1.4; border: 1px solid rgba(255,255,255,0.1); white-space: pre-wrap; word-break: break-all;">${escapeHtml(solution.implementation)}</pre>
                            </div>
                        ` : ''}

                    </div>
                `;
            }

            modalRoot.innerHTML = `
                <div class="card" style="width: 100%; max-width: 680px; max-height: 90vh; display: flex; flex-direction: column; background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); overflow: hidden;">
                    
                    <!-- HEADER -->
                    <div style="padding: 18px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: center; gap: 12px;">
                        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                            <span style="font-size: 16px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
                                <span>✨</span> Solve with AI
                            </span>
                            <span class="badge" style="${sevBadgeStyle} font-size: 10.5px; font-weight: 800;">
                                ${(severity || solution?.severity || 'HIGH').toUpperCase()}
                            </span>
                            <span class="badge badge-info" style="font-size: 10.5px;">${escapeHtml(category || solution?.category || 'On-Page')}</span>
                        </div>
                        <button id="btn-close-solve-modal" style="background: none; border: none; font-size: 24px; line-height: 1; color: var(--text-tertiary); cursor: pointer; padding: 4px;" aria-label="Close Modal">&times;</button>
                    </div>

                    <!-- BODY CONTENT -->
                    ${bodyHtml}

                    <!-- FOOTER ACTIONS -->
                    ${!isLoading && solution ? `
                        <div style="padding: 14px 24px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: flex-end; align-items: center; gap: 12px;">
                            <button id="btn-copy-solution" class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px; font-weight: 600;">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                                <span>Copy Solution</span>
                            </button>
                            <button id="btn-done-solution" class="btn btn-primary btn-sm" style="font-weight: 600; padding: 6px 18px;">
                                Done
                            </button>
                        </div>
                    ` : ''}

                </div>
            `;

            // Bind Event Handlers
            modalRoot.querySelector('#btn-close-solve-modal')?.addEventListener('click', () => modalRoot.remove());
            modalRoot.querySelector('#btn-close-error')?.addEventListener('click', () => modalRoot.remove());
            modalRoot.querySelector('#btn-done-solution')?.addEventListener('click', () => modalRoot.remove());

            modalRoot.querySelector('#btn-retry-solve')?.addEventListener('click', () => {
                isLoading = true;
                isError = false;
                renderModal();
                fetchSolution();
            });

            const copyBtn = modalRoot.querySelector('#btn-copy-solution');
            if (copyBtn && solution) {
                copyBtn.addEventListener('click', () => {
                    const textToCopy = solution.replacement_value || solution.implementation || solution.recommended_fix || '';
                    if (navigator.clipboard) {
                        navigator.clipboard.writeText(textToCopy).then(() => {
                            const originalText = copyBtn.innerHTML;
                            copyBtn.innerHTML = '<span>✓ Copied!</span>';
                            copyBtn.classList.add('btn-success');
                            setTimeout(() => {
                                copyBtn.innerHTML = originalText;
                                copyBtn.classList.remove('btn-success');
                            }, 2000);
                        }).catch(() => {
                            alert('Copied solution: ' + textToCopy);
                        });
                    } else {
                        alert('Solution:\n' + textToCopy);
                    }
                });
            }
        };

        let abortController = new AbortController();
        let isClosed = false;

        const closeModal = () => {
            isClosed = true;
            if (abortController) {
                try { abortController.abort(); } catch (e) {}
            }
            if (document.body.contains(modalRoot)) {
                modalRoot.remove();
            }
            document.removeEventListener('keydown', handleKey);
        };

        const fetchSolution = async () => {
            if (isClosed) return;
            try {
                if (!targetProjectId) {
                    isLoading = false;
                    isError = true;
                    errorMessage = 'Please select an active project to generate AI solutions.';
                    if (!isClosed) renderModal();
                    return;
                }

                const payload = {
                    rule_id: ruleId,
                    title: title,
                    category: category,
                    severity: severity,
                    description: description,
                    recommendation: recommendation,
                    affected_url: affectedUrl,
                    evidence_text: evidenceText
                };

                const res = await apiClient.post(`/api/projects/${targetProjectId}/ai/solve`, payload, { signal: abortController.signal });
                if (isClosed || abortController.signal.aborted) return;

                if (res?.solution) {
                    solution = res.solution;
                    isLoading = false;
                    isError = false;
                } else {
                    isLoading = false;
                    isError = true;
                    errorMessage = res?.message || 'Could not generate solution.';
                }
                if (!isClosed) renderModal();
            } catch (err) {
                if (isClosed || err?.name === 'AbortError' || err?.message === 'canceled' || abortController.signal.aborted) {
                    return;
                }
                console.warn('[SOLVE WITH AI FETCH ERROR]', err);
                isLoading = false;
                isError = true;
                errorMessage = err?.message || 'AI service temporarily unavailable. The detected problem and existing recommendation are still available.';
                if (!isClosed) renderModal();
            }
        };

        renderModal();
        document.body.appendChild(modalRoot);

        if (!solution) {
            fetchSolution();
        }

        // Close on backdrop click or Escape
        const handleBackdrop = (e) => {
            if (e.target === modalRoot) closeModal();
        };
        const handleKey = (e) => {
            if (e.key === 'Escape') closeModal();
        };

        modalRoot.querySelector('#btn-close-solve-modal')?.addEventListener('click', closeModal);
        modalRoot.querySelector('#btn-close-error')?.addEventListener('click', closeModal);
        modalRoot.querySelector('#btn-done-solution')?.addEventListener('click', closeModal);
        modalRoot.addEventListener('click', handleBackdrop);
        document.addEventListener('keydown', handleKey);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
