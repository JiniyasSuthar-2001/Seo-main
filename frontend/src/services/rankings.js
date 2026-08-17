import { apiClient } from './apiClient.js';

export const rankingsService = {
    async getRankings(projectId, limit = 50, offset = 0) {
        return await apiClient.get(`/api/projects/${projectId}/rankings?limit=${limit}&offset=${offset}`);
    }
};
