export class Router {
  constructor(viewContainer) {
    this.routes = {};
    this.viewContainer = viewContainer;
    
    window.addEventListener('popstate', () => this.handleRoute());
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
      if (e.target.matches('[data-link]')) {
        e.preventDefault();
        this.navigate(e.target.getAttribute('href'));
      } else if (e.target.closest('[data-link]')) {
        e.preventDefault();
        this.navigate(e.target.closest('[data-link]').getAttribute('href'));
      }
    });
  }
}
