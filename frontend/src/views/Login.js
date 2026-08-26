import { authStore } from '../core/authStore.js';
import { themeStore } from '../core/themeStore.js';

export class Login {
  constructor() {
    this.element = document.createElement('div');
    this.element.className = 'login-view-container';
  }

  render() {
    this.element.innerHTML = `
      <div class="login-wrapper">
        
        <!-- TOP CONTROLS: THEME SWITCHER -->
        <div class="login-topbar">
          <button id="login-theme-btn" class="theme-toggle-btn">
            <span>${themeStore.isDark() ? '🌙' : '☀'}</span>
            <span>${themeStore.isDark() ? 'Dark' : 'Light'}</span>
          </button>
        </div>

        <!-- TWO-COLUMN CONTAINER -->
        <div class="login-grid">
          
          <!-- LEFT COLUMN: PRODUCT BRANDING & ANALYTICS VISUALS -->
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
              Monitor your websites, technical SEO health, search performance, and Google properties from one intelligent workspace.
            </p>

            <!-- PLATFORM CAPABILITIES FEATURE HIGHLIGHTS -->
            <div class="analytics-preview-card">
              <div class="preview-header">
                <div class="preview-title">Platform Capabilities Overview</div>
                <span class="preview-tag">SECURE WORKSPACE</span>
              </div>
              
              <div class="preview-metrics-grid">
                <div class="preview-metric">
                  <span class="pm-label">Search Console</span>
                  <div class="pm-value" style="font-size: 14px; font-weight: 700; color: var(--text-primary);">Search Performance</div>
                  <span class="pm-subtext">Official Google REST API</span>
                </div>
                <div class="preview-metric">
                  <span class="pm-label">Business Profile</span>
                  <div class="pm-value" style="font-size: 14px; font-weight: 700; color: var(--text-primary);">Locations & Accounts</div>
                  <span class="pm-subtext">Google Workspace Integration</span>
                </div>
              </div>

              <div class="preview-status-bars">
                <div class="ps-bar-item">
                  <div class="ps-label"><span>Technical SEO Audits</span><span>On-Demand Crawling</span></div>
                  <div class="ps-track"><div class="ps-fill" style="width: 100%; background: var(--primary);"></div></div>
                </div>
                <div class="ps-bar-item">
                  <div class="ps-label"><span>Multi-Project Security</span><span>Lead & Team Access</span></div>
                  <div class="ps-track"><div class="ps-fill" style="width: 100%; background: var(--accent-purple);"></div></div>
                </div>
              </div>
            </div>

            <div class="branding-footer">
              Enterprise SEO Analytics Suite • Google Workspace Connected
            </div>
          </div>

          <!-- RIGHT COLUMN: LOGIN CARD -->
          <div class="login-card-col">
            <div class="login-card">
              
              <div class="card-title-group">
                <h2 class="card-headline">Welcome to SEO Intelligence</h2>
                <p class="card-subheadline">Sign in with your Google account to continue.</p>
              </div>

              <div id="login-error-box" style="display: none;" class="login-error-banner"></div>

              <!-- CONTINUE WITH GOOGLE PRIMARY CTA BUTTON -->
              <button id="btn-google-login" class="btn-google-oauth">
                <svg class="google-logo" width="20" height="20" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                <span id="google-btn-text">Continue with Google</span>
              </button>

              <div class="login-divider">
                <span>OR</span>
              </div>

              <!-- CONTINUE AS GUEST SECONDARY CTA BUTTON -->
              <button id="btn-guest-login" class="btn-guest-oauth">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                <span id="guest-btn-text">Continue as Guest</span>
              </button>
              <div class="guest-caption">
                Guest access is temporary and intended for testing.
              </div>

              <div class="privacy-notice">
                By continuing, you agree to the Terms of Service and Privacy Policy.
              </div>

              <!-- GOOGLE DISCOVERY SCOPES SUMMARY -->
              <div class="scopes-info">
                <div class="scopes-title">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                  <span>Official Google OAuth 2.0 Identity & API Scopes</span>
                </div>
                <div class="scopes-list">
                  <div>• Google Search Console (Search Properties & Performance)</div>
                  <div>• Google Analytics (GA4 Streams & Reports)</div>
                  <div>• Google Business Profile (Accounts & Locations)</div>
                </div>
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
          background: var(--bg-workspace);
          position: fixed;
          top: 0; left: 0;
          z-index: 999;
          overflow-y: auto;
          padding: 24px;
        }
        .login-wrapper {
          width: 100%;
          max-width: 1060px;
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
          background: linear-gradient(135deg, var(--primary), var(--accent-purple));
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
          box-shadow: 0 4px 12px var(--primary-glow);
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
          color: var(--text-primary);
          letter-spacing: -0.03em;
        }
        .headline-gradient {
          background: linear-gradient(135deg, var(--primary), var(--accent-purple));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .subtitle {
          font-size: 14.5px;
          color: var(--text-secondary);
          line-height: 1.6;
          max-width: 480px;
        }
        .analytics-preview-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: 20px;
          box-shadow: var(--shadow-sm);
        }
        .preview-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }
        .preview-title {
          font-size: 12.5px;
          font-weight: 700;
          color: var(--text-primary);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .preview-tag {
          font-size: 10px;
          font-weight: 700;
          background: var(--primary-light);
          color: var(--primary);
          padding: 2px 8px;
          border-radius: 10px;
        }
        .preview-metrics-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }
        .preview-metric {
          background: var(--bg-subtle);
          padding: 12px;
          border-radius: 8px;
          border: 1px solid var(--border-subtle);
        }
        .pm-label {
          font-size: 11px;
          color: var(--text-secondary);
          display: block;
        }
        .pm-value {
          font-size: 18px;
          font-weight: 800;
          color: var(--text-primary);
          margin: 4px 0 2px;
        }
        .pm-subtext {
          font-size: 10.5px;
          color: var(--text-tertiary);
        }
        .preview-status-bars {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .ps-label {
          display: flex;
          justify-content: space-between;
          font-size: 11.5px;
          color: var(--text-secondary);
          margin-bottom: 4px;
        }
        .ps-track {
          height: 6px;
          background: var(--bg-subtle);
          border-radius: 3px;
          overflow: hidden;
        }
        .ps-fill {
          height: 100%;
          border-radius: 3px;
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
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 16px;
          padding: 36px 32px;
          box-shadow: var(--shadow-md);
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .card-title-group {
          text-align: center;
        }
        .card-headline {
          font-size: 22px;
          font-weight: 800;
          color: var(--text-primary);
          letter-spacing: -0.02em;
          margin-bottom: 6px;
        }
        .card-subheadline {
          font-size: 13.5px;
          color: var(--text-secondary);
        }
        .btn-google-oauth {
          width: 100%;
          padding: 13px 20px;
          border-radius: 10px;
          border: 1px solid var(--border-hover);
          background: var(--bg-card);
          color: var(--text-primary);
          font-size: 14.5px;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: var(--shadow-sm);
        }
        .btn-google-oauth:hover {
          background: var(--bg-subtle);
          border-color: var(--primary);
          box-shadow: 0 4px 14px var(--primary-glow);
          transform: translateY(-1px);
        }
        .login-divider {
          display: flex;
          align-items: center;
          text-align: center;
          color: var(--text-tertiary);
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.05em;
          margin: 2px 0;
        }
        .login-divider::before, .login-divider::after {
          content: '';
          flex: 1;
          border-bottom: 1px solid var(--border-subtle);
        }
        .login-divider span {
          padding: 0 10px;
        }
        .btn-guest-oauth {
          width: 100%;
          padding: 12px 20px;
          border-radius: 10px;
          border: 1px solid var(--border);
          background: var(--bg-subtle);
          color: var(--text-primary);
          font-size: 14px;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .btn-guest-oauth:hover {
          background: var(--bg-card);
          border-color: var(--primary);
          transform: translateY(-1px);
        }
        .guest-caption {
          font-size: 11.5px;
          color: var(--text-tertiary);
          text-align: center;
          margin-top: -6px;
        }
        .privacy-notice {
          font-size: 11.5px;
          color: var(--text-tertiary);
          text-align: center;
          line-height: 1.5;
        }
        .scopes-info {
          background: var(--bg-subtle);
          border-radius: 10px;
          padding: 14px 16px;
          border: 1px solid var(--border-subtle);
          font-size: 12px;
        }
        .scopes-title {
          font-weight: 700;
          color: var(--text-primary);
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 8px;
        }
        .scopes-list {
          color: var(--text-secondary);
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .login-error-banner {
          background: var(--critical-bg);
          border: 1px solid var(--critical-border);
          color: var(--critical);
          padding: 10px 14px;
          border-radius: 8px;
          font-size: 12.5px;
        }

        @media (max-width: 860px) {
          .login-grid {
            grid-template-columns: 1fr;
            gap: 24px;
          }
          .login-branding-col {
            padding-right: 0;
            text-align: center;
          }
          .subtitle {
            margin: 0 auto;
          }
          .analytics-preview-card {
            display: none;
          }
        }
      </style>
    `;

    this.initHandlers();
    return this.element;
  }

  async mounted() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    const token = urlParams.get('token');

    if (token) {
      console.log('[GOOGLE UI] OAuth session token received in Login view.');
      localStorage.setItem('seo_auth_token', token);
      window.location.href = '/';
      return;
    }

    // Handle OAuth Callback redirect from Google
    if (code) {
      console.log('[GOOGLE UI] Returned from OAuth callback. Verifying code...');
      const googleBtn = document.getElementById('btn-google-login');
      const btnText = document.getElementById('google-btn-text');
      const errorBox = document.getElementById('login-error-box');

      if (googleBtn) googleBtn.disabled = true;
      if (btnText) btnText.innerText = 'Verifying Google Identity...';

      try {
        await authStore.handleOAuthCallbackCode(code, state);
        console.log('[GOOGLE UI] Google identity verified. Navigating to property discovery.');
        window.location.href = '/discovery';
        return;
      } catch (err) {
        if (googleBtn) googleBtn.disabled = false;
        if (btnText) btnText.innerText = 'Continue with Google';
        if (errorBox) {
          errorBox.style.display = 'block';
          errorBox.innerText = err.message || 'Google OAuth verification failed.';
        }
      }
    }

    // Check existing valid session — if valid, skip login screen instantly
    const isValid = await authStore.checkSession();
    if (isValid) {
      console.log('[GOOGLE UI] Valid session exists. Navigating to dashboard. NOT starting OAuth again.');
      window.location.href = '/';
    }
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

      const googleBtn = document.getElementById('btn-google-login');
      const errorBox = document.getElementById('login-error-box');
      const btnText = document.getElementById('google-btn-text');

      if (googleBtn) {
        googleBtn.addEventListener('click', async () => {
          googleBtn.disabled = true;
          if (btnText) btnText.innerText = 'Redirecting to Google OAuth...';
          if (errorBox) errorBox.style.display = 'none';

          try {
            const authUrl = await authStore.getGoogleOAuthLoginUrl();
            // Redirect browser directly to Google's official OAuth consent screen
            window.location.href = authUrl;
          } catch (err) {
            googleBtn.disabled = false;
            if (btnText) btnText.innerText = 'Continue with Google';
            if (errorBox) {
              errorBox.style.display = 'block';
              errorBox.innerText = err.message || 'Unable to generate Google OAuth URL. Please check backend GOOGLE_CLIENT_ID configuration.';
            }
          }
        });
      }

      const guestBtn = document.getElementById('btn-guest-login');
      const guestBtnText = document.getElementById('guest-btn-text');

      if (guestBtn) {
        guestBtn.addEventListener('click', async () => {
          guestBtn.disabled = true;
          if (googleBtn) googleBtn.disabled = true;
          if (guestBtnText) guestBtnText.innerText = 'Creating Guest Session...';
          if (errorBox) errorBox.style.display = 'none';

          try {
            await authStore.createGuestSession();
            console.log('[GUEST UI] Guest session established cleanly. Navigating to dashboard.');
            window.location.href = '/';
          } catch (err) {
            guestBtn.disabled = false;
            if (googleBtn) googleBtn.disabled = false;
            if (guestBtnText) guestBtnText.innerText = 'Continue as Guest';
            if (errorBox) {
              errorBox.style.display = 'block';
              errorBox.innerText = err.message || 'Unable to create guest session.';
            }
          }
        });
      }
    }, 50);
  }
}
