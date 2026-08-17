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

    setSelectedProjectId(id) {
        this.selectedProjectId = String(id);
        localStorage.setItem('seo_selected_project_id', this.selectedProjectId);
        this.notify();
    }

    async createProject(name, domain) {
        try {
            const newProj = await apiClient.post('/api/projects', { name, domain });
            await this.fetchProjects();
            if (newProj && newProj.id) {
                this.setSelectedProjectId(newProj.id);
            }
            return newProj;
        } catch (e) {
            console.error("[ProjectStore] Failed to create project:", e);
            throw e;
        }
    }
}

export const projectStore = new ProjectStore();
