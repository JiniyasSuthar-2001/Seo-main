import { MasterService } from '../../services/master_service.js';

export class MasterCredits {
  constructor() {
    this.element = document.createElement('div');
    this.element.className = 'master-credits-view';
    this.data = null;
    this.loading = true;
    this.error = null;
    this.search = '';
    this.page = 1;
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
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>
              <span>MASTER SPACE</span>
            </div>
            <h1 class="page-title" style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 0 0 4px 0;">AI Credit Wallets & Ledger</h1>
            <p class="page-subtitle" style="font-size: 13px; color: var(--text-secondary); margin: 0;">Centralized internal authorization accounting, balance allocation, and usage ledger</p>
          </div>
        </div>

        ${this.loading ? `
          <div class="loading-state" style="padding: 48px; text-align: center; color: var(--text-secondary);">
            <div class="spinner" style="margin: 0 auto 12px; width: 32px; height: 32px; border: 3px solid rgba(168, 85, 247, 0.2); border-top-color: #a855f7; border-radius: 50%; animation: spin 1s linear infinite;"></div>
            <p>Loading AI Credit Wallets & Transaction Ledger...</p>
          </div>
        ` : this.error ? `
          <div class="error-banner" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 14px 18px; border-radius: 8px; display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
            <span>${this.error}</span>
          </div>
        ` : `
          <!-- KPI SUMMARY ROW -->
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-title">TOTAL ALLOCATED</span>
              <span class="kpi-value">${(this.data?.summary?.total_allocated || 0).toLocaleString()}</span>
              <span class="kpi-sub">Total credits issued across accounts</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-title">TOTAL CONSUMED</span>
              <span class="kpi-value text-purple">${(this.data?.summary?.total_used || 0).toLocaleString()}</span>
              <span class="kpi-sub">Credits spent on AI requests</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-title">REMAINING BALANCE</span>
              <span class="kpi-value text-green">${(this.data?.summary?.total_remaining || 0).toLocaleString()}</span>
              <span class="kpi-sub">Available authorized credit pool</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-title">ACTIVE WALLETS</span>
              <span class="kpi-value">${this.data?.summary?.total_wallets || 0}</span>
              <span class="kpi-sub">Customer accounts with wallets</span>
            </div>
          </div>

          <!-- SEARCH & TABLE BAR -->
          <div class="card" style="margin-top: 20px; background: var(--card-bg, #18181b); border: 1px solid var(--border-color, #27272a); border-radius: 12px; overflow: hidden;">
            <div class="card-header" style="display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border-color, #27272a);">
              <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Customer AI Credit Wallets</h3>
              <div class="search-box">
                <input type="text" id="creditSearchInput" placeholder="Search by customer email..." value="${this.search}" class="form-control" style="width: 260px; padding: 8px 12px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px; font-size: 13px;">
              </div>
            </div>
            <div class="card-body" style="padding: 0; overflow-x: auto;">
              <table class="master-table" style="width: 100%; border-collapse: collapse; font-size: 13.5px;">
                <thead>
                  <tr style="background: rgba(255,255,255,0.02); text-align: left; font-weight: 600; color: var(--text-muted, #a1a1aa);">
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Customer</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Allocated</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Bonus</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Used</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Remaining</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Daily Limit</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Monthly Limit</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Status</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a; text-align: right;">Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${(this.data?.wallets && this.data.wallets.length > 0) ? this.data.wallets.map(w => `
                    <tr style="border-bottom: 1px solid #27272a;">
                      <td style="padding: 12px 16px;">
                        <strong style="color: var(--text-primary);">${w.customer_name || 'Customer'}</strong>
                        <div style="font-size: 11px; color: var(--text-muted, #a1a1aa);">${w.customer_email}</div>
                      </td>
                      <td style="padding: 12px 16px; color: var(--text-primary);">${(w.allocated_credits || 0).toLocaleString()}</td>
                      <td style="padding: 12px 16px; color: var(--text-primary);">${(w.bonus_credits || 0).toLocaleString()}</td>
                      <td style="padding: 12px 16px; color: var(--text-primary);">${(w.used_credits || 0).toLocaleString()}</td>
                      <td style="padding: 12px 16px;">
                        <strong style="color: ${w.remaining_credits > 0 ? '#10b981' : '#ef4444'};">
                          ${(w.remaining_credits || 0).toLocaleString()}
                        </strong>
                      </td>
                      <td style="padding: 12px 16px; color: var(--text-secondary);">${w.daily_limit ? w.daily_limit.toLocaleString() : 'Unlimited'}</td>
                      <td style="padding: 12px 16px; color: var(--text-secondary);">${w.monthly_limit ? w.monthly_limit.toLocaleString() : 'Unlimited'}</td>
                      <td style="padding: 12px 16px;">
                        <span class="badge badge-${w.is_enabled ? 'green' : 'red'}" style="font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px;">
                          ${w.status || (w.is_enabled ? 'ACTIVE' : 'DISABLED')}
                        </span>
                      </td>
                      <td style="padding: 12px 16px; text-align: right;">
                        <button class="btn btn-sm btn-secondary add-credits-btn" data-cid="${w.customer_id}" data-name="${w.customer_email}" style="padding: 4px 10px; font-size: 12px; margin-right: 4px; background: #27272a; color: #fff; border: 1px solid #3f3f46; border-radius: 4px; cursor: pointer;">
                          Add / Adjust
                        </button>
                        <button class="btn btn-sm btn-outline edit-limits-btn" data-cid="${w.customer_id}" data-enabled="${w.is_enabled}" data-daily="${w.daily_limit}" data-monthly="${w.monthly_limit}" style="padding: 4px 10px; font-size: 12px; background: transparent; color: #a1a1aa; border: 1px solid #3f3f46; border-radius: 4px; cursor: pointer;">
                          Limits
                        </button>
                      </td>
                    </tr>
                  `).join('') : `
                    <tr>
                      <td colspan="9" style="padding: 32px; text-align: center; color: var(--text-secondary);">No customer credit wallets found matching search.</td>
                    </tr>
                  `}
                </tbody>
              </table>
            </div>
          </div>

          <!-- RECENT TRANSACTIONS LEDGER -->
          <div class="card" style="margin-top: 24px; background: var(--card-bg, #18181b); border: 1px solid var(--border-color, #27272a); border-radius: 12px; overflow: hidden;">
            <div class="card-header" style="padding: 16px 20px; border-bottom: 1px solid var(--border-color, #27272a);">
              <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Immutable Credit Transaction Ledger</h3>
            </div>
            <div class="card-body" style="padding: 0; overflow-x: auto;">
              <table class="master-table" style="width: 100%; border-collapse: collapse; font-size: 13.5px;">
                <thead>
                  <tr style="background: rgba(255,255,255,0.02); text-align: left; font-weight: 600; color: var(--text-muted, #a1a1aa);">
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Date & Time</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Customer</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Type</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Amount</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Reason / Reference</th>
                    <th style="padding: 12px 16px; border-bottom: 1px solid #27272a;">Balance After</th>
                  </tr>
                </thead>
                <tbody>
                  ${(this.data?.recent_transactions && this.data.recent_transactions.length > 0) ? this.data.recent_transactions.map(tx => `
                    <tr style="border-bottom: 1px solid #27272a;">
                      <td style="padding: 12px 16px; font-size: 12px; color: var(--text-muted, #a1a1aa);">
                        ${new Date(tx.created_at).toLocaleString()}
                      </td>
                      <td style="padding: 12px 16px; color: var(--text-primary);">${tx.customer_email || tx.customer_id}</td>
                      <td style="padding: 12px 16px;">
                        <span class="badge badge-${tx.transaction_type === 'consumption' ? 'purple' : tx.transaction_type === 'allocation' ? 'green' : 'blue'}" style="font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px;">
                          ${tx.transaction_type}
                        </span>
                      </td>
                      <td style="padding: 12px 16px;">
                        <strong style="color: ${tx.amount < 0 || tx.transaction_type === 'consumption' ? '#ef4444' : '#10b981'};">
                          ${tx.amount > 0 ? '+' : ''}${tx.amount.toLocaleString()}
                        </strong>
                      </td>
                      <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary);">${tx.reason || tx.reference_id || 'N/A'}</td>
                      <td style="padding: 12px 16px; color: var(--text-primary);">${(tx.balance_after || 0).toLocaleString()}</td>
                    </tr>
                  `).join('') : `
                    <tr>
                      <td colspan="6" style="padding: 32px; text-align: center; color: var(--text-secondary);">No transaction ledger entries recorded.</td>
                    </tr>
                  `}
                </tbody>
              </table>
            </div>
          </div>
        `}
      </div>

      <!-- MODAL CONTAINER -->
      <div id="creditModalContainer"></div>

      <style>
        .master-credits-view { padding: 24px; max-width: 1400px; margin: 0 auto; }
        .kpi-grid {
          display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
        }
        .kpi-card {
          background: var(--card-bg, #18181b); border: 1px solid var(--border-color, #27272a);
          border-radius: 10px; padding: 16px;
        }
        .kpi-title { font-size: 11px; font-weight: 700; color: var(--text-muted, #a1a1aa); display: block; }
        .kpi-value { font-size: 24px; font-weight: 800; color: #fff; margin: 4px 0; display: block; }
        .kpi-sub { font-size: 11px; color: var(--text-muted, #a1a1aa); display: block; }
        .text-purple { color: #c084fc !important; }
        .text-green { color: #34d399 !important; }
        .badge-green { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .badge-red { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
        .badge-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
        .badge-blue { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
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
      this.data = await MasterService.getCreditsOverview(this.search, this.page);
      this.loading = false;
      this.error = null;
    } catch (err) {
      this.error = err.message || 'Failed to load credit wallets';
      this.loading = false;
    }
  }

  bindEvents() {
    const searchInput = this.element.querySelector('#creditSearchInput');
    if (searchInput) {
      let timeout;
      searchInput.oninput = (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(async () => {
          this.search = e.target.value;
          await this.fetchData();
          this.updateView();
        }, 400);
      };
    }

    const addBtns = this.element.querySelectorAll('.add-credits-btn');
    addBtns.forEach(btn => {
      btn.onclick = () => {
        const cid = btn.dataset.cid;
        const name = btn.dataset.name;
        this.openAddCreditsModal(cid, name);
      };
    });

    const editBtns = this.element.querySelectorAll('.edit-limits-btn');
    editBtns.forEach(btn => {
      btn.onclick = () => {
        const cid = btn.dataset.cid;
        const enabled = btn.dataset.enabled === 'true';
        const daily = btn.dataset.daily;
        const monthly = btn.dataset.monthly;
        this.openLimitsModal(cid, enabled, daily, monthly);
      };
    });
  }

  openAddCreditsModal(customer_id, customer_email) {
    const modalContainer = this.element.querySelector('#creditModalContainer');
    modalContainer.innerHTML = `
      <div class="modal-overlay" style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 999;">
        <div class="modal-card" style="background: #18181b; border: 1px solid #27272a; border-radius: 12px; width: 440px; padding: 24px;">
          <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 4px; color: #fff;">Allocate / Adjust Credits</h3>
          <p style="font-size: 12px; color: #a1a1aa; margin-bottom: 16px;">Target Customer: <strong>${customer_email}</strong></p>
          
          <div class="form-group" style="margin-bottom: 12px;">
            <label style="font-size: 12px; color: #a1a1aa; display: block; margin-bottom: 4px;">Transaction Type</label>
            <select id="modalType" class="form-control" style="width: 100%; padding: 8px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px;">
              <option value="allocation">Allocation (Plan Upgrade / Top-up)</option>
              <option value="bonus">Bonus Credits</option>
              <option value="adjustment">Manual Adjustment (+ / -)</option>
              <option value="refund">Credit Refund</option>
            </select>
          </div>

          <div class="form-group" style="margin-bottom: 12px;">
            <label style="font-size: 12px; color: #a1a1aa; display: block; margin-bottom: 4px;">Credit Amount</label>
            <input type="number" id="modalAmount" class="form-control" placeholder="e.g. 50000 or -500" required style="width: 100%; padding: 8px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px; box-sizing: border-box;">
            <small id="modalAmountHint" style="font-size: 11px; color: #71717a; display: block; margin-top: 4px;">Enter positive number for additions, negative number for deductions</small>
          </div>

          <div class="form-group" style="margin-bottom: 16px;">
            <label style="font-size: 12px; color: #a1a1aa; display: block; margin-bottom: 4px;">Reason for Credit Change (Audit Log Mandatory)</label>
            <input type="text" id="modalReason" class="form-control" placeholder="e.g. Upgrade to Pro Tier or Compensation" required style="width: 100%; padding: 8px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px; box-sizing: border-box;">
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button class="btn btn-secondary" id="closeCreditModalBtn" style="padding: 8px 14px; background: #27272a; color: #fff; border: 1px solid #3f3f46; border-radius: 6px; cursor: pointer;">Cancel</button>
            <button class="btn btn-primary" id="confirmCreditModalBtn" style="padding: 8px 14px; background: #2563eb; color: #fff; border: none; border-radius: 6px; font-weight: 700; cursor: pointer;">Confirm Action</button>
          </div>
        </div>
      </div>
    `;

    const typeSelect = modalContainer.querySelector('#modalType');
    const amountInput = modalContainer.querySelector('#modalAmount');
    const hintText = modalContainer.querySelector('#modalAmountHint');

    typeSelect.onchange = () => {
      if (typeSelect.value === 'adjustment') {
        hintText.innerText = 'For adjustments, enter + amount to add or - amount to deduct (e.g. +1000 or -1000).';
        amountInput.placeholder = 'e.g. +1000 or -1000';
      } else {
        hintText.innerText = 'Enter positive credit amount.';
        amountInput.placeholder = 'e.g. 50000';
      }
    };

    modalContainer.querySelector('#closeCreditModalBtn').onclick = () => { modalContainer.innerHTML = ''; };
    modalContainer.querySelector('#confirmCreditModalBtn').onclick = async () => {
      const amount = parseInt(modalContainer.querySelector('#modalAmount').value);
      const type = typeSelect.value;
      const reason = modalContainer.querySelector('#modalReason').value.trim();

      if (type === 'adjustment') {
        if (isNaN(amount) || amount === 0) {
          alert("Please enter a valid non-zero adjustment amount (e.g. +1000 or -1000).");
          return;
        }
      } else {
        if (isNaN(amount) || amount <= 0) {
          alert("Please enter a valid positive credit amount.");
          return;
        }
      }

      if (!reason) {
        alert("Please specify a reason for audit logging.");
        return;
      }

      try {
        await MasterService.allocateCustomerCredits(customer_id, amount, type, reason);
        alert("Credits updated successfully!");
        modalContainer.innerHTML = '';
        await this.fetchData();
        this.updateView();
      } catch (err) {
        alert(`Error updating credits: ${err.message}`);
      }
    };
  }

  openLimitsModal(customer_id, is_enabled, daily_limit, monthly_limit) {
    const modalContainer = this.element.querySelector('#creditModalContainer');
    modalContainer.innerHTML = `
      <div class="modal-overlay" style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 999;">
        <div class="modal-card" style="background: #18181b; border: 1px solid #27272a; border-radius: 12px; width: 440px; padding: 24px;">
          <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 4px; color: #fff;">Customer AI Limits & Controls</h3>
          <p style="font-size: 12px; color: #a1a1aa; margin-bottom: 16px;">Configure account enforcement policies</p>
          
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; background: rgba(255,255,255,0.03); padding: 10px 12px; border-radius: 8px;">
            <span style="font-size: 13px; font-weight: 600; color: #fff;">Enable Customer AI</span>
            <input type="checkbox" id="modalAiEnabled" ${is_enabled ? 'checked' : ''} style="width: 18px; height: 18px; cursor: pointer;">
          </div>

          <div class="form-group" style="margin-bottom: 12px;">
            <label style="font-size: 12px; color: #a1a1aa; display: block; margin-bottom: 4px;">Daily Credit Limit</label>
            <input type="number" id="modalDailyLimit" class="form-control" value="${daily_limit || 5000}" style="width: 100%; padding: 8px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px; box-sizing: border-box;">
          </div>

          <div class="form-group" style="margin-bottom: 16px;">
            <label style="font-size: 12px; color: #a1a1aa; display: block; margin-bottom: 4px;">Monthly Credit Limit</label>
            <input type="number" id="modalMonthlyLimit" class="form-control" value="${monthly_limit || 50000}" style="width: 100%; padding: 8px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px; box-sizing: border-box;">
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button class="btn btn-secondary" id="closeLimitsModalBtn" style="padding: 8px 14px; background: #27272a; color: #fff; border: 1px solid #3f3f46; border-radius: 6px; cursor: pointer;">Cancel</button>
            <button class="btn btn-primary" id="confirmLimitsModalBtn" style="padding: 8px 14px; background: #2563eb; color: #fff; border: none; border-radius: 6px; font-weight: 700; cursor: pointer;">Save Limits</button>
          </div>
        </div>
      </div>
    `;

    modalContainer.querySelector('#closeLimitsModalBtn').onclick = () => { modalContainer.innerHTML = ''; };
    modalContainer.querySelector('#confirmLimitsModalBtn').onclick = async () => {
      const enabled = modalContainer.querySelector('#modalAiEnabled').checked;
      const daily = parseInt(modalContainer.querySelector('#modalDailyLimit').value);
      const monthly = parseInt(modalContainer.querySelector('#modalMonthlyLimit').value);

      try {
        await MasterService.updateCustomerAISettings(customer_id, {
          is_enabled: enabled,
          daily_limit: daily,
          monthly_limit: monthly,
          reason: "Master Admin AI Limit Update"
        });
        alert("Customer AI limits saved successfully!");
        modalContainer.innerHTML = '';
        await this.fetchData();
        this.updateView();
      } catch (err) {
        alert(`Error updating limits: ${err.message}`);
      }
    };
  }
}
