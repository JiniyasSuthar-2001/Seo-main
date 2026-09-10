import { apiClient } from '../services/apiClient.js';
import { themeStore } from '../core/themeStore.js';
import { authStore } from '../core/authStore.js';

export class MasterTopBar {
  constructor() {
    this.element = document.createElement('header');
    this.element.className = 'topbar-wrapper master-topbar-wrapper';
    this.element.style.height = '100%';
  }

  render() {
    const userEmail = (authStore.user && authStore.user.email) ? authStore.user.email : 'admin@seo-platform.local';
    const userRole = (authStore.user?.platform_role || 'SUPER_ADMIN').toUpperCase();
    const userInitial = authStore.user?.name ? authStore.user.name.charAt(0).toUpperCase() : (userEmail.charAt(0).toUpperCase() || 'A');

    this.element.innerHTML = `
      <div style="height: 100%; padding: 0 28px; display: flex; align-items: center; justify-content: space-between; gap: 16px; border-bottom: 1px solid rgba(168, 85, 247, 0.15); background: var(--bg-card);">
        
        <!-- LEFT: MASTER SPACE BADGE & LIVE BREADCRUMB -->
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="display: flex; align-items: center; gap: 8px; background: rgba(168, 85, 247, 0.1); padding: 5px 12px; border-radius: 8px; border: 1px solid rgba(168, 85, 247, 0.25);">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="color: #a855f7; flex-shrink: 0;">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
            <span style="font-size: 13px; font-weight: 700; color: #a855f7; letter-spacing: 0.02em;">MASTER SPACE CONSOLE</span>
          </div>
          <span style="font-size: 12.5px; color: var(--text-tertiary);">• Multi-Tenant Administration & Platform Control</span>
        </div>

        <!-- RIGHT: HEALTH PILL, SWITCH TO CUSTOMER APP, THEME TOGGLE, ADMIN PROFILE -->
        <div style="display: flex; align-items: center; gap: 12px;">
          
          <!-- SYSTEM HEALTH PILL -->
          <div id="master-system-health-pill" style="display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 20px; background: var(--success-bg); border: 1px solid var(--success-border); font-size: 12px; font-weight: 600; color: var(--success); cursor: pointer;" title="Backend Platform Health">
            <span id="master-health-dot" style="width: 6px; height: 6px; border-radius: 50%; background: var(--success); box-shadow: 0 0 6px var(--success);"></span>
            <span id="master-health-text">System Normal</span>
          </div>

          <!-- SWITCH TO CUSTOMER WORKSPACE -->
          <a href="/" data-link class="btn btn-secondary btn-sm" style="display: flex; align-items: center; gap: 6px; font-weight: 600;" title="Return to Customer Website Application">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            <span>Customer App</span>
          </a>

          <!-- THEME TOGGLE SWITCH -->
          <button id="master-theme-toggle-btn" class="theme-toggle-btn" title="Toggle Dark / Light Theme">
            <span id="master-theme-icon">${themeStore.isDark() ? '🌙' : '☀'}</span>
            <span id="master-theme-label" style="font-size: 12px;">${themeStore.isDark() ? 'Dark' : 'Light'}</span>
          </button>

          <!-- ADMIN USER PROFILE CONTAINER -->
          <div style="display: flex; align-items: center; gap: 8px; background: var(--bg-subtle); padding: 3px 10px 3px 4px; border-radius: 20px; border: 1px solid rgba(168, 85, 247, 0.3);">
            <div style="width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #9333ea, #6366f1); color: #fff; font-weight: 700; font-size: 12px; display: flex; align-items: center; justify-content: center;">
              ${userInitial}
            </div>
            <div style="display: flex; flex-direction: column; line-height: 1.1;">
              <span style="font-size: 12px; font-weight: 700; color: var(--text-primary); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${userEmail}</span>
              <span style="font-size: 9.5px; font-weight: 700; color: #c084fc;">${userRole}</span>
            </div>
            <button id="btn-master-logout" title="Sign Out of Master Admin" style="background: none; border: none; font-size: 12px; color: var(--text-tertiary); cursor: pointer; padding: 2px 4px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
            </button>
          </div>

        </div>
      </div>
    `;

    this.initHealthPill();
    this.initThemeToggle();
    this.initLogout();
    return this.element;
  }

  initLogout() {
    setTimeout(() => {
      const logoutBtn = this.element.querySelector('#btn-master-logout');
      if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
          if (confirm('Sign out of Master Admin console?')) {
            authStore.logout();
          }
        });
      }
    }, 50);
  }

  initThemeToggle() {
    setTimeout(() => {
      const btn = this.element.querySelector('#master-theme-toggle-btn');
      const icon = this.element.querySelector('#master-theme-icon');
      const label = this.element.querySelector('#master-theme-label');

      if (!btn) return;

      const updateUI = (theme) => {
        if (icon) icon.innerText = theme === 'dark' ? '🌙' : '☀';
        if (label) label.innerText = theme === 'dark' ? 'Dark' : 'Light';
      };

      btn.addEventListener('click', () => {
        const newTheme = themeStore.toggleTheme();
        updateUI(newTheme);
      });

      themeStore.subscribe((theme) => updateUI(theme));
    }, 50);
  }

  initHealthPill() {
    setTimeout(() => {
      const pillEl = this.element.querySelector('#master-system-health-pill');
      const dotEl = this.element.querySelector('#master-health-dot');
      const textEl = this.element.querySelector('#master-health-text');
      if (!pillEl) return;

      const updatePill = (status) => {
        if (status === 'ONLINE') {
          pillEl.style.background = 'var(--success-bg)';
          pillEl.style.borderColor = 'var(--success-border)';
          pillEl.style.color = 'var(--success)';
          if (dotEl) { dotEl.style.background = 'var(--success)'; dotEl.style.boxShadow = '0 0 6px var(--success)'; }
          if (textEl) textEl.innerText = 'System Normal';
        } else if (status === 'DEGRADED') {
          pillEl.style.background = 'var(--warning-bg)';
          pillEl.style.borderColor = 'var(--warning-border)';
          pillEl.style.color = 'var(--warning)';
          if (dotEl) { dotEl.style.background = 'var(--warning)'; dotEl.style.boxShadow = '0 0 6px var(--warning)'; }
          if (textEl) textEl.innerText = 'Platform Degraded';
        } else {
          pillEl.style.background = 'var(--critical-bg)';
          pillEl.style.borderColor = 'var(--critical-border)';
          pillEl.style.color = 'var(--critical)';
          if (dotEl) { dotEl.style.background = 'var(--critical)'; dotEl.style.boxShadow = '0 0 6px var(--critical)'; }
          if (textEl) textEl.innerText = 'Platform Offline';
        }
      };

      updatePill(apiClient.status);
      apiClient.onStatusChange(updatePill);
    }, 100);
  }
}
