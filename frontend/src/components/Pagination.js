/**
 * Shared Global Pagination Component & Helper Utility
 * Enforces standard 20 rows per page limit across the entire platform.
 */

export class Pagination {
    constructor(options = {}) {
        this.totalItems = options.totalItems || 0;
        this.currentPage = options.currentPage || 1;
        this.pageSize = options.pageSize || 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
        this.onPageChange = options.onPageChange || (() => {});
    }

    static paginateArray(items = [], currentPage = 1, pageSize = 20) {
        const totalItems = items.length;
        const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
        const page = Math.min(Math.max(1, currentPage), totalPages);

        const startIndex = totalItems === 0 ? 0 : (page - 1) * pageSize;
        const endIndex = Math.min(startIndex + pageSize, totalItems);
        const paginatedItems = items.slice(startIndex, endIndex);

        return {
            items: paginatedItems,
            totalItems,
            totalPages,
            currentPage: page,
            startIndex: totalItems === 0 ? 0 : startIndex + 1,
            endIndex,
            pageSize
        };
    }

    render() {
        const totalPages = Math.max(1, Math.ceil(this.totalItems / this.pageSize));
        const page = Math.min(Math.max(1, this.currentPage), totalPages);
        const startIndex = this.totalItems === 0 ? 0 : (page - 1) * this.pageSize + 1;
        const endIndex = Math.min(page * this.pageSize, this.totalItems);

        const container = document.createElement('div');
        container.className = 'pagination-bar';
        container.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: var(--bg-card);
            border-top: 1px solid var(--border);
            font-size: 12.5px;
            color: var(--text-secondary);
            flex-wrap: wrap;
            gap: 12px;
        `;

        if (this.totalItems === 0) {
            container.innerHTML = `
                <div>Showing 0 of 0</div>
                <div style="display: flex; gap: 4px;">
                    <button class="btn btn-secondary btn-sm" disabled style="padding: 4px 10px; font-size: 12px;">‹ Previous</button>
                    <button class="btn btn-secondary btn-sm" disabled style="padding: 4px 10px; font-size: 12px;">Next ›</button>
                </div>
            `;
            return container;
        }

        // Generate Page Numbers Array with Ellipsis
        const pages = this.calculatePageNumbers(page, totalPages);

        const pagesButtonsHtml = pages.map(p => {
            if (p === '...') {
                return `<span style="padding: 4px 8px; color: var(--text-tertiary); font-weight: 600;">…</span>`;
            }
            const isCurrent = p === page;
            return `
                <button class="btn ${isCurrent ? 'btn-primary' : 'btn-secondary'} btn-sm btn-page-num" 
                        data-page="${p}" 
                        style="padding: 4px 10px; font-size: 12px; min-width: 28px; text-align: center; ${isCurrent ? 'font-weight: 700;' : ''}">
                    ${p}
                </button>
            `;
        }).join('');

        container.innerHTML = `
            <div style="font-weight: 600; color: var(--text-secondary);">
                Showing <strong style="color: var(--text-primary);">${startIndex}–${endIndex}</strong> of <strong style="color: var(--text-primary);">${this.totalItems}</strong>
            </div>
            <div style="display: flex; gap: 4px; align-items: center;">
                <button class="btn btn-secondary btn-sm btn-page-prev" 
                        ${page <= 1 ? 'disabled' : ''} 
                        style="padding: 4px 10px; font-size: 12px;">
                    ‹ Previous
                </button>
                <div style="display: flex; gap: 4px; align-items: center;">
                    ${pagesButtonsHtml}
                </div>
                <button class="btn btn-secondary btn-sm btn-page-next" 
                        ${page >= totalPages ? 'disabled' : ''} 
                        style="padding: 4px 10px; font-size: 12px;">
                    Next ›
                </button>
            </div>
        `;

        // Attach event listeners
        container.querySelector('.btn-page-prev')?.addEventListener('click', () => {
            if (page > 1) this.onPageChange(page - 1);
        });

        container.querySelector('.btn-page-next')?.addEventListener('click', () => {
            if (page < totalPages) this.onPageChange(page + 1);
        });

        container.querySelectorAll('.btn-page-num').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetPage = parseInt(e.currentTarget.getAttribute('data-page'), 10);
                if (targetPage && targetPage !== page) {
                    this.onPageChange(targetPage);
                }
            });
        });

        return container;
    }

    calculatePageNumbers(current, total) {
        if (total <= 7) {
            return Array.from({ length: total }, (_, i) => i + 1);
        }

        if (current <= 4) {
            return [1, 2, 3, 4, 5, '...', total];
        }

        if (current >= total - 3) {
            return [1, '...', total - 4, total - 3, total - 2, total - 1, total];
        }

        return [1, '...', current - 1, current, current + 1, '...', total];
    }
}
