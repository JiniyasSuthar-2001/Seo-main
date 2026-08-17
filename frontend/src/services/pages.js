import { apiClient } from './apiClient.js';
import { projectStore } from '../core/projectStore.js';

export const pagesService = {
    async getPages(projectId, limit = 50, offset = 0) {
        const id = projectId || projectStore.getSelectedProjectId();
        if (!id) return [];
        return await apiClient.get(`/api/projects/${id}/pages?limit=${limit}&offset=${offset}`);
    },
    async getPage(projectId, pageId) {
        const id = projectId || projectStore.getSelectedProjectId();
        if (!id) return null;
        return await apiClient.get(`/api/projects/${id}/pages/${pageId}`);
    }
};
