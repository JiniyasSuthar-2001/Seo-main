import { apiClient } from './apiClient.js';

export const technicalService = {
    async getIssues(projectId = '1', limit = 50, offset = 0) {
        return await apiClient.get(`/api/projects/${projectId}/technical?limit=${limit}&offset=${offset}`);
    }
};
