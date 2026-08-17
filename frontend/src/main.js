import { Router } from './core/router.js';
import { Sidebar } from './components/Sidebar.js';
import { TopBar } from './components/TopBar.js';

// Views
import { Dashboard } from './views/Dashboard.js';
import { Pages } from './views/Pages.js';
import { Keywords } from './views/Keywords.js';
import { Rankings } from './views/Rankings.js';
import { Backlinks } from './views/Backlinks.js';
import { InternalLinks } from './views/InternalLinks.js';
import { Competitors } from './views/Competitors.js';
import { Technical } from './views/Technical.js';
import { Import } from './views/Import.js';
import { Reports } from './views/Reports.js';
import { CrawlHistory } from './views/CrawlHistory.js';
import { Alerts } from './views/Alerts.js';
import { Settings } from './views/Settings.js';
import { Help } from './views/Help.js';

document.addEventListener('DOMContentLoaded', () => {
  const appRoot = document.getElementById('app-root');
  
  // App Shell Structure
  appRoot.innerHTML = `
    <div id="sidebar-container"></div>
    <div class="workspace-area">
      <div id="topbar-container"></div>
      <main class="view-container" id="view-container"></main>
    </div>
  `;

  // Render Shell Components
  const sidebarContainer = document.getElementById('sidebar-container');
  const topbarContainer = document.getElementById('topbar-container');
  const viewContainer = document.getElementById('view-container');

  const sidebar = new Sidebar();
  sidebarContainer.appendChild(sidebar.render());

  const topBar = new TopBar();
  topbarContainer.appendChild(topBar.render());

  // Initialize Router
  const router = new Router(viewContainer);
  
  router.addRoute('/', Dashboard);
  router.addRoute('/pages', Pages);
  router.addRoute('/keywords', Keywords);
  router.addRoute('/rankings', Rankings);
  router.addRoute('/backlinks', Backlinks);
  router.addRoute('/internal-links', InternalLinks);
  router.addRoute('/competitors', Competitors);
  router.addRoute('/technical', Technical);
  router.addRoute('/import', Import);
  router.addRoute('/reports', Reports);
  router.addRoute('/crawl-history', CrawlHistory);
  router.addRoute('/alerts', Alerts);
  router.addRoute('/settings', Settings);
  router.addRoute('/help', Help);

  router.init();
});
