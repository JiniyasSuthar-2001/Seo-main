import { router } from './router/router.js';
import { Sidebar } from './components/Sidebar.js';
import { Header } from './components/Header.js';
import { appState } from './state/appState.js';

class App {
  async init() {
    console.log("Initializing SEO Platform Frontend...");
    
    // Mount global components
    document.getElementById('sidebar-container').innerHTML = Sidebar.render();
    document.getElementById('header-container').innerHTML = Header.render();
    
    // Bind global events
    Sidebar.bindEvents();
    Header.bindEvents();
    
    // Init router
    await router.init();
    
    // Initialize data from API
    await appState.loadProject();
  }
}

const app = new App();
document.addEventListener('DOMContentLoaded', () => app.init());
