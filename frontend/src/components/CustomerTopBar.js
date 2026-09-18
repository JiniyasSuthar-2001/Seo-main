import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { crawlConfigModal } from './CrawlConfigModal.js';
import { themeStore } from '../core/themeStore.js';
import { authStore } from '../core/authStore.js';
import { aiChatModal } from './AIChatModal.js';

window.openAIChatAssistant = () => {
    aiChatModal.open();
};

window.startCrawl = () => {
    const selectedProj = projectStore.getSelectedProject();
    if (selectedProj) {
        crawlConfigModal.open(selectedProj.id, selectedProj.domain || selectedProj.url);
    } else if (projectStore.projects && projectStore.projects.length > 0) {
        const p = projectStore.projects[0];
        crawlConfigModal.open(p.id, p.domain || p.url);
    } else {
        window.showCreateProjectModal();
    }
};

window.showCreateProjectModal = () => {
  let modal = document.getElementById('create-project-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'create-project-modal';
    modal.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
      background: rgba(8, 12, 20, 0.7); backdrop-filter: blur(6px);
      display: flex; align-items: center; justify-content: center; z-index: 9999;
    `;
    modal.innerHTML = `
      <div style="background: var(--bg-card); width: 100%; max-width: 480px; padding: 28px; border-radius: 12px; border: 1px solid var(--border); box-shadow: var(--shadow-lg);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;">Add New SEO Project</h3>
          <button onclick="window.closeCreateProjectModal()" style="background: none; border: none; font-size: 20px; color: var(--text-tertiary); cursor: pointer;">&times;</button>
        </div>
        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.5;">
          Create an independent SEO workspace for another website domain. You will be assigned as Lead/Owner.
        </p>
        <form onsubmit="window.submitNewProject(event)">
          <div style="margin-bottom: 16px;">
            <label style="display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-bottom: 6px;">Project Name</label>
            <input id="modal-proj-name" type="text" placeholder="e.g. Acme Corporation" required style="width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-subtle); color: var(--text-primary);">
          </div>
          <div style="margin-bottom: 24px;">
            <label style="display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-bottom: 6px;">Target Website URL</label>
            <input id="modal-proj-domain" type="url" placeholder="https://example.com/" required style="width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-subtle); color: var(--text-primary);">
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button type="button" class="btn btn-secondary" onclick="window.closeCreateProjectModal()">Cancel</button>
            <button type="submit" class="btn btn-primary">Create Project</button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(modal);
  }
  modal.style.display = 'flex';
};

window.closeCreateProjectModal = () => {
  const modal = document.getElementById('create-project-modal');
  if (modal) modal.style.display = 'none';
};

window.submitNewProject = async (e) => {
  e.preventDefault();
  const name = document.getElementById('modal-proj-name').value.trim();
  const domain = document.getElementById('modal-proj-domain').value.trim();

  if (!name || !domain) {
    alert("Please enter both Project Name and Target Website URL.");
    return;
  }

  try {
    const res = await projectStore.createProject({ name, url: domain });
    window.closeCreateProjectModal();
    if (res && res.project && res.project.id) {
      projectStore.setSelectedProjectId(res.project.id);
      window.dispatchEvent(new CustomEvent('project:selected', { detail: { projectId: res.project.id } }));
      setTimeout(() => {
        crawlConfigModal.open(res.project.id, res.project.domain || res.project.url || domain);
      }, 200);
    }
  } catch (err) {
    alert(`Failed to create project: ${err.message || "Please check backend server status."}`);
  }
};

export class CustomerTopBar {
  constructor() {
    this.element = document.createElement('header');
    this.element.className = 'topbar-wrapper customer-topbar-wrapper';
    this.element.style.height = '100%';
  }

  render() {
    const isGuest = !!(authStore.user && (authStore.user.is_guest || authStore.user.auth_provider === 'guest' || (authStore.user.id && String(authStore.user.id).startsWith('guest_'))));
    const userEmail = isGuest ? 'Guest User' : (authStore.user && authStore.user.email ? authStore.user.email : 'user@seo-platform.local');
    const userInitial = isGuest ? 'G' : (authStore.user && authStore.user.name ? authStore.user.name.charAt(0).toUpperCase() : (userEmail.charAt(0).toUpperCase() || 'U'));

    this.element.innerHTML = `
      <div style="height: 100%; padding: 0 28px; display: flex; align-items: center; justify-content: space-between; gap: 16px;">
        
        <!-- LEFT: WORKSPACE / CATEGORIZED PROJECT SELECTOR CONTROLLED DROPDOWN & (+) ADD BUTTON -->
        <div style="display: flex; align-items: center; gap: 8px; flex: 1;">
          
          <!-- CUSTOM CONTROLLED PROJECT DROPDOWN CONTAINER (WORKS ACROSS MACOS AND WINDOWS) -->
          <div id="header-project-dropdown-container" style="position: relative; display: inline-flex; align-items: center;">
            <button id="header-project-dropdown-trigger" type="button" aria-haspopup="true" aria-expanded="false" style="display: flex; align-items: center; gap: 8px; background: var(--bg-subtle); padding: 6px 12px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px; font-weight: 600; color: var(--text-primary); cursor: pointer; outline: none; transition: all 0.15s ease;">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="color: var(--primary); flex-shrink: 0;"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
              <span id="header-project-selected-label" style="max-width: 240px; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">Loading projects...</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="color: var(--text-tertiary); margin-left: 2px; flex-shrink: 0;"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </button>

            <!-- CONTROLLED FLOATING DROPDOWN MENU -->
            <div id="header-project-dropdown-menu" style="display: none; position: absolute; top: calc(100% + 6px); left: 0; min-width: 280px; max-width: 360px; max-height: 400px; overflow-y: auto; background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 14px 30px rgba(0,0,0,0.3); z-index: 10000; padding: 6px;">
              <!-- Populated dynamically by initProjectSelector -->
            </div>
          </div>

          <!-- (+) ADD PROJECT BUTTON -->
          <button onclick="window.showCreateProjectModal()" title="Add New Project" style="width: 32px; height: 32px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-subtle); color: var(--primary); font-weight: 700; font-size: 16px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.15s ease;">
            +
          </button>
        </div>

        <!-- RIGHT: HEALTH PILL, RUN CRAWL CTA, THEME TOGGLE, USER PROFILE -->
        <div style="display: flex; align-items: center; gap: 12px;">
          
          <!-- SYSTEM HEALTH PILL -->
          <div id="system-health-pill" style="display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 20px; background: var(--success-bg); border: 1px solid var(--success-border); font-size: 12px; font-weight: 600; color: var(--success); cursor: pointer;" title="Click to test backend server connection">
            <span id="health-dot" style="width: 6px; height: 6px; border-radius: 50%; background: var(--success); box-shadow: 0 0 6px var(--success);"></span>
            <span id="health-text">Backend Online</span>
          </div>

          <!-- TEAM INVITATIONS BUTTON -->
          <div id="team-invites-badge-container"></div>

          <!-- AI ASSISTANT BUTTON -->
          <button class="btn btn-secondary btn-sm" onclick="window.openAIChatAssistant ? window.openAIChatAssistant() : null" style="display: flex; align-items: center; gap: 6px; border-color: rgba(139, 92, 246, 0.4); color: #8b5cf6;" title="Open Evidence-Grounded AI SEO Assistant">
            <span>🤖 AI Assistant</span>
          </button>

          <!-- QUICK CRAWL BUTTON -->
          <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
            <span>Run Crawl</span>
          </button>

          <!-- THEME TOGGLE SWITCH -->
          <button id="theme-toggle-btn" class="theme-toggle-btn" title="Toggle Dark / Light Theme">
            <span id="theme-icon">${themeStore.isDark() ? '🌙' : '☀'}</span>
            <span id="theme-label" style="font-size: 12px;">${themeStore.isDark() ? 'Dark' : 'Light'}</span>
          </button>

          <!-- USER PROFILE CONTAINER -->
          <div style="display: flex; align-items: center; gap: 8px; background: var(--bg-subtle); padding: 3px 10px 3px 4px; border-radius: 20px; border: 1px solid var(--border);">
            <div style="width: 28px; height: 28px; border-radius: 50%; background: ${isGuest ? 'linear-gradient(135deg, #2563eb, #7c3aed)' : 'linear-gradient(135deg, #4285f4, #34a853)'}; color: #fff; font-weight: 700; font-size: 12px; display: flex; align-items: center; justify-content: center;">
              ${userInitial}
            </div>
            <span style="font-size: 12px; font-weight: 600; color: var(--text-primary); max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${userEmail}</span>
            <button id="btn-logout" title="${isGuest ? 'Sign Out of Guest Mode' : 'Sign Out of Google Account'}" style="background: none; border: none; font-size: 12px; color: var(--text-tertiary); cursor: pointer; padding: 2px 4px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
            </button>
          </div>

        </div>
      </div>
    `;

    this.initProjectSelector();
    this.initHealthPill();
    this.initThemeToggle();
    this.initLogout();
    this.initPendingInvitations();
    return this.element;
  }

  initLogout() {
    setTimeout(() => {
      const logoutBtn = this.element.querySelector('#btn-logout');
      if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
          const isGuest = !!(authStore.user && (authStore.user.is_guest || authStore.user.auth_provider === 'guest' || (authStore.user.id && String(authStore.user.id).startsWith('guest_'))));
          const msg = isGuest ? 'Sign out of Guest Mode?' : 'Sign out of your account?';
          if (confirm(msg)) {
            authStore.logout();
          }
        });
      }
    }, 50);
  }

  initThemeToggle() {
    setTimeout(() => {
      const btn = this.element.querySelector('#theme-toggle-btn');
      const icon = this.element.querySelector('#theme-icon');
      const label = this.element.querySelector('#theme-label');

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
      const pillEl = this.element.querySelector('#system-health-pill');
      const dotEl = this.element.querySelector('#health-dot');
      const textEl = this.element.querySelector('#health-text');
      if (!pillEl) return;

      const updatePill = (status) => {
        if (status === 'ONLINE') {
          pillEl.style.background = 'var(--success-bg)';
          pillEl.style.borderColor = 'var(--success-border)';
          pillEl.style.color = 'var(--success)';
          if (dotEl) { dotEl.style.background = 'var(--success)'; dotEl.style.boxShadow = '0 0 6px var(--success)'; }
          if (textEl) textEl.innerText = 'Backend Online';
        } else if (status === 'DEGRADED') {
          pillEl.style.background = 'var(--warning-bg)';
          pillEl.style.borderColor = 'var(--warning-border)';
          pillEl.style.color = 'var(--warning)';
          if (dotEl) { dotEl.style.background = 'var(--warning)'; dotEl.style.boxShadow = '0 0 6px var(--warning)'; }
          if (textEl) textEl.innerText = 'Server Degraded';
        } else {
          pillEl.style.background = 'var(--critical-bg)';
          pillEl.style.borderColor = 'var(--critical-border)';
          pillEl.style.color = 'var(--critical)';
          if (dotEl) { dotEl.style.background = 'var(--critical)'; dotEl.style.boxShadow = '0 0 6px var(--critical)'; }
          if (textEl) textEl.innerText = 'Backend Offline';
        }
      };

      updatePill(apiClient.status);
      apiClient.onStatusChange(updatePill);

      pillEl.addEventListener('click', async () => {
        if (textEl) textEl.innerText = 'Checking...';
        try {
          if (typeof apiClient.checkHealth === 'function') {
            await apiClient.checkHealth();
          }
        } catch (e) {}
        updatePill(apiClient.status);
      });
    }, 100);
  }

  async initProjectSelector() {
    const triggerBtn = this.element.querySelector('#header-project-dropdown-trigger');
    const labelEl = this.element.querySelector('#header-project-selected-label');
    const menuEl = this.element.querySelector('#header-project-dropdown-menu');
    if (!triggerBtn || !labelEl || !menuEl) return;

    const closeDropdown = () => {
      menuEl.style.display = 'none';
      triggerBtn.setAttribute('aria-expanded', 'false');
    };

    const toggleDropdown = () => {
      const isHidden = menuEl.style.display === 'none' || !menuEl.style.display;
      if (isHidden) {
        menuEl.style.display = 'block';
        triggerBtn.setAttribute('aria-expanded', 'true');
        
        // Viewport positioning guard for macOS & Windows
        requestAnimationFrame(() => {
          const rect = menuEl.getBoundingClientRect();
          if (rect.right > window.innerWidth - 16) {
            menuEl.style.left = 'auto';
            menuEl.style.right = '0';
          } else {
            menuEl.style.left = '0';
            menuEl.style.right = 'auto';
          }
        });
      } else {
        closeDropdown();
      }
    };

    triggerBtn.onclick = (e) => {
      e.stopPropagation();
      toggleDropdown();
    };

    // Close on click outside
    document.addEventListener('click', (e) => {
      if (!this.element.contains(e.target)) {
        closeDropdown();
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeDropdown();
      }
    });

    const updateDropdownUI = () => {
      const selectedId = projectStore.getSelectedProjectId();
      const myProjects = projectStore.getMyProjects();
      const memberProjects = projectStore.getMemberProjects();
      const allProjects = projectStore.projects || [];

      // Determine active project label
      if (!selectedId || selectedId === 'all') {
        labelEl.innerText = '🌐 All Workspaces';
      } else {
        const found = allProjects.find(p => String(p.id) === String(selectedId));
        if (found) {
          const roleTag = found.user_role === 'OWNER' ? 'Lead' : 'Member';
          labelEl.innerText = `${found.name} (${roleTag})`;
        } else {
          labelEl.innerText = '🌐 All Workspaces';
        }
      }

      // Build menu HTML
      let html = '';

      // 1. All Workspaces option
      const isAllActive = !selectedId || selectedId === 'all';
      html += `
        <div class="custom-project-item" data-id="all" style="padding: 8px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; font-size: 13px; font-weight: 600; color: ${isAllActive ? 'var(--primary)' : 'var(--text-primary)'}; background: ${isAllActive ? 'var(--bg-subtle)' : 'transparent'}; transition: background 0.15s ease;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span>🌐</span>
            <span>All Workspaces</span>
          </div>
          ${isAllActive ? '<span style="color: var(--primary); font-weight: 700;">✓</span>' : ''}
        </div>
      `;

      // 2. MY WEBSITES (Lead/Owner)
      if (myProjects && myProjects.length > 0) {
        html += `
          <div style="padding: 10px 12px 4px 12px; font-size: 10.5px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em;">
            MY WEBSITES (Lead/Owner)
          </div>
        `;
        myProjects.forEach(p => {
          const isActive = String(p.id) === String(selectedId);
          const domStr = p.domain || p.url || '';
          html += `
            <div class="custom-project-item" data-id="${p.id}" style="padding: 8px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; font-size: 13px; color: ${isActive ? 'var(--primary)' : 'var(--text-primary)'}; background: ${isActive ? 'var(--bg-subtle)' : 'transparent'}; transition: background 0.15s ease;">
              <div style="min-width: 0; flex: 1; padding-right: 8px;">
                <div style="font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(p.name)}</div>
                ${domStr ? `<div style="font-size: 11px; color: var(--text-tertiary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-family: monospace;">${this.escapeHtml(domStr)}</div>` : ''}
              </div>
              <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                <span class="badge badge-secondary" style="font-size: 10px; padding: 2px 6px;">Lead</span>
                ${isActive ? '<span style="color: var(--primary); font-weight: 700;">✓</span>' : ''}
              </div>
            </div>
          `;
        });
      }

      // 3. PROJECTS I'M A MEMBER OF
      if (memberProjects && memberProjects.length > 0) {
        html += `
          <div style="padding: 10px 12px 4px 12px; font-size: 10.5px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em;">
            PROJECTS I'M A MEMBER OF
          </div>
        `;
        memberProjects.forEach(p => {
          const isActive = String(p.id) === String(selectedId);
          const domStr = p.domain || p.url || '';
          html += `
            <div class="custom-project-item" data-id="${p.id}" style="padding: 8px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; font-size: 13px; color: ${isActive ? 'var(--primary)' : 'var(--text-primary)'}; background: ${isActive ? 'var(--bg-subtle)' : 'transparent'}; transition: background 0.15s ease;">
              <div style="min-width: 0; flex: 1; padding-right: 8px;">
                <div style="font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(p.name)}</div>
                ${domStr ? `<div style="font-size: 11px; color: var(--text-tertiary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-family: monospace;">${this.escapeHtml(domStr)}</div>` : ''}
              </div>
              <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                <span class="badge badge-secondary" style="font-size: 10px; padding: 2px 6px;">Member</span>
                ${isActive ? '<span style="color: var(--primary); font-weight: 700;">✓</span>' : ''}
              </div>
            </div>
          `;
        });
      }

      menuEl.innerHTML = html;

      // Add click listeners to items
      menuEl.querySelectorAll('.custom-project-item').forEach(item => {
        item.addEventListener('click', (e) => {
          e.stopPropagation();
          const pId = item.getAttribute('data-id');
          closeDropdown();
          if (pId) {
            projectStore.setSelectedProjectId(pId);
            window.dispatchEvent(new CustomEvent('project:selected', { detail: { projectId: pId } }));
          }
        });
        item.addEventListener('mouseenter', () => {
          item.style.background = 'var(--bg-subtle)';
        });
        item.addEventListener('mouseleave', () => {
          const pId = item.getAttribute('data-id');
          const isItemActive = (!selectedId || selectedId === 'all') ? pId === 'all' : String(pId) === String(selectedId);
          item.style.background = isItemActive ? 'var(--bg-subtle)' : 'transparent';
        });
      });
    };

    try {
      await projectStore.ensureInitialized();
      updateDropdownUI();
    } catch (e) {}

    projectStore.subscribe(() => updateDropdownUI());
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

  async initPendingInvitations() {
    try {
      const [notifRes, invRes] = await Promise.all([
        apiClient.get('/api/notifications').catch(() => ({ unread_count: 0, notifications: [] })),
        apiClient.get('/api/auth/my-invitations').catch(() => ({ invitations: [] }))
      ]);

      const notifications = notifRes.notifications || [];
      const invitations = invRes.invitations || [];
      const unreadCount = notifRes.unread_count || 0;

      const container = this.element.querySelector('#team-invites-badge-container');
      if (!container) return;

      if (unreadCount > 0 || invitations.length > 0) {
        container.innerHTML = `
          <button class="btn btn-secondary btn-sm" onclick="window.openTeamInvitationsModal()" style="display: flex; align-items: center; gap: 6px; border-color: rgba(59, 130, 246, 0.4); color: #3b82f6; background: rgba(59, 130, 246, 0.1);" title="View Team Notifications & Invitations">
            <span>🔔</span>
            <span style="font-weight: 600;">Notifications</span>
            ${unreadCount > 0 ? `<span style="background: #ef4444; color: #fff; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 10px;">${unreadCount}</span>` : ''}
          </button>
        `;
      } else {
        container.innerHTML = '';
      }
    } catch (e) {
      console.warn('[TOPBAR] Failed to fetch notifications/invitations:', e);
    }
  }
}
