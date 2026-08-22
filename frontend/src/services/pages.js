import { apiClient } from './apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';

export const pagesService = {
    async getPages(projectId, limit = 50, offset = 0) {
        const id = resolveProjectId(projectId);
        if (!id) return [];
        return await apiClient.get(`/api/projects/${id}/pages?limit=${limit}&offset=${offset}`);
    },
    async getPage(projectId, pageId) {
        const id = resolveProjectId(projectId);
        if (!id) return null;
        return await apiClient.get(`/api/projects/${id}/pages/${pageId}`);
    }
};
