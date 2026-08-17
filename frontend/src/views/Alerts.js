export class Alerts {
    render() {
        const element = document.createElement('div');
        element.className = 'alerts-view';
        element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">SEO Alerts & Feed</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Real-time feed of critical technical issues, crawl failures, and threshold alerts.</p>
            </div>

            <div style="max-width: 900px; display: flex; flex-direction: column; gap: 16px;">
                <div class="card" style="padding: 24px; text-align: center;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; background: var(--success-bg); color: var(--success); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 12px;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    </div>
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">All Systems Normal</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; max-width: 400px; margin: 0 auto;">No unhandled critical alerts detected in your active workspace.</p>
                </div>
            </div>
        `;
        return element;
    }
}
