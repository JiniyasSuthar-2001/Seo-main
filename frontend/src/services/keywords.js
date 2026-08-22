import { apiClient } from './apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';

export const keywordsService = {
    async getKeywords(projectId, limit = 50, offset = 0) {
        const id = resolveProjectId(projectId);
        if (!id) return [];
        return await apiClient.get(`/api/projects/${id}/keywords?limit=${limit}&offset=${offset}`);
    },
    async getKeyword(projectId, keywordId) {
        const id = resolveProjectId(projectId);
        if (!id) return null;
        return await apiClient.get(`/api/projects/${id}/keywords/${keywordId}`);
    },
    async getKeywordPageAnalysis(projectId) {
        const id = resolveProjectId(projectId);
        if (!id) return [];
        return await apiClient.get(`/api/projects/${id}/keyword-page-analysis`);
    }
};
