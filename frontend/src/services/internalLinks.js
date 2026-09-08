import { apiClient } from './apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';

export const internalLinksService = {
    async getInternalLinks(projectId, limit = 50, offset = 0) {
        const id = resolveProjectId(projectId);
        if (!id) return { internal_links: [], orphan_pages: [], anchor_texts: [], total: 0 };
        return await apiClient.get(`/api/projects/${id}/internal-links?limit=${limit}&offset=${offset}`);
    },

    async getBrokenLinks(projectId, type = null, limit = 50, offset = 0, search = null) {
        const id = resolveProjectId(projectId);
        if (!id) return { broken_links: [], total: 0, internal_count: 0, external_count: 0 };
        let url = `/api/projects/${id}/internal-links/broken?limit=${limit}&offset=${offset}`;
        if (type && type !== 'all') {
            url += `&type=${encodeURIComponent(type)}`;
        }
        if (search && search.trim()) {
            url += `&search=${encodeURIComponent(search.trim())}`;
        }
        return await apiClient.get(url);
    }
};
