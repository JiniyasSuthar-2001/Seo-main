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
      // Directly trigger real crawl modal for the newly created website domain
      setTimeout(() => {
        crawlConfigModal.open(res.project.id, res.project.domain || res.project.url || domain);
      }, 200);
    }
  } catch (err) {
    alert(`Failed to create project: ${err.message || "Please check backend server status."}`);
  }
};

export class TopBar {
  constructor() {
    this.element = document.createElement('header');
    this.element.className = 'topbar-wrapper';
    this.element.style.height = '100%';
  }

  render() {
    const isGuest = !!(authStore.user && (authStore.user.is_guest || authStore.user.auth_provider === 'guest' || (authStore.user.id && String(authStore.user.id).startsWith('guest_'))));
    const userEmail = isGuest ? 'Guest User' : (authStore.user && authStore.user.email ? authStore.user.email : 'jiniyassuthar87@gmail.com');
    const userInitial = isGuest ? 'G' : (authStore.user && authStore.user.name ? authStore.user.name.charAt(0).toUpperCase() : (userEmail.charAt(0).toUpperCase() || 'J'));

    this.element.innerHTML = `
      ${isGuest ? `
        <div class="guest-mode-banner" style="background: linear-gradient(90deg, #2563eb, #7c3aed); color: #ffffff; padding: 5px 24px; font-size: 12px; font-weight: 600; display: flex; align-items: center; justify-content: space-between; gap: 12px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <span style="background: rgba(255,255,255,0.25); padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 800; letter-spacing: 0.04em;">GUEST MODE</span>
            <span>Your data is temporary. Sign in with Google to keep your workspace.</span>
          </div>
          <button id="guest-signin-google-btn" style="background: #ffffff; color: #0f172a; border: none; padding: 4px 12px; border-radius: 6px; font-size: 11.5px; font-weight: 700; cursor: pointer; transition: all 0.15s ease;" onclick="authStore.logout()">
            Sign in with Google
          </button>
        </div>
      ` : ''}

      <div style="height: ${isGuest ? 'calc(100% - 29px)' : '100%'}; padding: 0 28px; display: flex; align-items: center; justify-content: space-between; gap: 16px;">
        
        <!-- LEFT: WORKSPACE / CATEGORIZED PROJECT SELECTOR DROPDOWN & (+) ADD BUTTON & GLOBAL SEARCH -->
        <div style="display: flex; align-items: center; gap: 12px; flex: 1; max-width: 680px;">
          
          <!-- PROJECT SELECTOR CONTAINER -->
          <div style="display: flex; align-items: center; gap: 6px;">
            <div style="display: flex; align-items: center; gap: 8px; background: var(--bg-subtle); padding: 5px 12px; border-radius: 8px; border: 1px solid var(--border);">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="color: var(--primary); flex-shrink: 0;"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
              <select id="header-project-select" style="background: transparent; border: none; font-size: 13px; font-weight: 600; color: var(--text-primary); cursor: pointer; outline: none; max-width: 220px; text-overflow: ellipsis;">
                <option value="">Loading projects...</option>
              </select>
            </div>

            <!-- (+) ADD PROJECT BUTTON -->
            <button onclick="window.showCreateProjectModal()" title="Add New Project" style="width: 32px; height: 32px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-subtle); color: var(--primary); font-weight: 700; font-size: 16px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.15s ease;">
              +
            </button>
          </div>

          <!-- COMMAND SEARCH INPUT -->
          <div style="position: relative; flex: 1;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary);">
              <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input type="text" id="global-search-input" placeholder="Search pages, keywords, backlinks..." style="width: 100%; padding: 7px 12px 7px 34px; border: 1px solid var(--border); border-radius: 8px; font-size: 13px; background: var(--bg-subtle); color: var(--text-primary); transition: all 0.15s ease;">
            <span class="kbd" style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%); pointer-events: none;">Ctrl + K</span>
          </div>
        </div>

        <!-- RIGHT: HEALTH PILL, RUN CRAWL CTA, THEME TOGGLE, USER PROFILE -->
        <div style="display: flex; align-items: center; gap: 12px;">
          
          <!-- SYSTEM HEALTH PILL -->
          <div id="system-health-pill" style="display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 20px; background: var(--success-bg); border: 1px solid var(--success-border); font-size: 12px; font-weight: 600; color: var(--success); cursor: pointer;" title="Click to test backend server connection">
            <span id="health-dot" style="width: 6px; height: 6px; border-radius: 50%; background: var(--success); box-shadow: 0 0 6px var(--success);"></span>
            <span id="health-text">Backend Online</span>
          </div>

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
    this.initKeyboardShortcuts();
    this.initLogout();
    return this.element;
  }

  initLogout() {
    setTimeout(() => {
      const logoutBtn = document.getElementById('btn-logout');
      if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
          const isGuest = !!(authStore.user && (authStore.user.is_guest || authStore.user.auth_provider === 'guest' || (authStore.user.id && String(authStore.user.id).startsWith('guest_'))));
          const msg = isGuest ? 'Sign out of Guest Mode?' : 'Sign out of your Google Account?';
          if (confirm(msg)) {
            authStore.logout();
          }
        });
      }
    }, 50);
  }

  initThemeToggle() {
    setTimeout(() => {
      const btn = document.getElementById('theme-toggle-btn');
      const icon = document.getElementById('theme-icon');
      const label = document.getElementById('theme-label');

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

  initKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('global-search-input');
        if (searchInput) {
          searchInput.focus();
          searchInput.select();
        }
      }
    });
  }

  initHealthPill() {
    setTimeout(() => {
      const pillEl = document.getElementById('system-health-pill');
      const dotEl = document.getElementById('health-dot');
      const textEl = document.getElementById('health-text');
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
        await apiClient.checkHealth();
        updatePill(apiClient.status);
      });

      setInterval(() => apiClient.checkHealth(), 30000);
    }, 100);
  }

  async initProjectSelector() {
    const updateSelect = () => {
      const selectEl = document.getElementById('header-project-select');
      if (!selectEl) return;

      const selectedId = projectStore.getSelectedProjectId();
      const myProjects = projectStore.getMyProjects();
      const memberProjects = projectStore.getMemberProjects();

      if ((!myProjects || myProjects.length === 0) && (!memberProjects || memberProjects.length === 0)) {
        selectEl.innerHTML = `<option value="all">🌐 All Workspaces</option>`;
        return;
      }

      let optionsHtml = `<option value="all" ${!selectedId || selectedId === 'all' ? 'selected' : ''}>🌐 All Workspaces</option>`;

      if (myProjects && myProjects.length > 0) {
        optionsHtml += `<optgroup label="MY PROJECTS (Lead/Owner)">`;
        optionsHtml += myProjects.map(p => `
          <option value="${p.id}" ${String(p.id) === String(selectedId) ? 'selected' : ''}>
            ${p.name} (Lead)
          </option>
        `).join('');
        optionsHtml += `</optgroup>`;
      }

      if (memberProjects && memberProjects.length > 0) {
        optionsHtml += `<optgroup label="PROJECTS I'M A MEMBER OF">`;
        optionsHtml += memberProjects.map(p => `
          <option value="${p.id}" ${String(p.id) === String(selectedId) ? 'selected' : ''}>
            ${p.name} (Team Member)
          </option>
        `).join('');
        optionsHtml += `</optgroup>`;
      }

      selectEl.innerHTML = optionsHtml;

      if (selectedId) {
        selectEl.value = selectedId;
      }
    };

    try {
      await projectStore.ensureInitialized();
      updateSelect();
    } catch (e) {}

    projectStore.subscribe(() => updateSelect());

    setTimeout(() => {
      const selectEl = document.getElementById('header-project-select');
      if (selectEl && !selectEl.dataset.bound) {
        selectEl.dataset.bound = "true";
        selectEl.addEventListener('change', (e) => {
          const val = e.target.value;
          if (val) {
            projectStore.setSelectedProjectId(val);
            window.dispatchEvent(new CustomEvent('project:selected', { detail: { projectId: val } }));
          }
        });
      }
    }, 50);
  }
}
