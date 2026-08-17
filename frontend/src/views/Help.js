export class Help {
    render() {
        const element = document.createElement('div');
        element.className = 'help-view';
        element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Documentation & Help Center</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Learn how to analyze websites, manage local crawl storage, and optimize your SEO platform.</p>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; max-width: 900px;">
                <div class="card" style="padding: 24px;">
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">1. Running Real Crawls</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.5;">Click "Run Crawl" or "Analyze Website" on the Dashboard. The backend connects over the public Internet to fetch HTML, parse metadata, and map internal links.</p>
                </div>

                <div class="card" style="padding: 24px;">
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">2. Local Snapshot Storage</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.5;">All crawls are stored locally as immutable JSON snapshots inside <code>data/websites/[domain]/crawls/</code>. Old crawls are never overwritten.</p>
                </div>

                <div class="card" style="padding: 24px;">
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">3. AI SEO Analyst</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.5;">The LLM engine reasons over stored evidence to produce structured findings and answer questions directly from your website audit data.</p>
                </div>
            </div>
        `;
        return element;
    }
}
