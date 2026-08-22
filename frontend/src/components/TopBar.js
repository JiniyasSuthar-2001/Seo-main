import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';

window.showCreateProjectModal = () => {
  let modal = document.getElementById('create-project-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'create-project-modal';
    modal.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
      background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(4px);
      display: flex; align-items: center; justify-content: center; z-index: 9999;
    `;
    modal.innerHTML = `
      <div style="background: var(--bg-card); width: 100%; max-width: 480px; padding: 28px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;">Add New SEO Project</h3>
          <button onclick="window.closeCreateProjectModal()" style="background: none; border: none; font-size: 20px; color: var(--text-tertiary); cursor: pointer;">&times;</button>
        </div>
        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">
          Create an independent SEO workspace for another website domain.
        </p>
        <form onsubmit="window.submitNewProject(event)">
          <div style="margin-bottom: 16px;">
            <label style="display: block; font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 6px;">Project Name</label>
            <input id="modal-proj-name" type="text" placeholder="e.g. Acme Corporation" required style="width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-workspace); color: var(--text-primary);">
          </div>
          <div style="margin-bottom: 24px;">
            <label style="display: block; font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 6px;">Target Website URL</label>
            <input id="modal-proj-domain" type="url" placeholder="https://example.com/" required style="width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-workspace); color: var(--text-primary);">
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
    await projectStore.createProject({ name, url: domain });
    window.closeCreateProjectModal();
    window.location.reload();
  } catch (err) {
    alert(`Failed to create project: ${err.message || "Please check backend server status."}`);
  }
};

export class TopBar {
  constructor() {
    this.element = document.createElement('header');
    this.element.className = 'topbar-wrapper';
  }

  render() {
    this.element.innerHTML = `
      <div style="height: 100%; padding: 0 32px; display: flex; align-items: center; justify-content: space-between;">
        
        <!-- PROJECT SWITCHER DROPDOWN, (+) ADD BUTTON & COMMAND SEARCH -->
        <div style="display: flex; align-items: center; gap: 12px; flex: 1; max-width: 680px;">
          
          <!-- PROJECT SELECTOR CONTAINER WITH (+) BUTTON -->
          <div style="display: flex; align-items: center; gap: 6px;">
            <div style="display: flex; align-items: center; gap: 8px; background: var(--bg-subtle); padding: 4px 10px; border-radius: 8px; border: 1px solid var(--border);">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--primary);"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
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
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary);">
              <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input type="text" id="global-search-input" placeholder="Search pages, keywords, backlinks..." style="width: 100%; padding: 8px 12px 8px 36px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
            <span class="kbd" style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%);">Ctrl + K</span>
          </div>
        </div>

        <!-- RIGHT HEADER ACTIONS -->
        <div style="display: flex; align-items: center; gap: 16px;">
          
          <!-- SYSTEM HEALTH PILL -->
          <div id="system-health-pill" style="display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 12px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); font-size: 12px; font-weight: 600; color: #10b981; cursor: pointer;" title="Click to test backend server connection">

            <span id="health-dot" style="width: 6px; height: 6px; border-radius: 50%; background: #10b981; box-shadow: 0 0 6px #10b981;"></span>
            <span id="health-text">● Backend Online</span>
          </div>

          <!-- QUICK CRAWL BUTTON -->
          <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
            <span>Run Crawl</span>
          </button>

          <!-- USER AVATAR -->
          <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--sidebar-bg); color: #fff; font-weight: 700; font-size: 12px; display: flex; align-items: center; justify-content: center; cursor: pointer;" title="Jiniyas Suthar">
            JS
          </div>

        </div>
      </div>
    `;

    this.initProjectSelector();
    this.initHealthPill();
    return this.element;
  }

  initHealthPill() {
    setTimeout(() => {
      const pillEl = document.getElementById('system-health-pill');
      const dotEl = document.getElementById('health-dot');
      const textEl = document.getElementById('health-text');
      if (!pillEl) return;

      const updatePill = (status) => {
        if (status === 'ONLINE') {
          pillEl.style.background = 'rgba(16, 185, 129, 0.15)';
          pillEl.style.borderColor = 'rgba(16, 185, 129, 0.3)';
          pillEl.style.color = '#10b981';
          if (dotEl) { dotEl.style.background = '#10b981'; dotEl.style.boxShadow = '0 0 6px #10b981'; }
          if (textEl) textEl.innerText = '● Backend Online';
        } else if (status === 'DEGRADED') {
          pillEl.style.background = 'rgba(245, 158, 11, 0.15)';
          pillEl.style.borderColor = 'rgba(245, 158, 11, 0.3)';
          pillEl.style.color = '#f59e0b';
          if (dotEl) { dotEl.style.background = '#f59e0b'; dotEl.style.boxShadow = '0 0 6px #f59e0b'; }
          if (textEl) textEl.innerText = '● Server Degraded';
        } else {
          pillEl.style.background = 'rgba(239, 68, 68, 0.15)';
          pillEl.style.borderColor = 'rgba(239, 68, 68, 0.3)';
          pillEl.style.color = '#ef4444';
          if (dotEl) { dotEl.style.background = '#ef4444'; dotEl.style.boxShadow = '0 0 6px #ef4444'; }
          if (textEl) textEl.innerText = '● Backend Offline';
        }
      };

      updatePill(apiClient.status);
      apiClient.onStatusChange(updatePill);

      pillEl.addEventListener('click', async () => {
        if (textEl) textEl.innerText = '● Checking...';
        await apiClient.checkHealth();
        updatePill(apiClient.status);
      });

      // Periodic background health ping every 30s
      setInterval(() => apiClient.checkHealth(), 30000);
    }, 100);
  }

  async initProjectSelector() {
    const updateSelect = () => {
      const selectEl = document.getElementById('header-project-select');
      if (!selectEl) return;

      const projects = projectStore.projects;
      const selectedId = projectStore.getSelectedProjectId();

      if (!projects || projects.length === 0) {
        selectEl.innerHTML = `<option value="">No projects created</option>`;
        return;
      }

      selectEl.innerHTML = projects.map(p => `
        <option value="${p.id}" ${String(p.id) === String(selectedId) ? 'selected' : ''}>
          ${p.name} (${p.domain || p.url || 'No domain'})
        </option>
      `).join('');

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
