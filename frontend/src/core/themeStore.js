// Theme Store - Manages Dark / Light mode state with localStorage persistence

class ThemeStore {
  constructor() {
    this.STORAGE_KEY = 'seo_theme_mode';
    this.theme = this.getInitialTheme();
    this.listeners = [];
  }

  getInitialTheme() {
    const saved = localStorage.getItem(this.STORAGE_KEY);
    if (saved === 'dark' || saved === 'light') {
      return saved;
    }
    // Default to Dark Mode as specified in prompt requirement
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    return 'dark';
  }

  init() {
    this.applyTheme(this.theme);
    // Listen for system theme changes if user hasn't explicitly set a preference
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem(this.STORAGE_KEY)) {
        this.setTheme(e.matches ? 'dark' : 'light');
      }
    });
  }

  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    if (document.body) {
      document.body.setAttribute('data-theme', theme);
    }
  }

  setTheme(theme) {
    if (theme !== 'dark' && theme !== 'light') return;
    this.theme = theme;
    localStorage.setItem(this.STORAGE_KEY, theme);
    this.applyTheme(theme);
    this.notify();
  }

  toggleTheme() {
    const nextTheme = this.theme === 'dark' ? 'light' : 'dark';
    this.setTheme(nextTheme);
    return nextTheme;
  }

  getTheme() {
    return this.theme;
  }

  isDark() {
    return this.theme === 'dark';
  }

  subscribe(callback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback);
    };
  }

  notify() {
    this.listeners.forEach(cb => cb(this.theme));
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: this.theme } }));
  }
}

export const themeStore = new ThemeStore();
themeStore.init();
