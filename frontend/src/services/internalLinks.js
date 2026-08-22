import { apiClient } from './apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';

export const internalLinksService = {
    async getInternalLinks(projectId, limit = 50, offset = 0) {
        const id = resolveProjectId(projectId);
        if (!id) return [];
        return await apiClient.get(`/api/projects/${id}/internal-links?limit=${limit}&offset=${offset}`);
    }
};
