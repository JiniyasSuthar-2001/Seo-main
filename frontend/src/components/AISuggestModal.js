/**
 * AISuggestModal.js
 * ==================
 * Reusable AI suggestion modal component for Crawl Data SEO issues.
 *
 * Supports task types:
 *   meta_description | meta_title | image_alt | hreflang
 *
 * Usage (from any view):
 *   import { AISuggestModal } from '../components/AISuggestModal.js';
 *   AISuggestModal.show({ projectId, pageUrl, taskType, currentValue, issue });
 *
 * Features:
 *   - Loading state while AI generates
 *   - Success state: suggestion + char count + reason + Copy + Regenerate + Close
 *   - Provider breakdown: expandable "View Provider Responses"
 *   - Error state with retry
 *   - Per-image results table for image_alt task type
 *   - Hreflang issues list for hreflang task type
 */

import { apiClient } from '../services/apiClient.js';
import { projectStore } from '../core/projectStore.js';

const TASK_LABELS = {
    meta_description: 'Meta Description Suggestion',
    meta_title: 'Page Title Suggestion',
    image_alt: 'Image Alt Text Analysis',
    hreflang: 'Hreflang Analysis',
};

const TASK_ICONS = {
    meta_description: '📝',
    meta_title: '🏷️',
    image_alt: '🖼️',
    hreflang: '🌐',
};

const CHAR_TARGETS = {
    meta_description: { min: 120, max: 158, label: '120–158 chars recommended' },
    meta_title: { min: 30, max: 60, label: '30–60 chars recommended' },
    image_alt: { min: 5, max: 100, label: '5–100 chars per image' },
    hreflang: { min: 0, max: 9999, label: '' },
};

export class AISuggestModal {
    /**
     * Show the AI suggest modal.
     * @param {Object} opts
     * @param {string} opts.projectId
     * @param {string} opts.pageUrl
     * @param {string} opts.taskType
     * @param {string} [opts.currentValue]
     * @param {string} [opts.issue]
     */
    static show(opts = {}) {
        const instance = new AISuggestModal(opts);
        instance._mount();
        instance._fetchSuggestion();
    }

    constructor(opts) {
        this.projectId = opts.projectId || projectStore.getSelectedProjectId();
        this.pageUrl = opts.pageUrl || '';
        this.taskType = opts.taskType || 'meta_description';
        this.currentValue = opts.currentValue || '';
        this.issue = opts.issue || '';
        this.result = null;
        this.showProviders = false;
        this._overlay = null;
    }

    _mount() {
        // Remove any existing instance
        const existing = document.getElementById('ai-suggest-modal-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'ai-suggest-modal-overlay';
        overlay.style.cssText = `
            position: fixed; inset: 0; z-index: 99999;
            background: rgba(0,0,0,0.55); backdrop-filter: blur(4px);
            display: flex; align-items: center; justify-content: center;
            padding: 16px; animation: aiModalFadeIn 0.18s ease;
        `;
        overlay.innerHTML = `<style>
            @keyframes aiModalFadeIn { from { opacity:0 } to { opacity:1 } }
            @keyframes aiModalSlideUp { from { opacity:0; transform:translateY(16px) } to { opacity:1; transform:translateY(0) } }
            #ai-suggest-modal-card { animation: aiModalSlideUp 0.22s ease; }
            .ai-provider-badge { display:inline-flex; align-items:center; gap:4px; padding:2px 8px; border-radius:12px; font-size:10px; font-weight:700; background:rgba(59,130,246,0.1); color:#3b82f6; border:1px solid rgba(59,130,246,0.25); }
            .ai-provider-badge.fail { background:rgba(239,68,68,0.1); color:#ef4444; border-color:rgba(239,68,68,0.25); }
            .ai-char-bar { height:4px; border-radius:2px; background:var(--border); overflow:hidden; margin-top:4px; }
            .ai-char-bar-fill { height:100%; border-radius:2px; transition:width 0.3s ease; }
        </style>`;

        const card = document.createElement('div');
        card.id = 'ai-suggest-modal-card';
        card.style.cssText = `
            background: var(--bg-card, #1e293b);
            border: 1px solid var(--border, rgba(255,255,255,0.1));
            border-radius: 16px;
            padding: 28px;
            width: 100%;
            max-width: 620px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 24px 64px rgba(0,0,0,0.45);
        `;
        overlay.appendChild(card);
        document.body.appendChild(overlay);
        this._overlay = overlay;
        this._card = card;

        // Close on overlay click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) this._close();
        });

        this._renderLoading();
    }

    _renderLoading() {
        const label = TASK_LABELS[this.taskType] || 'AI Suggestion';
        const icon = TASK_ICONS[this.taskType] || '✨';
        this._card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:22px;">${icon}</span>
                    <div>
                        <div style="font-size:15px; font-weight:700; color:var(--text-primary);">${label}</div>
                        <div style="font-size:11px; color:var(--text-secondary); margin-top:1px; font-family:monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:380px;" title="${this._escHtml(this.pageUrl)}">${this._escHtml(this._shortenUrl(this.pageUrl))}</div>
                    </div>
                </div>
                <button id="ai-modal-close-btn" style="background:none; border:none; color:var(--text-tertiary); cursor:pointer; font-size:20px; line-height:1; padding:4px;">&times;</button>
            </div>
            <div style="padding:40px 24px; text-align:center; color:var(--text-secondary);">
                <div style="display:inline-block; width:28px; height:28px; border:3px solid var(--primary,#3b82f6); border-top-color:transparent; border-radius:50%; animation:spin 0.8s linear infinite; margin-bottom:12px;"></div>
                <style>@keyframes spin{to{transform:rotate(360deg)}}</style>
                <div style="font-size:13.5px; font-weight:600; color:var(--text-primary); margin-bottom:4px;">Analyzing page data…</div>
                <div style="font-size:12px;">Querying AI providers in parallel</div>
            </div>
        `;
        this._card.querySelector('#ai-modal-close-btn').addEventListener('click', () => this._close());
    }

    _renderError(msg) {
        const label = TASK_LABELS[this.taskType] || 'AI Suggestion';
        const icon = TASK_ICONS[this.taskType] || '✨';
        this._card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:22px;">${icon}</span>
                    <div style="font-size:15px; font-weight:700; color:var(--text-primary);">${label}</div>
                </div>
                <button id="ai-modal-close-btn2" style="background:none; border:none; color:var(--text-tertiary); cursor:pointer; font-size:20px; line-height:1; padding:4px;">&times;</button>
            </div>
            <div style="padding:24px; background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.25); border-radius:10px; margin-bottom:16px;">
                <div style="font-size:13px; font-weight:700; color:#ef4444; margin-bottom:6px;">⚠ Couldn't generate a recommendation</div>
                <div style="font-size:12px; color:var(--text-secondary);">${this._escHtml(msg || 'An error occurred. Please try again.')}</div>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:8px;">
                <button id="ai-modal-retry-btn" class="btn btn-primary btn-sm">Try Again</button>
                <button id="ai-modal-close-btn3" class="btn btn-secondary btn-sm">Close</button>
            </div>
        `;
        this._card.querySelector('#ai-modal-close-btn2').addEventListener('click', () => this._close());
        this._card.querySelector('#ai-modal-close-btn3').addEventListener('click', () => this._close());
        this._card.querySelector('#ai-modal-retry-btn').addEventListener('click', () => {
            this._renderLoading();
            this._fetchSuggestion();
        });
    }

    _renderSuccess(data) {
        const label = TASK_LABELS[this.taskType] || 'AI Suggestion';
        const icon = TASK_ICONS[this.taskType] || '✨';
        const charTarget = CHAR_TARGETS[this.taskType] || {};
        let bodyHtml = '';

        if (this.taskType === 'image_alt') {
            bodyHtml = this._renderImageAltBody(data);
        } else if (this.taskType === 'hreflang') {
            bodyHtml = this._renderHreflangBody(data);
        } else {
            bodyHtml = this._renderTextSuggestionBody(data, charTarget);
        }

        // Provider info bar
        const provUsed = data.provider_used || 'ai';
        const provCount = data.providers_queried || 1;
        const provOk = data.providers_succeeded || 1;

        // Provider responses section
        const provResponses = data.provider_responses || [];
        const provDetailHtml = provResponses.map(pr => `
            <div style="display:flex; align-items:flex-start; gap:10px; padding:10px 0; border-bottom:1px solid var(--border);">
                <span class="ai-provider-badge ${pr.success ? '' : 'fail'}" style="flex-shrink:0; margin-top:2px;">
                    ${pr.success ? '✓' : '✗'} ${this._escHtml(pr.provider)}
                </span>
                <div style="flex:1; min-width:0;">
                    ${pr.success && pr.response ? `
                        ${pr.response.suggestion ? `<div style="font-size:12px; color:var(--text-primary); line-height:1.5;">${this._escHtml(pr.response.suggestion)}</div>` : ''}
                        ${pr.score !== undefined ? `<div style="font-size:10px; color:var(--text-tertiary); margin-top:3px;">Quality score: ${Math.round(pr.score * 100)}%</div>` : ''}
                    ` : `
                        <div style="font-size:12px; color:#ef4444;">${this._escHtml(pr.error || 'No response')}</div>
                    `}
                </div>
            </div>
        `).join('');

        this._card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:22px;">${icon}</span>
                    <div>
                        <div style="font-size:15px; font-weight:700; color:var(--text-primary);">${label}</div>
                        <div style="font-size:11px; color:var(--text-secondary); margin-top:1px; font-family:monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:360px;" title="${this._escHtml(this.pageUrl)}">${this._escHtml(this._shortenUrl(this.pageUrl))}</div>
                    </div>
                </div>
                <button id="ai-modal-close-main" style="background:none; border:none; color:var(--text-tertiary); cursor:pointer; font-size:20px; line-height:1; padding:4px;">&times;</button>
            </div>

            ${bodyHtml}

            <!-- Provider info row -->
            <div style="display:flex; align-items:center; justify-content:space-between; margin-top:14px; padding-top:12px; border-top:1px solid var(--border);">
                <div style="font-size:11px; color:var(--text-tertiary);">
                    <span class="ai-provider-badge" style="margin-right:6px;">${this._escHtml(provUsed)}</span>
                    ${provOk}/${provCount} providers responded
                </div>
                ${provResponses.length > 0 ? `<button id="ai-modal-toggle-providers" style="background:none; border:none; color:var(--primary,#3b82f6); cursor:pointer; font-size:11.5px; font-weight:600; padding:0;">View Provider Responses ▾</button>` : ''}
            </div>

            <!-- Provider breakdown (collapsible) -->
            <div id="ai-provider-detail-section" style="display:none; margin-top:10px; padding-top:8px;">
                ${provDetailHtml}
            </div>

            <!-- Actions -->
            <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
                <button id="ai-modal-regen-btn" class="btn btn-secondary btn-sm" style="display:inline-flex; align-items:center; gap:5px;">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                    Regenerate
                </button>
                <button id="ai-modal-close-btn-footer" class="btn btn-secondary btn-sm">Close</button>
            </div>
        `;

        // Bind close
        this._card.querySelector('#ai-modal-close-main').addEventListener('click', () => this._close());
        this._card.querySelector('#ai-modal-close-btn-footer').addEventListener('click', () => this._close());

        // Bind regenerate
        this._card.querySelector('#ai-modal-regen-btn').addEventListener('click', () => {
            this._renderLoading();
            this._fetchSuggestion();
        });

        // Bind provider toggle
        const provToggle = this._card.querySelector('#ai-modal-toggle-providers');
        if (provToggle) {
            provToggle.addEventListener('click', () => {
                const section = this._card.querySelector('#ai-provider-detail-section');
                if (section) {
                    const showing = section.style.display !== 'none';
                    section.style.display = showing ? 'none' : 'block';
                    provToggle.textContent = showing ? 'View Provider Responses ▾' : 'Hide Provider Responses ▴';
                }
            });
        }

        // Bind copy buttons (text suggestion tasks)
        this._bindCopyButtons(data);
    }

    _renderTextSuggestionBody(data, charTarget) {
        const suggestion = data.suggestion || '';
        const charCount = data.char_count || suggestion.length;
        const reason = data.reason || '';
        const min = charTarget.min || 0;
        const max = charTarget.max || 9999;
        const good = charCount >= min && charCount <= max;
        const fillPct = max > 0 ? Math.min(100, (charCount / max) * 100) : 50;
        const barColor = good ? '#10b981' : charCount < min ? '#f59e0b' : '#ef4444';

        return `
            <div style="background:var(--bg-subtle,rgba(255,255,255,0.04)); border:1px solid var(--border); border-radius:10px; padding:16px; margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <div style="font-size:11px; font-weight:700; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.05em;">AI Suggestion</div>
                    <button data-copy-text="${this._escHtml(suggestion)}" id="ai-copy-suggestion-btn" class="btn btn-secondary btn-sm" style="font-size:11px; padding:3px 10px;">
                        Copy
                    </button>
                </div>
                <div style="font-size:13.5px; line-height:1.6; color:var(--text-primary); font-weight:500;">${this._escHtml(suggestion)}</div>
                <div style="margin-top:8px;">
                    <div style="display:flex; justify-content:space-between; font-size:10.5px; color:${barColor}; font-weight:600;">
                        <span>${charCount} characters</span>
                        <span>${charTarget.label || ''}</span>
                    </div>
                    <div class="ai-char-bar">
                        <div class="ai-char-bar-fill" style="width:${fillPct}%; background:${barColor};"></div>
                    </div>
                </div>
            </div>
            ${reason ? `
                <div style="padding:12px 14px; background:rgba(59,130,246,0.06); border:1px solid rgba(59,130,246,0.15); border-radius:8px; font-size:12px; color:var(--text-secondary); line-height:1.5;">
                    <strong style="color:var(--text-primary);">Why this suggestion:</strong> ${this._escHtml(reason)}
                </div>
            ` : ''}
        `;
    }

    _renderImageAltBody(data) {
        const images = data.images || [];
        if (!images.length) {
            return `<div style="padding:20px; text-align:center; color:var(--text-secondary);">No image data found for this page.</div>`;
        }
        const rows = images.map((img, i) => {
            const suggestion = img.suggestion || '';
            const charCount = img.char_count || suggestion.length;
            const verdict = img.verdict || (img.existing_alt ? 'appropriate' : 'missing');
            const verdictColor = verdict === 'appropriate' ? '#10b981' : verdict === 'missing' ? '#ef4444' : '#f59e0b';
            const verdictLabel = verdict === 'appropriate' ? '✓ Good' : verdict === 'missing' ? '✗ Missing' : '⚠ Improve';
            const filename = (img.src || '').split('/').pop().split('?')[0] || 'image';
            return `
                <div style="border:1px solid var(--border); border-radius:8px; padding:12px; margin-bottom:10px;">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
                        <div style="font-size:11.5px; font-weight:600; color:var(--text-primary); font-family:monospace;">${this._escHtml(filename)}</div>
                        <span style="font-size:10px; font-weight:700; color:${verdictColor}; padding:2px 7px; border-radius:10px; border:1px solid ${verdictColor}33;">${verdictLabel}</span>
                    </div>
                    ${img.existing_alt ? `<div style="font-size:11px; color:var(--text-secondary); margin-bottom:6px;"><span style="font-weight:600; color:var(--text-primary);">Current:</span> ${this._escHtml(img.existing_alt)}</div>` : ''}
                    ${verdict !== 'appropriate' && suggestion ? `
                        <div style="font-size:12px; color:var(--text-primary); background:var(--bg-subtle); border-radius:6px; padding:8px; margin-bottom:6px;">
                            <strong>Suggested:</strong> ${this._escHtml(suggestion)}
                            <span style="font-size:10px; color:var(--text-tertiary); margin-left:8px;">${charCount} chars</span>
                        </div>
                        <button data-copy-text="${this._escHtml(suggestion)}" class="ai-copy-img-btn btn btn-secondary btn-sm" style="font-size:10px; padding:2px 8px;">Copy</button>
                    ` : verdict === 'appropriate' ? `
                        <div style="font-size:12px; color:#10b981;">✓ Current alt text is appropriate. No change needed.</div>
                    ` : ''}
                    ${img.reason ? `<div style="font-size:11px; color:var(--text-secondary); margin-top:6px; font-style:italic;">${this._escHtml(img.reason)}</div>` : ''}
                </div>
            `;
        }).join('');
        return `<div style="max-height:380px; overflow-y:auto;">${rows}</div>`;
    }

    _renderHreflangBody(data) {
        const issues = data.issues || [];
        const summary = data.summary || '';
        if (!issues.length && !summary) {
            return `<div style="padding:20px; text-align:center; color:#10b981; font-weight:600;">✓ Hreflang configuration appears correct.</div>`;
        }
        const issueRows = issues.map(iss => `
            <div style="padding:10px 12px; border:1px solid rgba(239,68,68,0.2); border-radius:8px; margin-bottom:8px; background:rgba(239,68,68,0.05);">
                <div style="font-size:12.5px; font-weight:600; color:var(--text-primary); margin-bottom:4px;">⚠ ${this._escHtml(iss.issue || '')}</div>
                ${iss.recommendation ? `<div style="font-size:11.5px; color:var(--text-secondary); line-height:1.5;">${this._escHtml(iss.recommendation)}</div>` : ''}
            </div>
        `).join('');
        return `
            ${summary ? `<div style="font-size:13px; color:var(--text-primary); line-height:1.6; margin-bottom:12px; padding:12px; background:var(--bg-subtle); border-radius:8px;">${this._escHtml(summary)}</div>` : ''}
            ${issueRows}
            <div style="font-size:11px; color:var(--text-tertiary); margin-top:8px;">
                Valid entries: ${data.valid_entries || 0} · Problematic: ${data.problematic_entries || 0}
            </div>
        `;
    }

    _bindCopyButtons(data) {
        // Main copy button (text tasks)
        const mainCopy = this._card.querySelector('#ai-copy-suggestion-btn');
        if (mainCopy) {
            mainCopy.addEventListener('click', () => {
                const text = mainCopy.getAttribute('data-copy-text') || data.suggestion || '';
                this._copyToClipboard(text, mainCopy);
            });
        }

        // Per-image copy buttons
        this._card.querySelectorAll('.ai-copy-img-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.getAttribute('data-copy-text') || '';
                this._copyToClipboard(text, btn);
            });
        });
    }

    _copyToClipboard(text, btn) {
        navigator.clipboard.writeText(text).then(() => {
            const orig = btn.textContent;
            btn.textContent = 'Copied!';
            btn.style.color = '#10b981';
            setTimeout(() => {
                btn.textContent = orig;
                btn.style.color = '';
            }, 2000);
        }).catch(() => {
            // Fallback for older browsers
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.top = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            const orig = btn.textContent;
            btn.textContent = 'Copied!';
            setTimeout(() => { btn.textContent = orig; }, 2000);
        });
    }

    async _fetchSuggestion() {
        try {
            const data = await apiClient.post('/api/ai/crawl-suggest', {
                project_id: this.projectId,
                page_url: this.pageUrl,
                task_type: this.taskType,
                current_value: this.currentValue || undefined,
                issue: this.issue || undefined,
            });
            this.result = data;
            this._renderSuccess(data);
        } catch (err) {
            const msg = err?.detail || err?.message || 'Suggestion generation failed.';
            this._renderError(msg);
        }
    }

    _close() {
        if (this._overlay) {
            this._overlay.style.opacity = '0';
            this._overlay.style.transition = 'opacity 0.15s';
            setTimeout(() => this._overlay && this._overlay.remove(), 160);
            this._overlay = null;
        }
    }

    _escHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    _shortenUrl(url) {
        if (!url) return '';
        try {
            const u = new URL(url);
            const path = u.pathname.length > 40 ? '…' + u.pathname.slice(-38) : u.pathname;
            return u.hostname + path;
        } catch {
            return url.length > 55 ? url.slice(0, 52) + '…' : url;
        }
    }
}
