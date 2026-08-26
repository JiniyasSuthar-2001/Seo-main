/**
 * AIBadge.js — Standardized AI & Data Provenance Badge Component
 * Guarantees clear distinction between Raw Project Data vs. AI-Generated Output.
 */

export function renderAIBadge(type = 'analysis', extraText = '') {
  let badgeClass = 'badge-ai-analysis';
  let labelText = 'AI Analysis';
  let icon = '🤖';

  const cleanType = String(type).toLowerCase();
  if (cleanType.includes('generated') || cleanType === 'content') {
    badgeClass = 'badge-ai-generated';
    labelText = 'AI Generated';
    icon = '✨';
  } else if (cleanType.includes('assisted') || cleanType === 'action') {
    badgeClass = 'badge-ai-assisted';
    labelText = 'AI Assisted';
    icon = '⚡';
  }

  if (extraText) {
    labelText += ` (${extraText})`;
  }

  return `<span class="${badgeClass}">${icon} ${labelText}</span>`;
}

export function renderSourceBadge(sourceType = 'crawl', customLabel = null) {
  const cleanType = String(sourceType).toLowerCase();

  if (cleanType.includes('console') || cleanType.includes('gsc') || cleanType.includes('google_search_console')) {
    return `<span class="badge-gsc-data">📊 ${customLabel || 'Google Search Console'}</span>`;
  }
  if (cleanType.includes('import') || cleanType.includes('csv')) {
    return `<span class="badge-import-data">📁 ${customLabel || 'Imported Data'}</span>`;
  }
  if (cleanType.includes('serp') || cleanType.includes('rank_tracker')) {
    return `<span class="badge-gsc-data">🎯 ${customLabel || 'SERP Provider'}</span>`;
  }
  if (cleanType.includes('ai')) {
    return renderAIBadge('analysis', customLabel);
  }
  if (cleanType.includes('unavailable') || cleanType.includes('none')) {
    return `<span class="badge-import-data">🚫 ${customLabel || 'Unavailable'}</span>`;
  }

  return `<span class="badge-crawled-data">🕸️ ${customLabel || 'Crawled Data'}</span>`;
}

window.toggleEvidencePanel = (panelId) => {
  const panel = document.getElementById(panelId);
  const btn = document.getElementById(`btn-${panelId}`);
  if (!panel) return;

  const isHidden = panel.style.display === 'none' || !panel.style.display;
  panel.style.display = isHidden ? 'block' : 'none';
  if (btn) {
    btn.innerHTML = isHidden 
      ? `🔍 Hide Evidence ▲` 
      : `🔍 View Evidence ▼`;
  }
};

export function renderViewEvidenceButton(evidenceItems = [], panelId = '') {
  if (!evidenceItems || evidenceItems.length === 0) return '';
  const uniqueId = panelId || `evidence-${Math.random().toString(36).substring(2, 9)}`;

  const itemsHtml = evidenceItems.map(item => {
    if (typeof item === 'string') {
      return `<li style="margin-bottom: 4px;">${item}</li>`;
    }
    const label = item.type || item.label || 'Fact';
    const val = item.value || item.url || item.metric || JSON.stringify(item);
    const source = item.source || 'Crawled Data';
    return `
      <li style="margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
        <div>
          <strong style="color: var(--text-primary); font-size: 11.5px;">${label}:</strong> 
          <span style="font-family: monospace; color: var(--text-secondary); font-size: 11.5px;">${val}</span>
        </div>
        ${renderSourceBadge('crawl', source)}
      </li>
    `;
  }).join('');

  return `
    <div style="margin-top: 10px;">
      <button id="btn-${uniqueId}" class="btn-view-evidence" onclick="window.toggleEvidencePanel('${uniqueId}')">
        🔍 View Evidence ▼
      </button>
      <div id="${uniqueId}" class="evidence-disclosure-panel" style="display: none;">
        <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.04em;">
          UNDERLYING PROJECT EVIDENCE (GROUNDING DATA)
        </div>
        <ul style="margin: 0; padding-left: 16px; list-style-type: square; color: var(--text-secondary);">
          ${itemsHtml}
        </ul>
      </div>
    </div>
  `;
}
