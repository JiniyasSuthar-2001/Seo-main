import { authStore } from '../core/authStore.js';

export class MasterSidebar {
  render() {
    const element = document.createElement('aside');
    element.className = 'sidebar-nav master-sidebar-nav';

    element.innerHTML = `
      <!-- BRAND HEADER -->
      <div class="sidebar-brand master-brand" style="border-bottom: 1px solid rgba(168, 85, 247, 0.2);">
        <div class="brand-logo master-logo" style="background: linear-gradient(135deg, #9333ea, #6366f1); box-shadow: 0 4px 14px rgba(147, 51, 234, 0.35);">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
        </div>
        <div style="flex: 1;">
          <div class="brand-title" style="display: flex; align-items: center; gap: 6px;">
            <span>SEO Intelligence</span>
            <span style="font-size: 9px; font-weight: 800; background: rgba(168, 85, 247, 0.2); color: #c084fc; padding: 1px 6px; border-radius: 4px; border: 1px solid rgba(168, 85, 247, 0.3);">MASTER</span>
          </div>
          <div class="brand-subtitle" style="color: #a855f7; font-weight: 600;">Admin Console</div>
        </div>
      </div>

      <!-- MASTER NAVIGATION SCROLL AREA -->
      <div class="sidebar-scroll-area">
        <div class="nav-section">
          <div class="nav-section-label" style="color: #a855f7; font-weight: 800; display: flex; align-items: center; justify-content: space-between;">
            <span>MASTER SPACE OPERATIONS</span>
            <span style="font-size: 9px; background: rgba(168, 85, 247, 0.15); padding: 1px 5px; border-radius: 4px; color: #c084fc;">ROOT</span>
          </div>
          <nav class="nav-group">
            ${this.renderNavItem('/master', '<span>Dashboard</span>', '<rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect>', 'master.dashboard.view')}
            ${this.renderNavItem('/master/customers', '<span>Customers</span>', '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>', 'master.customers.view')}
            ${this.renderNavItem('/master/websites', '<span>Websites</span>', '<circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>', 'master.websites.view')}
            ${this.renderNavItem('/master/ai-analytics', '<span>AI Analytics</span>', '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>', 'master.ai_analytics.view')}
            ${this.renderNavItem('/master/ai-control', '<span>AI Control</span>', '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>', 'master.ai_control.view')}
            ${this.renderNavItem('/master/credits', '<span>Credits</span>', '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line>', 'master.credits.view')}
            ${this.renderNavItem('/master/providers', '<span>Providers</span>', '<rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line>', 'master.providers.view')}
            ${this.renderNavItem('/master/activity', '<span>Activity</span>', '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>', 'master.activity.view')}
            ${this.renderNavItem('/master/system-health', '<span>System Health</span>', '<path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>', 'master.system_health.view')}
            ${this.renderNavItem('/master/audit-logs', '<span>Audit Logs</span>', '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line>', 'master.audit_logs.view')}
          </nav>
        </div>

        ${authStore.hasMasterPermission('master.master_accounts.view') ? `
          <div class="nav-section">
            <div class="nav-section-label" style="color: var(--text-tertiary); font-weight: 700; padding: 6px 10px 4px;">
              <span>ADMINISTRATION</span>
            </div>
            <nav class="nav-group">
              ${this.renderNavItem('/master/accounts', '<span>Master Accounts</span>', '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><line x1="19" y1="8" x2="19" y2="14"></line><line x1="22" y1="11" x2="16" y2="11"></line>', 'master.master_accounts.view')}
            </nav>
          </div>
        ` : ''}
      </div>

      <!-- RETURN TO CUSTOMER APP FOOTER -->
      <div class="master-sidebar-footer">
        <a href="/" data-link class="return-customer-btn">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          <span>Customer Workspace</span>
        </a>
      </div>
    `;

    setTimeout(() => this.updateActiveState(element), 0);

    const handleUpdate = () => {
      // Re-render sidebar if permissions or mode changed
      this.updateActiveState(element);
    };
    window.addEventListener('popstate', handleUpdate);
    window.addEventListener('routechange', handleUpdate);

    return element;
  }

  renderNavItem(href, labelHtml, svgPaths, requiredPerm) {
    if (requiredPerm && !authStore.hasMasterPermission(requiredPerm)) {
      return '';
    }
    const cleanLabel = labelHtml.startsWith('<span>') ? labelHtml : `<span>${labelHtml}</span>`;
    return `
      <a href="${href}" data-link class="nav-item">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${svgPaths}</svg>
        ${cleanLabel}
      </a>
    `;
  }

  updateActiveState(container = document) {
    const currentPath = window.location.pathname || '/master';
    const items = container.querySelectorAll ? container.querySelectorAll('.nav-item') : document.querySelectorAll('.nav-item');
    if (!items || items.length === 0) return;

    let bestMatch = null;
    let bestMatchScore = -1;

    items.forEach(item => {
      item.classList.remove('active');
      item.removeAttribute('aria-current');

      const href = item.getAttribute('href');
      if (!href) return;

      const score = this.getRouteMatchScore(href, currentPath);
      if (score > bestMatchScore) {
        bestMatchScore = score;
        bestMatch = item;
      }
    });

    if (bestMatch && bestMatchScore > 0) {
      bestMatch.classList.add('active');
      bestMatch.setAttribute('aria-current', 'page');
    }
  }

  getRouteMatchScore(href, currentPath) {
    const cleanHref = href.toLowerCase().replace(/\/$/, '') || '/master';
    const cleanPath = currentPath.toLowerCase().replace(/\/$/, '') || '/master';

    if (cleanHref === cleanPath) return 100;
    if (cleanHref === '/master') {
      if (cleanPath === '/master' || cleanPath === '/master/dashboard') return 90;
      return 0;
    }
    if (cleanPath.startsWith(cleanHref + '/')) return 80;
    return 0;
  }
}
