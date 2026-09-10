import { authStore } from './authStore.js';
import { initTooltipListeners } from '../components/Tooltip.js';

export class Router {
  constructor(viewContainer) {
    this.routes = {};
    this.viewContainer = viewContainer;
    this.sessionAlreadyInitialized = false;
    
    window.addEventListener('popstate', () => this.handleRoute());
    window.addEventListener('project:selected', () => this.handleRoute());
    window.addEventListener('seo:crawl-completed', () => this.handleRoute());
  }

  addRoute(path, ViewComponent) {
    this.routes[path] = ViewComponent;
  }

  navigate(path) {
    const cleanPath = path && path.length > 1 ? path.replace(/\/+$/, '') : (path || '/');
    window.history.pushState({}, '', cleanPath);
    this.handleRoute();
  }

  async handleRoute() {
    const rawPath = window.location.pathname || '/';
    let path = rawPath.length > 1 ? rawPath.replace(/\/+$/, '') : rawPath;

    // 1. Check for token in URL query parameters (Google Auth callback)
    const urlParams = new URLSearchParams(window.location.search);
    const tokenParam = urlParams.get('token');

    if (tokenParam && tokenParam.trim()) {
      console.log('[AUTH] Application session token stored.');
      
      const cleanToken = tokenParam.trim();
      localStorage.setItem('seo_auth_token', cleanToken);
      authStore.token = cleanToken;
      authStore.isAuthenticated = true;

      // Remove token parameter from URL cleanly without page reload
      urlParams.delete('token');
      const newQuery = urlParams.toString();
      const cleanUrl = window.location.pathname + (newQuery ? `?${newQuery}` : '');
      window.history.replaceState({}, '', cleanUrl);
    }

    // 2. Validate persistent application authentication session
    const isFirstTime = !this.sessionAlreadyInitialized;
    if (isFirstTime) {
      console.log('[AUTH] Establishing application session...');
    }
    
    const hasSession = await authStore.checkSession();

    if (hasSession && authStore.user && isFirstTime) {
      console.log(`[AUTH] Current user loaded: ${authStore.user.email || authStore.user.id}`);
      console.log('[AUTH] Authentication initialization complete.');
      this.sessionAlreadyInitialized = true;
    }

    const isLoginPage = path === '/login' || path === '/master/login';

    if (path === '/login' && hasSession) {
      // Valid session exists — skip customer login and continue to authorized area
      window.history.replaceState({}, '', '/');
      path = '/';
    } else if (path === '/master/login' && hasSession) {
      const userRole = (authStore.user?.platform_role || 'USER').toUpperCase();
      const isMasterUser = ['SUPER_MASTER', 'MASTER_ADMIN', 'SUPER_ADMIN', 'ADMIN', 'SUPPORT', 'ANALYST'].includes(userRole);
      if (isMasterUser) {
        window.history.replaceState({}, '', '/master');
        path = '/master';
      }
    } else if (!isLoginPage && !hasSession) {
      // Unauthenticated — redirect to appropriate login
      if (path.startsWith('/master')) {
        console.warn('[AUTH] Unauthenticated Master access attempt. Redirecting to /master/login.');
        window.history.replaceState({}, '', '/master/login');
        path = '/master/login';
      } else {
        console.warn('[AUTH] Unauthenticated user. Redirecting to /login.');
        window.history.replaceState({}, '', '/login');
        path = '/login';
      }
    }

    // Master Route Protection Guard for Authenticated Users
    if (path.startsWith('/master') && path !== '/master/login') {
      const userRole = (authStore.user?.platform_role || 'USER').toUpperCase();
      const isMasterUser = ['SUPER_MASTER', 'MASTER_ADMIN', 'SUPER_ADMIN', 'ADMIN', 'SUPPORT', 'ANALYST'].includes(userRole);
      if (!isMasterUser) {
        console.warn(`[ROUTER GUARD] Unauthorized Master route attempt (${path}) by non-master role '${userRole}'. Redirecting to /master/login.`);
        window.history.replaceState({}, '', '/master/login');
        path = '/master/login';
      }
    }

    const sidebarContainer = document.getElementById('sidebar-container');
    const topbarContainer = document.getElementById('topbar-container');
    const workspaceArea = document.querySelector('.workspace-area');

    if (path === '/login' || path === '/master/login') {
      if (sidebarContainer) sidebarContainer.style.display = 'none';
      if (topbarContainer) topbarContainer.style.display = 'none';
      if (workspaceArea) workspaceArea.style.marginLeft = '0';
    } else {
      if (sidebarContainer) sidebarContainer.style.display = 'flex';
      if (topbarContainer) topbarContainer.style.display = 'block';
      if (workspaceArea) workspaceArea.style.marginLeft = '250px';
    }

    let ViewComponent = this.routes[path];
    if (!ViewComponent) {
      if (path.startsWith('/master/customers/')) {
        ViewComponent = this.routes['/master/customers/detail'];
      } else if (path.startsWith('/master/websites/')) {
        ViewComponent = this.routes['/master/websites/detail'];
      } else if (path.startsWith('/master')) {
        ViewComponent = this.routes['/master'] || this.routes['/'];
      } else {
        ViewComponent = this.routes['/'];
      }
    }
    
    window.dispatchEvent(new CustomEvent('routechange', { detail: { path } }));

    if (ViewComponent) {
      const view = new ViewComponent();
      this.viewContainer.innerHTML = '';
      
      const element = await view.render();
      this.viewContainer.appendChild(element);
      
      if (view.mounted) {
        view.mounted();
      }
      initTooltipListeners(this.viewContainer);
    }
  }

  async init() {
    await this.handleRoute();
    
    document.body.addEventListener('click', e => {
      const linkEl = e.target.matches('[data-link]') ? e.target : e.target.closest('[data-link]');
      if (linkEl) {
        e.preventDefault();
        this.navigate(linkEl.getAttribute('href'));
      }
    });
  }
}
