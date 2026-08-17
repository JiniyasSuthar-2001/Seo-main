import { apiClient } from './apiClient.js';

export const aiService = {
    async getInsights(projectId = '1') {
        return await apiClient.get(`/api/projects/${projectId}/ai/insights`);
    },
    
    async askChat(projectId = '1', query = '') {
        return await apiClient.post(`/api/projects/${projectId}/ai/chat`, { query: query });
    }
};
