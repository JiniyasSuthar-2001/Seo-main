export class Keywords {
    render() {
        const element = document.createElement('div');
        element.className = 'keywords-view';
        element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Keyword Intelligence</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Track target keywords, search volume, CPC, and keyword-to-page relevance.</p>
            </div>

            <div class="empty-state">
                <div class="empty-state-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                </div>
                <div class="empty-state-title">No Keyword Dataset Imported</div>
                <div class="empty-state-desc">Import your keyword CSV dataset to start analyzing search volume, search intent, target URL mappings, and topic cannibalization.</div>
                <a href="/import" data-link class="btn btn-primary">Import Keywords CSV</a>
            </div>
        `;
        return element;
    }
}
