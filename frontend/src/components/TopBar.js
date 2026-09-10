import { CustomerTopBar } from './CustomerTopBar.js';
import { MasterTopBar } from './MasterTopBar.js';

export class TopBar {
  constructor() {
    this.customerTopBar = new CustomerTopBar();
    this.masterTopBar = new MasterTopBar();
    this.currentMode = null; // 'customer' | 'master'
    this.container = null;
  }

  render() {
    const isMasterRoute = window.location.pathname.startsWith('/master');
    this.currentMode = isMasterRoute ? 'master' : 'customer';

    const wrapper = document.createElement('div');
    wrapper.id = 'topbar-inner-wrapper';
    wrapper.style.height = '100%';
    this.container = wrapper;

    const activeTopBar = this.currentMode === 'master' ? this.masterTopBar : this.customerTopBar;
    wrapper.appendChild(activeTopBar.render());

    const handleRouteChange = () => {
      const isMaster = window.location.pathname.startsWith('/master');
      const targetMode = isMaster ? 'master' : 'customer';

      if (targetMode !== this.currentMode && this.container) {
        this.currentMode = targetMode;
        this.container.innerHTML = '';
        const newTopBar = targetMode === 'master' ? this.masterTopBar : this.customerTopBar;
        this.container.appendChild(newTopBar.render());
      }
    };

    window.addEventListener('popstate', handleRouteChange);
    window.addEventListener('routechange', handleRouteChange);

    return wrapper;
  }
}
