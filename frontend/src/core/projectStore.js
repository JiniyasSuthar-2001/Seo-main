import { apiClient } from '../services/apiClient.js';

class ProjectStore {
    constructor() {
        this.projects = [];
        this.selectedProjectId = localStorage.getItem('seo_selected_project_id') || null;
        this.listeners = new Set();
    }

    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    notify() {
        this.listeners.forEach(fn => fn(this.selectedProjectId, this.getSelectedProject()));
    }

    async fetchProjects() {
        try {
            const data = await apiClient.get('/api/projects');
            this.projects = Array.isArray(data) ? data : (data.data || []);
            
            // If no selected project yet or invalid, set to first available project
            if (this.projects.length > 0) {
                const exists = this.projects.find(p => String(p.id) === String(this.selectedProjectId));
                if (!exists) {
                    this.setSelectedProjectId(this.projects[0].id);
                }
            } else {
                this.selectedProjectId = null;
                localStorage.removeItem('seo_selected_project_id');
                this.notify();
            }
        } catch (e) {
            console.error("[ProjectStore] Failed to fetch projects:", e);
            this.projects = [];
        }
        return this.projects;
    }

    getSelectedProjectId() {
        return this.selectedProjectId;
    }

    getSelectedProject() {
        if (!this.selectedProjectId || !this.projects.length) return null;
        return this.projects.find(p => String(p.id) === String(this.selectedProjectId)) || null;
    }

    getCurrentProject() {
        return this.getSelectedProject();
    }

    setSelectedProjectId(id) {
        this.selectedProjectId = id ? String(id) : null;
        if (this.selectedProjectId) {
            localStorage.setItem('seo_selected_project_id', this.selectedProjectId);
        } else {
            localStorage.removeItem('seo_selected_project_id');
        }
        this.notify();
    }

    async createProject(payload) {
        try {
            // Handle both object payload or legacy (name, domain) signature
            const body = typeof payload === 'object' ? payload : { name: arguments[0], url: arguments[1] };
            const newProj = await apiClient.post('/api/projects', body);
            await this.fetchProjects();
            const createdId = (newProj && newProj.project && newProj.project.id) || (newProj && newProj.id);
            if (createdId) {
                this.setSelectedProjectId(createdId);
            }
            return newProj;
        } catch (e) {
            console.error("[ProjectStore] Failed to create project:", e);
            throw e;
        }
    }

    async updateProject(id, payload) {
        try {
            const updated = await apiClient.put(`/api/projects/${id}`, payload);
            await this.fetchProjects();
            this.notify();
            return updated;
        } catch (e) {
            console.error("[ProjectStore] Failed to update project:", e);
            throw e;
        }
    }

    async deleteProject(id) {
        try {
            const res = await apiClient.delete(`/api/projects/${id}`);
            await this.fetchProjects();
            return res;
        } catch (e) {
            console.error("[ProjectStore] Failed to delete project:", e);
            throw e;
        }
    }
}

export const projectStore = new ProjectStore();
