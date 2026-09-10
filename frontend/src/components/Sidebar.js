import { CustomerSidebar } from './CustomerSidebar.js';
import { MasterSidebar } from './MasterSidebar.js';

export class Sidebar {
  constructor() {
    this.customerSidebar = new CustomerSidebar();
    this.masterSidebar = new MasterSidebar();
    this.currentMode = null; // 'customer' | 'master'
    this.container = null;
  }

  render() {
    const isMasterRoute = window.location.pathname.startsWith('/master');
    this.currentMode = isMasterRoute ? 'master' : 'customer';

    const wrapper = document.createElement('div');
    wrapper.id = 'sidebar-inner-wrapper';
    wrapper.style.height = '100%';
    this.container = wrapper;

    const activeSidebar = this.currentMode === 'master' ? this.masterSidebar : this.customerSidebar;
    wrapper.appendChild(activeSidebar.render());

    // Listen for navigation changes and switch sidebar mode if crossing boundary
    const handleRouteChange = () => {
      const isMaster = window.location.pathname.startsWith('/master');
      const targetMode = isMaster ? 'master' : 'customer';

      if (targetMode !== this.currentMode && this.container) {
        this.currentMode = targetMode;
        this.container.innerHTML = '';
        const newSidebar = targetMode === 'master' ? this.masterSidebar : this.customerSidebar;
        this.container.appendChild(newSidebar.render());
      } else if (this.container) {
        const active = this.currentMode === 'master' ? this.masterSidebar : this.customerSidebar;
        active.updateActiveState(this.container);
      }
    };

    window.addEventListener('popstate', handleRouteChange);
    window.addEventListener('routechange', handleRouteChange);

    return wrapper;
  }

  updateActiveState(container) {
    if (this.currentMode === 'master') {
      this.masterSidebar.updateActiveState(container || this.container);
    } else {
      this.customerSidebar.updateActiveState(container || this.container);
    }
  }
}
