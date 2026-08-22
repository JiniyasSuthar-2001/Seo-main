import { crawlService } from '../services/crawlService.js';
import { crawlProgressOverlay } from './CrawlProgressOverlay.js';
import { projectStore } from '../core/projectStore.js';

class CrawlConfigModalManager {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 6;
        this.projectId = null;
        this.targetUrl = '';
        this.modalElement = null;
        
        // Config State
        this.config = {
            scope_type: 'entire_domain',
            custom_path: '',
            max_pages: 5000,
            max_depth: 0,
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
            ignore_utm_params: true,
            analyze_technical: true,
            analyze_metadata: true,
            analyze_headings: true,
            analyze_images: true,
            analyze_internal_links: true
        };
    }

    open(projectId, targetUrl) {
        this.projectId = projectId || projectStore.getSelectedProjectId();
        const selectedProj = projectStore.getSelectedProject();
        this.targetUrl = targetUrl || (selectedProj ? selectedProj.domain || selectedProj.url : '') || 'https://example.com';
        this.currentStep = 1;
        this.resetToDefaults();
        this.renderModal();
    }

    resetToDefaults() {
        this.config = {
            scope_type: 'entire_domain',
            custom_path: '',
            max_pages: 5000,
            max_depth: 0,
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
            ignore_utm_params: true,
            analyze_technical: true,
            analyze_metadata: true,
            analyze_headings: true,
            analyze_images: true,
            analyze_internal_links: true
        };
    }

    renderModal() {
        if (this.modalElement) {
            this.modalElement.remove();
        }

        const backdrop = document.createElement('div');
        backdrop.id = 'crawl-config-modal-backdrop';
        backdrop.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.7); backdrop-filter: blur(6px);
            display: flex; align-items: center; justify-content: center; z-index: 99999; padding: 20px;
            font-family: 'Inter', system-ui, -apple-system, sans-serif; animation: fadeIn 0.2s ease-out;
        `;

        backdrop.innerHTML = `
            <style>
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                .wizard-step-pill {
                    padding: 6px 12px; border-radius: 20px; font-size: 11.5px; font-weight: 600;
                    color: var(--text-tertiary); background: var(--bg-subtle); transition: all 0.2s ease;
                    display: flex; align-items: center; gap: 6px; cursor: pointer; border: 1px solid transparent;
                }
                .wizard-step-pill.active {
                    color: var(--primary, #2563eb); background: rgba(37, 99, 235, 0.1); border-color: rgba(37, 99, 235, 0.3);
                }
                .wizard-step-pill.completed {
                    color: #10b981; background: rgba(16, 185, 129, 0.1);
                }
                .option-radio-card {
                    padding: 16px; border: 1.5px solid var(--border); border-radius: 10px;
                    background: var(--bg-card); cursor: pointer; transition: all 0.2s ease; margin-bottom: 12px;
                }
                .option-radio-card:hover {
                    border-color: var(--primary); background: var(--bg-subtle);
                }
                .option-radio-card.selected {
                    border-color: var(--primary); background: rgba(37, 99, 235, 0.05); box-shadow: 0 0 0 1px var(--primary);
                }
                .rule-tag {
                    display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
                    border-radius: 6px; background: var(--bg-subtle); border: 1px solid var(--border);
                    font-size: 12px; font-family: monospace; margin: 4px;
                }
            </style>
            <div class="card" style="width: 100%; max-width: 680px; background: var(--bg-card); border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4); overflow: hidden; display: flex; flex-direction: column; max-height: 90vh;">
                
                <!-- MODAL HEADER -->
                <div style="padding: 24px 28px 16px; border-bottom: 1px solid var(--border); background: var(--bg-card);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                <span class="badge badge-primary" style="font-size: 10px; font-weight: 700;">CRAWL CONFIGURATION WIZARD</span>
                                <span style="font-size: 12px; color: var(--text-tertiary);">Step ${this.currentStep} of ${this.totalSteps}</span>
                            </div>
                            <h2 style="font-size: 20px; font-weight: 700; margin: 0; color: var(--text-primary);">Configure SEO Crawl</h2>
                            <div style="font-size: 13px; color: var(--primary); font-family: monospace; font-weight: 600; margin-top: 2px;">${this.escapeHtml(this.targetUrl)}</div>
                        </div>
                        <button id="btn-close-config-modal" style="background: none; border: none; font-size: 22px; color: var(--text-secondary); cursor: pointer; padding: 0 4px;">&times;</button>
                    </div>

                    <!-- WIZARD STEP PILLS -->
                    <div style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px;">
                        <div class="wizard-step-pill ${this.currentStep === 1 ? 'active' : (this.currentStep > 1 ? 'completed' : '')}" data-step="1">① Scope</div>
                        <div class="wizard-step-pill ${this.currentStep === 2 ? 'active' : (this.currentStep > 2 ? 'completed' : '')}" data-step="2">② Limits</div>
                        <div class="wizard-step-pill ${this.currentStep === 3 ? 'active' : (this.currentStep > 3 ? 'completed' : '')}" data-step="3">③ Discovery</div>
                        <div class="wizard-step-pill ${this.currentStep === 4 ? 'active' : (this.currentStep > 4 ? 'completed' : '')}" data-step="4">④ Behavior</div>
                        <div class="wizard-step-pill ${this.currentStep === 5 ? 'active' : (this.currentStep > 5 ? 'completed' : '')}" data-step="5">⑤ Analysis</div>
                        <div class="wizard-step-pill ${this.currentStep === 6 ? 'active' : ''}" data-step="6">⑥ Review</div>
                    </div>
                </div>

                <!-- STEP CONTENT CONTAINER -->
                <div id="modal-step-body" style="padding: 28px; overflow-y: auto; flex: 1;">
                    ${this.renderStepContent()}
                </div>

                <!-- MODAL FOOTER -->
                <div style="padding: 18px 28px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: center;">
                    <button type="button" id="btn-reset-defaults" style="background: none; border: none; font-size: 12.5px; color: var(--text-secondary); cursor: pointer; text-decoration: underline;">Reset to Recommended</button>
                    
                    <div style="display: flex; gap: 10px;">
                        ${this.currentStep > 1 ? `
                            <button type="button" id="btn-wizard-back" class="btn btn-secondary">← Back</button>
                        ` : ''}
                        ${this.currentStep < this.totalSteps ? `
                            <button type="button" id="btn-wizard-next" class="btn btn-primary">Continue →</button>
                        ` : `
                            <button type="button" id="btn-wizard-start" class="btn btn-primary" style="background: linear-gradient(135deg, #2563eb, #1d4ed8); padding: 10px 24px; font-weight: 700;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                                <span>Start Real Crawl</span>
                            </button>
                        `}
                    </div>
                </div>

            </div>
        `;

        document.body.appendChild(backdrop);
        this.modalElement = backdrop;
        this.bindEvents();
    }

    renderStepContent() {
        switch (this.currentStep) {
            case 1:
                return `
                    <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 6px; color: var(--text-primary);">Where should we crawl?</h3>
                    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">Define the boundary limit for this crawl run. The crawler strictly respects this boundary.</p>

                    <div class="option-radio-card ${this.config.scope_type === 'entire_domain' ? 'selected' : ''}" data-scope="entire_domain">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <input type="radio" name="scope_radio" value="entire_domain" ${this.config.scope_type === 'entire_domain' ? 'checked' : ''}/>
                            <div>
                                <strong style="font-size: 14px; color: var(--text-primary); display: block;">Entire Website Domain</strong>
                                <span style="font-size: 12px; color: var(--text-secondary);">Crawl all HTML pages discovered across ${this.escapeHtml(this.targetUrl)}</span>
                            </div>
                        </div>
                    </div>

                    <div class="option-radio-card ${this.config.scope_type === 'specific_path' ? 'selected' : ''}" data-scope="specific_path">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <input type="radio" name="scope_radio" value="specific_path" ${this.config.scope_type === 'specific_path' ? 'checked' : ''}/>
                            <div style="flex: 1;">
                                <strong style="font-size: 14px; color: var(--text-primary); display: block;">Specific Sub-Path Only</strong>
                                <span style="font-size: 12px; color: var(--text-secondary);">Restrict boundary to pages starting with a specific sub-folder path (e.g. /services/)</span>
                            </div>
                        </div>
                        ${this.config.scope_type === 'specific_path' ? `
                            <div style="margin-top: 12px; padding-left: 26px;">
                                <input type="text" id="input-custom-path" value="${this.escapeHtml(this.config.custom_path)}" placeholder="/services/" style="width: 100%; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); color: var(--text-primary); font-family: monospace;"/>
                            </div>
                        ` : ''}
                    </div>

                    <div class="option-radio-card ${this.config.scope_type === 'subdomain' ? 'selected' : ''}" data-scope="subdomain">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <input type="radio" name="scope_radio" value="subdomain" ${this.config.scope_type === 'subdomain' ? 'checked' : ''}/>
                            <div>
                                <strong style="font-size: 14px; color: var(--text-primary); display: block;">Subdomain Only</strong>
                                <span style="font-size: 12px; color: var(--text-secondary);">Strictly crawl pages belonging to the exact host domain</span>
                            </div>
                        </div>
                    </div>

                    <div style="background: rgba(59, 130, 246, 0.08); border-left: 4px solid var(--primary); padding: 12px 16px; border-radius: 6px; margin-top: 20px; font-size: 12.5px; color: var(--text-secondary);">
                        🔒 <strong>Enforced Scope Protection:</strong> URLs outside your selected scope boundary will be filtered out before request dispatch.
                    </div>
                `;

            case 2:
                return `
                    <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 6px; color: var(--text-primary);">Control the crawl limits</h3>
                    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">Configure page ceilings, depth limits, and request throttling.</p>

                    <div style="margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <label style="font-size: 13px; font-weight: 600; color: var(--text-primary);">Maximum Pages Ceiling</label>
                            <span style="font-size: 14px; font-weight: 700; color: var(--primary); font-family: monospace;" id="val-max-pages">${this.config.max_pages.toLocaleString()} pages</span>
                        </div>
                        <input type="range" id="range-max-pages" min="100" max="25000" step="500" value="${this.config.max_pages}" style="width: 100%; accent-color: var(--primary); cursor: pointer;"/>
                        <div style="font-size: 11.5px; color: var(--text-tertiary); margin-top: 4px;">Maximum number of pages the crawler will process during this crawl run.</div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
                        <div>
                            <label style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Max Crawl Depth Level</label>
                            <select id="select-max-depth" style="width: 100%; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); color: var(--text-primary);">
                                <option value="0" ${this.config.max_depth === 0 ? 'selected' : ''}>Unlimited (Follow all links)</option>
                                <option value="1" ${this.config.max_depth === 1 ? 'selected' : ''}>1 Level (Homepage links only)</option>
                                <option value="2" ${this.config.max_depth === 2 ? 'selected' : ''}>2 Levels</option>
                                <option value="3" ${this.config.max_depth === 3 ? 'selected' : ''}>3 Levels</option>
                                <option value="5" ${this.config.max_depth === 5 ? 'selected' : ''}>5 Levels</option>
                                <option value="10" ${this.config.max_depth === 10 ? 'selected' : ''}>10 Levels</option>
                            </select>
                        </div>

                        <div>
                            <label style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Request Timeout</label>
                            <select id="select-timeout" style="width: 100%; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); color: var(--text-primary);">
                                <option value="10" ${this.config.request_timeout === 10 ? 'selected' : ''}>10 Seconds (Fast)</option>
                                <option value="20" ${this.config.request_timeout === 20 ? 'selected' : ''}>20 Seconds (Recommended)</option>
                                <option value="30" ${this.config.request_timeout === 30 ? 'selected' : ''}>30 Seconds (Slow server)</option>
                            </select>
                        </div>
                    </div>

                    <div style="margin-bottom: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <label style="font-size: 13px; font-weight: 600; color: var(--text-primary);">Crawl Request Delay</label>
                            <span style="font-size: 13px; font-weight: 700; color: var(--text-primary); font-family: monospace;" id="val-crawl-delay">${this.config.crawl_delay_ms} ms</span>
                        </div>
                        <input type="range" id="range-crawl-delay" min="0" max="2000" step="100" value="${this.config.crawl_delay_ms}" style="width: 100%; accent-color: var(--primary); cursor: pointer;"/>
                        <div style="font-size: 11.5px; color: var(--text-tertiary); margin-top: 4px;">Adds a delay between asynchronous batch requests to prevent server rate limiting.</div>
                    </div>
                `;

            case 3:
                return `
                    <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 6px; color: var(--text-primary);">How should pages be discovered?</h3>
                    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">Enable discovery mechanisms and configure robots.txt compliance rules.</p>

                    <div style="display: flex; flex-direction: column; gap: 14px; margin-bottom: 20px;">
                        <label style="display: flex; align-items: flex-start; gap: 12px; padding: 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-workspace); cursor: pointer;">
                            <input type="checkbox" id="chk-internal-links" ${this.config.discover_internal_links ? 'checked' : ''} style="margin-top: 2px; width: 16px; height: 16px;"/>
                            <div>
                                <strong style="font-size: 13.5px; color: var(--text-primary); display: block;">Internal Hyperlink Discovery</strong>
                                <span style="font-size: 12px; color: var(--text-secondary);">Discover new HTML pages by following internal href links found on crawled pages.</span>
                            </div>
                        </label>

                        <label style="display: flex; align-items: flex-start; gap: 12px; padding: 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-workspace); cursor: pointer;">
                            <input type="checkbox" id="chk-sitemap" ${this.config.discover_sitemap ? 'checked' : ''} style="margin-top: 2px; width: 16px; height: 16px;"/>
                            <div>
                                <strong style="font-size: 13.5px; color: var(--text-primary); display: block;">Inspect XML Sitemap (/sitemap.xml)</strong>
                                <span style="font-size: 12px; color: var(--text-secondary);">Automatically fetch and parse sitemap.xml to populate the crawl queue with indexed URLs.</span>
                            </div>
                        </label>

                        <div style="padding: 16px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-workspace);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <div>
                                    <strong style="font-size: 13.5px; color: var(--text-primary); display: block;">Respect robots.txt Directives</strong>
                                    <span style="font-size: 12px; color: var(--text-secondary);">Follow Disallow rules declared in ${this.escapeHtml(this.targetUrl)}/robots.txt</span>
                                </div>
                                <input type="checkbox" id="chk-respect-robots" ${this.config.respect_robots_txt ? 'checked' : ''} style="width: 18px; height: 18px; cursor: pointer;"/>
                            </div>
                            ${!this.config.respect_robots_txt ? `
                                <div style="margin-top: 10px; padding: 10px 12px; background: rgba(245, 158, 11, 0.12); border-left: 3px solid #f59e0b; border-radius: 4px; font-size: 12px; color: #d97706;">
                                    ⚠️ <strong>Warning:</strong> Disabling robots.txt will bypass site owner crawl restrictions and attempt to access disallowed paths.
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;

            case 4:
                return `
                    <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 6px; color: var(--text-primary);">Crawler Behavior & Path Rules</h3>
                    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">Configure user-agent identity, redirection handling, and path inclusion/exclusion patterns.</p>

                    <div style="margin-bottom: 18px;">
                        <label style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Crawler User-Agent String</label>
                        <input type="text" id="input-user-agent" value="${this.escapeHtml(this.config.user_agent)}" style="width: 100%; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); color: var(--text-primary); font-family: monospace;"/>
                        <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Identifies our crawler bot to web server logs. Third-party user-agents are not spoofed.</div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px;">
                        <div style="padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-subtle);">
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">JavaScript Rendering</div>
                            <span class="badge badge-secondary" style="font-size: 10.5px;">Disabled</span>
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Unavailable — browser renderer not configured (Playwright required)</div>
                        </div>

                        <div style="padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-workspace); display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-size: 12px; font-weight: 600; color: var(--text-primary);">Follow HTTP Redirects</div>
                                <div style="font-size: 11px; color: var(--text-secondary);">Trace 301 / 302 redirect chains</div>
                            </div>
                            <input type="checkbox" id="chk-follow-redirects" ${this.config.follow_redirects ? 'checked' : ''} style="width: 16px; height: 16px;"/>
                        </div>
                    </div>

                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Exclude Path Patterns (Skip URLs)</label>
                        <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                            <input type="text" id="input-add-exclude" placeholder="e.g. /cart/* or /admin/*" style="flex: 1; padding: 7px 10px; font-size: 12.5px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); font-family: monospace;"/>
                            <button type="button" id="btn-add-exclude" class="btn btn-secondary btn-sm">+ Add Exclude Rule</button>
                        </div>
                        <div id="exclude-rules-container">
                            ${this.config.exclude_patterns.map((pat, idx) => `
                                <span class="rule-tag">
                                    <span>${this.escapeHtml(pat)}</span>
                                    <button type="button" class="btn-remove-rule" data-type="exclude" data-idx="${idx}" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 14px;">&times;</button>
                                </span>
                            `).join('')}
                        </div>
                    </div>
                `;

            case 5:
                return `
                    <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 6px; color: var(--text-primary);">URL Handling & Audit Modules</h3>
                    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">Choose parameters to strip and technical SEO analysis modules to evaluate.</p>

                    <label style="display: flex; align-items: flex-start; gap: 12px; padding: 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-workspace); cursor: pointer; margin-bottom: 20px;">
                        <input type="checkbox" id="chk-ignore-utm" ${this.config.ignore_utm_params ? 'checked' : ''} style="margin-top: 2px; width: 16px; height: 16px;"/>
                        <div>
                            <strong style="font-size: 13.5px; color: var(--text-primary); display: block;">Ignore Analytics Tracking Parameters (utm_*, fbclid)</strong>
                            <span style="font-size: 12px; color: var(--text-secondary);">Strips marketing tracking parameters from discovered URLs to prevent duplicate crawl queue entries.</span>
                        </div>
                    </label>

                    <div style="font-size: 12px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase; margin-bottom: 10px;">ACTIVE SEO AUDIT MODULES</div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px;">
                        <label style="display: flex; align-items: center; gap: 8px; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); font-size: 13px; color: var(--text-primary);">
                            <input type="checkbox" checked disabled/> Technical & HTTP Audit
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); font-size: 13px; color: var(--text-primary);">
                            <input type="checkbox" checked disabled/> Title & Meta Description
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); font-size: 13px; color: var(--text-primary);">
                            <input type="checkbox" checked disabled/> H1 - H3 Heading Hierarchy
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); font-size: 13px; color: var(--text-primary);">
                            <input type="checkbox" checked disabled/> Images & Alt Text Audit
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); font-size: 13px; color: var(--text-primary);">
                            <input type="checkbox" checked disabled/> Internal & External Link Graph
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-workspace); font-size: 13px; color: var(--text-primary);">
                            <input type="checkbox" checked disabled/> Canonicals & Robots Meta
                        </label>
                    </div>

                    <div style="padding: 12px 16px; background: var(--bg-subtle); border-radius: 8px; font-size: 12px; color: var(--text-secondary); border: 1px solid var(--border);">
                        ℹ️ <strong>Performance Analysis:</strong> Core Web Vitals and Lighthouse performance analysis are currently unavailable for this crawl run.
                    </div>
                `;

            case 6:
                return `
                    <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 6px; color: var(--text-primary);">Review Crawl Configuration</h3>
                    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">Review your final crawl settings before launching the engine.</p>

                    <div style="background: var(--bg-workspace); border: 1px solid var(--border); border-radius: 10px; padding: 20px; font-size: 13px; margin-bottom: 20px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                            <div>
                                <span style="color: var(--text-secondary); display: block; font-size: 11px; text-transform: uppercase;">TARGET WEBSITE</span>
                                <strong style="color: var(--text-primary); font-family: monospace;">${this.escapeHtml(this.targetUrl)}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-secondary); display: block; font-size: 11px; text-transform: uppercase;">CRAWL SCOPE</span>
                                <strong style="color: var(--text-primary);">${this.config.scope_type.replace('_', ' ').toUpperCase()} ${this.config.custom_path ? `(${this.config.custom_path})` : ''}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-secondary); display: block; font-size: 11px; text-transform: uppercase;">MAX PAGES CEILING</span>
                                <strong style="color: var(--primary);">${this.config.max_pages.toLocaleString()} pages</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-secondary); display: block; font-size: 11px; text-transform: uppercase;">MAX CRAWL DEPTH</span>
                                <strong style="color: var(--text-primary);">${this.config.max_depth === 0 ? 'Unlimited' : `${this.config.max_depth} Levels`}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-secondary); display: block; font-size: 11px; text-transform: uppercase;">ROBOTS.TXT COMPLIANCE</span>
                                <strong style="color: ${this.config.respect_robots_txt ? '#10b981' : '#f59e0b'};">${this.config.respect_robots_txt ? '✓ Respect Directives' : '⚠️ Ignore Directives'}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-secondary); display: block; font-size: 11px; text-transform: uppercase;">CRAWL REQUEST DELAY</span>
                                <strong style="color: var(--text-primary);">${this.config.crawl_delay_ms} ms</strong>
                            </div>
                        </div>

                        ${this.config.exclude_patterns.length > 0 ? `
                            <div style="margin-top: 14px; border-top: 1px solid var(--border); padding-top: 10px;">
                                <span style="color: var(--text-secondary); font-size: 11px; text-transform: uppercase; display: block; margin-bottom: 4px;">EXCLUDE RULES</span>
                                <div>
                                    ${this.config.exclude_patterns.map(p => `<code style="background: var(--bg-subtle); padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 4px;">${this.escapeHtml(p)}</code>`).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>

                    <div style="background: rgba(16, 185, 129, 0.08); border-left: 4px solid #10b981; padding: 12px 16px; border-radius: 6px; font-size: 12.5px; color: var(--text-secondary);">
                        ✓ <strong>Ready to Crawl:</strong> Configuration validated. The real Python SEO crawler will launch in background mode.
                    </div>
                `;

            default:
                return '';
        }
    }

    bindEvents() {
        if (!this.modalElement) return;

        const btnClose = this.modalElement.querySelector('#btn-close-config-modal');
        if (btnClose) btnClose.addEventListener('click', () => this.close());

        const btnReset = this.modalElement.querySelector('#btn-reset-defaults');
        if (btnReset) btnReset.addEventListener('click', () => {
            this.resetToDefaults();
            this.renderModal();
        });

        // Step Navigation Pills
        const stepPills = this.modalElement.querySelectorAll('.wizard-step-pill');
        stepPills.forEach(pill => {
            pill.addEventListener('click', (e) => {
                const targetStep = parseInt(e.currentTarget.getAttribute('data-step'), 10);
                if (targetStep) {
                    this.currentStep = targetStep;
                    this.renderModal();
                }
            });
        });

        // Step 1: Scope Radios
        const scopeCards = this.modalElement.querySelectorAll('.option-radio-card');
        scopeCards.forEach(card => {
            card.addEventListener('click', (e) => {
                const val = e.currentTarget.getAttribute('data-scope');
                if (val) {
                    this.config.scope_type = val;
                    this.renderModal();
                }
            });
        });

        const inputCustomPath = this.modalElement.querySelector('#input-custom-path');
        if (inputCustomPath) {
            inputCustomPath.addEventListener('input', (e) => {
                this.config.custom_path = e.target.value.trim();
            });
        }

        // Step 2: Limits Inputs
        const rangePages = this.modalElement.querySelector('#range-max-pages');
        if (rangePages) {
            rangePages.addEventListener('input', (e) => {
                this.config.max_pages = parseInt(e.target.value, 10);
                const valEl = this.modalElement.querySelector('#val-max-pages');
                if (valEl) valEl.innerText = `${this.config.max_pages.toLocaleString()} pages`;
            });
        }

        const selectDepth = this.modalElement.querySelector('#select-max-depth');
        if (selectDepth) {
            selectDepth.addEventListener('change', (e) => {
                this.config.max_depth = parseInt(e.target.value, 10);
            });
        }

        const selectTimeout = this.modalElement.querySelector('#select-timeout');
        if (selectTimeout) {
            selectTimeout.addEventListener('change', (e) => {
                this.config.request_timeout = parseFloat(e.target.value);
            });
        }

        const rangeDelay = this.modalElement.querySelector('#range-crawl-delay');
        if (rangeDelay) {
            rangeDelay.addEventListener('input', (e) => {
                this.config.crawl_delay_ms = parseInt(e.target.value, 10);
                const valEl = this.modalElement.querySelector('#val-crawl-delay');
                if (valEl) valEl.innerText = `${this.config.crawl_delay_ms} ms`;
            });
        }

        // Step 3: Discovery Checkboxes
        const chkInternal = this.modalElement.querySelector('#chk-internal-links');
        if (chkInternal) {
            chkInternal.addEventListener('change', (e) => {
                this.config.discover_internal_links = e.target.checked;
            });
        }

        const chkSitemap = this.modalElement.querySelector('#chk-sitemap');
        if (chkSitemap) {
            chkSitemap.addEventListener('change', (e) => {
                this.config.discover_sitemap = e.target.checked;
            });
        }

        const chkRobots = this.modalElement.querySelector('#chk-respect-robots');
        if (chkRobots) {
            chkRobots.addEventListener('change', (e) => {
                this.config.respect_robots_txt = e.target.checked;
                this.renderModal();
            });
        }

        // Step 4: User Agent & Exclude Rules
        const inputUA = this.modalElement.querySelector('#input-user-agent');
        if (inputUA) {
            inputUA.addEventListener('input', (e) => {
                this.config.user_agent = e.target.value.trim();
            });
        }

        const chkRedirects = this.modalElement.querySelector('#chk-follow-redirects');
        if (chkRedirects) {
            chkRedirects.addEventListener('change', (e) => {
                this.config.follow_redirects = e.target.checked;
            });
        }

        const btnAddExclude = this.modalElement.querySelector('#btn-add-exclude');
        const inputExclude = this.modalElement.querySelector('#input-add-exclude');
        if (btnAddExclude && inputExclude) {
            btnAddExclude.addEventListener('click', () => {
                const val = inputExclude.value.trim();
                if (val && !this.config.exclude_patterns.includes(val)) {
                    this.config.exclude_patterns.push(val);
                    this.renderModal();
                }
            });
        }

        const btnRemoveRules = this.modalElement.querySelectorAll('.btn-remove-rule');
        btnRemoveRules.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
                this.config.exclude_patterns.splice(idx, 1);
                this.renderModal();
            });
        });

        // Step 5: Ignore UTM
        const chkUtm = this.modalElement.querySelector('#chk-ignore-utm');
        if (chkUtm) {
            chkUtm.addEventListener('change', (e) => {
                this.config.ignore_utm_params = e.target.checked;
            });
        }

        // Back / Next / Start Buttons
        const btnBack = this.modalElement.querySelector('#btn-wizard-back');
        if (btnBack) {
            btnBack.addEventListener('click', () => {
                if (this.currentStep > 1) {
                    this.currentStep--;
                    this.renderModal();
                }
            });
        }

        const btnNext = this.modalElement.querySelector('#btn-wizard-next');
        if (btnNext) {
            btnNext.addEventListener('click', () => {
                if (this.currentStep < this.totalSteps) {
                    this.currentStep++;
                    this.renderModal();
                }
            });
        }

        const btnStart = this.modalElement.querySelector('#btn-wizard-start');
        if (btnStart) {
            btnStart.addEventListener('click', async () => {
                btnStart.disabled = true;
                btnStart.innerText = 'Launching Real Crawler...';
                await this.executeCrawl();
            });
        }
    }

    async executeCrawl() {
        try {
            // Determine target crawl URL based on scope
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
            alert(`Backend API error starting crawl: ${e.message || 'Unable to start crawl.'}`);
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
