import { crawlService } from '../services/crawlService.js';
import { crawlProgressOverlay } from './CrawlProgressOverlay.js';
import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { COUNTRY_DATASET, findCountry, detectUserDefaultCountry } from '../constants/countries.js';

class CrawlConfigModalManager {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 7;
        this.projectId = null;
        this.targetUrl = '';
        this.modalElement = null;
        this.saveTimeout = null;
        this.countrySearchQuery = '';
        
        // Default Crawl Config State
        this.config = {
            scope_type: 'entire_domain',
            custom_path: '',
            max_pages: 5000,
            max_depth: 3,
            request_timeout: 20.0,
            crawl_delay_ms: 500,
            respect_robots_txt: true,
            discover_sitemap: true,
            custom_sitemap_url: '',
            discover_internal_links: true,
            user_agent: 'SEO-Intelligence-Bot/1.0 (Mozilla/5.0 Compatible)',
            follow_redirects: true,
            include_patterns: [],
            exclude_patterns: ['/admin/*', '/login/*', '/cart/*'],
            target_countries: [],
            ignore_tracking_parameters: true,
            audit_modules: {
                technical_http: true,
                metadata: true,
                headings: true,
                images: true,
                links: true,
                canonicals_robots: true
            },
            performance_analysis: {
                available: false,
                reason: "Core Web Vitals and Lighthouse performance analysis are currently unavailable for this crawl run."
            }
        };
    }

    async open(projectId, targetUrl) {
        this.projectId = projectId || projectStore.getSelectedProjectId();
        const selectedProj = projectStore.getSelectedProject();
        this.targetUrl = targetUrl || (selectedProj ? selectedProj.domain || selectedProj.url : '') || 'https://example.com';
        this.currentStep = 1;
        this.countrySearchQuery = '';

        this.renderModalShell();
        await this.loadRemoteConfig();
        this.renderStepContent();
    }

    async loadRemoteConfig() {
        if (!this.projectId) return;
        try {
            this.setSaveStatus('Loading...', 'info');
            const data = await apiClient.get(`/api/projects/${this.projectId}/crawl-config`);
            if (data && data.config) {
                const remote = data.config;
                this.config = {
                    ...this.config,
                    ...remote,
                    target_countries: Array.isArray(remote.target_countries) ? remote.target_countries : [],
                    audit_modules: {
                        ...this.config.audit_modules,
                        ...(remote.audit_modules || {})
                    }
                };
            }
            this.setSaveStatus('✓ Saved', 'success', 1500);
        } catch (err) {
            console.warn("[CRAWL CONFIG] Using local defaults:", err);
            this.setSaveStatus('Local settings', 'info', 1500);
        }
    }

    renderModalShell() {
        if (this.modalElement) {
            this.modalElement.remove();
        }

        const backdrop = document.createElement('div');
        backdrop.id = 'crawl-config-modal-backdrop';
        backdrop.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(6px);
            display: flex; align-items: center; justify-content: center; z-index: 99999; padding: 16px;
            font-family: 'Inter', system-ui, -apple-system, sans-serif; animation: fadeIn 0.15s ease-out;
        `;

        backdrop.innerHTML = `
            <style>
                @keyframes fadeIn { from { opacity: 0; transform: scale(0.99); } to { opacity: 1; transform: scale(1); } }
                .wizard-step-pill {
                    padding: 5px 11px; border-radius: 16px; font-size: 11px; font-weight: 600;
                    color: var(--text-tertiary, #94a3b8); background: var(--bg-subtle, #1e293b); transition: all 0.15s ease;
                    display: flex; align-items: center; gap: 4px; cursor: pointer; border: 1px solid transparent; white-space: nowrap;
                }
                .wizard-step-pill.active {
                    color: #fff; background: #2563eb; border-color: #3b82f6; box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
                }
                .wizard-step-pill.completed {
                    color: #10b981; background: rgba(16, 185, 129, 0.12); border-color: rgba(16, 185, 129, 0.3);
                }
                .option-radio-card {
                    padding: 12px 16px; border: 1.5px solid var(--border, #334155); border-radius: 10px;
                    background: var(--bg-card, #0f172a); cursor: pointer; transition: all 0.15s ease; margin-bottom: 10px;
                }
                .option-radio-card:hover {
                    border-color: #3b82f6; background: rgba(37, 99, 235, 0.04);
                }
                .option-radio-card.selected {
                    border-color: #2563eb; background: rgba(37, 99, 235, 0.08); box-shadow: 0 0 0 1px #2563eb;
                }
                .depth-pill-btn {
                    flex: 1; padding: 7px 10px; border: 1.5px solid var(--border, #334155); border-radius: 8px;
                    background: var(--bg-workspace, #1e293b); color: var(--text-primary, #f8fafc); font-size: 12px; font-weight: 700;
                    cursor: pointer; transition: all 0.15s ease; text-align: center;
                }
                .depth-pill-btn:hover {
                    border-color: #3b82f6; background: rgba(37, 99, 235, 0.1);
                }
                .depth-pill-btn.active {
                    background: #2563eb; border-color: #3b82f6; color: #ffffff; box-shadow: 0 3px 8px rgba(37, 99, 235, 0.35);
                }
                .audit-module-toggle-card {
                    display: flex; align-items: center; justify-content: space-between; padding: 12px 14px;
                    border: 1.5px solid var(--border, #334155); border-radius: 10px; background: var(--bg-workspace, #0f172a);
                    cursor: pointer; transition: all 0.15s ease;
                }
                .audit-module-toggle-card:hover {
                    border-color: #3b82f6; background: rgba(37, 99, 235, 0.04);
                }
                .audit-module-toggle-card.active {
                    border-color: rgba(16, 185, 129, 0.5); background: rgba(16, 185, 129, 0.06);
                }
                .rule-tag {
                    display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px;
                    border-radius: 6px; background: var(--bg-subtle, #1e293b); border: 1px solid var(--border, #334155);
                    font-size: 11.5px; font-family: monospace; margin: 3px;
                }
            </style>

            <!-- MANDATORY CONSISTENT MODAL SIZE: 680px WIDTH × 600px HEIGHT FIXED DIMENSIONS -->
            <div class="card" style="width: 680px; max-width: 92vw; height: 600px; max-height: 88vh; background: var(--bg-card, #0f172a); border-radius: 14px; box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.5); overflow: hidden; display: flex; flex-direction: column; border: 1px solid var(--border, #334155);">
                
                <!-- FIXED MODAL HEADER -->
                <div style="flex-shrink: 0; padding: 18px 24px 12px; border-bottom: 1px solid var(--border, #334155); background: var(--bg-card, #0f172a);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <h2 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text-primary, #f8fafc);">SEO Crawl Settings</h2>
                            <span class="badge badge-primary" style="font-size: 10px; font-weight: 700; padding: 2px 8px;">${this.escapeHtml(this.targetUrl)}</span>
                            <span id="config-save-status" style="font-size: 11.5px; font-weight: 600;"></span>
                        </div>
                        <button type="button" id="btn-close-config-modal" style="background: none; border: none; font-size: 22px; color: var(--text-secondary, #94a3b8); cursor: pointer; padding: 0 4px; line-height: 1;">&times;</button>
                    </div>

                    <!-- WIZARD STEP PILLS (7 STEPS) -->
                    <div id="wizard-pills-container" style="display: flex; gap: 6px; overflow-x: auto; padding-bottom: 2px;">
                        <button type="button" class="wizard-step-pill active" data-step="1">① Scope</button>
                        <button type="button" class="wizard-step-pill" data-step="2">② Limits & Depth</button>
                        <button type="button" class="wizard-step-pill" data-step="3">③ Discovery</button>
                        <button type="button" class="wizard-step-pill" data-step="4">④ Country Targeting</button>
                        <button type="button" class="wizard-step-pill" data-step="5">⑤ Behavior</button>
                        <button type="button" class="wizard-step-pill" data-step="6">⑥ Audit Modules</button>
                        <button type="button" class="wizard-step-pill" data-step="7">⑦ Review</button>
                    </div>
                </div>

                <!-- SCROLLABLE STEP CONTENT CONTAINER -->
                <div id="modal-step-body" style="flex: 1; padding: 22px 28px; overflow-y: auto;"></div>

                <!-- FIXED MODAL FOOTER -->
                <div style="flex-shrink: 0; padding: 14px 24px; border-top: 1px solid var(--border, #334155); background: var(--bg-subtle, #1e293b); display: flex; justify-content: space-between; align-items: center;">
                    <button type="button" id="btn-reset-defaults" style="background: none; border: none; font-size: 12px; color: var(--text-secondary, #94a3b8); cursor: pointer; text-decoration: underline;">Reset Defaults</button>
                    
                    <div style="display: flex; gap: 10px;" id="modal-footer-buttons"></div>
                </div>

            </div>
        `;

        document.body.appendChild(backdrop);
        this.modalElement = backdrop;

        this.modalElement.querySelector('#btn-close-config-modal')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.close();
        });

        this.modalElement.querySelector('#btn-reset-defaults')?.addEventListener('click', async (e) => {
            e.preventDefault();
            await this.resetToDefaults();
        });

        this.modalElement.querySelectorAll('.wizard-step-pill').forEach(pill => {
            pill.addEventListener('click', (e) => {
                e.preventDefault();
                const targetStep = parseInt(e.currentTarget.getAttribute('data-step'), 10);
                if (targetStep && targetStep !== this.currentStep) {
                    this.currentStep = targetStep;
                    this.renderStepContent();
                }
            });
        });
    }

    renderStepContent() {
        if (!this.modalElement) return;

        const bodyContainer = this.modalElement.querySelector('#modal-step-body');
        const footerButtons = this.modalElement.querySelector('#modal-footer-buttons');

        this.modalElement.querySelectorAll('.wizard-step-pill').forEach(pill => {
            const stepNum = parseInt(pill.getAttribute('data-step'), 10);
            pill.classList.remove('active', 'completed');
            if (stepNum === this.currentStep) {
                pill.classList.add('active');
            } else if (stepNum < this.currentStep) {
                pill.classList.add('completed');
            }
        });

        if (footerButtons) {
            footerButtons.innerHTML = `
                ${this.currentStep > 1 ? `
                    <button type="button" id="btn-wizard-back" class="btn btn-secondary btn-sm" style="padding: 8px 16px;">← Back</button>
                ` : ''}
                ${this.currentStep < this.totalSteps ? `
                    <button type="button" id="btn-wizard-next" class="btn btn-primary btn-sm" style="padding: 8px 18px;">Continue →</button>
                ` : `
                    <button type="button" id="btn-wizard-start" class="btn btn-primary btn-sm" style="background: #2563eb; padding: 8px 20px; font-weight: 700;">
                        <span>Start Real Crawl</span>
                    </button>
                `}
            `;

            footerButtons.querySelector('#btn-wizard-back')?.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.currentStep > 1) {
                    this.currentStep--;
                    this.renderStepContent();
                }
            });

            footerButtons.querySelector('#btn-wizard-next')?.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.currentStep < this.totalSteps) {
                    this.currentStep++;
                    this.renderStepContent();
                }
            });

            footerButtons.querySelector('#btn-wizard-start')?.addEventListener('click', async (e) => {
                e.preventDefault();
                const btnStart = e.currentTarget;
                btnStart.disabled = true;
                btnStart.innerText = 'Launching...';
                await this.executeCrawl();
            });
        }

        if (!bodyContainer) return;

        switch (this.currentStep) {
            case 1:
                bodyContainer.innerHTML = `
                    <div style="margin-bottom: 16px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 4px 0; color: var(--text-primary, #f8fafc);">Where should we crawl?</h3>
                        <p style="font-size: 12.5px; color: var(--text-secondary, #94a3b8); margin: 0;">Define boundary limit for this crawl run. Scope boundary operates independently of depth level.</p>
                    </div>

                    <div class="option-radio-card ${this.config.scope_type === 'entire_domain' ? 'selected' : ''}" data-scope="entire_domain">
                        <div style="display: flex; align-items: flex-start; gap: 10px;">
                            <input type="radio" name="scope_radio" value="entire_domain" ${this.config.scope_type === 'entire_domain' ? 'checked' : ''} style="margin-top: 2px;"/>
                            <div>
                                <strong style="font-size: 13.5px; color: var(--text-primary, #f8fafc); display: block;">Entire Website Domain</strong>
                                <span style="font-size: 12px; color: var(--text-secondary, #94a3b8);">Crawl all HTML pages discovered across ${this.escapeHtml(this.targetUrl)}</span>
                            </div>
                        </div>
                    </div>

                    <div class="option-radio-card ${this.config.scope_type === 'specific_path' ? 'selected' : ''}" data-scope="specific_path">
                        <div style="display: flex; align-items: flex-start; gap: 10px;">
                            <input type="radio" name="scope_radio" value="specific_path" ${this.config.scope_type === 'specific_path' ? 'checked' : ''} style="margin-top: 2px;"/>
                            <div style="flex: 1;">
                                <strong style="font-size: 13.5px; color: var(--text-primary, #f8fafc); display: block;">Specific Subfolder Only</strong>
                                <span style="font-size: 12px; color: var(--text-secondary, #94a3b8);">Restrict boundary strictly to URLs matching a specific folder path (e.g. /services/)</span>
                            </div>
                        </div>
                        <div id="custom-path-input-wrap" style="margin-top: 10px; padding-left: 24px; ${this.config.scope_type === 'specific_path' ? '' : 'display: none;'}">
                            <input type="text" id="input-custom-path" value="${this.escapeHtml(this.config.custom_path)}" placeholder="/services/" style="width: 100%; padding: 7px 10px; font-size: 12px; border: 1px solid var(--border, #334155); border-radius: 6px; background: var(--bg-workspace, #1e293b); color: var(--text-primary, #f8fafc); font-family: monospace;"/>
                        </div>
                    </div>

                    <div class="option-radio-card ${this.config.scope_type === 'subdomain' ? 'selected' : ''}" data-scope="subdomain">
                        <div style="display: flex; align-items: flex-start; gap: 10px;">
                            <input type="radio" name="scope_radio" value="subdomain" ${this.config.scope_type === 'subdomain' ? 'checked' : ''} style="margin-top: 2px;"/>
                            <div>
                                <strong style="font-size: 13.5px; color: var(--text-primary, #f8fafc); display: block;">Exact Host Subdomain Only</strong>
                                <span style="font-size: 12px; color: var(--text-secondary, #94a3b8);">Strictly crawl pages belonging to the exact subdomain host</span>
                            </div>
                        </div>
                    </div>
                `;

                bodyContainer.querySelectorAll('.option-radio-card').forEach(card => {
                    card.addEventListener('click', (e) => {
                        e.preventDefault();
                        const val = card.getAttribute('data-scope');
                        if (val && this.config.scope_type !== val) {
                            const oldScope = this.config.scope_type;
                            this.config.scope_type = val;

                            bodyContainer.querySelectorAll('.option-radio-card').forEach(c => c.classList.remove('selected'));
                            card.classList.add('selected');
                            const radio = card.querySelector('input[type="radio"]');
                            if (radio) radio.checked = true;

                            const pathWrap = bodyContainer.querySelector('#custom-path-input-wrap');
                            if (pathWrap) pathWrap.style.display = val === 'specific_path' ? 'block' : 'none';

                            this.persistControlChange({ scope_type: val }, () => {
                                this.config.scope_type = oldScope;
                                this.renderStepContent();
                            });
                        }
                    });
                });

                bodyContainer.querySelector('#input-custom-path')?.addEventListener('input', (e) => {
                    const newPath = e.target.value.trim();
                    const oldPath = this.config.custom_path;
                    this.config.custom_path = newPath;
                    this.debouncePersist({ custom_path: newPath }, () => {
                        this.config.custom_path = oldPath;
                    });
                });
                break;

            case 2:
                bodyContainer.innerHTML = `
                    <div style="margin-bottom: 16px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 4px 0; color: var(--text-primary, #f8fafc);">Max Crawl Depth & Page Limits</h3>
                        <p style="font-size: 12.5px; color: var(--text-secondary, #94a3b8); margin: 0;">Configure link level depth ceilings and maximum page limits.</p>
                    </div>

                    <div style="margin-bottom: 20px; background: var(--bg-card, #0f172a); border: 1px solid var(--border, #334155); padding: 16px 18px; border-radius: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <label style="font-size: 13px; font-weight: 700; color: var(--text-primary, #f8fafc);">Max Crawl Depth Level</label>
                            <span id="depth-pill-active-badge" class="badge badge-primary" style="font-size: 10.5px; font-weight: 700;">Level ${this.config.max_depth === 0 ? 'Unlimited' : this.config.max_depth}</span>
                        </div>

                        <div style="display: flex; gap: 8px; margin-bottom: 12px;" id="depth-selector-pills">
                            <button type="button" class="depth-pill-btn ${this.config.max_depth === 1 ? 'active' : ''}" data-depth="1">1</button>
                            <button type="button" class="depth-pill-btn ${this.config.max_depth === 2 ? 'active' : ''}" data-depth="2">2</button>
                            <button type="button" class="depth-pill-btn ${this.config.max_depth === 3 ? 'active' : ''}" data-depth="3">3</button>
                            <button type="button" class="depth-pill-btn ${this.config.max_depth === 5 ? 'active' : ''}" data-depth="5">5</button>
                            <button type="button" class="depth-pill-btn ${this.config.max_depth === 10 ? 'active' : ''}" data-depth="10">10</button>
                            <button type="button" class="depth-pill-btn ${this.config.max_depth === 0 ? 'active' : ''}" data-depth="0">Unlimited</button>
                        </div>

                        <div id="depth-explanation-box" style="padding: 10px 12px; background: var(--bg-workspace, #1e293b); border-radius: 8px; border: 1px solid var(--border, #334155); font-size: 12px; color: var(--text-secondary, #94a3b8);">
                            ${this.getDepthExplanationHTML(this.config.max_depth)}
                        </div>
                    </div>

                    <div style="margin-bottom: 18px; background: var(--bg-card, #0f172a); border: 1px solid var(--border, #334155); padding: 16px 18px; border-radius: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <label style="font-size: 13px; font-weight: 700; color: var(--text-primary, #f8fafc);">Maximum Pages Ceiling</label>
                            <span style="font-size: 13.5px; font-weight: 800; color: #3b82f6; font-family: monospace;" id="val-max-pages">
                                ${this.formatMaxPagesLabel(this.config.max_pages)}
                            </span>
                        </div>
                        
                        <input type="range" id="range-max-pages" min="100" max="5001" step="100" value="${this.getMaxPagesSliderValue(this.config.max_pages)}" style="width: 100%; accent-color: #2563eb; cursor: pointer; height: 5px; margin-bottom: 10px;"/>

                        <div style="display: flex; gap: 6px; margin-bottom: 6px;" id="pages-quick-pills">
                            <button type="button" class="depth-pill-btn ${this.config.max_pages === 500 ? 'active' : ''}" data-pages="500">500</button>
                            <button type="button" class="depth-pill-btn ${this.config.max_pages === 1000 ? 'active' : ''}" data-pages="1000">1,000</button>
                            <button type="button" class="depth-pill-btn ${this.config.max_pages === 2500 ? 'active' : ''}" data-pages="2500">2,500</button>
                            <button type="button" class="depth-pill-btn ${this.config.max_pages === 5000 ? 'active' : ''}" data-pages="5000">5,000</button>
                            <button type="button" class="depth-pill-btn ${this.is5000PlusMode(this.config.max_pages) ? 'active' : ''}" data-pages="5000+">5000+</button>
                        </div>

                        <div id="max-pages-info-note" style="font-size: 11.5px; color: #60a5fa; line-height: 1.4; display: ${this.is5000PlusMode(this.config.max_pages) ? 'block' : 'none'};">
                            ⚡ <strong>Large-Site Mode (5000+):</strong> Crawler will continue scanning until all eligible URLs within the configured crawl scope are exhausted.
                        </div>
                    </div>
                `;

                bodyContainer.querySelectorAll('.depth-pill-btn[data-depth]').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.preventDefault();
                        const depthVal = parseInt(btn.getAttribute('data-depth'), 10);
                        if (this.config.max_depth !== depthVal) {
                            const oldVal = this.config.max_depth;
                            this.config.max_depth = depthVal;

                            bodyContainer.querySelectorAll('.depth-pill-btn[data-depth]').forEach(b => b.classList.remove('active'));
                            btn.classList.add('active');

                            const badge = bodyContainer.querySelector('#depth-pill-active-badge');
                            if (badge) badge.innerText = `Level ${depthVal === 0 ? 'Unlimited' : depthVal}`;

                            const expBox = bodyContainer.querySelector('#depth-explanation-box');
                            if (expBox) expBox.innerHTML = this.getDepthExplanationHTML(depthVal);

                            this.persistControlChange({ max_depth: depthVal }, () => {
                                this.config.max_depth = oldVal;
                                this.renderStepContent();
                            });
                        }
                    });
                });

                const rangePages = bodyContainer.querySelector('#range-max-pages');
                const valEl = bodyContainer.querySelector('#val-max-pages');
                const infoNoteEl = bodyContainer.querySelector('#max-pages-info-note');

                const updatePagesUI = (valStr) => {
                    const isPlus = (valStr === '5000+' || parseInt(valStr, 10) >= 5001);
                    const finalVal = isPlus ? '5000+' : parseInt(valStr, 10);
                    const oldVal = this.config.max_pages;
                    this.config.max_pages = finalVal;

                    if (valEl) valEl.innerText = this.formatMaxPagesLabel(finalVal);
                    if (infoNoteEl) infoNoteEl.style.display = isPlus ? 'block' : 'none';
                    if (rangePages) rangePages.value = isPlus ? 5001 : finalVal;

                    bodyContainer.querySelectorAll('#pages-quick-pills .depth-pill-btn').forEach(pill => {
                        const target = pill.getAttribute('data-pages');
                        if ((target === '5000+' && isPlus) || (parseInt(target, 10) === finalVal)) {
                            pill.classList.add('active');
                        } else {
                            pill.classList.remove('active');
                        }
                    });

                    this.debouncePersist({ max_pages: finalVal }, () => {
                        this.config.max_pages = oldVal;
                    });
                };

                if (rangePages) {
                    rangePages.addEventListener('input', (e) => {
                        updatePagesUI(e.target.value);
                    });
                }

                bodyContainer.querySelectorAll('#pages-quick-pills .depth-pill-btn').forEach(pill => {
                    pill.addEventListener('click', (e) => {
                        e.preventDefault();
                        const pVal = pill.getAttribute('data-pages');
                        updatePagesUI(pVal);
                    });
                });
                break;

            case 3:
                bodyContainer.innerHTML = `
                    <div style="margin-bottom: 16px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 4px 0; color: var(--text-primary, #f8fafc);">Discovery & Robots Compliance</h3>
                        <p style="font-size: 12.5px; color: var(--text-secondary, #94a3b8); margin: 0;">Configure discovery channels and robots.txt compliance rules.</p>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px;">
                        <label style="display: flex; align-items: flex-start; gap: 12px; padding: 14px; border: 1.5px solid var(--border, #334155); border-radius: 10px; background: var(--bg-workspace, #1e293b); cursor: pointer;">
                            <input type="checkbox" id="chk-internal-links" ${this.config.discover_internal_links ? 'checked' : ''} style="margin-top: 2px; accent-color: #2563eb;"/>
                            <div>
                                <strong style="font-size: 13px; color: var(--text-primary, #f8fafc); display: block;">Internal Link Discovery</strong>
                                <span style="font-size: 12px; color: var(--text-secondary, #94a3b8);">Discover HTML pages by following internal href links.</span>
                            </div>
                        </label>

                        <label style="display: flex; align-items: flex-start; gap: 12px; padding: 14px; border: 1.5px solid var(--border, #334155); border-radius: 10px; background: var(--bg-workspace, #1e293b); cursor: pointer;">
                            <input type="checkbox" id="chk-sitemap" ${this.config.discover_sitemap ? 'checked' : ''} style="margin-top: 2px; accent-color: #2563eb;"/>
                            <div>
                                <strong style="font-size: 13px; color: var(--text-primary, #f8fafc); display: block;">Inspect XML Sitemap (/sitemap.xml)</strong>
                                <span style="font-size: 12px; color: var(--text-secondary, #94a3b8);">Fetch and parse sitemap.xml to populate crawl queue.</span>
                            </div>
                        </label>

                        <div style="padding: 14px; border: 1.5px solid var(--border, #334155); border-radius: 10px; background: var(--bg-workspace, #1e293b);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong style="font-size: 13px; color: var(--text-primary, #f8fafc); display: block;">Respect robots.txt Directives</strong>
                                    <span style="font-size: 12px; color: var(--text-secondary, #94a3b8);">Follow Disallow rules declared in robots.txt</span>
                                </div>
                                <input type="checkbox" id="chk-respect-robots" ${this.config.respect_robots_txt ? 'checked' : ''} style="accent-color: #2563eb;"/>
                            </div>
                        </div>
                    </div>
                `;

                const chkInternal = bodyContainer.querySelector('#chk-internal-links');
                if (chkInternal) {
                    chkInternal.addEventListener('change', (e) => {
                        const val = e.target.checked;
                        const oldVal = !val;
                        this.config.discover_internal_links = val;
                        this.persistControlChange({ discover_internal_links: val }, () => {
                            this.config.discover_internal_links = oldVal;
                            chkInternal.checked = oldVal;
                        });
                    });
                }

                const chkSitemap = bodyContainer.querySelector('#chk-sitemap');
                if (chkSitemap) {
                    chkSitemap.addEventListener('change', (e) => {
                        const val = e.target.checked;
                        const oldVal = !val;
                        this.config.discover_sitemap = val;
                        this.persistControlChange({ discover_sitemap: val }, () => {
                            this.config.discover_sitemap = oldVal;
                            chkSitemap.checked = oldVal;
                        });
                    });
                }

                const chkRobots = bodyContainer.querySelector('#chk-respect-robots');
                if (chkRobots) {
                    chkRobots.addEventListener('change', (e) => {
                        const val = e.target.checked;
                        const oldVal = !val;
                        this.config.respect_robots_txt = val;
                        this.persistControlChange({ respect_robots_txt: val }, () => {
                            this.config.respect_robots_txt = oldVal;
                            chkRobots.checked = oldVal;
                        });
                    });
                }
                break;

            case 4:
                // STEP 4: COUNTRY TARGETING
                const selectedProj = projectStore.getSelectedProject();
                const defaultDetected = detectUserDefaultCountry(selectedProj?.target_country);
                const selectedCountries = Array.isArray(this.config.target_countries) ? this.config.target_countries : [];
                const selectedCount = selectedCountries.length;
                const isLimitReached = selectedCount >= 5;

                const q = (this.countrySearchQuery || '').trim().toLowerCase().replace(/^\+/, '');
                const filteredCountries = COUNTRY_DATASET.filter(c => {
                    if (!q) return true;
                    const cleanDial = c.dialCode.replace(/^\+/, '').toLowerCase();
                    return c.name.toLowerCase().includes(q) ||
                           cleanDial.includes(q) ||
                           c.code.toLowerCase() === q;
                });

                bodyContainer.innerHTML = `
                    <div style="margin-bottom: 14px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 4px;">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary, #f8fafc);">Country Targeting</h3>
                            <span class="badge ${isLimitReached ? 'badge-warning' : 'badge-primary'}" id="country-counter-badge" style="font-size: 11px; font-weight: 700; padding: 4px 10px;">
                                ${selectedCount} / 5 countries selected
                            </span>
                        </div>
                        <p style="font-size: 12.5px; color: var(--text-secondary, #94a3b8); margin: 0;">
                            Select up to 5 target countries to consider when collecting and analyzing location-specific SEO information.
                        </p>
                    </div>

                    ${isLimitReached ? `
                        <div style="padding: 8px 12px; background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; font-size: 12px; color: var(--warning, #f59e0b); font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
                            <span>⚠️ Maximum of 5 countries selected. Deselect a country to choose another.</span>
                        </div>
                    ` : ''}

                    <!-- DEFAULT COUNTRY INDICATOR WHEN NO MANUAL SELECTION EXISTS -->
                    ${selectedCount === 0 ? `
                        <div style="padding: 10px 14px; background: var(--bg-workspace, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; margin-bottom: 12px; font-size: 12px;">
                            <div style="font-weight: 700; color: var(--text-tertiary, #94a3b8); text-transform: uppercase; font-size: 10px; margin-bottom: 2px;">Default Target Location</div>
                            ${defaultDetected ? `
                                <div style="color: var(--text-primary, #f8fafc); font-weight: 600;">
                                    Using your current country: <span style="color: var(--primary, #3b82f6);">${this.escapeHtml(defaultDetected.name)} (${this.escapeHtml(defaultDetected.dialCode)})</span>
                                </div>
                            ` : `
                                <div style="color: var(--text-secondary, #94a3b8);">
                                    No country selected — using global/default targeting.
                                </div>
                            `}
                        </div>
                    ` : ''}

                    <!-- SELECTED COUNTRY TAG CHIPS WITH REMOVE BUTTON -->
                    ${selectedCount > 0 ? `
                        <div style="margin-bottom: 12px;" id="selected-country-chips-wrap">
                            <div style="font-size: 10.5px; font-weight: 700; color: var(--text-tertiary, #94a3b8); text-transform: uppercase; margin-bottom: 4px;">ACTIVE TARGET COUNTRIES</div>
                            ${selectedCountries.map(code => {
                                const item = findCountry(code);
                                if (!item) return '';
                                return `
                                    <span class="rule-tag" style="background: rgba(37, 99, 235, 0.15); border-color: rgba(37, 99, 235, 0.4); color: var(--text-primary, #f8fafc); font-size: 12px; font-weight: 600; padding: 4px 10px; margin: 2px; display: inline-flex; align-items: center; gap: 6px;">
                                        <span>${this.escapeHtml(item.name)} (${this.escapeHtml(item.dialCode)})</span>
                                        <button type="button" class="btn-remove-country-chip" data-code="${item.code}" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 14px; font-weight: 800; line-height: 1; padding: 0 2px;">&times;</button>
                                    </span>
                                `;
                            }).join('')}
                        </div>
                    ` : ''}

                    <!-- SEARCH FIELD -->
                    <div style="margin-bottom: 10px;">
                        <input type="text" id="input-country-search" value="${this.escapeHtml(this.countrySearchQuery)}" placeholder="Search countries by name or calling code (e.g. India, +91, 91)..."
                               style="width: 100%; padding: 8px 12px; font-size: 12.5px; border: 1.5px solid var(--border, #334155); border-radius: 8px; background: var(--bg-workspace, #1e293b); color: var(--text-primary, #f8fafc); outline: none; transition: border-color 0.15s ease;"/>
                    </div>

                    <!-- SCROLLABLE COUNTRY SELECTION LIST -->
                    <div style="max-height: 190px; overflow-y: auto; border: 1.5px solid var(--border, #334155); border-radius: 8px; background: var(--bg-card, #0f172a);" id="country-list-scroll-box">
                        ${filteredCountries.length > 0 ? filteredCountries.map(c => {
                            const isSelected = selectedCountries.includes(c.code);
                            const isDisabled = isLimitReached && !isSelected;
                            return `
                                <label class="country-row-item ${isSelected ? 'selected' : ''}" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 14px; border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.06)); cursor: ${isDisabled ? 'not-allowed' : 'pointer'}; background: ${isSelected ? 'rgba(37, 99, 235, 0.08)' : 'transparent'}; opacity: ${isDisabled ? '0.5' : '1'}; transition: background 0.15s ease;">
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <input type="checkbox" class="chk-country-select" data-code="${c.code}" ${isSelected ? 'checked' : ''} ${isDisabled ? 'disabled' : ''} style="accent-color: #2563eb; cursor: ${isDisabled ? 'not-allowed' : 'pointer'};"/>
                                        <span style="font-size: 13px; font-weight: ${isSelected ? '700' : '500'}; color: ${isSelected ? 'var(--text-primary, #f8fafc)' : 'var(--text-secondary, #cbd5e1)'};">
                                            ${this.escapeHtml(c.name)}
                                        </span>
                                    </div>
                                    <span style="font-size: 12px; font-weight: 600; color: var(--text-tertiary, #94a3b8); font-family: monospace;">
                                        ${this.escapeHtml(c.dialCode)}
                                    </span>
                                </label>
                            `;
                        }).join('') : `
                            <div style="padding: 24px; text-align: center; color: var(--text-tertiary, #94a3b8); font-size: 13px;">
                                No countries found
                            </div>
                        `}
                    </div>
                    <div style="font-size: 11px; color: var(--text-tertiary, #94a3b8); margin-top: 6px; text-align: right;">Select up to 5 countries</div>
                `;

                // Search event handler
                const inputSearch = bodyContainer.querySelector('#input-country-search');
                if (inputSearch) {
                    inputSearch.focus();
                    // Set cursor at end of input
                    inputSearch.selectionStart = inputSearch.selectionEnd = inputSearch.value.length;
                    inputSearch.addEventListener('input', (e) => {
                        this.countrySearchQuery = e.target.value;
                        this.renderStepContent();
                    });
                }

                // Checkbox toggle handler
                bodyContainer.querySelectorAll('.chk-country-select').forEach(chk => {
                    chk.addEventListener('change', (e) => {
                        const code = e.target.getAttribute('data-code');
                        let currentList = Array.isArray(this.config.target_countries) ? [...this.config.target_countries] : [];
                        const oldList = [...currentList];

                        if (e.target.checked) {
                            if (!currentList.includes(code) && currentList.length < 5) {
                                currentList.push(code);
                            }
                        } else {
                            currentList = currentList.filter(c => c !== code);
                        }

                        this.config.target_countries = currentList;
                        this.renderStepContent();

                        this.persistControlChange({ target_countries: currentList }, () => {
                            this.config.target_countries = oldList;
                            this.renderStepContent();
                        });
                    });
                });

                // Remove Chip tag button handler
                bodyContainer.querySelectorAll('.btn-remove-country-chip').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.preventDefault();
                        const code = e.currentTarget.getAttribute('data-code');
                        let currentList = Array.isArray(this.config.target_countries) ? [...this.config.target_countries] : [];
                        const oldList = [...currentList];

                        currentList = currentList.filter(c => c !== code);
                        this.config.target_countries = currentList;
                        this.renderStepContent();

                        this.persistControlChange({ target_countries: currentList }, () => {
                            this.config.target_countries = oldList;
                            this.renderStepContent();
                        });
                    });
                });
                break;

            case 5:
                bodyContainer.innerHTML = `
                    <div style="margin-bottom: 16px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 4px 0; color: var(--text-primary, #f8fafc);">Crawler Behavior & Exclusion Rules</h3>
                        <p style="font-size: 12.5px; color: var(--text-secondary, #94a3b8); margin: 0;">Configure bot identity and URL exclusion rules.</p>
                    </div>

                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-size: 12.5px; font-weight: 700; color: var(--text-primary, #f8fafc); margin-bottom: 6px;">Crawler User-Agent Identity</label>
                        <input type="text" id="input-user-agent" value="${this.escapeHtml(this.config.user_agent)}" style="width: 100%; padding: 8px 12px; font-size: 12px; border: 1px solid var(--border, #334155); border-radius: 6px; background: var(--bg-workspace, #1e293b); color: var(--text-primary, #f8fafc); font-family: monospace;"/>
                    </div>

                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-size: 12.5px; font-weight: 700; color: var(--text-primary, #f8fafc); margin-bottom: 6px;">Exclude Path Patterns</label>
                        <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                            <input type="text" id="input-add-exclude" placeholder="/cart/*" style="flex: 1; padding: 7px 10px; font-size: 12px; border: 1px solid var(--border, #334155); border-radius: 6px; background: var(--bg-workspace, #1e293b); font-family: monospace; color: var(--text-primary, #f8fafc);"/>
                            <button type="button" id="btn-add-exclude" class="btn btn-secondary btn-sm" style="padding: 6px 12px;">+ Add</button>
                        </div>
                        <div id="exclude-rules-container">
                            ${this.renderExcludeRulesHTML()}
                        </div>
                    </div>
                `;

                const inputUA = bodyContainer.querySelector('#input-user-agent');
                if (inputUA) {
                    inputUA.addEventListener('input', (e) => {
                        const val = e.target.value.trim();
                        const oldVal = this.config.user_agent;
                        this.config.user_agent = val;
                        this.debouncePersist({ user_agent: val }, () => {
                            this.config.user_agent = oldVal;
                        });
                    });
                }

                const btnAddExclude = bodyContainer.querySelector('#btn-add-exclude');
                const inputExclude = bodyContainer.querySelector('#input-add-exclude');
                if (btnAddExclude && inputExclude) {
                    btnAddExclude.addEventListener('click', (e) => {
                        e.preventDefault();
                        const val = inputExclude.value.trim();
                        if (val && !this.config.exclude_patterns.includes(val)) {
                            this.config.exclude_patterns.push(val);
                            inputExclude.value = '';
                            this.updateExcludeTagsUI(bodyContainer);
                            this.persistControlChange({ exclude_patterns: this.config.exclude_patterns }, () => {
                                this.config.exclude_patterns = this.config.exclude_patterns.filter(p => p !== val);
                                this.updateExcludeTagsUI(bodyContainer);
                            });
                        }
                    });
                }

                this.bindRemoveRuleButtons(bodyContainer);
                break;

            case 6:
                bodyContainer.innerHTML = `
                    <div style="margin-bottom: 16px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 4px 0; color: var(--text-primary, #f8fafc);">SEO Audit Modules</h3>
                        <p style="font-size: 12.5px; color: var(--text-secondary, #94a3b8); margin: 0;">Configure rule modules and URL parameter stripping.</p>
                    </div>

                    <div style="margin-bottom: 16px; padding: 14px; border: 1.5px solid var(--border, #334155); border-radius: 10px; background: var(--bg-workspace, #1e293b); display: flex; align-items: flex-start; gap: 10px;">
                        <input type="checkbox" id="chk-ignore-utm" ${this.config.ignore_tracking_parameters ? 'checked' : ''} style="margin-top: 2px; accent-color: #2563eb;"/>
                        <div>
                            <strong style="font-size: 13px; color: var(--text-primary, #f8fafc); display: block;">Ignore Tracking Parameters (utm_*, fbclid)</strong>
                            <span style="font-size: 11.5px; color: var(--text-secondary, #94a3b8);">Strips marketing parameters from discovered URLs to prevent queue duplication.</span>
                        </div>
                    </div>

                    <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary, #94a3b8); text-transform: uppercase; margin-bottom: 10px;">ACTIVE AUDIT MODULES</div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
                        <div class="audit-module-toggle-card ${this.config.audit_modules.technical_http ? 'active' : ''}" data-mod="technical_http">
                            <div>
                                <strong style="font-size: 12.5px; color: var(--text-primary, #f8fafc); display: block;">Technical & HTTP</strong>
                                <span style="font-size: 11px; color: var(--text-secondary, #94a3b8);">Status codes & SSL</span>
                            </div>
                            <span class="badge ${this.config.audit_modules.technical_http ? 'badge-success' : 'badge-secondary'}" style="font-size: 10px;">${this.config.audit_modules.technical_http ? 'Active' : 'Off'}</span>
                        </div>

                        <div class="audit-module-toggle-card ${this.config.audit_modules.metadata ? 'active' : ''}" data-mod="metadata">
                            <div>
                                <strong style="font-size: 12.5px; color: var(--text-primary, #f8fafc); display: block;">Title & Meta Description</strong>
                                <span style="font-size: 11px; color: var(--text-secondary, #94a3b8);">Titles & descriptions</span>
                            </div>
                            <span class="badge ${this.config.audit_modules.metadata ? 'badge-success' : 'badge-secondary'}" style="font-size: 10px;">${this.config.audit_modules.metadata ? 'Active' : 'Off'}</span>
                        </div>

                        <div class="audit-module-toggle-card ${this.config.audit_modules.headings ? 'active' : ''}" data-mod="headings">
                            <div>
                                <strong style="font-size: 12.5px; color: var(--text-primary, #f8fafc); display: block;">Headings Hierarchy</strong>
                                <span style="font-size: 11px; color: var(--text-secondary, #94a3b8);">H1-H3 tags</span>
                            </div>
                            <span class="badge ${this.config.audit_modules.headings ? 'badge-success' : 'badge-secondary'}" style="font-size: 10px;">${this.config.audit_modules.headings ? 'Active' : 'Off'}</span>
                        </div>

                        <div class="audit-module-toggle-card ${this.config.audit_modules.images ? 'active' : ''}" data-mod="images">
                            <div>
                                <strong style="font-size: 12.5px; color: var(--text-primary, #f8fafc); display: block;">Images & Alt Text</strong>
                                <span style="font-size: 11px; color: var(--text-secondary, #94a3b8);">Missing ALT text</span>
                            </div>
                            <span class="badge ${this.config.audit_modules.images ? 'badge-success' : 'badge-secondary'}" style="font-size: 10px;">${this.config.audit_modules.images ? 'Active' : 'Off'}</span>
                        </div>

                        <div class="audit-module-toggle-card ${this.config.audit_modules.links ? 'active' : ''}" data-mod="links">
                            <div>
                                <strong style="font-size: 12.5px; color: var(--text-primary, #f8fafc); display: block;">Link Graph</strong>
                                <span style="font-size: 11px; color: var(--text-secondary, #94a3b8);">Internal broken links</span>
                            </div>
                            <span class="badge ${this.config.audit_modules.links ? 'badge-success' : 'badge-secondary'}" style="font-size: 10px;">${this.config.audit_modules.links ? 'Active' : 'Off'}</span>
                        </div>

                        <div class="audit-module-toggle-card ${this.config.audit_modules.canonicals_robots ? 'active' : ''}" data-mod="canonicals_robots">
                            <div>
                                <strong style="font-size: 12.5px; color: var(--text-primary, #f8fafc); display: block;">Canonicals & Robots</strong>
                                <span style="font-size: 11px; color: var(--text-secondary, #94a3b8);">Robots & canonicals</span>
                            </div>
                            <span class="badge ${this.config.audit_modules.canonicals_robots ? 'badge-success' : 'badge-secondary'}" style="font-size: 10px;">${this.config.audit_modules.canonicals_robots ? 'Active' : 'Off'}</span>
                        </div>
                    </div>
                `;

                const chkUtm = bodyContainer.querySelector('#chk-ignore-utm');
                if (chkUtm) {
                    chkUtm.addEventListener('change', (e) => {
                        const val = e.target.checked;
                        const oldVal = !val;
                        this.config.ignore_tracking_parameters = val;
                        this.persistControlChange({ ignore_tracking_parameters: val }, () => {
                            this.config.ignore_tracking_parameters = oldVal;
                            chkUtm.checked = oldVal;
                        });
                    });
                }

                bodyContainer.querySelectorAll('.audit-module-toggle-card').forEach(card => {
                    card.addEventListener('click', (e) => {
                        e.preventDefault();
                        const modKey = card.getAttribute('data-mod');
                        if (modKey && this.config.audit_modules.hasOwnProperty(modKey)) {
                            const newVal = !this.config.audit_modules[modKey];
                            const oldVal = !newVal;
                            this.config.audit_modules[modKey] = newVal;

                            card.classList.toggle('active', newVal);
                            const badge = card.querySelector('.badge');
                            if (badge) {
                                badge.className = `badge ${newVal ? 'badge-success' : 'badge-secondary'}`;
                                badge.innerText = newVal ? 'Active' : 'Off';
                            }

                            this.persistControlChange({ audit_modules: { [modKey]: newVal } }, () => {
                                this.config.audit_modules[modKey] = oldVal;
                                card.classList.toggle('active', oldVal);
                                if (badge) {
                                    badge.className = `badge ${oldVal ? 'badge-success' : 'badge-secondary'}`;
                                    badge.innerText = oldVal ? 'Active' : 'Off';
                                }
                            });
                        }
                    });
                });
                break;

            case 7:
                const activeModulesCount = Object.values(this.config.audit_modules).filter(Boolean).length;
                const revProj = projectStore.getSelectedProject();
                const revDetectedDefault = detectUserDefaultCountry(revProj?.target_country);
                const revCountries = Array.isArray(this.config.target_countries) ? this.config.target_countries : [];
                
                let countryTargetingSummary = 'Global / Default Targeting';
                if (revCountries.length > 0) {
                    countryTargetingSummary = revCountries.map(c => {
                        const item = findCountry(c);
                        return item ? `${item.name} (${item.dialCode})` : c;
                    }).join(', ');
                } else if (revDetectedDefault) {
                    countryTargetingSummary = `Current Country: ${revDetectedDefault.name} (${revDetectedDefault.dialCode})`;
                }

                bodyContainer.innerHTML = `
                    <div style="margin-bottom: 16px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 4px 0; color: var(--text-primary, #f8fafc);">Review Crawl Configuration</h3>
                        <p style="font-size: 12.5px; color: var(--text-secondary, #94a3b8); margin: 0;">Review validated settings before launching engine.</p>
                    </div>

                    <div style="background: var(--bg-card, #0f172a); border: 1px solid var(--border, #334155); border-radius: 10px; padding: 18px; font-size: 12.5px; margin-bottom: 16px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                            <div>
                                <span style="color: var(--text-tertiary, #94a3b8); display: block; font-size: 10.5px; text-transform: uppercase; font-weight: 700;">TARGET URL</span>
                                <strong style="color: var(--text-primary, #f8fafc); font-family: monospace;">${this.escapeHtml(this.targetUrl)}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-tertiary, #94a3b8); display: block; font-size: 10.5px; text-transform: uppercase; font-weight: 700;">CRAWL SCOPE</span>
                                <strong style="color: var(--text-primary, #f8fafc);">${this.config.scope_type.replace('_', ' ').toUpperCase()}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-tertiary, #94a3b8); display: block; font-size: 10.5px; text-transform: uppercase; font-weight: 700;">COUNTRY TARGETING</span>
                                <strong style="color: #3b82f6;">${this.escapeHtml(countryTargetingSummary)}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-tertiary, #94a3b8); display: block; font-size: 10.5px; text-transform: uppercase; font-weight: 700;">MAX CRAWL DEPTH</span>
                                <strong style="color: #3b82f6;">Level ${this.config.max_depth === 0 ? 'Unlimited' : this.config.max_depth}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-tertiary, #94a3b8); display: block; font-size: 10.5px; text-transform: uppercase; font-weight: 700;">MAX PAGES CEILING</span>
                                <strong style="color: var(--text-primary, #f8fafc);">${this.config.max_pages.toLocaleString()} pages</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-tertiary, #94a3b8); display: block; font-size: 10.5px; text-transform: uppercase; font-weight: 700;">ROBOTS.TXT</span>
                                <strong style="color: ${this.config.respect_robots_txt ? '#10b981' : '#f59e0b'};">${this.config.respect_robots_txt ? '✓ Respect Directives' : '⚠️ Ignore Directives'}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-tertiary, #94a3b8); display: block; font-size: 10.5px; text-transform: uppercase; font-weight: 700;">AUDIT MODULES</span>
                                <strong style="color: var(--text-primary, #f8fafc);">${activeModulesCount} / 6 Active</strong>
                            </div>
                        </div>
                    </div>
                `;
                break;
        }
    }

    getDepthExplanationHTML(depthVal) {
        switch (depthVal) {
            case 1:
                return `<strong>Level 1 — Seed + direct 1-hop links:</strong> Crawl the starting URL and all directly linked internal pages (Seed → Level 1).`;
            case 2:
                return `<strong>Level 2 — Seed + 2 link levels deep:</strong> Crawl starting URL up to 2 link hops (Seed → Category → Item).`;
            case 3:
                return `<strong>Level 3 — Up to 3 link levels deep:</strong> Crawl starting URL up to 3 link hops (Seed → Section → Sub-section → Page).`;
            case 5:
                return `<strong>Level 5 — Up to 5 link levels deep:</strong> Useful for medium-sized websites with nested hierarchies.`;
            case 10:
                return `<strong>Level 10 — Up to 10 link levels deep:</strong> Deep crawling for large websites with deeply nested navigation.`;
            case 0:
            default:
                return `<strong>Unlimited — Follow all internal links until ceiling:</strong> Unrestricted depth until max page limit or crawl queue exhaustion.`;
        }
    }

    renderExcludeRulesHTML() {
        return this.config.exclude_patterns.map((pat, idx) => `
            <span class="rule-tag">
                <span>${this.escapeHtml(pat)}</span>
                <button type="button" class="btn-remove-rule" data-idx="${idx}" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 12px; margin-left: 2px;">&times;</button>
            </span>
        `).join('');
    }

    updateExcludeTagsUI(container) {
        const wrap = container.querySelector('#exclude-rules-container');
        if (wrap) {
            wrap.innerHTML = this.renderExcludeRulesHTML();
            this.bindRemoveRuleButtons(container);
        }
    }

    bindRemoveRuleButtons(container) {
        container.querySelectorAll('.btn-remove-rule').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
                const removedVal = this.config.exclude_patterns[idx];
                this.config.exclude_patterns.splice(idx, 1);
                this.updateExcludeTagsUI(container);
                this.persistControlChange({ exclude_patterns: this.config.exclude_patterns }, () => {
                    this.config.exclude_patterns.splice(idx, 0, removedVal);
                    this.updateExcludeTagsUI(container);
                });
            });
        });
    }

    debouncePersist(patchPayload, revertFn) {
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        this.setSaveStatus('Saving...', 'saving');
        this.saveTimeout = setTimeout(async () => {
            await this.persistControlChange(patchPayload, revertFn);
        }, 400);
    }

    async persistControlChange(patchPayload, revertFn) {
        if (!this.projectId) return;
        try {
            this.setSaveStatus('Saving...', 'saving');
            const data = await apiClient.patch(`/api/projects/${this.projectId}/crawl-config`, patchPayload);
            if (data && data.config) {
                const remote = data.config;
                this.config = {
                    ...this.config,
                    ...remote,
                    target_countries: Array.isArray(remote.target_countries) ? remote.target_countries : [],
                    audit_modules: {
                        ...this.config.audit_modules,
                        ...(remote.audit_modules || {})
                    }
                };
            }
            this.setSaveStatus('✓ Saved', 'success', 1500);
        } catch (err) {
            console.error("[CRAWL CONFIG] Async patch error:", err);
            if (typeof revertFn === 'function') {
                revertFn();
            }
            this.setSaveStatus(`✕ Error saving`, 'error', 3000);
        }
    }

    setSaveStatus(msg, type = 'info', fadeMs = 0) {
        if (!this.modalElement) return;
        const el = this.modalElement.querySelector('#config-save-status');
        if (!el) return;

        el.innerText = msg;
        if (type === 'saving') {
            el.style.color = '#3b82f6';
        } else if (type === 'success') {
            el.style.color = '#10b981';
        } else if (type === 'error') {
            el.style.color = '#ef4444';
        } else {
            el.style.color = 'var(--text-tertiary, #94a3b8)';
        }

        if (fadeMs > 0) {
            setTimeout(() => {
                if (el.innerText === msg) {
                    el.innerText = '';
                }
            }, fadeMs);
        }
    }

    async resetToDefaults() {
        this.config = {
            scope_type: 'entire_domain',
            custom_path: '',
            max_pages: 5000,
            max_depth: 3,
            request_timeout: 20.0,
            crawl_delay_ms: 500,
            respect_robots_txt: true,
            discover_sitemap: true,
            custom_sitemap_url: '',
            discover_internal_links: true,
            user_agent: 'SEO-Intelligence-Bot/1.0 (Mozilla/5.0 Compatible)',
            follow_redirects: true,
            include_patterns: [],
            exclude_patterns: ['/admin/*', '/login/*', '/cart/*'],
            target_countries: [],
            ignore_tracking_parameters: true,
            audit_modules: {
                technical_http: true,
                metadata: true,
                headings: true,
                images: true,
                links: true,
                canonicals_robots: true
            },
            performance_analysis: {
                available: false,
                reason: "Core Web Vitals and Lighthouse performance analysis are currently unavailable for this crawl run."
            }
        };

        this.renderStepContent();
        await this.persistControlChange(this.config);
    }

    is5000PlusMode(val) {
        return val === '5000+' || val === 0 || val === '0' || val === null || val === undefined || parseInt(val, 10) >= 5001;
    }

    formatMaxPagesLabel(val) {
        if (this.is5000PlusMode(val)) {
            return '5000+ pages';
        }
        const num = parseInt(val, 10);
        return isNaN(num) ? '5000+ pages' : `${num.toLocaleString()} pages`;
    }

    getMaxPagesSliderValue(val) {
        if (this.is5000PlusMode(val)) {
            return 5001;
        }
        const num = parseInt(val, 10);
        return isNaN(num) ? 5001 : Math.min(5000, Math.max(100, num));
    }

    async executeCrawl() {
        try {
            let crawlTarget = this.targetUrl;
            if (this.config.scope_type === 'specific_path' && this.config.custom_path) {
                const base = this.targetUrl.replace(/\/+$/, '');
                const sub = this.config.custom_path.startsWith('/') ? this.config.custom_path : '/' + this.config.custom_path;
                crawlTarget = base + sub;
            }

            const data = await crawlService.startCrawl(this.projectId, crawlTarget, this.config);
            this.close();
            crawlProgressOverlay.start(this.projectId, data.session_id, crawlTarget);
        } catch (e) {
            alert(`Error starting crawl: ${e.message || 'Unable to start crawl.'}`);
            const btnStart = this.modalElement?.querySelector('#btn-wizard-start');
            if (btnStart) {
                btnStart.disabled = false;
                btnStart.innerText = 'Start Real Crawl';
            }
        }
    }

    close() {
        if (this.modalElement) {
            this.modalElement.remove();
            this.modalElement = null;
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

export const crawlConfigModal = new CrawlConfigModalManager();
