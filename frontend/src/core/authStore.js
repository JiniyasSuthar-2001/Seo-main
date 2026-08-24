import { API_BASE_URL } from '../config/api.js';

class AuthStore {
  constructor() {
    this.TOKEN_KEY = 'seo_auth_token';
    this.USER_KEY = 'seo_user';
    this.extractTokenFromUrl();
    this.user = this.getStoredUser();
    this.token = localStorage.getItem(this.TOKEN_KEY) || null;
    this.isAuthenticated = !!this.token;
    this.isCheckingSession = false;
    this.discoveredProperties = [];
    this.listeners = [];
  }

  extractTokenFromUrl() {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const tokenFromUrl = urlParams.get('token');
      if (tokenFromUrl && tokenFromUrl.trim()) {
        localStorage.setItem(this.TOKEN_KEY, tokenFromUrl.trim());
        urlParams.delete('token');
        const newSearch = urlParams.toString();
        const newUrl = window.location.pathname + (newSearch ? `?${newSearch}` : '');
        window.history.replaceState({}, document.title, newUrl);
      }
    } catch (e) {}
  }

  getStoredUser() {
    try {
      const saved = localStorage.getItem(this.USER_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  }

  async checkSession() {
    this.isCheckingSession = true;
    const token = localStorage.getItem(this.TOKEN_KEY);
    
    if (!token) {
      this.isAuthenticated = false;
      this.user = null;
      this.isCheckingSession = false;
      return false;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (res.ok) {
        const data = await res.json();
        this.token = token;
        this.user = {
          id: data.user_id,
          email: data.email,
          masked_email: data.masked_email,
          name: data.name,
          picture: data.picture,
          auth_provider: 'google'
        };
        this.isAuthenticated = true;
        localStorage.setItem(this.USER_KEY, JSON.stringify(this.user));
        this.isCheckingSession = false;
        this.notify();
        return true;
      } else {
        this.logoutSilently();
        this.isCheckingSession = false;
        return false;
      }
    } catch (err) {
      console.warn('[AUTH STORE] Session check fallback:', err);
      this.isAuthenticated = !!this.token;
      this.isCheckingSession = false;
      return this.isAuthenticated;
    }
  }

  async getGoogleOAuthLoginUrl() {
    const res = await fetch(`${API_BASE_URL}/api/auth/google/login-url`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to generate Google OAuth login URL.');
    }
    const data = await res.json();
    return data.auth_url;
  }

  async handleOAuthCallbackCode(code, state) {
    const res = await fetch(`${API_BASE_URL}/api/auth/google/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state || '')}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Google OAuth token verification failed.');
    }

    const data = await res.json();
    this.token = data.access_token;
    this.user = data.user;
    this.isAuthenticated = true;

    localStorage.setItem(this.TOKEN_KEY, this.token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(this.user));

    this.notify();
    return data;
  }

  async discoverGoogleProperties() {
    const token = this.token || localStorage.getItem(this.TOKEN_KEY);
    if (!token) return [];
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/discover-google-properties`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (!res.ok) throw new Error('Failed to discover Google properties.');
      const data = await res.json();
      this.discoveredProperties = data.properties || [];
      return this.discoveredProperties;
    } catch (err) {
      console.error('[AUTH STORE] Discovery error:', err);
      return [];
    }
  }

  async registerDiscoveredProjects(properties) {
    const token = this.token || localStorage.getItem(this.TOKEN_KEY);
    if (!token) return null;
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register-discovered-projects`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ properties })
      });

      if (!res.ok) throw new Error('Failed to register Google properties as workspace projects.');
      const data = await res.json();
      return data;
    } catch (err) {
      console.error('[AUTH STORE] Project registration error:', err);
      throw err;
    }
  }

  async acceptInvitation(invitationId) {
    const token = this.token || localStorage.getItem(this.TOKEN_KEY);
    if (!token) throw new Error('Authentication required to accept invitation.');

    const res = await fetch(`${API_BASE_URL}/api/auth/accept-invitation/${invitationId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Failed to accept invitation.');
    }

    return await res.json();
  }

  logoutSilently() {
    this.token = null;
    this.user = null;
    this.isAuthenticated = false;
    this.discoveredProperties = [];
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.notify();
  }

  async logout() {
    try {
      const token = this.token || localStorage.getItem(this.TOKEN_KEY);
      if (token) {
        await fetch(`${API_BASE_URL}/api/auth/logout`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        }).catch(() => {});
      }
    } finally {
      this.logoutSilently();
      window.location.href = '/login';
    }
  }

  subscribe(callback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback);
    };
  }

  notify() {
    this.listeners.forEach(cb => cb({ user: this.user, isAuthenticated: this.isAuthenticated }));
  }
}

export const authStore = new AuthStore();
