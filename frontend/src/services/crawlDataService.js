import { apiClient } from './apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';
import { API_BASE_URL } from '../config/api.js';

export const crawlDataService = {
    async getAvailableCrawls(projectId) {
        const id = resolveProjectId(projectId);
        if (!id) return [];
        const res = await apiClient.get(`/api/projects/${id}/crawl-data/crawls`);
        return res?.crawls || [];
    },

    async getCrawlDataTab(projectId, tabName, params = {}) {
        const id = resolveProjectId(projectId);
        if (!id) return null;

        const queryParts = [];
        if (params.crawl_id) queryParts.push(`crawl_id=${encodeURIComponent(params.crawl_id)}`);
        if (params.search) queryParts.push(`search=${encodeURIComponent(params.search)}`);
        if (params.filter_field && params.filter_value) {
            queryParts.push(`filter_field=${encodeURIComponent(params.filter_field)}`);
            queryParts.push(`filter_value=${encodeURIComponent(params.filter_value)}`);
        }
        if (params.sort_by) queryParts.push(`sort_by=${encodeURIComponent(params.sort_by)}`);
        if (params.sort_dir) queryParts.push(`sort_dir=${encodeURIComponent(params.sort_dir)}`);
        queryParts.push(`limit=${params.limit || 20}`);
        queryParts.push(`offset=${params.offset || 0}`);

        const qs = queryParts.length ? `?${queryParts.join('&')}` : '';
        return await apiClient.get(`/api/projects/${id}/crawl-data/${tabName}${qs}`);
    },

    getTabCsvExportUrl(projectId, tabName, crawlId = null) {
        const id = resolveProjectId(projectId);
        let url = `${API_BASE_URL}/api/projects/${id}/crawl-data/${tabName}/export.csv`;
        if (crawlId) url += `?crawl_id=${encodeURIComponent(crawlId)}`;
        return url;
    },

    getCrawlXlsxExportUrl(projectId, crawlId = null) {
        const id = resolveProjectId(projectId);
        let url = `${API_BASE_URL}/api/projects/${id}/crawl-data/export.xlsx`;
        if (crawlId) url += `?crawl_id=${encodeURIComponent(crawlId)}`;
        return url;
    },

    async downloadFile(url, defaultFilename) {
        const token = localStorage.getItem('access_token');
        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(url, { headers });
        if (!res.ok) {
            throw new Error(`Export download failed (${res.status} ${res.statusText})`);
        }

        const blob = await res.blob();
        const disposition = res.headers.get('content-disposition');
        let filename = defaultFilename;
        if (disposition && disposition.includes('filename=')) {
            const match = disposition.match(/filename=["']?([^"';]+)["']?/);
            if (match && match[1]) filename = match[1];
        }

        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
    },

    async getAISuggestion({ projectId, pageUrl, taskType, currentValue = null, issue = null, provider = null, model = null }, options = {}) {
        const id = resolveProjectId(projectId);
        if (!id) throw new Error('No active project ID found.');

        const payload = {
            project_id: id,
            page_url: pageUrl,
            task_type: taskType,
            current_value: currentValue,
            issue: issue,
            provider: provider,
            model: model
        };

        return await apiClient.post('/api/ai/crawl-suggest', payload, options);
    }
};
