import { apiClient } from './apiClient.js';

export const keywordsService = {
    async getKeywords(projectId, limit = 50, offset = 0) {
        return await apiClient.get(`/api/projects/${projectId}/keywords?limit=${limit}&offset=${offset}`);
    },
    async getKeyword(projectId, keywordId) {
        return await apiClient.get(`/api/projects/${projectId}/keywords/${keywordId}`);
    },
    async getKeywordPageAnalysis(projectId) {
        return await apiClient.get(`/api/projects/${projectId}/keyword-page-analysis`);
    }
};
