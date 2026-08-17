import { apiClient } from './apiClient.js';

export const pagesService = {
    async getPages(projectId, limit = 50, offset = 0) {
        return await apiClient.get(`/api/projects/${projectId}/pages?limit=${limit}&offset=${offset}`);
    },
    async getPage(projectId, pageId) {
        return await apiClient.get(`/api/projects/${projectId}/pages/${pageId}`);
    },
    async getPageSeo(projectId, pageId) {
        return await apiClient.get(`/api/projects/${projectId}/pages/${pageId}/seo`);
    }
};
