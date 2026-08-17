import { KeywordsPage } from '../pages/KeywordsPage.js';
import { DashboardPage } from '../pages/DashboardPage.js';

class Router {
  constructor() {
    this.routes = {
      '/dashboard': DashboardPage,
      '/search/keywords': KeywordsPage,
      // ...other routes
    };
    this.currentRoute = null;
  }

  async init() {
    window.addEventListener('popstate', () => this.handleRoute(window.location.pathname));
    
    // Intercept navigation
    document.body.addEventListener('click', e => {
      const link = e.target.closest('[data-route]');
      if (link) {
        e.preventDefault();
        this.navigate(link.dataset.route);
      }
    });

    // Default route
    const path = window.location.pathname === '/' ? '/dashboard' : window.location.pathname;
    await this.handleRoute(path);
  }

  async navigate(path) {
    window.history.pushState({}, '', path);
    await this.handleRoute(path);
  }

  async handleRoute(path) {
    this.currentRoute = path;
    const container = document.getElementById('view-container');
    const PageClass = this.routes[path] || DashboardPage;
    
    const page = new PageClass();
    container.innerHTML = await page.render();
    if (page.afterRender) {
      await page.afterRender();
    }
    
    // Update Active Nav State
    document.querySelectorAll('[data-route]').forEach(el => el.classList.remove('active'));
    const activeEl = document.querySelector(`[data-route="${path}"]`);
    if(activeEl) activeEl.classList.add('active');
  }
}

export const router = new Router();
