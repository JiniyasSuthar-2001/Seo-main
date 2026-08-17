export class Competitors {
    render() {
        const element = document.createElement('div');
        element.className = 'competitors-view';
        element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Competitor Analysis</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Compare keyword overlap, search visibility, and domain metrics against market competitors.</p>
            </div>

            <div class="empty-state">
                <div class="empty-state-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                </div>
                <div class="empty-state-title">No Competitors Configured</div>
                <div class="empty-state-desc">Add competitor website domains to benchmark SEO metrics, keyword gap analysis, and content coverage.</div>
                <a href="/import" data-link class="btn btn-primary">Add Competitor Data</a>
            </div>
        `;
        return element;
    }
}
