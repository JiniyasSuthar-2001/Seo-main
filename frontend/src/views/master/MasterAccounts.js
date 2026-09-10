import { apiClient } from '../../services/apiClient.js';
import { authStore } from '../../core/authStore.js';

export class MasterAccounts {
  constructor() {
    this.element = document.createElement('div');
    this.element.className = 'master-accounts-view';
    this.accounts = [];
    this.permissionGroups = [];
    this.allPermissions = [];
    this.searchQuery = '';
    this.roleFilter = 'all';
    this.statusFilter = 'all';
    this.currentPage = 1;
    this.totalAccounts = 0;
    this.activeModal = null;
  }

  async render() {
    this.element.innerHTML = `
      <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
        
        <!-- HEADER -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
          <div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); font-weight: 700; font-size: 11px; padding: 3px 8px; border-radius: 6px;">ADMINISTRATION</span>
              <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; font-size: 11px; font-weight: 600;">Role: ${authStore.user?.platform_role || 'SUPER_MASTER'}</span>
            </div>
            <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 6px 0 0 0;">Master Account Management</h1>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 4px 0 0 0;">Create and delegate administrative access with full or selective Master permissions</p>
          </div>

          <!-- CREATE MASTER ACCOUNT BUTTON -->
          <div>
            <button id="btn-open-create-account" class="btn btn-primary" style="display: flex; align-items: center; gap: 8px; font-weight: 700; background: linear-gradient(135deg, #9333ea, #6366f1); border: none; padding: 10px 18px; border-radius: 8px; color: #fff; cursor: pointer; box-shadow: 0 4px 14px rgba(147, 51, 234, 0.3);">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
              <span>Create Master Account</span>
            </button>
          </div>
        </div>

        <!-- TOP METRICS GRID -->
        <div id="master-accounts-metrics" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">
          <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Total Master Accounts</div>
            <div id="metric-total-accounts" style="font-size: 28px; font-weight: 800; color: #a855f7; margin-top: 4px;">-</div>
            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Administrative identities</div>
          </div>
          <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Super Masters</div>
            <div id="metric-super-masters" style="font-size: 28px; font-weight: 800; color: #3b82f6; margin-top: 4px;">-</div>
            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Full root authority</div>
          </div>
          <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Master Admins</div>
            <div id="metric-master-admins" style="font-size: 28px; font-weight: 800; color: #10b981; margin-top: 4px;">-</div>
            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Selective / Full delegated</div>
          </div>
          <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Active Accounts</div>
            <div id="metric-active-accounts" style="font-size: 28px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">-</div>
            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Ready for authentication</div>
          </div>
        </div>

        <!-- SEARCH & FILTER BAR -->
        <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border); margin-bottom: 20px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
          <div style="flex: 1; min-width: 240px; position: relative;">
            <input 
              type="text" 
              id="input-account-search" 
              placeholder="Search by Master ID, name, or email..." 
              value="${this.searchQuery}"
              style="width: 100%; padding: 9px 12px 9px 36px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 13px; color: var(--text-primary); outline: none;"
            />
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 12px; top: 11px; color: var(--text-secondary);">
              <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </div>

          <div style="display: flex; gap: 8px;">
            <select id="select-role-filter" style="padding: 8px 12px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 12.5px; font-weight: 600; color: var(--text-primary); outline: none;">
              <option value="all">All Roles</option>
              <option value="SUPER_MASTER">SUPER_MASTER</option>
              <option value="MASTER_ADMIN">MASTER_ADMIN</option>
            </select>

            <select id="select-status-filter" style="padding: 8px 12px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 12.5px; font-weight: 600; color: var(--text-primary); outline: none;">
              <option value="all">All Status</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="DISABLED">DISABLED</option>
            </select>
          </div>
        </div>

        <!-- ACCOUNTS TABLE CONTAINER -->
        <div id="accounts-table-container" class="card" style="padding: 0; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border); overflow: hidden;">
          <div style="padding: 32px; text-align: center; color: var(--text-secondary);">Loading Master accounts...</div>
        </div>

        <!-- MODALS CONTAINER -->
        <div id="master-modal-container"></div>
      </div>
    `;

    this.bindEvents();
    this.loadPermissions();
    this.fetchAccounts();
    return this.element;
  }

  bindEvents() {
    const searchInput = this.element.querySelector('#input-account-search');
    const roleSelect = this.element.querySelector('#select-role-filter');
    const statusSelect = this.element.querySelector('#select-status-filter');
    const createBtn = this.element.querySelector('#btn-open-create-account');

    if (searchInput) {
      let timeout;
      searchInput.oninput = (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          this.searchQuery = e.target.value.trim();
          this.currentPage = 1;
          this.fetchAccounts();
        }, 300);
      };
    }

    if (roleSelect) {
      roleSelect.onchange = (e) => {
        this.roleFilter = e.target.value;
        this.currentPage = 1;
        this.fetchAccounts();
      };
    }

    if (statusSelect) {
      statusSelect.onchange = (e) => {
        this.statusFilter = e.target.value;
        this.currentPage = 1;
        this.fetchAccounts();
      };
    }

    if (createBtn) {
      createBtn.onclick = () => this.openCreateAccountModal();
    }
  }

  async loadPermissions() {
    try {
      const data = await apiClient.get('/api/master/permissions');
      this.permissionGroups = data.groups || [];
      this.allPermissions = data.all_permissions || [];
    } catch (err) {
      console.warn('[MASTER ACCOUNTS] Error loading permissions catalog:', err);
    }
  }

  async fetchAccounts() {
    const tableContainer = this.element.querySelector('#accounts-table-container');
    try {
      const res = await apiClient.get(`/api/master/accounts?search=${encodeURIComponent(this.searchQuery)}&role=${this.roleFilter}&status=${this.statusFilter}&page=${this.currentPage}&page_size=20`);
      this.accounts = res.items || [];
      this.totalAccounts = res.total || 0;
      this.updateMetrics();
      this.renderTable();
    } catch (err) {
      console.error('[MASTER ACCOUNTS] Fetch error:', err);
      if (tableContainer) {
        tableContainer.innerHTML = `
          <div style="padding: 32px; text-align: center; color: #ef4444;">
            <h3>Failed to load Master accounts</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">${err.message || 'Access denied or network error.'}</p>
          </div>
        `;
      }
    }
  }

  updateMetrics() {
    const totalEl = this.element.querySelector('#metric-total-accounts');
    const superEl = this.element.querySelector('#metric-super-masters');
    const adminEl = this.element.querySelector('#metric-master-admins');
    const activeEl = this.element.querySelector('#metric-active-accounts');

    let superCount = 0;
    let adminCount = 0;
    let activeCount = 0;

    this.accounts.forEach(acc => {
      const role = (acc.role || '').toUpperCase();
      const status = (acc.status || '').toUpperCase();
      if (role === 'SUPER_MASTER' || role === 'SUPER_ADMIN') superCount++;
      else adminCount++;
      if (status === 'ACTIVE') activeCount++;
    });

    if (totalEl) totalEl.innerText = this.totalAccounts;
    if (superEl) superEl.innerText = superCount;
    if (adminEl) adminEl.innerText = adminCount;
    if (activeEl) activeEl.innerText = activeCount;
  }

  renderTable() {
    const tableContainer = this.element.querySelector('#accounts-table-container');
    if (!tableContainer) return;

    if (this.accounts.length === 0) {
      tableContainer.innerHTML = `
        <div style="padding: 48px 24px; text-align: center; color: var(--text-secondary);">
          <div style="font-size: 32px; margin-bottom: 8px;">👥</div>
          <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">No Master Accounts Found</h3>
          <p style="font-size: 13px; margin: 0;">Try adjusting your search criteria or create a new Master Admin account.</p>
        </div>
      `;
      return;
    }

    tableContainer.innerHTML = `
      <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
        <thead>
          <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11.5px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.04em;">
            <th style="padding: 14px 18px;">Master Identity</th>
            <th style="padding: 14px 18px;">Role</th>
            <th style="padding: 14px 18px;">Status</th>
            <th style="padding: 14px 18px;">Authority / Permissions</th>
            <th style="padding: 14px 18px;">Last Login</th>
            <th style="padding: 14px 18px; text-align: right;">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${this.accounts.map(acc => this.renderAccountRow(acc)).join('')}
        </tbody>
      </table>
    `;

    this.bindRowActions();
  }

  renderAccountRow(acc) {
    const isSuper = ['SUPER_MASTER', 'SUPER_ADMIN'].includes((acc.role || '').toUpperCase());
    const isActive = (acc.status || '').toUpperCase() === 'ACTIVE';
    const isSelf = authStore.user?.id === acc.id;

    const perms = acc.permissions || [];
    const isFullAuth = isSuper || perms.includes('*') || perms.includes('ALL') || perms.length >= 20;
    const permBadge = isFullAuth
      ? `<span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); font-weight: 700; font-size: 11px;">⚡ Full Authority</span>`
      : `<span class="badge" style="background: rgba(59, 130, 246, 0.12); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.25); font-weight: 600; font-size: 11px;">${perms.length} Permissions</span>`;

    const statusBadge = isActive
      ? `<span class="badge badge-success" style="font-size: 11px;">Active</span>`
      : `<span class="badge badge-critical" style="font-size: 11px;">Disabled</span>`;

    const roleBadge = isSuper
      ? `<span class="badge" style="background: linear-gradient(135deg, rgba(147, 51, 234, 0.2), rgba(99, 102, 241, 0.2)); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); font-weight: 800; font-size: 11px;">SUPER_MASTER</span>`
      : `<span class="badge" style="background: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.25); font-weight: 700; font-size: 11px;">MASTER_ADMIN</span>`;

    const lastLoginStr = acc.last_login_at ? acc.last_login_at.replace('T', ' ').split('.')[0] : 'Never';

    return `
      <tr style="border-bottom: 1px solid var(--border); transition: background-color 0.12s ease;">
        <td style="padding: 14px 18px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 34px; height: 34px; border-radius: 50%; background: ${isSuper ? 'linear-gradient(135deg, #9333ea, #6366f1)' : 'var(--bg-subtle)'}; color: ${isSuper ? '#fff' : 'var(--text-primary)'}; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; border: 1px solid var(--border);">
              ${(acc.name || acc.id || 'M').charAt(0).toUpperCase()}
            </div>
            <div>
              <div style="font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
                <span>${this.escapeHtml(acc.name || acc.id)}</span>
                ${isSelf ? '<span style="font-size: 9.5px; background: var(--bg-subtle); padding: 1px 5px; border-radius: 4px; color: var(--text-tertiary);">You</span>' : ''}
              </div>
              <div style="font-size: 11.5px; color: var(--text-secondary); font-family: monospace;">${this.escapeHtml(acc.id)}</div>
            </div>
          </div>
        </td>
        <td style="padding: 14px 18px;">${roleBadge}</td>
        <td style="padding: 14px 18px;">${statusBadge}</td>
        <td style="padding: 14px 18px;">${permBadge}</td>
        <td style="padding: 14px 18px; font-size: 12px; color: var(--text-secondary); font-family: monospace;">${lastLoginStr}</td>
        <td style="padding: 14px 18px; text-align: right;">
          <div style="display: inline-flex; align-items: center; gap: 6px;">
            <button class="btn btn-secondary btn-sm btn-edit-account" data-id="${acc.id}" title="Edit Profile & Permissions" style="padding: 4px 8px; font-size: 12px;">
              Edit
            </button>
            ${!isSuper && !isSelf ? `
              <button class="btn btn-secondary btn-sm btn-toggle-status" data-id="${acc.id}" data-action="${isActive ? 'disable' : 'enable'}" title="${isActive ? 'Disable Master Access' : 'Enable Master Access'}" style="padding: 4px 8px; font-size: 12px; color: ${isActive ? '#ef4444' : '#10b981'};">
                ${isActive ? 'Disable' : 'Enable'}
              </button>
            ` : ''}
            <button class="btn btn-secondary btn-sm btn-revoke-sessions" data-id="${acc.id}" title="Revoke Active JWT Sessions" style="padding: 4px 8px; font-size: 12px;">
              Revoke
            </button>
            ${!isSuper && !isSelf ? `
              <button class="btn btn-secondary btn-sm btn-delete-account" data-id="${acc.id}" title="Delete Master Account" style="padding: 4px 8px; font-size: 12px; color: #ef4444;">
                ✕
              </button>
            ` : ''}
          </div>
        </td>
      </tr>
    `;
  }

  bindRowActions() {
    this.element.querySelectorAll('.btn-edit-account').forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute('data-id');
        const acc = this.accounts.find(a => a.id === id);
        if (acc) this.openEditAccountModal(acc);
      };
    });

    this.element.querySelectorAll('.btn-toggle-status').forEach(btn => {
      btn.onclick = async () => {
        const id = btn.getAttribute('data-id');
        const action = btn.getAttribute('data-action');
        const confirmMsg = action === 'disable'
          ? `Disable Master account '${id}'? This will immediately revoke all active sessions.`
          : `Enable Master account '${id}'?`;
        
        if (confirm(confirmMsg)) {
          try {
            await apiClient.post(`/api/master/accounts/${encodeURIComponent(id)}/${action}`);
            await this.fetchAccounts();
          } catch (err) {
            alert(err.message || 'Operation failed.');
          }
        }
      };
    });

    this.element.querySelectorAll('.btn-revoke-sessions').forEach(btn => {
      btn.onclick = async () => {
        const id = btn.getAttribute('data-id');
        if (confirm(`Revoke all active sessions for Master account '${id}'? The user will be required to log in again.`)) {
          try {
            await apiClient.post(`/api/master/accounts/${encodeURIComponent(id)}/revoke-sessions`);
            alert(`Sessions revoked for '${id}'.`);
            await this.fetchAccounts();
          } catch (err) {
            alert(err.message || 'Revocation failed.');
          }
        }
      };
    });

    this.element.querySelectorAll('.btn-delete-account').forEach(btn => {
      btn.onclick = async () => {
        const id = btn.getAttribute('data-id');
        if (confirm(`PERMANENT ACTION: Delete Master account '${id}'? This cannot be undone.`)) {
          try {
            await apiClient.delete(`/api/master/accounts/${encodeURIComponent(id)}`);
            await this.fetchAccounts();
          } catch (err) {
            alert(err.message || 'Deletion failed.');
          }
        }
      };
    });
  }

  openCreateAccountModal() {
    const modalContainer = this.element.querySelector('#master-modal-container');
    if (!modalContainer) return;

    modalContainer.innerHTML = `
      <div style="position: fixed; inset: 0; background: rgba(0, 0, 0, 0.65); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; backdrop-filter: blur(4px);">
        <div class="card" style="background: var(--bg-card); width: 100%; max-width: 680px; max-height: 90vh; border-radius: 16px; border: 1px solid rgba(168, 85, 247, 0.3); display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);">
          
          <!-- MODAL HEADER -->
          <div style="padding: 20px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h2 style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin: 0;">Create Master Account</h2>
              <p style="font-size: 12.5px; color: var(--text-secondary); margin: 2px 0 0 0;">Provision a new Master Admin with full or selective authority</p>
            </div>
            <button id="btn-close-modal" style="background: none; border: none; font-size: 20px; color: var(--text-secondary); cursor: pointer;">✕</button>
          </div>

          <!-- MODAL BODY -->
          <div style="padding: 24px; overflow-y: auto; flex: 1;">
            <div id="create-modal-error" style="display: none; padding: 10px 14px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; color: #ef4444; font-size: 12.5px; margin-bottom: 16px;"></div>

            <form id="form-create-master-account" style="display: flex; flex-direction: column; gap: 16px;">
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <div>
                  <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">Display Name</label>
                  <input type="text" id="create-acc-name" required placeholder="e.g. Operations Admin" style="width: 100%; padding: 9px 12px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 13px; color: var(--text-primary); outline: none;" />
                </div>
                <div>
                  <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">Login ID / Email</label>
                  <input type="text" id="create-acc-login-id" required placeholder="e.g. AdminOps@master" style="width: 100%; padding: 9px 12px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 13px; color: var(--text-primary); outline: none;" />
                </div>
              </div>

              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <div>
                  <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">Password</label>
                  <input type="password" id="create-acc-password" required placeholder="Min. 8 characters" style="width: 100%; padding: 9px 12px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 13px; color: var(--text-primary); outline: none;" />
                </div>
                <div>
                  <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">Confirm Password</label>
                  <input type="password" id="create-acc-confirm-password" required placeholder="Re-enter password" style="width: 100%; padding: 9px 12px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 13px; color: var(--text-primary); outline: none;" />
                </div>
              </div>

              <div>
                <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">Account Role</label>
                <select id="create-acc-role" style="width: 100%; padding: 9px 12px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 13px; color: var(--text-primary); outline: none;">
                  <option value="MASTER_ADMIN">MASTER_ADMIN (Delegated Master)</option>
                  ${authStore.user?.platform_role === 'SUPER_MASTER' ? '<option value="SUPER_MASTER">SUPER_MASTER (Root Super Master)</option>' : ''}
                </select>
              </div>

              <!-- FULL AUTHORITY SWITCH -->
              <div style="padding: 12px 14px; background: rgba(168, 85, 247, 0.08); border: 1px solid rgba(168, 85, 247, 0.25); border-radius: 10px; display: flex; align-items: center; justify-content: space-between;">
                <div>
                  <div style="font-size: 13px; font-weight: 700; color: #a855f7;">Full Master Authority</div>
                  <div style="font-size: 11.5px; color: var(--text-secondary);">Grants all current and future Master Space permissions automatically</div>
                </div>
                <input type="checkbox" id="create-acc-full-auth" style="width: 18px; height: 18px; cursor: pointer; accent-color: #a855f7;" />
              </div>

              <!-- SELECTIVE PERMISSIONS LIST -->
              <div id="create-permissions-wrapper">
                <div style="font-size: 12.5px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                  <span>SELECTIVE MASTER PERMISSIONS</span>
                  <span style="font-size: 11px; color: var(--text-secondary);">Check required permissions below</span>
                </div>

                <div style="display: flex; flex-direction: column; gap: 14px;">
                  ${this.permissionGroups.map(grp => `
                    <div style="background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px;">
                      <div style="font-size: 11.5px; font-weight: 800; color: var(--primary); text-transform: uppercase; margin-bottom: 6px;">
                        ${grp.name}
                      </div>
                      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                        ${grp.permissions.map(p => `
                          <label style="display: flex; align-items: flex-start; gap: 6px; font-size: 12px; color: var(--text-primary); cursor: pointer;">
                            <input type="checkbox" class="perm-checkbox" value="${p.id}" style="margin-top: 2px; accent-color: #a855f7;" />
                            <span>${p.label}</span>
                          </label>
                        `).join('')}
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>
            </form>
          </div>

          <!-- MODAL FOOTER -->
          <div style="padding: 16px 24px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: flex-end; gap: 10px;">
            <button id="btn-cancel-modal" class="btn btn-secondary">Cancel</button>
            <button id="btn-submit-create-account" class="btn btn-primary" style="background: linear-gradient(135deg, #9333ea, #6366f1); border: none; font-weight: 700; color: #fff;">
              Create Master Account
            </button>
          </div>

        </div>
      </div>
    `;

    // Bind modal handlers
    const closeBtn = modalContainer.querySelector('#btn-close-modal');
    const cancelBtn = modalContainer.querySelector('#btn-cancel-modal');
    const submitBtn = modalContainer.querySelector('#btn-submit-create-account');
    const fullAuthCheck = modalContainer.querySelector('#create-acc-full-auth');
    const permWrapper = modalContainer.querySelector('#create-permissions-wrapper');
    const errBox = modalContainer.querySelector('#create-modal-error');

    const closeModal = () => { modalContainer.innerHTML = ''; };
    if (closeBtn) closeBtn.onclick = closeModal;
    if (cancelBtn) cancelBtn.onclick = closeModal;

    if (fullAuthCheck && permWrapper) {
      fullAuthCheck.onchange = (e) => {
        const isFull = e.target.checked;
        permWrapper.style.opacity = isFull ? '0.4' : '1';
        permWrapper.style.pointerEvents = isFull ? 'none' : 'auto';
        modalContainer.querySelectorAll('.perm-checkbox').forEach(cb => cb.checked = isFull);
      };
    }

    if (submitBtn) {
      submitBtn.onclick = async () => {
        errBox.style.display = 'none';
        const name = modalContainer.querySelector('#create-acc-name').value.trim();
        const loginId = modalContainer.querySelector('#create-acc-login-id').value.trim();
        const password = modalContainer.querySelector('#create-acc-password').value;
        const confirmPass = modalContainer.querySelector('#create-acc-confirm-password').value;
        const role = modalContainer.querySelector('#create-acc-role').value;
        const fullAuth = fullAuthCheck.checked;

        const selectedPerms = [];
        modalContainer.querySelectorAll('.perm-checkbox:checked').forEach(cb => {
          selectedPerms.push(cb.value);
        });

        if (!name || !loginId || !password) {
          errBox.innerText = 'All fields are required.';
          errBox.style.display = 'block';
          return;
        }

        if (password !== confirmPass) {
          errBox.innerText = 'Passwords do not match.';
          errBox.style.display = 'block';
          return;
        }

        submitBtn.disabled = true;
        submitBtn.innerText = 'Creating Account...';

        try {
          await apiClient.post('/api/master/accounts', {
            name,
            login_id: loginId,
            password,
            confirm_password: confirmPass,
            role,
            full_authority: fullAuth,
            permissions: selectedPerms
          });

          closeModal();
          await this.fetchAccounts();
        } catch (err) {
          errBox.innerText = err.message || 'Failed to create Master account.';
          errBox.style.display = 'block';
          submitBtn.disabled = false;
          submitBtn.innerText = 'Create Master Account';
        }
      };
    }
  }

  openEditAccountModal(acc) {
    const modalContainer = this.element.querySelector('#master-modal-container');
    if (!modalContainer) return;

    const currentPerms = acc.permissions || [];
    const isFullAuth = currentPerms.includes('*') || currentPerms.includes('ALL') || currentPerms.length >= 20;

    modalContainer.innerHTML = `
      <div style="position: fixed; inset: 0; background: rgba(0, 0, 0, 0.65); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; backdrop-filter: blur(4px);">
        <div class="card" style="background: var(--bg-card); width: 100%; max-width: 680px; max-height: 90vh; border-radius: 16px; border: 1px solid rgba(168, 85, 247, 0.3); display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);">
          
          <!-- MODAL HEADER -->
          <div style="padding: 20px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h2 style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin: 0;">Edit Master Account</h2>
              <p style="font-size: 12.5px; color: var(--text-secondary); margin: 2px 0 0 0;">Update details and permissions for '${this.escapeHtml(acc.id)}'</p>
            </div>
            <button id="btn-close-modal" style="background: none; border: none; font-size: 20px; color: var(--text-secondary); cursor: pointer;">✕</button>
          </div>

          <!-- MODAL BODY -->
          <div style="padding: 24px; overflow-y: auto; flex: 1;">
            <div id="edit-modal-error" style="display: none; padding: 10px 14px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; color: #ef4444; font-size: 12.5px; margin-bottom: 16px;"></div>

            <form id="form-edit-master-account" style="display: flex; flex-direction: column; gap: 16px;">
              <div>
                <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">Display Name</label>
                <input type="text" id="edit-acc-name" value="${this.escapeHtml(acc.name || acc.id)}" style="width: 100%; padding: 9px 12px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 13px; color: var(--text-primary); outline: none;" />
              </div>

              <div>
                <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">Reset Password (Leave blank to keep current)</label>
                <input type="password" id="edit-acc-password" placeholder="Enter new password if resetting" style="width: 100%; padding: 9px 12px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 13px; color: var(--text-primary); outline: none;" />
              </div>

              <!-- FULL AUTHORITY SWITCH -->
              <div style="padding: 12px 14px; background: rgba(168, 85, 247, 0.08); border: 1px solid rgba(168, 85, 247, 0.25); border-radius: 10px; display: flex; align-items: center; justify-content: space-between;">
                <div>
                  <div style="font-size: 13px; font-weight: 700; color: #a855f7;">Full Master Authority</div>
                  <div style="font-size: 11.5px; color: var(--text-secondary);">Grants all current and future Master Space permissions automatically</div>
                </div>
                <input type="checkbox" id="edit-acc-full-auth" ${isFullAuth ? 'checked' : ''} style="width: 18px; height: 18px; cursor: pointer; accent-color: #a855f7;" />
              </div>

              <!-- SELECTIVE PERMISSIONS LIST -->
              <div id="edit-permissions-wrapper" style="${isFullAuth ? 'opacity: 0.4; pointer-events: none;' : ''}">
                <div style="font-size: 12.5px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                  <span>ASSIGNED MASTER PERMISSIONS</span>
                  <span style="font-size: 11px; color: var(--text-secondary);">Select specific permissions</span>
                </div>

                <div style="display: flex; flex-direction: column; gap: 14px;">
                  ${this.permissionGroups.map(grp => `
                    <div style="background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px;">
                      <div style="font-size: 11.5px; font-weight: 800; color: var(--primary); text-transform: uppercase; margin-bottom: 6px;">
                        ${grp.name}
                      </div>
                      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                        ${grp.permissions.map(p => `
                          <label style="display: flex; align-items: flex-start; gap: 6px; font-size: 12px; color: var(--text-primary); cursor: pointer;">
                            <input type="checkbox" class="edit-perm-checkbox" value="${p.id}" ${currentPerms.includes(p.id) || isFullAuth ? 'checked' : ''} style="margin-top: 2px; accent-color: #a855f7;" />
                            <span>${p.label}</span>
                          </label>
                        `).join('')}
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>
            </form>
          </div>

          <!-- MODAL FOOTER -->
          <div style="padding: 16px 24px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: flex-end; gap: 10px;">
            <button id="btn-cancel-modal" class="btn btn-secondary">Cancel</button>
            <button id="btn-submit-edit-account" class="btn btn-primary" style="background: linear-gradient(135deg, #9333ea, #6366f1); border: none; font-weight: 700; color: #fff;">
              Save Changes
            </button>
          </div>

        </div>
      </div>
    `;

    const closeBtn = modalContainer.querySelector('#btn-close-modal');
    const cancelBtn = modalContainer.querySelector('#btn-cancel-modal');
    const submitBtn = modalContainer.querySelector('#btn-submit-edit-account');
    const fullAuthCheck = modalContainer.querySelector('#edit-acc-full-auth');
    const permWrapper = modalContainer.querySelector('#edit-permissions-wrapper');
    const errBox = modalContainer.querySelector('#edit-modal-error');

    const closeModal = () => { modalContainer.innerHTML = ''; };
    if (closeBtn) closeBtn.onclick = closeModal;
    if (cancelBtn) cancelBtn.onclick = closeModal;

    if (fullAuthCheck && permWrapper) {
      fullAuthCheck.onchange = (e) => {
        const isFull = e.target.checked;
        permWrapper.style.opacity = isFull ? '0.4' : '1';
        permWrapper.style.pointerEvents = isFull ? 'none' : 'auto';
        modalContainer.querySelectorAll('.edit-perm-checkbox').forEach(cb => cb.checked = isFull);
      };
    }

    if (submitBtn) {
      submitBtn.onclick = async () => {
        errBox.style.display = 'none';
        const name = modalContainer.querySelector('#edit-acc-name').value.trim();
        const password = modalContainer.querySelector('#edit-acc-password').value;
        const fullAuth = fullAuthCheck.checked;

        const selectedPerms = [];
        modalContainer.querySelectorAll('.edit-perm-checkbox:checked').forEach(cb => {
          selectedPerms.push(cb.value);
        });

        submitBtn.disabled = true;
        submitBtn.innerText = 'Saving...';

        try {
          const payload = {
            name,
            full_authority: fullAuth,
            permissions: selectedPerms
          };
          if (password) payload.password = password;

          await apiClient.patch(`/api/master/accounts/${encodeURIComponent(acc.id)}`, payload);
          closeModal();
          await this.fetchAccounts();
        } catch (err) {
          errBox.innerText = err.message || 'Failed to update account.';
          errBox.style.display = 'block';
          submitBtn.disabled = false;
          submitBtn.innerText = 'Save Changes';
        }
      };
    }
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}
