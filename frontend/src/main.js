// Global error handler to intercept third-party browser extension / PerformanceObserver telemetry errors
window.addEventListener('error', (event) => {
    if (event?.message && (
        event.message.includes("Cannot read properties of undefined (reading 'startTime')") ||
        event.message.includes("reportAllChanges")
    )) {
        event.stopImmediatePropagation();
        event.preventDefault();
        return true;
    }
}, true);

window.addEventListener('unhandledrejection', (event) => {
    if (event?.reason?.message && (
        event.reason.message.includes("Cannot read properties of undefined (reading 'startTime')") ||
        event.reason.message.includes("reportAllChanges")
    )) {
        event.stopImmediatePropagation();
        event.preventDefault();
    }
}, true);

import { themeStore } from './core/themeStore.js';
import { authStore } from './core/authStore.js';
import { Router } from './core/router.js';
import { Sidebar } from './components/Sidebar.js';
import { TopBar } from './components/TopBar.js';
import { aiFloatingButton } from './components/AIFloatingButton.js';

// Views
import { Login } from './views/Login.js';
import { Discovery } from './views/Discovery.js';
import { Dashboard } from './views/Dashboard.js';
import { Projects } from './views/Projects.js';
import { Pages } from './views/Pages.js';
import { Keywords } from './views/Keywords.js';
import { Rankings } from './views/Rankings.js';
import { Backlinks } from './views/Backlinks.js';
import { InternalLinks } from './views/InternalLinks.js';
import { Competitors } from './views/Competitors.js';
import { Technical } from './views/Technical.js';
import { Opportunities } from './views/Opportunities.js';
import { Import } from './views/Import.js';
import { Reports } from './views/Reports.js';
import { CrawlHistory } from './views/CrawlHistory.js';
import { CrawlData } from './views/CrawlData.js';
import { Alerts } from './views/Alerts.js';
import { Settings } from './views/Settings.js';
import { Integrations } from './views/Integrations.js';
import { Help } from './views/Help.js';

// Master Space Views
import { MasterLogin } from './views/master/MasterLogin.js';
import { MasterDashboard } from './views/master/MasterDashboard.js';
import { MasterCustomers } from './views/master/MasterCustomers.js';
import { MasterCustomerDetail } from './views/master/MasterCustomerDetail.js';
import { MasterWebsites } from './views/master/MasterWebsites.js';
import { MasterWebsiteDetail } from './views/master/MasterWebsiteDetail.js';
import { MasterAIAnalytics } from './views/master/MasterAIAnalytics.js';
import { MasterAIControl } from './views/master/MasterAIControl.js';
import { MasterCredits } from './views/master/MasterCredits.js';
import { MasterProviders } from './views/master/MasterProviders.js';
import { MasterActivity } from './views/master/MasterActivity.js';
import { MasterSystemHealth } from './views/master/MasterSystemHealth.js';
import { MasterAuditLogs } from './views/master/MasterAuditLogs.js';
import { MasterAccounts } from './views/master/MasterAccounts.js';

document.addEventListener('DOMContentLoaded', () => {
  themeStore.init();
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

  document.body.appendChild(aiFloatingButton.render());

  // Initialize Router
  const router = new Router(viewContainer);
  
  router.addRoute('/login', Login);
  router.addRoute('/discovery', Discovery);
  router.addRoute('/', Dashboard);
  router.addRoute('/projects', Projects);
  router.addRoute('/pages', Pages);
  router.addRoute('/crawl-data', CrawlData);
  router.addRoute('/keywords', Keywords);
  router.addRoute('/rankings', Rankings);
  router.addRoute('/backlinks', Backlinks);
  router.addRoute('/internal-links', InternalLinks);
  router.addRoute('/competitors', Competitors);
  router.addRoute('/technical', Technical);
  router.addRoute('/opportunities', Opportunities);
  router.addRoute('/import', Import);
  router.addRoute('/reports', Reports);
  router.addRoute('/crawl-history', CrawlHistory);
  router.addRoute('/alerts', Alerts);
  router.addRoute('/settings', Settings);
  router.addRoute('/integrations', Integrations);
  router.addRoute('/help', Help);

  // Master Space Routes
  router.addRoute('/master/login', MasterLogin);
  router.addRoute('/master', MasterDashboard);
  router.addRoute('/master/accounts', MasterAccounts);
  router.addRoute('/master/customers', MasterCustomers);
  router.addRoute('/master/customers/detail', MasterCustomerDetail);
  router.addRoute('/master/websites', MasterWebsites);
  router.addRoute('/master/websites/detail', MasterWebsiteDetail);
  router.addRoute('/master/ai-analytics', MasterAIAnalytics);
  router.addRoute('/master/ai-control', MasterAIControl);
  router.addRoute('/master/credits', MasterCredits);
  router.addRoute('/master/providers', MasterProviders);
  router.addRoute('/master/activity', MasterActivity);
  router.addRoute('/master/system-health', MasterSystemHealth);
  router.addRoute('/master/audit-logs', MasterAuditLogs);

  router.init();
});
