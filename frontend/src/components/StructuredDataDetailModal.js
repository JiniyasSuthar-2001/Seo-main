/**
 * Structured Data Detail Modal Component
 * Displays real Schema.org JSON-LD structured data evidence captured during website crawl.
 * Supports schema type filtering, URL search, 20 items per page pagination, and raw JSON-LD inspection.
 * Zero fabricated data.
 */
import { Pagination } from './Pagination.js';

function escapeHtml(str) {
    if (!str && str !== 0) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

export class StructuredDataDetailModal {
    static open({ structuredDataSummary, domain, crawlTimestamp }) {
        const existing = document.getElementById('structured-data-detail-modal-root');
        if (existing) existing.remove();

        const summary = structuredDataSummary || {
            evaluated: false,
            total_pages_checked: 0,
            total_pages_with_schema: 0,
            total_pages_missing_schema: 0,
            total_schemas_detected: 0,
            unique_schema_types_count: 0,
            schema_types_found: {},
            pages_detail: []
        };

        const allPages = Array.isArray(summary.pages_detail) ? summary.pages_detail : [];
        const schemaTypesMap = summary.schema_types_found || {};
        const schemaTypeEntries = Object.entries(schemaTypesMap);

        let activeTab = 'all'; // 'all' | 'with_schema' | 'missing_schema'
        let activeTypeFilter = null; // null or specific schema type string
        let searchQuery = '';
        let currentPage = 1;
        const pageSize = 20;
        let expandedJsonUrls = new Set();

        const modalRoot = document.createElement('div');
        modalRoot.id = 'structured-data-detail-modal-root';
        modalRoot.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(6px); display: flex; align-items: center;
            justify-content: center; z-index: 9999; padding: 20px;
        `;

        const renderModalContent = () => {
            // Apply Filters: Tab, Type Filter, Search Query
            let filteredPages = allPages.filter(p => {
                // Tab filter
                if (activeTab === 'with_schema' && !p.has_structured_data) return false;
                if (activeTab === 'missing_schema' && p.has_structured_data) return false;

                // Schema Type chip filter
                if (activeTypeFilter) {
                    const pageTypes = (p.detected_schema_types || []).map(t => String(t).toLowerCase());
                    if (!pageTypes.includes(activeTypeFilter.toLowerCase())) return false;
                }

                // Search query filter (matches URL or schema type)
                if (searchQuery) {
                    const q = searchQuery.toLowerCase();
                    const urlMatch = (p.url || '').toLowerCase().includes(q);
                    const typeMatch = (p.detected_schema_types || []).some(t => String(t).toLowerCase().includes(q));
                    if (!urlMatch && !typeMatch) return false;
                }

                return true;
            });

            const paginated = Pagination.paginateArray(filteredPages, currentPage, pageSize);
            currentPage = paginated.currentPage;

            modalRoot.innerHTML = `
                <div class="card" style="width: 100%; max-width: 1080px; max-height: 92vh; display: flex; flex-direction: column; background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.4); overflow: hidden;">
                    
                    <!-- MODAL HEADER -->
                    <div style="padding: 18px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap;">
                                <span style="font-size: 11px; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.5px;">STRUCTURED DATA & SCHEMA.ORG AUDIT</span>
                                <span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 10.5px;">
                                    Data Source: Real Crawl &lt;script type="application/ld+json"&gt;
                                </span>
                            </div>
                            <h2 style="font-size: 19px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">
                                Structured Data Breakdown — ${escapeHtml(domain || 'Target Site')}
                            </h2>
                            <div style="font-size: 12.5px; color: var(--text-secondary);">
                                Evaluated on ${escapeHtml(crawlTimestamp || 'Latest Completed Crawl')} • ${allPages.length} scanned pages analyzed
                            </div>
                        </div>
                        <button id="btn-close-sd-modal" style="background: none; border: none; font-size: 26px; line-height: 1; color: var(--text-tertiary); cursor: pointer; padding: 4px;" title="Close">&times;</button>
                    </div>

                    <!-- SCROLLABLE BODY -->
                    <div style="flex: 1; overflow-y: auto; display: flex; flex-direction: column;">
                        
                        <!-- SUMMARY STATS BAR -->
                        <div style="padding: 16px 24px; background: rgba(59, 130, 246, 0.03); border-bottom: 1px solid var(--border); display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px;">
                            <div style="background: var(--bg-card); padding: 12px 16px; border-radius: 10px; border: 1px solid var(--border);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Pages Checked</div>
                                <div style="font-size: 22px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${summary.total_pages_checked || allPages.length}</div>
                                <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 1px;">HTML 200 Pages</div>
                            </div>
                            <div style="background: var(--bg-card); padding: 12px 16px; border-radius: 10px; border: 1px solid var(--border); border-left: 3px solid var(--success);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--success); text-transform: uppercase;">With Structured Data</div>
                                <div style="font-size: 22px; font-weight: 800; color: var(--success); margin-top: 2px;">${summary.total_pages_with_schema || 0}</div>
                                <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 1px;">✓ Schema Detected</div>
                            </div>
                            <div style="background: var(--bg-card); padding: 12px 16px; border-radius: 10px; border: 1px solid var(--border); border-left: 3px solid ${summary.total_pages_missing_schema > 0 ? 'var(--warning)' : 'var(--border)'};">
                                <div style="font-size: 11px; font-weight: 700; color: ${summary.total_pages_missing_schema > 0 ? 'var(--warning)' : 'var(--text-secondary)'}; text-transform: uppercase;">Missing Structured Data</div>
                                <div style="font-size: 22px; font-weight: 800; color: ${summary.total_pages_missing_schema > 0 ? 'var(--warning)' : 'var(--text-primary)'}; margin-top: 2px;">${summary.total_pages_missing_schema || 0}</div>
                                <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 1px;">${summary.total_pages_missing_schema > 0 ? '⚠ Rich snippet ineligible' : 'All pages have schema'}</div>
                            </div>
                            <div style="background: var(--bg-card); padding: 12px 16px; border-radius: 10px; border: 1px solid var(--border);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase;">Schema Types Detected</div>
                                <div style="font-size: 22px; font-weight: 800; color: var(--primary); margin-top: 2px;">${summary.unique_schema_types_count || schemaTypeEntries.length}</div>
                                <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 1px;">${summary.total_schemas_detected || 0} total schema instances</div>
                            </div>
                        </div>

                        <!-- SCHEMA TYPES CHIPS ROW -->
                        ${schemaTypeEntries.length > 0 ? `
                            <div style="padding: 14px 24px; border-bottom: 1px solid var(--border); background: var(--bg-card);">
                                <div style="font-size: 11.5px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                                    <span>Detected Schema Types (Click to filter pages):</span>
                                    ${activeTypeFilter ? `
                                        <button id="btn-clear-type-filter" style="background: none; border: none; color: var(--primary); font-size: 11px; font-weight: 600; cursor: pointer;">
                                            Clear Type Filter (${escapeHtml(activeTypeFilter)}) ✕
                                        </button>
                                    ` : ''}
                                </div>
                                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                                    ${schemaTypeEntries.map(([type, count]) => {
                                        const isActive = activeTypeFilter && activeTypeFilter.toLowerCase() === type.toLowerCase();
                                        return `
                                            <button class="btn-schema-chip" data-type="${escapeHtml(type)}" 
                                                    style="display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid ${isActive ? 'var(--primary)' : 'var(--border)'}; background: ${isActive ? 'rgba(37, 99, 235, 0.12)' : 'var(--bg-subtle)'}; color: ${isActive ? 'var(--primary)' : 'var(--text-primary)'}; transition: all 0.15s ease;">
                                                <span>🏷️ ${escapeHtml(type)}</span>
                                                <span style="background: ${isActive ? 'var(--primary)' : 'var(--border)'}; color: ${isActive ? '#fff' : 'var(--text-secondary)'}; padding: 1px 7px; border-radius: 10px; font-size: 10.5px; font-weight: 700;">
                                                    ${count} page${count === 1 ? '' : 's'}
                                                </span>
                                            </button>
                                        `;
                                    }).join('')}
                                </div>
                            </div>
                        ` : ''}

                        <!-- CONTROLS ROW: TABS & SEARCH -->
                        <div style="padding: 12px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                            
                            <!-- TAB SWITCHER -->
                            <div style="display: flex; gap: 4px; background: var(--bg-card); padding: 3px; border-radius: 8px; border: 1px solid var(--border);">
                                <button class="btn-sd-tab ${activeTab === 'all' ? 'active' : ''}" data-tab="all" 
                                        style="padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; border: none; background: ${activeTab === 'all' ? 'var(--primary)' : 'transparent'}; color: ${activeTab === 'all' ? '#fff' : 'var(--text-secondary)'}; cursor: pointer;">
                                    All Pages (${allPages.length})
                                </button>
                                <button class="btn-sd-tab ${activeTab === 'with_schema' ? 'active' : ''}" data-tab="with_schema" 
                                        style="padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; border: none; background: ${activeTab === 'with_schema' ? 'var(--success)' : 'transparent'}; color: ${activeTab === 'with_schema' ? '#fff' : 'var(--text-secondary)'}; cursor: pointer;">
                                    ✓ Has Schema (${summary.total_pages_with_schema || 0})
                                </button>
                                <button class="btn-sd-tab ${activeTab === 'missing_schema' ? 'active' : ''}" data-tab="missing_schema" 
                                        style="padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; border: none; background: ${activeTab === 'missing_schema' ? 'var(--warning)' : 'transparent'}; color: ${activeTab === 'missing_schema' ? '#fff' : 'var(--text-secondary)'}; cursor: pointer;">
                                    ⚠ Missing Schema (${summary.total_pages_missing_schema || 0})
                                </button>
                            </div>

                            <!-- SEARCH INPUT -->
                            <div style="position: relative; min-width: 240px; flex: 1; max-width: 360px;">
                                <input type="text" id="sd-search-input" value="${escapeHtml(searchQuery)}" placeholder="Search URL or schema type..." 
                                       style="width: 100%; padding: 6px 12px 6px 30px; font-size: 12.5px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); outline: none;" />
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary);">
                                    <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                                </svg>
                            </div>
                        </div>

                        <!-- EVIDENCE TABLE -->
                        <div style="flex: 1; overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 10px 16px; width: 38%;">Page URL</th>
                                        <th style="padding: 10px 16px; width: 18%;">Structured Data Status</th>
                                        <th style="padding: 10px 16px; width: 12%;">Count</th>
                                        <th style="padding: 10px 16px; width: 22%;">Detected Schema Types</th>
                                        <th style="padding: 10px 16px; width: 10%; text-align: right;">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${paginated.items.length > 0 ? paginated.items.map((p) => {
                                        const isExpanded = expandedJsonUrls.has(p.url);
                                        const typesList = p.detected_schema_types || [];
                                        const rawJsonStr = p.raw_json_ld && p.raw_json_ld.length > 0 
                                            ? JSON.stringify(p.raw_json_ld.length === 1 ? p.raw_json_ld[0] : p.raw_json_ld, null, 2)
                                            : null;

                                        return `
                                            <tr style="border-bottom: 1px solid var(--border);">
                                                <td style="padding: 12px 16px; vertical-align: top;">
                                                    <a href="${escapeHtml(p.url)}" target="_blank" rel="noopener noreferrer" 
                                                       style="color: var(--primary); text-decoration: none; font-weight: 600; word-break: break-all; display: inline-flex; align-items: center; gap: 4px;">
                                                        <span>${escapeHtml(p.url)}</span>
                                                        <span style="font-size: 10px; color: var(--text-tertiary);">↗</span>
                                                    </a>
                                                </td>
                                                <td style="padding: 12px 16px; vertical-align: top;">
                                                    ${p.has_structured_data ? `
                                                        <span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 11px; font-weight: 700;">
                                                            ✓ Detected
                                                        </span>
                                                    ` : `
                                                        <span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); font-size: 11px; font-weight: 700;">
                                                            ⚠ Missing Schema
                                                        </span>
                                                    `}
                                                </td>
                                                <td style="padding: 12px 16px; vertical-align: top; font-weight: 700; color: var(--text-primary);">
                                                    ${p.schema_count || 0} ${p.schema_count === 1 ? 'type' : 'types'}
                                                </td>
                                                <td style="padding: 12px 16px; vertical-align: top;">
                                                    ${typesList.length > 0 ? `
                                                        <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                                                            ${typesList.map(t => `
                                                                <span class="badge badge-info" style="font-size: 11px; font-weight: 600; background: rgba(59, 130, 246, 0.1); color: #2563eb; border: 1px solid rgba(59, 130, 246, 0.25);">
                                                                    ${escapeHtml(t)}
                                                                </span>
                                                            `).join('')}
                                                        </div>
                                                    ` : `
                                                        <span style="font-size: 12px; color: var(--text-tertiary); font-style: italic;">None detected</span>
                                                    `}
                                                </td>
                                                <td style="padding: 12px 16px; vertical-align: top; text-align: right;">
                                                    ${rawJsonStr ? `
                                                        <button class="btn btn-secondary btn-sm btn-toggle-json" data-url="${escapeHtml(p.url)}" 
                                                                style="font-size: 11px; font-weight: 600; padding: 3px 8px; white-space: nowrap;">
                                                            ${isExpanded ? 'Hide JSON' : 'View JSON-LD'}
                                                        </button>
                                                    ` : `
                                                        <span style="font-size: 11px; color: var(--text-tertiary);">-</span>
                                                    `}
                                                </td>
                                            </tr>
                                            ${isExpanded && rawJsonStr ? `
                                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border);">
                                                    <td colspan="5" style="padding: 14px 18px;">
                                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                                            <span style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">
                                                                Captured &lt;script type="application/ld+json"&gt; Content
                                                            </span>
                                                            <button class="btn btn-secondary btn-sm btn-copy-json" data-json="${escapeHtml(rawJsonStr)}" 
                                                                    style="font-size: 10.5px; padding: 2px 8px;">
                                                                📋 Copy JSON-LD
                                                            </button>
                                                        </div>
                                                        <pre style="margin: 0; padding: 12px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; font-family: 'SFMono-Regular', Consolas, Menlo, monospace; font-size: 11.5px; line-height: 1.45; color: var(--text-primary); max-height: 240px; overflow-y: auto; white-space: pre-wrap; word-break: break-all;"><code>${escapeHtml(rawJsonStr)}</code></pre>
                                                    </td>
                                                </tr>
                                            ` : ''}
                                        `;
                                    }).join('') : `
                                        <tr>
                                            <td colspan="5" style="padding: 36px; text-align: center; color: var(--text-secondary);">
                                                ${allPages.length === 0 ? 'No website crawl data available for Structured Data analysis.' : 'No pages match the selected filters.'}
                                            </td>
                                        </tr>
                                    `}
                                </tbody>
                            </table>
                        </div>

                        <!-- PAGINATION FOOTER -->
                        <div id="sd-modal-pagination-slot" style="padding: 12px 24px; border-top: 1px solid var(--border); background: var(--bg-card); display: flex; justify-content: space-between; align-items: center;">
                            <div style="font-size: 12px; color: var(--text-secondary);">
                                Showing <strong>${paginated.items.length > 0 ? (paginated.currentPage - 1) * pageSize + 1 : 0}</strong> - <strong>${Math.min(paginated.currentPage * pageSize, filteredPages.length)}</strong> of <strong>${filteredPages.length}</strong> pages
                            </div>
                            <div id="sd-pagination-controls"></div>
                        </div>

                    </div>
                </div>
            `;

            // Append Pagination Controls
            const paginationSlot = modalRoot.querySelector('#sd-pagination-controls');
            if (paginationSlot && filteredPages.length > pageSize) {
                const pag = new Pagination({
                    totalItems: filteredPages.length,
                    currentPage: paginated.currentPage,
                    pageSize: pageSize,
                    onPageChange: (newPage) => {
                        currentPage = newPage;
                        renderModalContent();
                    }
                });
                paginationSlot.appendChild(pag.render());
            }

            // Bind Event Listeners
            modalRoot.querySelector('#btn-close-sd-modal')?.addEventListener('click', () => {
                modalRoot.remove();
            });

            // Close modal on background backdrop click
            modalRoot.addEventListener('click', (e) => {
                if (e.target === modalRoot) modalRoot.remove();
            });

            // Tab switcher
            modalRoot.querySelectorAll('.btn-sd-tab').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    activeTab = e.currentTarget.getAttribute('data-tab');
                    currentPage = 1;
                    renderModalContent();
                });
            });

            // Schema Type chip buttons
            modalRoot.querySelectorAll('.btn-schema-chip').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const type = e.currentTarget.getAttribute('data-type');
                    if (activeTypeFilter && activeTypeFilter.toLowerCase() === type.toLowerCase()) {
                        activeTypeFilter = null;
                    } else {
                        activeTypeFilter = type;
                    }
                    currentPage = 1;
                    renderModalContent();
                });
            });

            // Clear Type Filter button
            modalRoot.querySelector('#btn-clear-type-filter')?.addEventListener('click', () => {
                activeTypeFilter = null;
                currentPage = 1;
                renderModalContent();
            });

            // Search input
            const searchInput = modalRoot.querySelector('#sd-search-input');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    searchQuery = e.target.value.trim();
                    currentPage = 1;
                    renderModalContent();
                    // Keep search input focused after re-render
                    setTimeout(() => {
                        const newInp = modalRoot.querySelector('#sd-search-input');
                        if (newInp) {
                            newInp.focus();
                            newInp.setSelectionRange(newInp.value.length, newInp.value.length);
                        }
                    }, 10);
                });
            }

            // View JSON toggle
            modalRoot.querySelectorAll('.btn-toggle-json').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const url = e.currentTarget.getAttribute('data-url');
                    if (expandedJsonUrls.has(url)) {
                        expandedJsonUrls.delete(url);
                    } else {
                        expandedJsonUrls.add(url);
                    }
                    renderModalContent();
                });
            });

            // Copy JSON-LD button
            modalRoot.querySelectorAll('.btn-copy-json').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const jsonStr = e.currentTarget.getAttribute('data-json');
                    if (jsonStr) {
                        navigator.clipboard.writeText(jsonStr).then(() => {
                            const originalText = e.currentTarget.innerText;
                            e.currentTarget.innerText = '✓ Copied!';
                            setTimeout(() => { e.currentTarget.innerText = originalText; }, 1500);
                        }).catch(() => {
                            alert("Failed to copy to clipboard.");
                        });
                    }
                });
            });
        };

        renderModalContent();
        document.body.appendChild(modalRoot);
    }
}
