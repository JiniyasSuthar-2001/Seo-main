export class Sidebar {
  render() {
    const element = document.createElement('aside');
    element.className = 'sidebar-nav';
    element.innerHTML = `
      <!-- BRAND HEADER -->
      <div style="padding: 24px 20px 16px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid var(--sidebar-border);">
        <div style="width: 34px; height: 34px; border-radius: 8px; background: linear-gradient(135deg, #2563eb, #3b82f6); display: flex; align-items: center; justify-content: center; color: #fff; box-shadow: 0 2px 8px rgba(37,99,235,0.4);">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
        </div>
        <div>
          <div style="font-weight: 700; font-size: 15px; color: #fff; letter-spacing: -0.01em;">SEO Intelligence</div>
          <div style="font-size: 11px; color: var(--sidebar-text); font-weight: 500;">Workspace Suite</div>
        </div>
      </div>

      <!-- NAVIGATION GROUPS -->
      <div style="padding: 16px 12px; display: flex; flex-direction: column; gap: 18px; flex: 1; overflow-y: auto;">
        
        <!-- OVERVIEW -->
        <div>
          <div class="nav-section-label">OVERVIEW</div>
          <nav class="nav-group">
            <a href="/" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
              <span>SEO Overview</span>
            </a>
          </nav>
        </div>

        <!-- AUDIT & PAGES -->
        <div>
          <div class="nav-section-label">AUDIT & PAGES</div>
          <nav class="nav-group">
            <a href="/technical" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
              <span>SEO Audit</span>
            </a>
            <a href="/pages" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>
              <span>Crawled Pages</span>
            </a>
          </nav>
        </div>

        <!-- RESEARCH & RANKINGS -->
        <div>
          <div class="nav-section-label">RESEARCH & RANKINGS</div>
          <nav class="nav-group">
            <a href="/keywords" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
              <span>Keywords</span>
            </a>
            <a href="/rankings" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
              <span>Rankings</span>
            </a>
          </nav>
        </div>

        <!-- COMPETITORS & LINKS -->
        <div>
          <div class="nav-section-label">COMPETITORS & LINKS</div>
          <nav class="nav-group">
            <a href="/competitors" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
              <span>Competitors</span>
            </a>
            <a href="/backlinks" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
              <span>Backlinks</span>
            </a>
            <a href="/internal-links" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
              <span>Internal Links</span>
            </a>
          </nav>
        </div>

        <!-- INSIGHTS & REPORTS -->
        <div>
          <div class="nav-section-label">INSIGHTS & REPORTS</div>
          <nav class="nav-group">
            <a href="/alerts" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
              <span>Alerts</span>
            </a>
            <a href="/opportunities" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
              <span>Opportunities</span>
            </a>
            <a href="/reports" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
              <span>Reports</span>
            </a>
            <a href="/import" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
              <span>Import Data</span>
            </a>
            <a href="/crawl-history" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 16 16 14"></polyline></svg>
              <span>Crawl History</span>
            </a>
          </nav>
        </div>


        <!-- SYSTEM -->
        <div>
          <div class="nav-section-label">SYSTEM</div>
          <nav class="nav-group">
            <a href="/projects" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
              <span>SEO Projects</span>
            </a>
            <a href="/integrations" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
              <span>Integrations</span>
            </a>
            <a href="/settings" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
              <span>Settings</span>
            </a>
            <a href="/help" data-link class="nav-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
              <span>Help & Docs</span>
            </a>
          </nav>
        </div>

      </div>

      <style>
        .sidebar-nav {
          display: flex;
          flex-direction: column;
          height: 100%;
        }
        .nav-section-label {
          font-size: 10px;
          font-weight: 700;
          color: #64748b;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          padding: 0 12px;
          margin-bottom: 6px;
        }
        .nav-group {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .nav-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 8px 12px;
          border-radius: 6px;
          color: var(--sidebar-text);
          text-decoration: none;
          font-size: 13px;
          font-weight: 500;
          transition: all 0.15s ease;
        }
        .nav-item:hover {
          background: var(--sidebar-item-hover);
          color: #ffffff;
        }
        .nav-item.active {
          background: var(--sidebar-item-active);
          color: #ffffff;
          box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);
        }
        .nav-item svg {
          opacity: 0.8;
          transition: opacity 0.15s ease;
        }
        .nav-item:hover svg, .nav-item.active svg {
          opacity: 1;
        }
      </style>
    `;

    this.initActiveHighlight(element);
    return element;
  }

  initActiveHighlight(sidebarElement) {
    const updateActive = (pathname) => {
      const currentPath = pathname || window.location.pathname;
      const navItems = sidebarElement.querySelectorAll('.nav-item');
      navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href === '/' && currentPath === '/') {
          item.classList.add('active');
        } else if (href !== '/' && currentPath.startsWith(href)) {
          item.classList.add('active');
        } else {
          item.classList.remove('active');
        }
      });
    };

    setTimeout(() => updateActive(), 50);

    window.addEventListener('routechange', (e) => {
      updateActive(e.detail ? e.detail.path : null);
    });
  }
}
