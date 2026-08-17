const API_BASE = 'http://localhost:8000/api';

export const keywordService = {
  async getKeywords(projectId, skip=0, limit=100) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/keywords/?skip=${skip}&limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch keywords");
    return res.json();
  }
};
