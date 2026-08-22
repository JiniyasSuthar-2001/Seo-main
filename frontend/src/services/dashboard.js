import { apiClient } from './apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';

export const dashboardService = {
    async getWorkspaceOverview() {
        return await apiClient.get('/api/workspace/overview');
    },

    async getSummary(projectId) {
        const id = resolveProjectId(projectId);
        if (!id) return { status: 'empty', message: 'No project selected.' };
        return await apiClient.get(`/api/projects/${id}/summary`);
    }
};

