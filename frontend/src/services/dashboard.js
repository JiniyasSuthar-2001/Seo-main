import { apiClient } from './apiClient.js';

export const dashboardService = {
    async getSummary(projectId) {
        return await apiClient.get(`/api/projects/${projectId}/summary`);
    }
};
