export class Router {
  constructor(viewContainer) {
    this.routes = {};
    this.viewContainer = viewContainer;
    
    window.addEventListener('popstate', () => this.handleRoute());
    window.addEventListener('project:selected', () => this.handleRoute());
  }


  addRoute(path, ViewComponent) {
    this.routes[path] = ViewComponent;
  }

  navigate(path) {
    window.history.pushState({}, '', path);
    this.handleRoute();
  }

  async handleRoute() {
    const path = window.location.pathname;
    const ViewComponent = this.routes[path] || this.routes['/'];
    
    // Dispatch global routechange event for active navbar highlighting
    window.dispatchEvent(new CustomEvent('routechange', { detail: { path } }));

    if (ViewComponent) {
      const view = new ViewComponent();
      this.viewContainer.innerHTML = '';
      
      const element = await view.render();
      this.viewContainer.appendChild(element);
      
      if(view.mounted) {
        view.mounted();
      }
    }
  }

  init() {
    this.handleRoute();
    
    // Intercept all internal links
    document.body.addEventListener('click', e => {
      const linkEl = e.target.matches('[data-link]') ? e.target : e.target.closest('[data-link]');
      if (linkEl) {
        e.preventDefault();
        this.navigate(linkEl.getAttribute('href'));
      }
    });
  }
}
