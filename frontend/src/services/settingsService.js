import { apiClient } from './apiClient.js';
import { API_BASE_URL } from '../config/api.js';
import { resolveProjectId } from '../utils/projectResolver.js';

export const settingsService = {
    async checkHealth() {
        try {
            const res = await apiClient.get('/api/health');
            return { status: 'connected', data: res };
        } catch (e) {
            return { status: 'offline', error: e.message };
        }
    },
    
    async getProjectSummary(projectId) {
        const id = resolveProjectId(projectId);
        if (!id) return { status: 'empty' };
        try {
            return await apiClient.get(`/api/projects/${id}/summary`);
        } catch (e) {
            return { status: 'empty' };
        }
    },

    getApiBaseUrl() {
        return API_BASE_URL;
    }
};
