import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';

export class Projects {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'projects-view';
        this.searchQuery = '';
        this.statusFilter = 'all';
        this.sortBy = 'updated';
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary);">SEO Projects</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px; font-size: 14px;">Manage, review, edit and export all your SEO projects from one place.</p>
                </div>
                <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <a href="${API_BASE_URL}/api/projects/all/pdf" target="_blank" class="btn btn-secondary" title="Download Consolidated PDF Report for All Projects">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 6px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        <span>Download All Projects PDF</span>
                    </a>
                    <a href="${API_BASE_URL}/api/projects/all/export" target="_blank" class="btn btn-secondary" title="Export Consolidated ZIP Data for All Projects">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 6px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        <span>Export All Project Data</span>
                    </a>
                    <button class="btn btn-primary" onclick="window.showCreateProjectModalModalView()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right: 6px;"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                        <span>+ Add Project</span>
                    </button>
                </div>
            </div>

            <!-- SEARCH, FILTER & SORT BAR -->
            <div style="margin-bottom: 24px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; background: var(--bg-card); padding: 16px; border-radius: 10px; border: 1px solid var(--border);">
                <!-- SEARCH INPUT -->
                <div style="position: relative; flex: 1; min-width: 240px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary);">
                        <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    <input id="projects-search-input" type="text" placeholder="Search by name, domain, or URL..." style="width: 100%; padding: 10px 14px 10px 40px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-workspace); color: var(--text-primary);">
                </div>

                <!-- FILTER DROPDOWN -->
                <div style="display: flex; align-items: center; gap: 8px;">
                    <label style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Filter:</label>
                    <select id="projects-filter-select" style="padding: 9px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                        <option value="all">All Projects</option>
                        <option value="crawled">Crawled</option>
                        <option value="uncrawled">Not Crawled</option>
                        <option value="critical">Has Critical Issues</option>
                        <option value="warning">Has Warnings</option>
                    </select>
                </div>

                <!-- SORT DROPDOWN -->
                <div style="display: flex; align-items: center; gap: 8px;">
                    <label style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Sort:</label>
                    <select id="projects-sort-select" style="padding: 9px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                        <option value="updated">Recently Updated</option>
                        <option value="created">Recently Created</option>
                        <option value="issues">Most Issues</option>
                        <option value="pages">Most Pages</option>
                        <option value="name">Alphabetical</option>
                    </select>
                </div>
            </div>

            <!-- PROJECTS LIST CONTAINER -->
            <div id="projects-list-container">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading projects...
                </div>
            </div>

            <!-- EDIT & DELETE MODAL CONTAINER -->
            <div id="projects-modal-area"></div>
        `;

        this.initEventListeners();
        return this.element;
    }

    initEventListeners() {
        window.showCreateProjectModalModalView = () => {
            if (window.showCreateProjectModal) {
                window.showCreateProjectModal();
            }
        };

        window.openProjectWorkspace = (id) => {
            projectStore.setSelectedProjectId(id);
            window.location.href = '/';
        };

        window.openEditProjectModal = (id) => {
            const p = projectStore.projects.find(proj => String(proj.id) === String(id));
            if (!p) return;

            const modalArea = document.getElementById('projects-modal-area');
            if (!modalArea) return;

            modalArea.innerHTML = `
                <div id="edit-proj-modal" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 9999;">
                    <div style="background: var(--bg-card); width: 100%; max-width: 520px; padding: 28px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                            <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;">Edit Project: ${p.name}</h3>
                            <button onclick="document.getElementById('edit-proj-modal').remove()" style="background: none; border: none; font-size: 20px; color: var(--text-tertiary); cursor: pointer;">&times;</button>
                        </div>
                        <form onsubmit="window.saveEditedProject(event, '${p.id}', '${p.domain}')">
                            <div style="margin-bottom: 14px;">
                                <label style="display: block; font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 6px;">Project Name</label>
                                <input id="edit-name" type="text" value="${p.name}" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-workspace); color: var(--text-primary);">
                            </div>
                            <div style="margin-bottom: 14px;">
                                <label style="display: block; font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 6px;">Website URL</label>
                                <input id="edit-url" type="url" value="${p.url}" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-workspace); color: var(--text-primary);">
                            </div>
                            <div style="margin-bottom: 14px;">
                                <label style="display: block; font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 6px;">Description (Optional)</label>
                                <input id="edit-desc" type="text" value="${p.description || ''}" placeholder="e.g. Primary client domain" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-workspace); color: var(--text-primary);">
                            </div>
                            <div style="margin-bottom: 20px;">
                                <label style="display: block; font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 6px;">Industry / Notes (Optional)</label>
                                <input id="edit-ind" type="text" value="${p.industry || ''}" placeholder="e.g. Electrical, E-Commerce, Marketing" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-workspace); color: var(--text-primary);">
                            </div>
                            <div style="display: flex; justify-content: flex-end; gap: 10px;">
                                <button type="button" class="btn btn-secondary" onclick="document.getElementById('edit-proj-modal').remove()">Cancel</button>
                                <button type="submit" class="btn btn-primary">Save Changes</button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
        };

        window.saveEditedProject = async (e, id, origDomain) => {
            e.preventDefault();
            const name = document.getElementById('edit-name').value.trim();
            const url = document.getElementById('edit-url').value.trim();
            const description = document.getElementById('edit-desc').value.trim();
            const industry = document.getElementById('edit-ind').value.trim();

            if (origDomain && !url.includes(origDomain)) {
                const conf = confirm(`Notice: Changing the project website URL from '${origDomain}' will update its domain identity. Existing crawl history remains linked to this project ID. Proceed?`);
                if (!conf) return;
            }

            try {
                await projectStore.updateProject(id, { name, url, description, industry });
                const modal = document.getElementById('edit-proj-modal');
                if (modal) modal.remove();
                window.location.reload();
            } catch (err) {
                alert(`Failed to update project: ${err.message || "Network error"}`);
            }
        };

        window.confirmDeleteProject = (id, name) => {
            const modalArea = document.getElementById('projects-modal-area');
            if (!modalArea) return;

            modalArea.innerHTML = `
                <div id="delete-proj-modal" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 9999;">
                    <div style="background: var(--bg-card); width: 100%; max-width: 480px; padding: 28px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3);">
                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: rgba(239, 68, 68, 0.1); color: #ef4444; display: flex; align-items: center; justify-content: center;">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                            </div>
                            <div>
                                <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;">Delete '${name}'?</h3>
                                <p style="font-size: 13px; color: var(--text-secondary); margin-top: 2px;">This action cannot be undone.</p>
                            </div>
                        </div>
                        <p style="font-size: 14px; color: var(--text-primary); margin-bottom: 20px; line-height: 1.5; background: var(--bg-subtle); padding: 12px; border-radius: 6px; border-left: 4px solid #ef4444;">
                            Are you sure you want to delete this SEO project? This will remove the project and its associated SEO datasets, crawl history, snapshots, and reports.
                        </p>
                        <div style="display: flex; justify-content: flex-end; gap: 10px;">
                            <button type="button" class="btn btn-secondary" onclick="document.getElementById('delete-proj-modal').remove()">Cancel</button>
                            <button type="button" class="btn" style="background: #ef4444; color: #fff;" onclick="window.executeDeleteProject('${id}')">Delete Project Workspace</button>
                        </div>
                    </div>
                </div>
            `;
        };

        window.executeDeleteProject = async (id) => {
            try {
                await projectStore.deleteProject(id);
                const modal = document.getElementById('delete-proj-modal');
                if (modal) modal.remove();
                window.location.reload();
            } catch (err) {
                alert(`Failed to delete project: ${err.message || "Server error"}`);
            }
        };
    }

    async mounted() {
        const container = document.getElementById('projects-list-container');
        const searchInput = document.getElementById('projects-search-input');
        const filterSelect = document.getElementById('projects-filter-select');
        const sortSelect = document.getElementById('projects-sort-select');

        if (!container) return;

        const renderProjectsList = (projects) => {
            const selectedId = projectStore.getSelectedProjectId();
            let result = [...projects];

            // 1. Search Filter
            if (this.searchQuery) {
                const q = this.searchQuery.toLowerCase();
                result = result.filter(p => 
                    p.name.toLowerCase().includes(q) || 
                    (p.domain && p.domain.toLowerCase().includes(q)) || 
                    (p.url && p.url.toLowerCase().includes(q))
                );
            }

            // 2. Status Filter
            if (this.statusFilter === 'crawled') {
                result = result.filter(p => p.has_crawled);
            } else if (this.statusFilter === 'uncrawled') {
                result = result.filter(p => !p.has_crawled);
            } else if (this.statusFilter === 'critical') {
                result = result.filter(p => (p.critical_issues || 0) > 0);
            } else if (this.statusFilter === 'warning') {
                result = result.filter(p => (p.warnings || 0) > 0);
            }

            // 3. Sorting
            if (this.sortBy === 'name') {
                result.sort((a, b) => a.name.localeCompare(b.name));
            } else if (this.sortBy === 'pages') {
                result.sort((a, b) => (b.pages_count || 0) - (a.pages_count || 0));
            } else if (this.sortBy === 'issues') {
                result.sort((a, b) => (b.issues_count || 0) - (a.issues_count || 0));
            } else if (this.sortBy === 'created') {
                result.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
            } else {
                result.sort((a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0));
            }

            if (!result || result.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                        </div>
                        <div class="empty-state-title">No SEO Projects Yet</div>
                        <div class="empty-state-desc">${this.searchQuery || this.statusFilter !== 'all' ? 'No projects matched your search and filter criteria.' : 'Create your first SEO project to start storing crawls, technical audits, keywords, rankings, backlinks and reports.'}</div>
                        <button class="btn btn-primary" onclick="window.showCreateProjectModalModalView()">+ Add SEO Project</button>
                    </div>
                `;
                return;
            }

            let cards = result.map(p => {
                const isSelected = String(p.id) === String(selectedId);
                const createdDate = p.created_at ? new Date(p.created_at).toLocaleDateString() : 'N/A';
                const lastCrawlDate = p.last_crawl ? new Date(p.last_crawl).toLocaleDateString() : 'No Crawls';

                return `
                    <div class="card" style="padding: 24px; display: flex; flex-direction: column; justify-content: space-between; border: 1px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}; ${isSelected ? 'box-shadow: 0 0 0 2px var(--primary-bg);' : ''}">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                <div>
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <h3 style="font-size: 17px; font-weight: 700; color: var(--text-primary); margin: 0;">${p.name}</h3>
                                        ${isSelected ? '<span class="badge badge-success">ACTIVE WORKSPACE</span>' : ''}
                                    </div>
                                    <a href="${p.url}" target="_blank" style="font-size: 13px; color: var(--primary); text-decoration: none; display: inline-block; margin-top: 4px;">
                                        ${p.url}
                                    </a>
                                </div>
                                <span class="badge ${p.has_crawled ? 'badge-info' : 'badge-warning'}">
                                    ${p.crawl_status}
                                </span>
                            </div>

                            ${p.description ? `<p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 14px; line-height: 1.4;">${p.description}</p>` : ''}

                            <!-- METRICS GRID FOR PROJECT -->
                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 16px 0; background: var(--bg-subtle); padding: 12px; border-radius: 8px;">
                                <div>
                                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Pages</div>
                                    <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);">${p.pages_count}</div>
                                </div>
                                <div>
                                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Issues</div>
                                    <div style="font-size: 16px; font-weight: 700; color: ${p.issues_count > 0 ? 'var(--critical)' : 'var(--text-primary)'};">${p.issues_count}</div>
                                </div>
                                <div>
                                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Keywords</div>
                                    <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);">${p.keywords_count}</div>
                                </div>
                                <div>
                                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Links</div>
                                    <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);">${p.internal_links_count}</div>
                                </div>
                                <div>
                                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Backlinks</div>
                                    <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);">${p.backlinks_count}</div>
                                </div>
                                <div>
                                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Last Crawl</div>
                                    <div style="font-size: 12px; font-weight: 600; color: var(--text-primary);">${lastCrawlDate}</div>
                                </div>
                            </div>
                        </div>

                        <!-- PROJECT CARD ACTIONS: VIEW, EDIT, DOWNLOAD PDF, DOWNLOAD DATA, DELETE -->
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; pt-12; border-top: 1px solid var(--border); flex-wrap: wrap; gap: 8px;">
                            <span style="font-size: 11px; color: var(--text-tertiary);">Created: ${createdDate}</span>
                            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                                <button class="btn btn-primary btn-sm" onclick="window.openProjectWorkspace('${p.id}')">View</button>
                                <button class="btn btn-secondary btn-sm" onclick="window.openEditProjectModal('${p.id}')">Edit</button>
                                <a href="${API_BASE_URL}/api/projects/${p.id}/report.pdf" target="_blank" class="btn btn-secondary btn-sm" title="Download Full Project PDF Report">Download PDF</a>
                                <a href="${API_BASE_URL}/api/projects/${p.id}/export" target="_blank" class="btn btn-secondary btn-sm" title="Download ZIP CSV Package">Download Data</a>
                                <button class="btn btn-secondary btn-sm" style="color: #ef4444;" onclick="window.confirmDeleteProject('${p.id}', '${p.name.replace(/'/g, "\\'")}')">Delete</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px;">
                    ${cards}
                </div>
            `;
        };

        try {
            const projects = await projectStore.fetchProjects();
            renderProjectsList(projects);

            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    this.searchQuery = e.target.value;
                    renderProjectsList(projectStore.projects);
                });
            }
            if (filterSelect) {
                filterSelect.addEventListener('change', (e) => {
                    this.statusFilter = e.target.value;
                    renderProjectsList(projectStore.projects);
                });
            }
            if (sortSelect) {
                sortSelect.addEventListener('change', (e) => {
                    this.sortBy = e.target.value;
                    renderProjectsList(projectStore.projects);
                });
            }
        } catch (e) {
            container.innerHTML = `<div class="card" style="padding: 32px; text-align: center; color: var(--critical);">Unable to load projects from backend API.</div>`;
        }
    }
}
