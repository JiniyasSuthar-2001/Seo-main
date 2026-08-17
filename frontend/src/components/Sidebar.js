export const Sidebar = {
  render() {
    return `
      <aside id="sidebar" class="sidebar">
        <div class="sidebar-header">
          <div class="brand-name">SEO Intelligence</div>
        </div>
        <nav class="sidebar-nav">
          <a href="#" class="nav-link" data-route="/dashboard">Dashboard</a>
          <a href="#" class="nav-link" data-route="/search/keywords">Keywords</a>
        </nav>
      </aside>
    `;
  },
  bindEvents() {}
};
