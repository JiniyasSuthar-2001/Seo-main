import { authStore } from '../../core/authStore.js';

export class MasterLogin {
  constructor() {
    this.element = document.createElement('div');
    this.element.className = 'master-login-view';
  }

  async render() {
    this.element.innerHTML = `
      <div style="min-height: 85vh; display: flex; align-items: center; justify-content: center; padding: 24px;">
        <div class="card" style="width: 100%; max-width: 440px; padding: 36px 32px; background: var(--bg-card); border-radius: 16px; border: 1px solid rgba(168, 85, 247, 0.25); box-shadow: 0 12px 36px rgba(0, 0, 0, 0.12); position: relative; overflow: hidden;">
          
          <!-- TOP ACCENT BAR -->
          <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #9333ea, #6366f1, #3b82f6);"></div>

          <!-- BRAND HEADER -->
          <div style="text-align: center; margin-bottom: 28px;">
            <div style="width: 52px; height: 52px; border-radius: 14px; background: linear-gradient(135deg, #9333ea, #6366f1); margin: 0 auto 14px; display: flex; align-items: center; justify-content: center; color: #fff; box-shadow: 0 4px 16px rgba(147, 51, 234, 0.35);">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              </svg>
            </div>
            
            <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(168, 85, 247, 0.1); padding: 3px 10px; border-radius: 6px; border: 1px solid rgba(168, 85, 247, 0.25); margin-bottom: 8px;">
              <span style="font-size: 11px; font-weight: 800; color: #a855f7; letter-spacing: 0.05em;">MASTER SPACE CONSOLE</span>
            </div>
            
            <h1 style="font-size: 22px; font-weight: 800; color: var(--text-primary); margin: 0 0 4px 0;">Secure Master Access</h1>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 0;">Multi-tenant platform control and system administration</p>
          </div>

          <!-- ERROR BANNER -->
          <div id="master-login-error" style="display: none; padding: 12px 14px; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; margin-bottom: 20px; font-size: 13px; color: #ef4444; text-align: center;"></div>

          <!-- MASTER LOGIN FORM -->
          <form id="master-login-form" style="display: flex; flex-direction: column; gap: 16px;">
            <div>
              <label for="master-login-id" style="display: block; font-size: 12.5px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">
                Master Login ID / Email
              </label>
              <input 
                type="text" 
                id="master-login-id" 
                required 
                placeholder="Enter Master Login ID" 
                autocomplete="username"
                style="width: 100%; padding: 11px 14px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 13.5px; color: var(--text-primary); outline: none; transition: border-color 0.15s ease;"
              />
            </div>

            <div>
              <label for="master-login-password" style="display: block; font-size: 12.5px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">
                Password
              </label>
              <input 
                type="password" 
                id="master-login-password" 
                required 
                placeholder="Enter Master password" 
                autocomplete="current-password"
                style="width: 100%; padding: 11px 14px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-size: 13.5px; color: var(--text-primary); outline: none; transition: border-color 0.15s ease;"
              />
            </div>

            <button 
              type="submit" 
              id="btn-submit-master-login" 
              class="btn btn-primary"
              style="margin-top: 6px; padding: 12px; font-size: 14px; font-weight: 700; background: linear-gradient(135deg, #9333ea, #6366f1); border: none; border-radius: 8px; color: #fff; cursor: pointer; transition: opacity 0.15s ease; box-shadow: 0 4px 14px rgba(147, 51, 234, 0.35);"
            >
              Sign In to Master Admin
            </button>
          </form>

          <!-- RETURN TO CUSTOMER APP -->
          <div style="margin-top: 24px; padding-top: 18px; border-top: 1px solid var(--border); text-align: center;">
            <a href="/" data-link style="font-size: 13px; font-weight: 600; color: var(--text-secondary); text-decoration: none; display: inline-flex; align-items: center; gap: 6px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
              <span>Return to Customer Workspace</span>
            </a>
          </div>

        </div>
      </div>
    `;

    this.bindEvents();
    return this.element;
  }

  bindEvents() {
    const form = this.element.querySelector('#master-login-form');
    const loginIdInput = this.element.querySelector('#master-login-id');
    const passwordInput = this.element.querySelector('#master-login-password');
    const errorEl = this.element.querySelector('#master-login-error');
    const submitBtn = this.element.querySelector('#btn-submit-master-login');

    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.innerText = 'Authenticating Master Access...';

        try {
          const loginId = loginIdInput.value.trim();
          const password = passwordInput.value;
          await authStore.masterLogin(loginId, password);

          // On success, redirect to Master root dashboard
          window.location.href = '/master';
        } catch (err) {
          errorEl.innerText = err.message || 'Master authentication failed.';
          errorEl.style.display = 'block';
          submitBtn.disabled = false;
          submitBtn.innerText = 'Sign In to Master Admin';
        }
      });
    }
  }
}
