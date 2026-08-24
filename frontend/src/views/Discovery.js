import { authStore } from '../core/authStore.js';
import { projectStore } from '../core/projectStore.js';
import { themeStore } from '../core/themeStore.js';

export class Discovery {
  constructor() {
    this.element = document.createElement('div');
    this.element.className = 'discovery-view-container';
    this.properties = [];
    this.selectedPropertyIds = new Set();
  }

  render() {
    this.element.innerHTML = `
      <div style="padding: 40px; text-align: center;">
        <div class="skeleton" style="height: 24px; width: 300px; margin: 0 auto 16px;"></div>
        <div class="skeleton" style="height: 200px; width: 100%; max-width: 800px; margin: 0 auto;"></div>
      </div>
    `;
    return this.element;
  }

  async mounted() {
    try {
      this.properties = await authStore.discoverGoogleProperties();
      this.selectedPropertyIds = new Set(this.properties.map(p => p.id));
      this.renderDiscoveryUI();
    } catch (err) {
      this.element.innerHTML = `
        <div class="card" style="padding: 36px 24px; text-align: center; max-width: 520px; margin: 40px auto;">
          <h3 style="font-size: 18px; font-weight: 700; color: var(--critical);">Google Connection Warning</h3>
          <p style="color: var(--text-secondary); margin: 10px 0 20px;">
            Unable to discover Google properties at this time. You can proceed directly to your workspace.
          </p>
          <button class="btn btn-primary" onclick="window.location.href='/'">Go to Workspace Overview</button>
        </div>
      `;
    }
  }

  renderDiscoveryUI() {
    const accountEmail = authStore.user && authStore.user.email ? authStore.user.email : 'jiniyassuthar87@gmail.com';

    this.element.innerHTML = `
      <div class="discovery-wrapper">
        
        <!-- HEADER -->
        <div class="discovery-header">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; margin-bottom: 20px;">
            <div>
              <div style="display: inline-flex; align-items: center; gap: 8px; background: var(--success-bg); border: 1px solid var(--success-border); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; color: var(--success); margin-bottom: 8px;">
                <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--success);"></span>
                Google OAuth Connected (${accountEmail})
              </div>
              <h1 style="font-size: 26px; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.02em;">We found your Google properties</h1>
              <p style="color: var(--text-secondary); font-size: 14px; margin-top: 4px; max-width: 680px; line-height: 1.5;">
                We've discovered websites and business properties available through your connected Google account. Discovered websites are registered as <strong>Not Crawled</strong> projects so you can run your first audit whenever ready.
              </p>
            </div>

            <button id="discovery-theme-btn" class="theme-toggle-btn">
              <span>${themeStore.isDark() ? '🌙' : '☀'}</span>
              <span>${themeStore.isDark() ? 'Dark' : 'Light'}</span>
            </button>
          </div>

          <!-- STEP PROGRESS BAR -->
          <div class="step-progress-bar">
            <div class="step-item completed">
              <span class="step-num">✓</span>
              <span>Step 1: Google connected</span>
            </div>
            <div class="step-item active">
              <span class="step-num">2</span>
              <span>Step 2: Properties discovered</span>
            </div>
            <div class="step-item">
              <span class="step-num">3</span>
              <span>Step 3: Projects ready (Not Crawled)</span>
            </div>
            <div class="step-item">
              <span class="step-num">4</span>
              <span>Step 4: Run your first crawl</span>
            </div>
          </div>
        </div>

        <!-- DISCOVERED PROPERTIES LIST -->
        <div class="card" style="padding: 24px; margin-bottom: 24px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 10px;">
            <div>
              <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Discovered Google Accounts & Properties (${this.properties.length})</h3>
              <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Properties found across Google Search Console, Analytics, and Business Profile.</div>
            </div>
            <button class="btn btn-secondary btn-sm" id="btn-select-all">Select All (${this.properties.length})</button>
          </div>

          ${this.properties.length === 0 ? `
            <div class="empty-state">
              <div class="empty-state-icon">🌐</div>
              <h3 class="empty-state-title">No websites found</h3>
              <p class="empty-state-desc">We couldn't find any eligible websites or properties in your connected Google account.</p>
              <div style="display: flex; gap: 10px; justify-content: center;">
                <button class="btn btn-primary" onclick="window.showCreateProjectModal()">Add Website Manually</button>
              </div>
            </div>
          ` : `
            <div style="display: flex; flex-direction: column; gap: 12px;">
              ${this.properties.map(p => `
                <div class="property-card ${this.selectedPropertyIds.has(p.id) ? 'selected' : ''}" data-prop-id="${p.id}">
                  <div style="display: flex; align-items: center; gap: 14px; flex: 1;">
                    <input type="checkbox" class="prop-checkbox" ${this.selectedPropertyIds.has(p.id) ? 'checked' : ''} data-id="${p.id}" style="width: 18px; height: 18px; cursor: pointer; accent-color: var(--primary);"/>
                    <div>
                      <strong style="font-size: 15px; color: var(--text-primary); display: block;">${p.name}</strong>
                      <span style="font-size: 12px; color: var(--text-secondary);">${p.url || p.domain}</span>
                      <div style="display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap;">
                        ${p.sources.map(src => `<span class="badge badge-info" style="font-size: 10px;">${src}</span>`).join('')}
                      </div>
                    </div>
                  </div>

                  <div style="display: flex; items-center; gap: 16px; flex-wrap: wrap;">
                    <div style="text-align: right;">
                      <span class="badge badge-info" style="font-size: 11px; font-weight: 700;">Status: Connected</span>
                      <div style="font-size: 11.5px; color: var(--text-tertiary); margin-top: 4px;">Crawl: <strong style="color: var(--text-secondary);">Not Crawled</strong></div>
                    </div>
                  </div>
                </div>
              `).join('')}
            </div>
          `}
        </div>

        <!-- BOTTOM ACTION FOOTER -->
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
          <button class="btn btn-secondary" onclick="window.showCreateProjectModal()">+ Add Website Manually</button>

          <div style="display: flex; gap: 12px;">
            <button class="btn btn-ghost" onclick="window.location.href='/'">Skip for Now</button>
            <button id="btn-import-discovery" class="btn btn-primary" style="padding: 10px 24px; font-size: 14px;">
              Register Selected Properties & Open Workspace &rarr;
            </button>
          </div>
        </div>

      </div>

      <style>
        .discovery-wrapper {
          max-width: 980px;
          margin: 0 auto;
          padding: 24px 0 60px;
        }
        .discovery-header {
          margin-bottom: 24px;
        }
        .step-progress-bar {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 10px;
          background: var(--bg-card);
          padding: 12px 16px;
          border-radius: 12px;
          border: 1px solid var(--border);
        }
        .step-item {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          font-weight: 600;
          color: var(--text-tertiary);
        }
        .step-item.active {
          color: var(--primary);
        }
        .step-item.completed {
          color: var(--success);
        }
        .step-num {
          width: 22px;
          height: 22px;
          border-radius: 50%;
          background: var(--bg-subtle);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
        }
        .step-item.active .step-num {
          background: var(--primary-light);
          color: var(--primary);
        }
        .step-item.completed .step-num {
          background: var(--success-bg);
          color: var(--success);
        }

        .property-card {
          padding: 16px 20px;
          border-radius: 10px;
          border: 1px solid var(--border);
          background: var(--bg-subtle);
          display: flex;
          justify-content: space-between;
          align-items: center;
          transition: all 0.2s ease;
        }
        .property-card.selected {
          border-color: var(--primary);
          background: var(--bg-card);
          box-shadow: var(--shadow-sm);
        }
      </style>
    `;

    this.initHandlers();
  }

  initHandlers() {
    setTimeout(() => {
      const themeBtn = document.getElementById('discovery-theme-btn');
      if (themeBtn) {
        themeBtn.addEventListener('click', () => {
          themeStore.toggleTheme();
          const isDark = themeStore.isDark();
          themeBtn.innerHTML = `<span>${isDark ? '🌙' : '☀'}</span><span>${isDark ? 'Dark' : 'Light'}</span>`;
        });
      }

      const checkboxes = this.element.querySelectorAll('.prop-checkbox');
      checkboxes.forEach(cb => {
        cb.addEventListener('change', (e) => {
          const id = e.target.getAttribute('data-id');
          if (e.target.checked) this.selectedPropertyIds.add(id);
          else this.selectedPropertyIds.delete(id);

          const card = this.element.querySelector(`.property-card[data-prop-id="${id}"]`);
          if (card) {
            if (e.target.checked) card.classList.add('selected');
            else card.classList.remove('selected');
          }
        });
      });

      const importBtn = document.getElementById('btn-import-discovery');
      if (importBtn) {
        importBtn.addEventListener('click', async () => {
          importBtn.disabled = true;
          importBtn.innerText = 'Registering Projects (Not Crawled)...';

          const selectedList = this.properties.filter(p => this.selectedPropertyIds.has(p.id));
          try {
            await authStore.registerDiscoveredProjects(selectedList);
            await projectStore.ensureInitialized(true);
            window.location.href = '/';
          } catch (err) {
            importBtn.disabled = false;
            importBtn.innerText = 'Register Selected Properties & Open Workspace →';
            alert('Failed to register projects: ' + err.message);
          }
        });
      }
    }, 50);
  }
}
