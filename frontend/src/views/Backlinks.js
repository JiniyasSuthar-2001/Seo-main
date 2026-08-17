export class Backlinks {
    render() {
        const element = document.createElement('div');
        element.className = 'backlinks-view';
        element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Backlink Profile</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Track referring domains, external inbound links, anchor text distribution, and link status.</p>
            </div>

            <div class="empty-state">
                <div class="empty-state-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
                </div>
                <div class="empty-state-title">No Backlink Dataset Imported</div>
                <div class="empty-state-desc">Import backlink audit data to inspect referring URL profiles, dofollow/nofollow ratios, and target page backlink counts.</div>
                <a href="/import" data-link class="btn btn-primary">Import Backlinks CSV</a>
            </div>
        `;
        return element;
    }
}
