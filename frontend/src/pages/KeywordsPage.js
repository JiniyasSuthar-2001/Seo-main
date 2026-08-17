import { keywordService } from '../services/keywordService.js';
import { appState } from '../state/appState.js';

export class KeywordsPage {
  async render() {
    return `
      <div class="page-header">
        <div>
          <h1>Keywords</h1>
          <p>Organic keywords and their alignment with pages.</p>
        </div>
      </div>
      <div id="keywords-content" class="module-content">
        <div>Loading keyword data...</div>
      </div>
    `;
  }

  async afterRender() {
    const projectId = appState.getCurrentProjectId();
    if (!projectId) {
      document.getElementById('keywords-content').innerHTML = `<div>No project selected.</div>`;
      return;
    }

    try {
      const response = await keywordService.getKeywords(projectId);
      this.renderTable(response.data);
    } catch (err) {
      document.getElementById('keywords-content').innerHTML = `<div style="color:red">Error loading data. Is the backend running?</div>`;
    }
  }

  renderTable(data) {
    const container = document.getElementById('keywords-content');
    if (!data || data.length === 0) {
      container.innerHTML = `<div>No keyword data imported yet.</div>`;
      return;
    }

    const rows = data.map(k => `
      <tr>
        <td>${k.keyword}</td>
        <td>${k.target_url || '-'}</td>
        <td>${k.position || '-'}</td>
        <td>${k.search_volume || '-'}</td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div class="table-container">
        <table>
          <thead>
            <tr><th>Keyword</th><th>Target URL</th><th>Position</th><th>Volume</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }
}
