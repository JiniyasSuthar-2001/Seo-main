import { apiClient } from './apiClient.js';
import { projectStore } from '../core/projectStore.js';

export const dashboardService = {
    async getSummary(projectId) {
        const id = projectId || projectStore.getSelectedProjectId();
        if (!id) return { status: 'empty', message: 'No project selected.' };
        return await apiClient.get(`/api/projects/${id}/summary`);
    }
};
