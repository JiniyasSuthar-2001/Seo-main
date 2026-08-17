export class TopBar {
  render() {
    const element = document.createElement('header');
    element.className = 'topbar-wrapper';
    element.innerHTML = `
      <div style="height: 100%; padding: 0 32px; display: flex; align-items: center; justify-content: space-between;">
        
        <!-- GLOBAL COMMAND SEARCH BAR -->
        <div style="display: flex; align-items: center; gap: 12px; flex: 1; max-width: 440px;">
          <div style="position: relative; width: 100%;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary);">
              <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input type="text" id="global-search-input" placeholder="Search pages, keywords, backlinks..." style="width: 100%; padding: 8px 12px 8px 36px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary); transition: border-color 0.15s ease;">
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
    return element;
  }
}
