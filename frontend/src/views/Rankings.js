export class Rankings {
    render() {
        const element = document.createElement('div');
        element.className = 'rankings-view';
        element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Ranking Tracker</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Monitor keyword position distribution, SERP movements, and historical ranking trends.</p>
            </div>

            <div class="empty-state">
                <div class="empty-state-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                </div>
                <div class="empty-state-title">No Ranking Data Available</div>
                <div class="empty-state-desc">Import position tracking data to monitor SERP position improvements, declines, top gains, and target URL rankings.</div>
                <a href="/import" data-link class="btn btn-primary">Import Rankings CSV</a>
            </div>
        `;
        return element;
    }
}
