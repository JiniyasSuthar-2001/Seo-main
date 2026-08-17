import { apiClient } from './apiClient.js';
import { projectStore } from '../core/projectStore.js';

export const aiService = {
    async getInsights(projectId) {
        const id = projectId || projectStore.getSelectedProjectId();
        if (!id) return { insights: [] };
        return await apiClient.get(`/api/projects/${id}/ai/insights`);
    },
    
    async askChat(projectId, query = '') {
        const id = projectId || projectStore.getSelectedProjectId();
        if (!id) return { answer: "No project selected." };
        return await apiClient.post(`/api/projects/${id}/ai/chat`, { query: query });
    }
};
