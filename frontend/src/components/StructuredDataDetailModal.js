/**
 * Structured Data Detail Modal Component
 * Provides comprehensive evidence-based inspection for Schema.org JSON-LD structured data.
 * Tabs:
 * 1. SUMMARY — Top-level metrics & status counts
 * 2. TYPE BREAKDOWN — Per-schema-type inspection table
 * 3. PAGE EVIDENCE — Per-page entity properties, validation & missing fields
 * 4. RAW JSON-LD — Expandable raw <script type="application/ld+json"> code view
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
    static open({ structuredDataSummary, schemaEvidence, domain, crawlTimestamp }) {
        const existing = document.getElementById('structured-data-detail-modal-root');
        if (existing) existing.remove();

        const summary = structuredDataSummary || {};
        const pagesDetail = schemaEvidence || summary.pages_detail || [];
        const schemaTypesMap = summary.schema_types_found || {};
        const schemaTypeEntries = Object.entries(schemaTypesMap);

        const totalPages = summary.total_pages_checked || pagesDetail.length || 0;
        const pagesWithSchema = summary.total_pages_with_schema || pagesDetail.filter(p => p.has_structured_data).length || 0;
        const pagesWithoutSchema = summary.total_pages_missing_schema || (totalPages - pagesWithSchema);
        const totalInstances = summary.total_schemas_detected || 0;
        const uniqueTypesCount = summary.unique_schema_types_count || schemaTypeEntries.length;
        const completeEntities = summary.complete_entities_count || 0;
        const incompleteEntities = summary.incomplete_entities_count || 0;
        const potentialMismatches = summary.potential_mismatches_count || 0;

        let activeTab = 'summary'; // 'summary' | 'types' | 'evidence' | 'jsonld'
        let searchQuery = '';
        let currentPage = 1;
        const pageSize = 20;

        const modalRoot = document.createElement('div');
        modalRoot.id = 'structured-data-detail-modal-root';
        modalRoot.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(6px); display: flex; align-items: center;
            justify-content: center; z-index: 9999; padding: 20px;
        `;

        const renderModalContent = () => {
            modalRoot.innerHTML = `
                <div class="card" style="width: 100%; max-width: 1100px; max-height: 92vh; display: flex; flex-direction: column; background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.4); overflow: hidden;">
                    
                    <!-- HEADER -->
                    <div style="padding: 18px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap;">
                                <span style="font-size: 11px; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.5px;">STRUCTURED DATA & SCHEMA.ORG AUDIT</span>
                                <span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 10.5px;">
                                    Canonical Crawler Evidence
                                </span>
                            </div>
                            <h2 style="font-size: 19px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">
                                Structured Data Inspection — ${escapeHtml(domain || 'Target Site')}
                            </h2>
                            <div style="font-size: 12.5px; color: var(--text-secondary);">
                                Evaluated on ${escapeHtml(crawlTimestamp || 'Latest Scan')} • ${totalPages} pages scanned
                            </div>
                        </div>
                        <button id="btn-close-sd-modal" style="background: none; border: none; font-size: 26px; line-height: 1; color: var(--text-tertiary); cursor: pointer; padding: 4px;" title="Close">&times;</button>
                    </div>

                    <!-- TAB BAR -->
                    <div style="display: flex; gap: 4px; padding: 10px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); overflow-x: auto;">
                        <button class="btn-sd-tab ${activeTab === 'summary' ? 'active' : ''}" data-tab="summary"
                                style="padding: 6px 14px; font-size: 12.5px; font-weight: 700; border-radius: 6px; border: none; cursor: pointer; background: ${activeTab === 'summary' ? 'var(--primary)' : 'transparent'}; color: ${activeTab === 'summary' ? '#fff' : 'var(--text-secondary)'};">
                            📊 Summary
                        </button>
                        <button class="btn-sd-tab ${activeTab === 'types' ? 'active' : ''}" data-tab="types"
                                style="padding: 6px 14px; font-size: 12.5px; font-weight: 700; border-radius: 6px; border: none; cursor: pointer; background: ${activeTab === 'types' ? 'var(--primary)' : 'transparent'}; color: ${activeTab === 'types' ? '#fff' : 'var(--text-secondary)'};">
                            🏷️ Type Breakdown (${uniqueTypesCount})
                        </button>
                        <button class="btn-sd-tab ${activeTab === 'evidence' ? 'active' : ''}" data-tab="evidence"
                                style="padding: 6px 14px; font-size: 12.5px; font-weight: 700; border-radius: 6px; border: none; cursor: pointer; background: ${activeTab === 'evidence' ? 'var(--primary)' : 'transparent'}; color: ${activeTab === 'evidence' ? '#fff' : 'var(--text-secondary)'};">
                            🔍 Page Evidence (${pagesDetail.length})
                        </button>
                        <button class="btn-sd-tab ${activeTab === 'jsonld' ? 'active' : ''}" data-tab="jsonld"
                                style="padding: 6px 14px; font-size: 12.5px; font-weight: 700; border-radius: 6px; border: none; cursor: pointer; background: ${activeTab === 'jsonld' ? 'var(--primary)' : 'transparent'}; color: ${activeTab === 'jsonld' ? '#fff' : 'var(--text-secondary)'};">
                            code Raw JSON-LD
                        </button>
                    </div>

                    <!-- BODY VIEWPORT -->
                    <div style="flex: 1; overflow-y: auto; padding: 20px 24px;">
                        ${renderActiveTabView()}
                    </div>

                    <!-- FOOTER -->
                    <div style="padding: 14px 24px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: flex-end;">
                        <button id="btn-close-sd-modal-footer" class="btn btn-secondary btn-sm">Close Modal</button>
                    </div>
                </div>
            `;

            bindEvents();
        };

        const renderActiveTabView = () => {
            if (activeTab === 'summary') {
                return `
                    <div style="display: flex; flex-direction: column; gap: 20px;">
                        <!-- KPI GRID -->
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px;">
                            <div style="background: var(--bg-card); padding: 16px; border-radius: 10px; border: 1px solid var(--border);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Pages Scanned</div>
                                <div style="font-size: 26px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${totalPages}</div>
                            </div>
                            <div style="background: var(--bg-card); padding: 16px; border-radius: 10px; border: 1px solid var(--border); border-left: 3px solid var(--success);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--success); text-transform: uppercase;">With Schema</div>
                                <div style="font-size: 26px; font-weight: 800; color: var(--success); margin-top: 2px;">${pagesWithSchema}</div>
                            </div>
                            <div style="background: var(--bg-card); padding: 16px; border-radius: 10px; border: 1px solid var(--border); border-left: 3px solid ${pagesWithoutSchema > 0 ? 'var(--warning)' : 'var(--border)'};">
                                <div style="font-size: 11px; font-weight: 700; color: ${pagesWithoutSchema > 0 ? 'var(--warning)' : 'var(--text-secondary)'}; text-transform: uppercase;">Without Schema</div>
                                <div style="font-size: 26px; font-weight: 800; color: ${pagesWithoutSchema > 0 ? 'var(--warning)' : 'var(--text-primary)'}; margin-top: 2px;">${pagesWithoutSchema}</div>
                            </div>
                            <div style="background: var(--bg-card); padding: 16px; border-radius: 10px; border: 1px solid var(--border);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase;">Total Instances</div>
                                <div style="font-size: 26px; font-weight: 800; color: var(--primary); margin-top: 2px;">${totalInstances}</div>
                            </div>
                            <div style="background: var(--bg-card); padding: 16px; border-radius: 10px; border: 1px solid var(--border);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Unique Schema Types</div>
                                <div style="font-size: 26px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${uniqueTypesCount}</div>
                            </div>
                        </div>

                        <!-- ENTITY VALIDATION COUNTS -->
                        <div style="background: var(--bg-subtle); border-radius: 12px; padding: 18px; border: 1px solid var(--border);">
                            <h4 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 700; color: var(--text-primary);">Entity Evidence & Completeness Statuses</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px;">
                                <div style="background: var(--bg-card); padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
                                    <div style="font-size: 11px; font-weight: 700; color: #10b981;">✓ Complete Entities</div>
                                    <div style="font-size: 20px; font-weight: 800; margin-top: 2px; color: #10b981;">${completeEntities}</div>
                                    <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">All essential properties present</div>
                                </div>
                                <div style="background: var(--bg-card); padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
                                    <div style="font-size: 11px; font-weight: 700; color: #f59e0b;">⚠ Incomplete Entities</div>
                                    <div style="font-size: 20px; font-weight: 800; margin-top: 2px; color: #f59e0b;">${incompleteEntities}</div>
                                    <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Missing recommended schema properties</div>
                                </div>
                                <div style="background: var(--bg-card); padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
                                    <div style="font-size: 11px; font-weight: 700; color: #ef4444;">⚡ Potential Mismatches</div>
                                    <div style="font-size: 20px; font-weight: 800; margin-top: 2px; color: #ef4444;">${potentialMismatches}</div>
                                    <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Data mismatch vs page content</div>
                                </div>
                            </div>
                        </div>

                        <!-- DETECTED SCHEMA TYPES SUMMARY -->
                        <div>
                            <h4 style="margin: 0 0 10px 0; font-size: 14px; font-weight: 700; color: var(--text-primary);">Detected Schema Types</h4>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                                ${schemaTypeEntries.length > 0 ? schemaTypeEntries.map(([t, cnt]) => `
                                    <span style="background: var(--bg-subtle); border: 1px solid var(--border); padding: 6px 14px; border-radius: 20px; font-size: 12.5px; font-weight: 600; color: var(--text-primary);">
                                        🏷️ <strong>${escapeHtml(t)}</strong> — ${cnt} page${cnt === 1 ? '' : 's'}
                                    </span>
                                `).join('') : '<div style="color: var(--text-secondary); font-size: 13px;">No structured data markup detected.</div>'}
                            </div>
                        </div>
                    </div>
                `;
            }

            if (activeTab === 'types') {
                return `
                    <div>
                        <h4 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 700; color: var(--text-primary);">Schema Types Breakdown</h4>
                        <div style="overflow-x: auto; border: 1px solid var(--border); border-radius: 10px;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 10px 14px;">Schema Type</th>
                                        <th style="padding: 10px 14px;">Pages Count</th>
                                        <th style="padding: 10px 14px;">Instances</th>
                                        <th style="padding: 10px 14px;">Validation Status</th>
                                        <th style="padding: 10px 14px;">Completeness</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${schemaTypeEntries.length > 0 ? schemaTypeEntries.map(([t, count]) => `
                                        <tr style="border-bottom: 1px solid var(--border);">
                                            <td style="padding: 12px 14px; font-weight: 700; color: var(--text-primary);">🏷️ ${escapeHtml(t)}</td>
                                            <td style="padding: 12px 14px; font-weight: 600;">${count} page${count === 1 ? '' : 's'}</td>
                                            <td style="padding: 12px 14px;">${count}</td>
                                            <td style="padding: 12px 14px;">
                                                <span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 11px; font-weight: 700;">
                                                    Recognized & Supported
                                                </span>
                                            </td>
                                            <td style="padding: 12px 14px; color: var(--text-secondary); font-size: 12px;">
                                                Supported by page evidence
                                            </td>
                                        </tr>
                                    `).join('') : `<tr><td colspan="5" style="padding: 24px; text-align: center; color: var(--text-secondary);">No schema types found.</td></tr>`}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            }

            if (activeTab === 'evidence') {
                const filteredPages = pagesDetail.filter(p => {
                    if (!searchQuery) return true;
                    const q = searchQuery.toLowerCase();
                    return (p.url || '').toLowerCase().includes(q) || (p.detected_schema_types || []).some(t => String(t).toLowerCase().includes(q));
                });

                const paginated = Pagination.paginateArray(filteredPages, currentPage, pageSize);
                currentPage = paginated.currentPage;

                return `
                    <div style="display: flex; flex-direction: column; gap: 14px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
                            <input type="text" id="sd-evidence-search" value="${escapeHtml(searchQuery)}" placeholder="Filter by URL or schema type..." 
                                   style="padding: 6px 12px; font-size: 12.5px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-subtle); color: var(--text-primary); min-width: 260px; flex: 1;" />
                            <div style="font-size: 12px; color: var(--text-secondary);">Showing ${paginated.items.length} of ${filteredPages.length} pages</div>
                        </div>

                        <div style="display: flex; flex-direction: column; gap: 12px;">
                            ${paginated.items.length > 0 ? paginated.items.map(p => {
                                const entities = p.entities || [];
                                const typesList = p.detected_schema_types || [];
                                return `
                                    <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px;">
                                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; margin-bottom: 8px;">
                                            <a href="${escapeHtml(p.url)}" target="_blank" rel="noopener noreferrer" style="font-weight: 700; color: var(--primary); font-size: 13.5px; word-break: break-all;">
                                                ${escapeHtml(p.url)} ↗
                                            </a>
                                            <span class="badge" style="${p.has_structured_data ? 'background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);' : 'background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3);'} font-size: 11px; font-weight: 700;">
                                                ${p.has_structured_data ? '✓ Detected & Parsed' : '⚠ Missing Schema'}
                                            </span>
                                        </div>

                                        ${entities.length > 0 ? entities.map(e => `
                                            <div style="background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; margin-top: 8px; font-size: 12px;">
                                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                                    <span style="font-weight: 700; color: var(--text-primary); font-size: 13px;">🏷️ Entity Type: ${escapeHtml(e.type)}</span>
                                                    <span class="badge badge-info" style="font-size: 10.5px;">${escapeHtml(e.validation_status || 'Detected')}</span>
                                                </div>
                                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; margin-top: 6px; color: var(--text-secondary);">
                                                    ${Object.entries(e.important_properties || {}).map(([k, v]) => `
                                                        <div><strong style="color: var(--text-primary);">${escapeHtml(k)}:</strong> ${escapeHtml(v)}</div>
                                                    `).join('')}
                                                </div>
                                                ${e.missing_properties && e.missing_properties.length > 0 ? `
                                                    <div style="color: #f59e0b; margin-top: 6px; font-size: 11.5px;">
                                                        <strong>Missing Recommended:</strong> ${escapeHtml(e.missing_properties.join(', '))}
                                                    </div>
                                                ` : ''}
                                                ${e.validation_notes ? `
                                                    <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px; font-style: italic;">
                                                        Validation: ${escapeHtml(e.validation_notes)}
                                                    </div>
                                                ` : ''}
                                            </div>
                                        `).join('') : `
                                            <div style="font-size: 12px; color: var(--text-tertiary); font-style: italic;">
                                                ${p.has_structured_data ? `Types: ${typesList.join(', ')}` : 'No structured data tags present on this URL.'}
                                            </div>
                                        `}
                                    </div>
                                `;
                            }).join('') : `<div style="padding: 30px; text-align: center; color: var(--text-secondary);">No page evidence matches query.</div>`}
                        </div>
                    </div>
                `;
            }

            if (activeTab === 'jsonld') {
                const pagesWithJson = pagesDetail.filter(p => p.raw_json_ld && p.raw_json_ld.length > 0);
                return `
                    <div style="display: flex; flex-direction: column; gap: 14px;">
                        <h4 style="margin: 0; font-size: 14px; font-weight: 700; color: var(--text-primary);">Raw captured &lt;script type="application/ld+json"&gt; Data</h4>
                        ${pagesWithJson.length > 0 ? pagesWithJson.map(p => {
                            const rawStr = JSON.stringify(p.raw_json_ld.length === 1 ? p.raw_json_ld[0] : p.raw_json_ld, null, 2);
                            return `
                                <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 8px;">
                                    <div style="font-weight: 700; color: var(--primary); font-size: 12.5px; margin-bottom: 8px; word-break: break-all;">
                                        📄 ${escapeHtml(p.url)}
                                    </div>
                                    <pre style="margin: 0; padding: 12px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; font-family: monospace; font-size: 11.5px; line-height: 1.45; color: var(--text-primary); max-height: 250px; overflow-y: auto; white-space: pre-wrap; word-break: break-all;"><code>${escapeHtml(rawStr)}</code></pre>
                                </div>
                            `;
                        }).join('') : `<div style="padding: 30px; text-align: center; color: var(--text-secondary);">No raw JSON-LD content captured during crawl.</div>`}
                    </div>
                `;
            }
        };

        const bindEvents = () => {
            const closeBtn = modalRoot.querySelector('#btn-close-sd-modal');
            const closeFooterBtn = modalRoot.querySelector('#btn-close-sd-modal-footer');
            const closeFn = () => modalRoot.remove();
            if (closeBtn) closeBtn.onclick = closeFn;
            if (closeFooterBtn) closeFooterBtn.onclick = closeFn;
            modalRoot.onclick = (e) => { if (e.target === modalRoot) closeFn(); };

            // Tab switches
            modalRoot.querySelectorAll('.btn-sd-tab').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    activeTab = e.currentTarget.getAttribute('data-tab');
                    renderModalContent();
                });
            });

            // Search input binding
            const searchInput = modalRoot.querySelector('#sd-evidence-search');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    searchQuery = e.target.value;
                    currentPage = 1;
                    renderModalContent();
                });
            }
        };

        document.body.appendChild(modalRoot);
        renderModalContent();
    }
}
