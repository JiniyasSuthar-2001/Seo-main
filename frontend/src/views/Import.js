export class Import {
    render() {
        const element = document.createElement('div');
        element.className = 'import-view';
        element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Data Import Workspace</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Upload external CSV datasets to populate keywords, rankings, backlinks, and competitor analytics.</p>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; max-width: 960px;">
                <div class="card" style="padding: 24px;">
                    <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    </div>
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">Keywords CSV</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 20px; line-height: 1.5;">Import target keyword lists, search volume, CPC, and target URL mappings.</p>
                    <button class="btn btn-secondary" style="width: 100%;">Upload Keywords CSV</button>
                </div>

                <div class="card" style="padding: 24px;">
                    <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                    </div>
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">Rankings CSV</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 20px; line-height: 1.5;">Import position tracking records, SERP history, and rank movements.</p>
                    <button class="btn btn-secondary" style="width: 100%;">Upload Rankings CSV</button>
                </div>

                <div class="card" style="padding: 24px;">
                    <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
                    </div>
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">Backlinks CSV</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 20px; line-height: 1.5;">Import referring domains, external target URLs, and anchor text profiles.</p>
                    <button class="btn btn-secondary" style="width: 100%;">Upload Backlinks CSV</button>
                </div>
            </div>
        `;
        return element;
    }
}
