import { apiClient } from './apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';

export const crawlService = {
    async startCrawl(projectId, url) {
        const id = resolveProjectId(projectId);
        if (!id) throw new Error("No active project selected for crawling.");
        return await apiClient.post(`/api/projects/${id}/crawl`, { url: url });
    },
    
    async getCrawlStatus(projectId, sessionId) {
        const id = resolveProjectId(projectId);
        if (!id) return null;
        return await apiClient.get(`/api/projects/${id}/crawl/${sessionId}`);
    },

    async getCrawlHistory(projectId) {
        const id = resolveProjectId(projectId);
        if (!id) return [];
        return await apiClient.get(`/api/projects/${id}/crawl-history`);
    }
};
