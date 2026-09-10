import { authStore } from '../core/authStore.js';

export class CustomerSidebar {
  render() {
    const element = document.createElement('aside');
    element.className = 'sidebar-nav customer-sidebar-nav';

    element.innerHTML = `
      <!-- BRAND HEADER -->
      <div class="sidebar-brand">
        <div class="brand-logo">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
        </div>
        <div style="flex: 1;">
          <div class="brand-title">SEO Intelligence</div>
          <div class="brand-subtitle">Analytics Platform</div>
        </div>
      </div>

      <!-- NAVIGATION GROUPS -->
      <div class="sidebar-scroll-area">
        
        <!-- WEBSITE -->
        <div class="nav-section">
          <div class="nav-section-label">WEBSITE</div>
          <nav class="nav-group">
            <a href="/" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
              <span>Overview</span>
            </a>
            <a href="/projects" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
              <span>My Website</span>
            </a>
            <a href="/pages" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>
              <span>Pages</span>
            </a>
            <a href="/technical" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
              <span>Website Check</span>
            </a>
          </nav>
        </div>

        <!-- GROWTH -->
        <div class="nav-section">
          <div class="nav-section-label">GROWTH</div>
          <nav class="nav-group">
            <a href="/keywords" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
              <span>Keywords</span>
            </a>
            <a href="/rankings" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
              <span>Search Rankings</span>
            </a>
            <a href="/backlinks" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
              <span>Links</span>
            </a>
            <a href="/internal-links" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
              <span>Internal Links</span>
            </a>
            <a href="/competitors" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
              <span>Competitors</span>
            </a>
            <a href="/opportunities" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
              <span>Recommended Actions</span>
            </a>
          </nav>
        </div>

        <!-- REPORTS -->
        <div class="nav-section">
          <div class="nav-section-label">REPORTS</div>
          <nav class="nav-group">
            <a href="/reports" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
              <span>Reports</span>
            </a>
            <a href="/crawl-data" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="3" y1="15" x2="21" y2="15"></line><line x1="9" y1="3" x2="9" y2="21"></line><line x1="15" y1="3" x2="15" y2="21"></line></svg>
              <span>Crawl Data</span>
            </a>
            <a href="/crawl-history" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 16 16 14"></polyline></svg>
              <span>Website Scan History</span>
            </a>
            <a href="/alerts" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
              <span>Alerts</span>
            </a>
          </nav>
        </div>

        <!-- DATA & SETTINGS -->
        <div class="nav-section">
          <div class="nav-section-label">DATA & SETTINGS</div>
          <nav class="nav-group">
            <a href="/import" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
              <span>Import Data</span>
            </a>
            <a href="/integrations" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
              <span>Connections</span>
            </a>
            <a href="/settings" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
              <span>Settings</span>
            </a>
            <a href="/help" data-link class="nav-item">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
              <span>Help</span>
            </a>
          </nav>
        </div>

      </div>
    `;

    setTimeout(() => this.updateActiveState(element), 0);

    const handleUpdate = () => this.updateActiveState(element);
    window.addEventListener('popstate', handleUpdate);
    window.addEventListener('routechange', handleUpdate);
    window.addEventListener('project:selected', handleUpdate);

    return element;
  }

  updateActiveState(container = document) {
    const currentPath = window.location.pathname || '/';
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
    const cleanHref = href.toLowerCase().replace(/\/$/, '') || '/';
    const cleanPath = currentPath.toLowerCase().replace(/\/$/, '') || '/';

    if (cleanHref === cleanPath) return 100;
    if (cleanHref === '/') {
      if (cleanPath === '/' || cleanPath === '' || cleanPath === '/overview') return 90;
      return 0;
    }
    if (cleanPath.startsWith(cleanHref + '/')) return 80;
    const segments = cleanPath.split('/').filter(Boolean);
    const hrefSegment = cleanHref.replace(/^\//, '');
    if (segments.includes(hrefSegment)) return 70;

    return 0;
  }
}
