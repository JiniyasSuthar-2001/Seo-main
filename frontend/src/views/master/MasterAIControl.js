import { MasterService } from '../../services/master_service.js';

export class MasterAIControl {
  constructor() {
    this.element = document.createElement('div');
    this.element.className = 'master-ai-control-view';
    this.settings = null;
    this.budgets = null;
    this.loading = true;
    this.error = null;
  }

  async render() {
    await this.fetchData();
    this.updateView();
    return this.element;
  }

  updateView() {
    this.element.innerHTML = `
      <div>
        <div class="page-header" style="margin-bottom: 24px;">
          <div>
            <div class="master-badge" style="display: inline-flex; align-items: center; gap: 6px; background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); font-weight: 700; font-size: 11px; padding: 4px 8px; border-radius: 6px; margin-bottom: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
              <span>MASTER CONTROL</span>
            </div>
            <h1 class="page-title" style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 0 0 4px 0;">Platform AI Control & Kill Switches</h1>
            <p class="page-subtitle" style="font-size: 13px; color: var(--text-secondary); margin: 0;">Global enforcement layer for AI features, budgets, limits, and provider routing</p>
          </div>
          <div class="header-actions" style="margin-top: 12px;">
            <button class="btn btn-secondary" id="refreshControlBtn" style="padding: 6px 14px; font-size: 13px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); cursor: pointer;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
              <span>Refresh Status</span>
            </button>
          </div>
        </div>

        ${this.loading ? `
          <div class="loading-state" style="padding: 48px; text-align: center; color: var(--text-secondary);">
            <div class="spinner" style="margin: 0 auto 12px; width: 32px; height: 32px; border: 3px solid rgba(168, 85, 247, 0.2); border-top-color: #a855f7; border-radius: 50%; animation: spin 1s linear infinite;"></div>
            <p>Loading AI Control settings...</p>
          </div>
        ` : this.error ? `
          <div class="error-banner" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 14px 18px; border-radius: 8px; display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <span>${this.error}</span>
          </div>
        ` : `
          <!-- EMERGENCY KILL SWITCH BAR -->
          <div class="emergency-bar ${!this.settings?.global_ai_enabled ? 'emergency-active' : ''}">
            <div class="emergency-info">
              <div class="emergency-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
              </div>
              <div>
                <h3 class="emergency-title">GLOBAL PLATFORM KILL SWITCH</h3>
                <p class="emergency-desc">
                  ${this.settings?.global_ai_enabled 
                    ? 'Platform AI operations are currently active and authorized.' 
                    : '<strong style="color: #ef4444;">GLOBAL AI IS PAUSED. All incoming LLM requests across all customers will be rejected immediately at the gateway level.</strong>'}
                </p>
              </div>
            </div>
            <div class="emergency-controls">
              ${this.settings?.global_ai_enabled ? `
                <button class="btn btn-danger" id="pauseAllAiBtn" style="background: #ef4444; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 700; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>
                  <span>PAUSE ALL AI</span>
                </button>
              ` : `
                <button class="btn btn-success" id="resumeAllAiBtn" style="background: #10b981; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 700; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                  <span>RESUME ALL AI</span>
                </button>
              `}
            </div>
          </div>

          <!-- GRID SECTION: FEATURE SWITCHES + BUDGET CONTROL -->
          <div class="control-grid" style="margin-top: 20px;">
            <!-- CARD 1: FEATURE KILL SWITCHES -->
            <div class="card control-card">
              <div class="card-header">
                <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Feature Sub-System Switches</h3>
                <span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #a855f7; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px;">Enforcement Layer</span>
              </div>
              <div class="card-body">
                <div class="toggle-row">
                  <div class="toggle-label">
                    <span class="toggle-name">New AI Requests</span>
                    <span class="toggle-desc">Allow users to trigger new live AI solution and chat analyses</span>
                  </div>
                  <label class="switch">
                    <input type="checkbox" id="toggleNewRequests" ${this.settings?.new_requests_enabled ? 'checked' : ''}>
                    <span class="slider round"></span>
                  </label>
                </div>

                <div class="toggle-row">
                  <div class="toggle-label">
                    <span class="toggle-name">Background AI Tasks</span>
                    <span class="toggle-desc">Allow scheduled crawl AI enrichment and batch keyword background tasks</span>
                  </div>
                  <label class="switch">
                    <input type="checkbox" id="toggleBackgroundAi" ${this.settings?.background_ai_enabled ? 'checked' : ''}>
                    <span class="slider round"></span>
                  </label>
                </div>

                <div class="toggle-row">
                  <div class="toggle-label">
                    <span class="toggle-name">AI Executive Reports</span>
                    <span class="toggle-desc">Include AI narrative summaries in generated PDF/CSV reports</span>
                  </div>
                  <label class="switch">
                    <input type="checkbox" id="toggleAiReports" ${this.settings?.ai_reports_enabled ? 'checked' : ''}>
                    <span class="slider round"></span>
                  </label>
                </div>
              </div>
            </div>

            <!-- CARD 2: PLATFORM AI BUDGET CONTROL -->
            <div class="card control-card">
              <div class="card-header">
                <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Platform AI Budget Controls</h3>
                <span class="badge badge-${this.getBudgetBadgeColor()}" style="font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px;">${this.budgets?.platform_budget?.status || 'NORMAL'}</span>
              </div>
              <div class="card-body">
                <div class="budget-stat-row">
                  <div class="budget-stat">
                    <span class="b-label">Daily Budget Threshold</span>
                    <span class="b-val">$${this.settings?.daily_budget_usd || 50}</span>
                    <span class="b-used">Current Spend: $${this.budgets?.platform_budget?.daily_cost_usd || 0} (${this.budgets?.platform_budget?.daily_pct || 0}%)</span>
                  </div>
                  <div class="budget-stat">
                    <span class="b-label">Monthly Limit</span>
                    <span class="b-val">$${this.settings?.monthly_budget_usd || 1000}</span>
                    <span class="b-used">Current Spend: $${this.budgets?.platform_budget?.monthly_cost_usd || 0} (${this.budgets?.platform_budget?.monthly_pct || 0}%)</span>
                  </div>
                </div>

                <div class="form-group" style="margin-top: 14px;">
                  <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Monthly Budget Threshold ($USD)</label>
                  <input type="number" id="monthlyBudgetInput" class="form-control" value="${this.settings?.monthly_budget_usd || 1000}" min="1" step="50" style="width: 100%; padding: 8px 10px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px; box-sizing: border-box;">
                </div>

                <div class="form-group" style="margin-top: 10px;">
                  <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Daily Budget Threshold ($USD)</label>
                  <input type="number" id="dailyBudgetInput" class="form-control" value="${this.settings?.daily_budget_usd || 50}" min="1" step="10" style="width: 100%; padding: 8px 10px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px; box-sizing: border-box;">
                </div>

                <div class="toggle-row" style="margin-top: 10px; border-top: 1px solid #27272a; padding-top: 10px;">
                  <div class="toggle-label">
                    <span class="toggle-name">Hard Stop at 100% Budget</span>
                    <span class="toggle-desc">Automatically reject AI requests when budget limit is exhausted</span>
                  </div>
                  <label class="switch">
                    <input type="checkbox" id="toggleBudgetHardStop" ${this.settings?.budget_hard_stop ? 'checked' : ''}>
                    <span class="slider round"></span>
                  </label>
                </div>

                <button class="btn btn-primary" id="saveBudgetBtn" style="margin-top: 14px; width: 100%; padding: 8px 14px; background: #2563eb; color: #fff; border: none; border-radius: 6px; font-weight: 700; font-size: 13px; cursor: pointer;">
                  Save Budget Settings
                </button>
              </div>
            </div>

            <!-- CARD 3: PROVIDER ROUTING & FAILOVER -->
            <div class="card control-card" style="grid-column: span 2;">
              <div class="card-header">
                <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Provider Routing & Dynamic Failover</h3>
                <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px;">Gateway Architecture</span>
              </div>
              <div class="card-body">
                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
                  Configure primary LLM provider for normal reasoning and automated fallback provider if primary experiences timeouts or 5xx failures. Failure accounting guarantees <strong>zero double-charging</strong>.
                </p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                  <div class="form-group">
                    <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Primary Provider</label>
                    <select id="primaryProviderSelect" class="form-control" style="width: 100%; padding: 8px 10px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px;">
                      <option value="gemini" ${this.settings?.primary_provider === 'gemini' ? 'selected' : ''}>Google Gemini 2.5 Flash</option>
                      <option value="openai" ${this.settings?.primary_provider === 'openai' ? 'selected' : ''}>OpenAI GPT-4o / Mini</option>
                      <option value="groq" ${this.settings?.primary_provider === 'groq' ? 'selected' : ''}>Groq Llama-3 (High Speed)</option>
                      <option value="ollama" ${this.settings?.primary_provider === 'ollama' ? 'selected' : ''}>Ollama Local Private LLM</option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Fallback Provider (On Primary Failure)</label>
                    <select id="fallbackProviderSelect" class="form-control" style="width: 100%; padding: 8px 10px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px;">
                      <option value="ollama" ${this.settings?.fallback_provider === 'ollama' ? 'selected' : ''}>Ollama Local (Offline Fallback)</option>
                      <option value="gemini" ${this.settings?.fallback_provider === 'gemini' ? 'selected' : ''}>Google Gemini Flash</option>
                      <option value="groq" ${this.settings?.fallback_provider === 'groq' ? 'selected' : ''}>Groq Fast Platform LLM</option>
                    </select>
                  </div>
                </div>
                <button class="btn btn-secondary" id="saveRoutingBtn" style="margin-top: 14px; padding: 8px 14px; background: #27272a; color: #fff; border: 1px solid #3f3f46; border-radius: 6px; font-weight: 600; font-size: 13px; cursor: pointer;">
                  Save Provider Routing Rules
                </button>
              </div>
            </div>
          </div>
        `}
      </div>

      <style>
        .master-ai-control-view {
          padding: 24px;
          max-width: 1400px;
          margin: 0 auto;
        }
        .emergency-bar {
          background: #18181b;
          border: 1px solid #27272a;
          border-radius: 12px;
          padding: 20px 24px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          transition: all 0.25s ease;
        }
        .emergency-bar.emergency-active {
          background: rgba(239, 68, 68, 0.08);
          border-color: rgba(239, 68, 68, 0.4);
        }
        .emergency-info {
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .emergency-icon {
          width: 44px;
          height: 44px;
          border-radius: 10px;
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .emergency-title {
          font-size: 14px;
          font-weight: 800;
          letter-spacing: 0.05em;
          color: #ef4444;
          margin: 0;
        }
        .emergency-desc {
          font-size: 13px;
          color: var(--text-secondary, #a1a1aa);
          margin-top: 2px;
          margin-bottom: 0;
        }
        .control-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        .control-card {
          background: var(--card-bg, #18181b);
          border: 1px solid var(--border-color, #27272a);
          border-radius: 12px;
          padding: 20px;
        }
        .card-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-bottom: 14px;
          border-bottom: 1px solid var(--border-color, #27272a);
          margin-bottom: 16px;
        }
        .toggle-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 0;
        }
        .toggle-name {
          font-size: 14px;
          font-weight: 600;
          color: var(--text-main, #ffffff);
          display: block;
        }
        .toggle-desc {
          font-size: 12px;
          color: var(--text-muted, #a1a1aa);
        }
        .budget-stat-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 12px;
        }
        .budget-stat {
          background: rgba(255,255,255,0.03);
          border: 1px solid var(--border-color, #27272a);
          border-radius: 8px;
          padding: 12px;
        }
        .b-label {
          font-size: 11px;
          color: var(--text-muted, #a1a1aa);
          display: block;
        }
        .b-val {
          font-size: 20px;
          font-weight: 700;
          color: #38bdf8;
          display: block;
          margin: 2px 0;
        }
        .b-used {
          font-size: 11px;
          color: #a1a1aa;
        }
        .switch {
          position: relative;
          display: inline-block;
          width: 44px;
          height: 24px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
          position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
          background-color: #3f3f46; transition: .3s; border-radius: 24px;
        }
        .slider:before {
          position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px;
          background-color: white; transition: .3s; border-radius: 50%;
        }
        input:checked + .slider { background-color: #a855f7; }
        input:checked + .slider:before { transform: translateX(20px); }
        .badge-green { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .badge-yellow { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
        .badge-red { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      </style>
    `;

    this.bindEvents();
  }

  async fetchData() {
    this.loading = true;
    try {
      const [settingsRes, budgetsRes] = await Promise.all([
        MasterService.getAIControl(),
        MasterService.getBudgets()
      ]);
      this.settings = settingsRes;
      this.budgets = budgetsRes;
      this.loading = false;
      this.error = null;
    } catch (err) {
      this.error = err.message || 'Failed to load AI Control settings';
      this.loading = false;
    }
  }

  getBudgetBadgeColor() {
    const status = this.budgets?.platform_budget?.status;
    if (status === 'CRITICAL' || status === 'HARD_STOP') return 'red';
    if (status === 'WARNING') return 'yellow';
    return 'green';
  }

  bindEvents() {
    const refreshBtn = this.element.querySelector('#refreshControlBtn');
    if (refreshBtn) {
      refreshBtn.onclick = async () => {
        await this.fetchData();
        this.updateView();
      };
    }

    const pauseAllBtn = this.element.querySelector('#pauseAllAiBtn');
    if (pauseAllBtn) {
      pauseAllBtn.onclick = () => this.handleGlobalToggle(false, "Pause All AI (Emergency Kill Switch)");
    }

    const resumeAllBtn = this.element.querySelector('#resumeAllAiBtn');
    if (resumeAllBtn) {
      resumeAllBtn.onclick = () => this.handleGlobalToggle(true, "Resume All AI");
    }

    const toggleNewRequests = this.element.querySelector('#toggleNewRequests');
    if (toggleNewRequests) {
      toggleNewRequests.onchange = (e) => this.handleUpdateSetting({ new_requests_enabled: e.target.checked });
    }

    const toggleBackgroundAi = this.element.querySelector('#toggleBackgroundAi');
    if (toggleBackgroundAi) {
      toggleBackgroundAi.onchange = (e) => this.handleUpdateSetting({ background_ai_enabled: e.target.checked });
    }

    const toggleAiReports = this.element.querySelector('#toggleAiReports');
    if (toggleAiReports) {
      toggleAiReports.onchange = (e) => this.handleUpdateSetting({ ai_reports_enabled: e.target.checked });
    }

    const saveBudgetBtn = this.element.querySelector('#saveBudgetBtn');
    if (saveBudgetBtn) {
      saveBudgetBtn.onclick = () => {
        const monthly = parseFloat(this.element.querySelector('#monthlyBudgetInput').value);
        const daily = parseFloat(this.element.querySelector('#dailyBudgetInput').value);
        const hardStop = this.element.querySelector('#toggleBudgetHardStop').checked;
        this.handleUpdateSetting({
          monthly_budget_usd: monthly,
          daily_budget_usd: daily,
          budget_hard_stop: hardStop
        });
      };
    }

    const saveRoutingBtn = this.element.querySelector('#saveRoutingBtn');
    if (saveRoutingBtn) {
      saveRoutingBtn.onclick = async () => {
        const primary = this.element.querySelector('#primaryProviderSelect').value;
        const fallback = this.element.querySelector('#fallbackProviderSelect').value;
        if (confirm(`Confirm Provider Routing Update:\nPrimary: ${primary}\nFallback: ${fallback}`)) {
          try {
            await MasterService.updateProviderRouting({ primary_provider: primary, fallback_provider: fallback });
            alert("Provider routing rules updated successfully.");
            await this.fetchData();
            this.updateView();
          } catch (err) {
            alert(`Error updating routing rules: ${err.message}`);
          }
        }
      };
    }
  }

  async handleGlobalToggle(enabled, actionName) {
    if (confirm(`CRITICAL CONFIRMATION: Are you sure you want to execute '${actionName}'?\n\nThis will immediately ${enabled ? 'enable' : 'pause'} LLM request execution across all platform customers.`)) {
      try {
        await MasterService.updateAIControl({ global_ai_enabled: enabled, reason: actionName });
        await this.fetchData();
        this.updateView();
      } catch (err) {
        alert(`Error executing control action: ${err.message}`);
      }
    }
  }

  async handleUpdateSetting(payload) {
    try {
      await MasterService.updateAIControl(payload);
      await this.fetchData();
      this.updateView();
    } catch (err) {
      alert(`Error updating settings: ${err.message}`);
    }
  }
}
