export class Reports {
    render() {
        const element = document.createElement('div');
        element.className = 'reports-view';
        element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">SEO Reports & Exports</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Generate executive PDF and CSV summaries from your historical crawl snapshots.</p>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; max-width: 900px; margin-bottom: 32px;">
                <div class="card" style="padding: 24px;">
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Executive Summary PDF</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 16px;">Comprehensive SEO audit report containing top risks, opportunities, and page metrics.</p>
                    <button class="btn btn-primary" style="width: 100%;">Generate Executive PDF</button>
                </div>

                <div class="card" style="padding: 24px;">
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Technical Audit CSV</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 16px;">Export raw evidence-backed technical issues, affected URLs, and severity ratings.</p>
                    <button class="btn btn-secondary" style="width: 100%;">Export Issues CSV</button>
                </div>

                <div class="card" style="padding: 24px;">
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Internal Link Graph CSV</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 16px;">Export source-target URL mapping and anchor text for link architecture auditing.</p>
                    <button class="btn btn-secondary" style="width: 100%;">Export Link Graph CSV</button>
                </div>
            </div>

            <div class="card" style="padding: 0; overflow: hidden; max-width: 900px;">
                <div style="padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); font-weight: 600; font-size: 14px;">
                    Recent Generated Reports
                </div>
                <div style="padding: 32px; text-align: center; color: var(--text-secondary); font-size: 14px;">
                    No report exports generated yet. Click above to generate your first audit report.
                </div>
            </div>
        `;
        return element;
    }
}
