import { apiClient } from './apiClient.js';

export const internalLinksService = {
    async getInternalLinks(projectId = '1', limit = 50, offset = 0) {
        return await apiClient.get(`/api/projects/${projectId}/internal-links?limit=${limit}&offset=${offset}`);
    }
};
