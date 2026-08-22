import { apiClient } from './apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';

export const rankingsService = {
    async getRankings(projectId, limit = 50, offset = 0) {
        const id = resolveProjectId(projectId);
        if (!id) return [];
        return await apiClient.get(`/api/projects/${id}/rankings?limit=${limit}&offset=${offset}`);
    }
};
