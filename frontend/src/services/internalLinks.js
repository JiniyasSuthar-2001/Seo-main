import { apiClient } from './apiClient.js';
import { projectStore } from '../core/projectStore.js';

export const internalLinksService = {
    async getInternalLinks(projectId, limit = 50, offset = 0) {
        const id = projectId || projectStore.getSelectedProjectId();
        if (!id) return [];
        return await apiClient.get(`/api/projects/${id}/internal-links?limit=${limit}&offset=${offset}`);
    }
};
