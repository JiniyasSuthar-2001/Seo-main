import { projectStore } from '../core/projectStore.js';

export class TopBar {
  constructor() {
    this.element = document.createElement('header');
    this.element.className = 'topbar-wrapper';
  }

  render() {
    this.element.innerHTML = `
      <div style="height: 100%; padding: 0 32px; display: flex; align-items: center; justify-content: space-between;">
        
        <!-- PROJECT SWITCHER DROPDOWN & COMMAND SEARCH -->
        <div style="display: flex; align-items: center; gap: 16px; flex: 1; max-width: 650px;">
          
          <!-- PROJECT SELECTOR -->
          <div style="display: flex; align-items: center; gap: 8px; background: var(--bg-subtle); padding: 4px 10px; border-radius: 8px; border: 1px solid var(--border);">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--primary);"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
            <select id="header-project-select" style="background: transparent; border: none; font-size: 13px; font-weight: 600; color: var(--text-primary); cursor: pointer; outline: none;">
              <option value="">Loading projects...</option>
            </select>
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
          <div style="display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 12px; background: var(--success-bg); border: 1px solid var(--success-border); font-size: 12px; font-weight: 600; color: var(--success);">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--success); box-shadow: 0 0 6px var(--success);"></span>
            <span>● Connected</span>
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
    return this.element;
  }

  async initProjectSelector() {
    setTimeout(async () => {
      const selectEl = document.getElementById('header-project-select');
      if (!selectEl) return;

      await projectStore.fetchProjects();
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

      selectEl.addEventListener('change', (e) => {
        const val = e.target.value;
        if (val) {
          projectStore.setSelectedProjectId(val);
          // Refresh window location or view so all components reload data for new project
          window.location.reload();
        }
      });
    }, 100);
  }
}
