import { apiClient } from './apiClient.js';

export const crawlService = {
    async startCrawl(projectId, url) {
        return await apiClient.post(`/api/projects/${projectId}/crawl`, { url: url });
    },
    
    async getCrawlStatus(projectId, sessionId) {
        return await apiClient.get(`/api/projects/${projectId}/crawl/${sessionId}`);
    },

    async getCrawlHistory(projectId = '1') {
        return await apiClient.get(`/api/projects/${projectId}/crawl-history`);
    }
};
