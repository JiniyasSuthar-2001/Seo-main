import { MasterService } from '../../services/master_service.js';

export class MasterCredits {
  constructor() {
    this.data = null;
    this.loading = true;
    this.error = null;
    this.search = '';
    this.page = 1;
  }

  async render(container) {
    this.container = container;
    await this.fetchData();

    container.innerHTML = `
      <div class="master-credits-view">
        <div class="page-header">
          <div>
            <div class="master-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>
              <span>MASTER SPACE</span>
            </div>
            <h1 class="page-title">AI Credit Wallets & Ledger</h1>
            <p class="page-subtitle">Centralized internal authorization accounting, balance allocation, and usage ledger</p>
          </div>
        </div>

        ${this.loading ? `
          <div class="loading-state">
            <div class="spinner"></div>
            <p>Loading AI Credit Wallets & Transaction Ledger...</p>
          </div>
        ` : this.error ? `
          <div class="error-banner">
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
          <div class="card" style="margin-top: 20px;">
            <div class="card-header" style="display: flex; align-items: center; justify-content: space-between;">
              <h3>Customer AI Credit Wallets</h3>
              <div class="search-box">
                <input type="text" id="creditSearchInput" placeholder="Search by customer email..." value="${this.search}" class="form-control" style="width: 260px;">
              </div>
            </div>
            <div class="card-body" style="padding: 0;">
              <table class="master-table">
                <thead>
                  <tr>
                    <th>Customer</th>
                    <th>Allocated</th>
                    <th>Bonus</th>
                    <th>Used</th>
                    <th>Remaining</th>
                    <th>Daily Limit</th>
                    <th>Monthly Limit</th>
                    <th>Status</th>
                    <th style="text-align: right;">Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${(this.data?.wallets || []).map(w => `
                    <tr>
                      <td>
                        <strong>${w.customer_name || 'Customer'}</strong>
                        <div style="font-size: 11px; color: var(--text-muted);">${w.customer_email}</div>
                      </td>
                      <td>${(w.allocated_credits || 0).toLocaleString()}</td>
                      <td>${(w.bonus_credits || 0).toLocaleString()}</td>
                      <td>${(w.used_credits || 0).toLocaleString()}</td>
                      <td>
                        <strong style="color: ${w.remaining_credits > 0 ? '#10b981' : '#ef4444'};">
                          ${(w.remaining_credits || 0).toLocaleString()}
                        </strong>
                      </td>
                      <td>${w.daily_limit ? w.daily_limit.toLocaleString() : 'Unlimited'}</td>
                      <td>${w.monthly_limit ? w.monthly_limit.toLocaleString() : 'Unlimited'}</td>
                      <td>
                        <span class="badge badge-${w.is_enabled ? 'green' : 'red'}">
                          ${w.status || (w.is_enabled ? 'ACTIVE' : 'DISABLED')}
                        </span>
                      </td>
                      <td style="text-align: right;">
                        <button class="btn btn-sm btn-secondary add-credits-btn" data-cid="${w.customer_id}" data-name="${w.customer_email}">
                          Add / Adjust
                        </button>
                        <button class="btn btn-sm btn-outline edit-limits-btn" data-cid="${w.customer_id}" data-enabled="${w.is_enabled}" data-daily="${w.daily_limit}" data-monthly="${w.monthly_limit}">
                          Limits
                        </button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>

          <!-- RECENT TRANSACTIONS LEDGER -->
          <div class="card" style="margin-top: 24px;">
            <div class="card-header">
              <h3>Immutable Credit Transaction Ledger</h3>
            </div>
            <div class="card-body" style="padding: 0;">
              <table class="master-table">
                <thead>
                  <tr>
                    <th>Date & Time</th>
                    <th>Customer</th>
                    <th>Type</th>
                    <th>Amount</th>
                    <th>Reason / Reference</th>
                    <th>Balance After</th>
                  </tr>
                </thead>
                <tbody>
                  ${(this.data?.recent_transactions || []).map(tx => `
                    <tr>
                      <td style="font-size: 12px; color: var(--text-muted);">
                        ${new Date(tx.created_at).toLocaleString()}
                      </td>
                      <td>${tx.customer_email || tx.customer_id}</td>
                      <td>
                        <span class="badge badge-${tx.transaction_type === 'consumption' ? 'purple' : tx.transaction_type === 'allocation' ? 'green' : 'blue'}">
                          ${tx.transaction_type}
                        </span>
                      </td>
                      <td>
                        <strong style="color: ${tx.amount < 0 || tx.transaction_type === 'consumption' ? '#ef4444' : '#10b981'};">
                          ${tx.amount > 0 ? '+' : ''}${tx.amount.toLocaleString()}
                        </strong>
                      </td>
                      <td style="font-size: 12px;">${tx.reason || tx.reference_id || 'N/A'}</td>
                      <td>${(tx.balance_after || 0).toLocaleString()}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        `}
      </div>

      <!-- ADD CREDITS MODAL CONTAINER -->
      <div id="creditModalContainer"></div>

      <style>
        .master-credits-view { padding: 24px; }
        .kpi-grid {
          display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
        }
        .kpi-card {
          background: var(--card-bg, #18181b); border: 1px solid var(--border-color, #27272a);
          border-radius: 10px; padding: 16px;
        }
        .kpi-title { font-size: 11px; font-weight: 700; color: var(--text-muted); }
        .kpi-value { font-size: 24px; font-weight: 800; color: #fff; margin: 4px 0; }
        .kpi-sub { font-size: 11px; color: var(--text-muted); }
        .text-purple { color: #c084fc !important; }
        .text-green { color: #34d399 !important; }
        .master-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
        .master-table th, .master-table td { padding: 12px 16px; border-bottom: 1px solid var(--border-color, #27272a); }
        .master-table th { background: rgba(255,255,255,0.02); text-align: left; font-weight: 600; color: var(--text-muted); }
      </style>
    `;

    this.bindEvents();
  }

  async fetchData() {
    this.loading = true;
    try {
      this.data = await MasterService.getCreditsOverview(this.search, this.page);
      this.loading = false;
    } catch (err) {
      this.error = err.message || 'Failed to load credit wallets';
      this.loading = false;
    }
  }

  bindEvents() {
    const searchInput = this.container.querySelector('#creditSearchInput');
    if (searchInput) {
      let timeout;
      searchInput.oninput = (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          this.search = e.target.value;
          this.render(this.container);
        }, 400);
      };
    }

    const addBtns = this.container.querySelectorAll('.add-credits-btn');
    addBtns.forEach(btn => {
      btn.onclick = () => {
        const cid = btn.dataset.cid;
        const name = btn.dataset.name;
        this.openAddCreditsModal(cid, name);
      };
    });

    const editBtns = this.container.querySelectorAll('.edit-limits-btn');
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
    const modalContainer = this.container.querySelector('#creditModalContainer');
    modalContainer.innerHTML = `
      <div class="modal-overlay" style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 999;">
        <div class="modal-card" style="background: #18181b; border: 1px solid #27272a; border-radius: 12px; width: 440px; padding: 24px;">
          <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">Allocate / Adjust Credits</h3>
          <p style="font-size: 12px; color: #a1a1aa; margin-bottom: 16px;">Target Customer: <strong>${customer_email}</strong></p>
          
          <div class="form-group" style="margin-bottom: 12px;">
            <label style="font-size: 12px; color: #a1a1aa;">Transaction Type</label>
            <select id="modalType" class="form-control" style="width: 100%; padding: 8px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px;">
              <option value="allocation">Allocation (Plan Upgrade / Top-up)</option>
              <option value="bonus">Bonus Credits</option>
              <option value="adjustment">Manual Adjustment (+ / -)</option>
              <option value="refund">Credit Refund</option>
            </select>
          </div>

          <div class="form-group" style="margin-bottom: 12px;">
            <label style="font-size: 12px; color: #a1a1aa;">Credit Amount</label>
            <input type="number" id="modalAmount" class="form-control" placeholder="e.g. 50000 or -500" required style="width: 100%; padding: 8px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px;">
            <small id="modalAmountHint" style="font-size: 11px; color: #71717a; display: block; margin-top: 4px;">Enter positive number for additions, negative number for deductions</small>
          </div>

          <div class="form-group" style="margin-bottom: 16px;">
            <label style="font-size: 12px; color: #a1a1aa;">Reason for Credit Change (Audit Log Mandatory)</label>
            <input type="text" id="modalReason" class="form-control" placeholder="e.g. Upgrade to Pro Tier or Compensation" required style="width: 100%; padding: 8px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px;">
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button class="btn btn-secondary" id="closeCreditModalBtn">Cancel</button>
            <button class="btn btn-primary" id="confirmCreditModalBtn">Confirm Action</button>
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
        this.render(this.container);
      } catch (err) {
        alert(`Error updating credits: ${err.message}`);
      }
    };
  }


  openLimitsModal(customer_id, is_enabled, daily_limit, monthly_limit) {
    const modalContainer = this.container.querySelector('#creditModalContainer');
    modalContainer.innerHTML = `
      <div class="modal-overlay" style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 999;">
        <div class="modal-card" style="background: #18181b; border: 1px solid #27272a; border-radius: 12px; width: 440px; padding: 24px;">
          <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">Customer AI Limits & Controls</h3>
          <p style="font-size: 12px; color: #a1a1aa; margin-bottom: 16px;">Configure account enforcement policies</p>
          
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; background: rgba(255,255,255,0.03); padding: 10px 12px; border-radius: 8px;">
            <span style="font-size: 13px; font-weight: 600;">Enable Customer AI</span>
            <input type="checkbox" id="modalAiEnabled" ${is_enabled ? 'checked' : ''} style="width: 18px; height: 18px;">
          </div>

          <div class="form-group" style="margin-bottom: 12px;">
            <label style="font-size: 12px; color: #a1a1aa;">Daily Credit Limit</label>
            <input type="number" id="modalDailyLimit" class="form-control" value="${daily_limit || 5000}" style="width: 100%; padding: 8px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px;">
          </div>

          <div class="form-group" style="margin-bottom: 16px;">
            <label style="font-size: 12px; color: #a1a1aa;">Monthly Credit Limit</label>
            <input type="number" id="modalMonthlyLimit" class="form-control" value="${monthly_limit || 50000}" style="width: 100%; padding: 8px; background: #09090b; border: 1px solid #27272a; color: #fff; border-radius: 6px;">
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button class="btn btn-secondary" id="closeLimitsModalBtn">Cancel</button>
            <button class="btn btn-primary" id="confirmLimitsModalBtn">Save Limits</button>
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
        this.render(this.container);
      } catch (err) {
        alert(`Error updating limits: ${err.message}`);
      }
    };
  }
}
