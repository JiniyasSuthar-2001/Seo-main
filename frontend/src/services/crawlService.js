import { apiClient } from './apiClient.js';
import { projectStore } from '../core/projectStore.js';

export const crawlService = {
    async startCrawl(projectId, url) {
        const id = projectId || projectStore.getSelectedProjectId();
        return await apiClient.post(`/api/projects/${id}/crawl`, { url: url });
    },
    
    async getCrawlStatus(projectId, sessionId) {
        const id = projectId || projectStore.getSelectedProjectId();
        return await apiClient.get(`/api/projects/${id}/crawl/${sessionId}`);
    },

    async getCrawlHistory(projectId) {
        const id = projectId || projectStore.getSelectedProjectId();
        if (!id) return [];
        return await apiClient.get(`/api/projects/${id}/crawl-history`);
    }
};
