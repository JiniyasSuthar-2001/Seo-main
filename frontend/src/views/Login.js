import { authStore } from '../core/authStore.js';
import { themeStore } from '../core/themeStore.js';

export class Login {
  constructor() {
    this.element = document.createElement('div');
    this.element.className = 'login-view-container';
    this.isRegisterMode = false;
  }

  render() {
    this.element.innerHTML = `
      <div class="login-wrapper">
        
        <!-- TOP CONTROLS: THEME SWITCHER -->
        <div class="login-topbar">
          <button id="login-theme-btn" class="theme-toggle-btn" style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 20px; padding: 6px 14px; font-size: 13px; color: var(--text-primary); cursor: pointer; display: flex; align-items: center; gap: 6px;">
            <span>${themeStore.isDark() ? '🌙' : '☀'}</span>
            <span>${themeStore.isDark() ? 'Dark' : 'Light'}</span>
          </button>
        </div>

        <!-- TWO-COLUMN CONTAINER -->
        <div class="login-grid">
          
          <!-- LEFT COLUMN: PRODUCT BRANDING -->
          <div class="login-branding-col">
            <div class="brand-badge">
              <div class="brand-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
              </div>
              <span class="brand-name">SEO Intelligence</span>
            </div>

            <h1 class="headline">Understand.<br/><span class="headline-gradient">Audit. Improve.</span></h1>
            
            <p class="subtitle">
              Monitor your websites, technical SEO health, search performance, and competitive intelligence from one unified platform.
            </p>

            <!-- PLATFORM CAPABILITIES -->
            <div class="analytics-preview-card">
              <div class="preview-header">
                <div class="preview-title">Enterprise SEO Platform</div>
                <span class="preview-tag">SECURE WORKSPACE</span>
              </div>
              
              <div class="preview-metrics-grid">
                <div class="preview-metric">
                  <span class="pm-label">Technical Audit</span>
                  <div class="pm-value" style="font-size: 14px; font-weight: 700; color: var(--text-primary);">Deep Web Crawler</div>
                  <span class="pm-subtext">Automated SEO Audits</span>
                </div>
                <div class="preview-metric">
                  <span class="pm-label">Keyword & Rank Tracking</span>
                  <div class="pm-value" style="font-size: 14px; font-weight: 700; color: var(--text-primary);">SERP Intelligence</div>
                  <span class="pm-subtext">Competitive Benchmarks</span>
                </div>
              </div>
            </div>

            <div class="branding-footer">
              Enterprise SEO Analytics Suite • Secure Role-Based Access
            </div>
          </div>

          <!-- RIGHT COLUMN: CLEAN SAAS LOGIN CARD -->
          <div class="login-card-col">
            <div class="login-card">
              
              <div class="card-title-group">
                <h2 class="card-headline" id="login-title">Sign in to your SEO Platform</h2>
                <p class="card-subheadline" id="login-subtitle">Enter your email and password to access your SEO workspace.</p>
              </div>

              <div id="login-error-box" style="display: none;" class="login-error-banner"></div>
              <div id="login-success-box" style="display: none;" class="login-success-banner"></div>

              <!-- FORM FIELDS -->
              <form id="platform-auth-form" onsubmit="return false;" style="display: flex; flex-direction: column; gap: 16px;">
                
                <div id="name-field-group" style="display: none;">
                  <label class="form-label" style="display: block; font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Full Name</label>
                  <input type="text" id="login-name" class="form-input" placeholder="e.g. Alex Morgan" style="width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; background: var(--bg-input, var(--bg-card)); color: var(--text-primary); outline: none;" />
                </div>

                <div>
                  <label class="form-label" style="display: block; font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Email Address</label>
                  <input type="email" id="login-email" class="form-input" placeholder="name@company.com" required style="width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; background: var(--bg-input, var(--bg-card)); color: var(--text-primary); outline: none;" />
                </div>

                <div>
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <label class="form-label" style="font-size: 13px; font-weight: 600; color: var(--text-primary);">Password</label>
                    <a href="#" id="forgot-password-link" style="font-size: 12px; color: var(--primary); text-decoration: none; font-weight: 600;">Forgot password?</a>
                  </div>
                  <input type="password" id="login-password" class="form-input" placeholder="••••••••" required style="width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; background: var(--bg-input, var(--bg-card)); color: var(--text-primary); outline: none;" />
                </div>

                <!-- PRIMARY SIGN IN BUTTON -->
                <button type="submit" id="btn-submit-auth" class="btn-primary-auth" style="width: 100%; padding: 12px; border: none; border-radius: 8px; background: var(--primary); color: #ffffff; font-size: 14px; font-weight: 700; cursor: pointer; transition: all 0.15s ease; margin-top: 6px;">
                  <span id="btn-auth-text">Sign In</span>
                </button>
              </form>

              <!-- TOGGLE BETWEEN SIGN IN AND REGISTER -->
              <div style="margin-top: 20px; text-align: center; font-size: 13.5px; color: var(--text-secondary);">
                <span id="toggle-auth-prompt">Don't have an account?</span>
                <a href="#" id="toggle-auth-mode-btn" style="color: var(--primary); font-weight: 700; text-decoration: none; margin-left: 4px;">Create Account</a>
              </div>

              <div class="privacy-notice" style="margin-top: 24px; font-size: 12px; color: var(--text-tertiary); text-align: center; border-top: 1px solid var(--border); padding-top: 16px;">
                Protected by Enterprise Role-Based Access Control • Privacy & Security Guaranteed
              </div>

            </div>
          </div>

        </div>

      </div>

      <style>
        .login-view-container {
          min-height: 100vh;
          width: 100vw;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--bg-workspace, #f8fafc);
          position: fixed;
          top: 0; left: 0;
          z-index: 999;
          overflow-y: auto;
          padding: 24px;
        }
        .login-wrapper {
          width: 100%;
          max-width: 1020px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .login-topbar {
          display: flex;
          justify-content: flex-end;
        }
        .login-grid {
          display: grid;
          grid-template-columns: 1.1fr 0.9fr;
          gap: 36px;
          align-items: center;
        }
        .login-branding-col {
          display: flex;
          flex-direction: column;
          gap: 20px;
          padding-right: 12px;
        }
        .brand-badge {
          display: inline-flex;
          align-items: center;
          gap: 10px;
        }
        .brand-icon {
          width: 36px;
          height: 36px;
          border-radius: 10px;
          background: linear-gradient(135deg, var(--primary, #2563eb), #7c3aed);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
        }
        .brand-name {
          font-size: 18px;
          font-weight: 800;
          color: var(--text-primary);
          letter-spacing: -0.02em;
        }
        .headline {
          font-size: 38px;
          font-weight: 800;
          line-height: 1.15;
          letter-spacing: -0.03em;
          color: var(--text-primary);
          margin: 0;
        }
        .headline-gradient {
          background: linear-gradient(135deg, var(--primary, #2563eb), #7c3aed);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .subtitle {
          font-size: 15px;
          color: var(--text-secondary);
          line-height: 1.6;
          margin: 0;
        }
        .analytics-preview-card {
          background: var(--bg-card, #ffffff);
          border: 1px solid var(--border, #e2e8f0);
          border-radius: 14px;
          padding: 20px;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
        }
        .preview-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 14px;
        }
        .preview-title {
          font-size: 13px;
          font-weight: 700;
          color: var(--text-primary);
        }
        .preview-tag {
          font-size: 10px;
          font-weight: 800;
          padding: 3px 8px;
          border-radius: 12px;
          background: rgba(37, 99, 235, 0.1);
          color: var(--primary, #2563eb);
          letter-spacing: 0.04em;
        }
        .preview-metrics-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }
        .preview-metric {
          background: var(--bg-subtle, #f1f5f9);
          padding: 12px;
          border-radius: 8px;
        }
        .pm-label {
          font-size: 11px;
          font-weight: 600;
          color: var(--text-secondary);
          display: block;
          margin-bottom: 2px;
        }
        .pm-subtext {
          font-size: 11px;
          color: var(--text-tertiary);
          display: block;
          margin-top: 2px;
        }
        .branding-footer {
          font-size: 12px;
          color: var(--text-tertiary);
        }

        .login-card-col {
          display: flex;
          justify-content: center;
        }
        .login-card {
          width: 100%;
          max-width: 420px;
          background: var(--bg-card, #ffffff);
          border: 1px solid var(--border, #e2e8f0);
          border-radius: 16px;
          padding: 32px;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06);
        }
        .card-title-group {
          margin-bottom: 24px;
        }
        .card-headline {
          font-size: 22px;
          font-weight: 700;
          color: var(--text-primary);
          margin: 0 0 6px 0;
          letter-spacing: -0.02em;
        }
        .card-subheadline {
          font-size: 13.5px;
          color: var(--text-secondary);
          margin: 0;
          line-height: 1.5;
        }
        .login-error-banner {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #ef4444;
          padding: 10px 14px;
          border-radius: 8px;
          font-size: 13px;
          margin-bottom: 16px;
        }
        .login-success-banner {
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid rgba(16, 185, 129, 0.3);
          color: #10b981;
          padding: 10px 14px;
          border-radius: 8px;
          font-size: 13px;
          margin-bottom: 16px;
        }
        .form-input:focus {
          border-color: var(--primary, #2563eb) !important;
          box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
        }
        .btn-primary-auth:hover {
          opacity: 0.92;
        }

        @media (max-width: 860px) {
          .login-grid {
            grid-template-columns: 1fr;
            gap: 24px;
          }
          .login-branding-col {
            display: none;
          }
        }
      </style>
    `;

    this.initHandlers();
    return this.element;
  }

  initHandlers() {
    setTimeout(() => {
      const themeBtn = document.getElementById('login-theme-btn');
      if (themeBtn) {
        themeBtn.addEventListener('click', () => {
          themeStore.toggleTheme();
          const isDark = themeStore.isDark();
          themeBtn.innerHTML = `<span>${isDark ? '🌙' : '☀'}</span><span>${isDark ? 'Dark' : 'Light'}</span>`;
        });
      }

      const form = document.getElementById('platform-auth-form');
      const submitBtn = document.getElementById('btn-submit-auth');
      const authText = document.getElementById('btn-auth-text');
      const errorBox = document.getElementById('login-error-box');
      const toggleModeBtn = document.getElementById('toggle-auth-mode-btn');
      const togglePrompt = document.getElementById('toggle-auth-prompt');
      const nameGroup = document.getElementById('name-field-group');
      const titleEl = document.getElementById('login-title');
      const subtitleEl = document.getElementById('login-subtitle');

      if (toggleModeBtn) {
        toggleModeBtn.addEventListener('click', (e) => {
          e.preventDefault();
          this.isRegisterMode = !this.isRegisterMode;

          if (errorBox) errorBox.style.display = 'none';
          const pwdInput = document.getElementById('login-password');
          if (this.isRegisterMode) {
            titleEl.innerText = "Create your SEO Account";
            subtitleEl.innerText = "Register a new account to start auditing and managing SEO projects.";
            authText.innerText = "Create Account";
            togglePrompt.innerText = "Already have an account?";
            toggleModeBtn.innerText = "Sign In";
            if (nameGroup) nameGroup.style.display = "block";
            if (pwdInput) pwdInput.placeholder = "At least 8 characters";
          } else {
            titleEl.innerText = "Sign in to your SEO Platform";
            subtitleEl.innerText = "Enter your email and password to access your SEO workspace.";
            authText.innerText = "Sign In";
            togglePrompt.innerText = "Don't have an account?";
            toggleModeBtn.innerText = "Create Account";
            if (nameGroup) nameGroup.style.display = "none";
            if (pwdInput) pwdInput.placeholder = "••••••••";
          }
        });
      }

      if (form) {
        form.addEventListener('submit', async (e) => {
          e.preventDefault();
          const email = document.getElementById('login-email')?.value || '';
          const password = document.getElementById('login-password')?.value || '';
          const name = document.getElementById('login-name')?.value || '';

          if (errorBox) errorBox.style.display = 'none';
          if (submitBtn) submitBtn.disabled = true;
          if (authText) authText.innerText = this.isRegisterMode ? 'Creating Account...' : 'Signing In...';

          try {
            if (this.isRegisterMode) {
              await authStore.register(name, email, password);
            } else {
              await authStore.login(email, password);
            }
            console.log('[AUTH UI] Authentication successful. Navigating to dashboard.');
            window.location.href = '/';
          } catch (err) {
            if (submitBtn) submitBtn.disabled = false;
            if (authText) authText.innerText = this.isRegisterMode ? 'Create Account' : 'Sign In';
            if (errorBox) {
              errorBox.style.display = 'block';
              errorBox.innerText = err.message || 'Authentication failed. Please check your credentials.';
            }
          }
        });
      }

      const forgotLink = document.getElementById('forgot-password-link');
      if (forgotLink) {
        forgotLink.addEventListener('click', (e) => {
          e.preventDefault();
          alert("To reset your password, please contact your workspace administrator or check your email provider.");
        });
      }
    }, 50);
  }
}
