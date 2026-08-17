import { apiClient } from './apiClient.js';
import { projectStore } from '../core/projectStore.js';

export const technicalService = {
    async getIssues(projectId, limit = 50, offset = 0) {
        const id = projectId || projectStore.getSelectedProjectId();
        if (!id) return [];
        return await apiClient.get(`/api/projects/${id}/technical?limit=${limit}&offset=${offset}`);
    }
};
