import { dashboardService } from '../services/dashboard.js';
import { crawlService } from '../services/crawlService.js';
import { aiService } from '../services/aiService.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { API_BASE_URL } from '../config/api.js';

window.startCrawl = async () => {
    const selectedProj = projectStore.getSelectedProject();
    const urlInput = document.getElementById('project-url');
    const url = urlInput ? urlInput.value : (selectedProj ? selectedProj.domain || selectedProj.url : null);
    
    if (!url) {
        alert("Please enter a valid website URL to crawl.");
        return;
    }

    const progressDiv = document.getElementById('crawl-progress');
    if (progressDiv) progressDiv.style.display = 'block';
    
    try {
        const projectId = selectedProj ? selectedProj.id : null;
        const data = await crawlService.startCrawl(projectId, url);
        
        const interval = setInterval(async () => {
            try {
                const statusData = await crawlService.getCrawlStatus(projectId, data.session_id);
                
                const statsEl = document.getElementById('crawl-stats');
                if (statsEl) statsEl.innerText = `${statusData.pages_crawled} / ${statusData.pages_discovered} pages`;
                
                if (statusData.pages_discovered > 0) {
                    const barEl = document.getElementById('crawl-bar');
                    if (barEl) barEl.style.width = `${(statusData.pages_crawled / statusData.pages_discovered) * 100}%`;
                }
                
                if (statusData.status === 'completed') {
                    clearInterval(interval);
                    
                    const statsEl = document.getElementById('crawl-stats');
                    if (statsEl) statsEl.innerText = "Crawl Complete!";
                    const barEl = document.getElementById('crawl-bar');
                    if (barEl) barEl.style.backgroundColor = 'var(--success)';
                    
                    alert('Crawl finished successfully! Dashboard will now refresh.');
                    
                    setTimeout(() => {
                        if (progressDiv) progressDiv.style.display = 'none';
                        window.location.reload();
                    }, 1500);
                    
                } else if (statusData.status === 'failed') {
                    clearInterval(interval);
                    alert('Crawl failed. Please check backend terminal logs for error details.');
                    if (progressDiv) progressDiv.style.display = 'none';
                }
            } catch (pollError) {
                console.error("Status polling failed:", pollError);
                clearInterval(interval);
            }
        }, 1000);
        
    } catch(e) {
        alert("Backend API unavailable. Please ensure the server is running on http://127.0.0.1:8020.");
    }
};

window.createFirstProject = async (e) => {
    e.preventDefault();
    const name = document.getElementById('new-proj-name').value.trim();
    const domain = document.getElementById('new-proj-domain').value.trim();

    if (!name || !domain) {
        alert("Please enter project name and website URL.");
        return;
    }

    try {
        await projectStore.createProject({ name, url: domain });
        window.location.reload();
    } catch (err) {
        alert("Failed to create project. Please check backend API server status.");
    }
};

window.askAIChat = async () => {
    const input = document.getElementById('ai-chat-input');
    const responseBox = document.getElementById('ai-chat-response');
    if (!input || !input.value.trim()) return;
    
    responseBox.style.display = 'block';
    responseBox.innerHTML = '<span style="color: var(--text-secondary);">Analyzing project crawl evidence...</span>';
    
    try {
        const projectId = projectStore.getSelectedProjectId();
        const res = await aiService.askChat(projectId, input.value.trim());
        responseBox.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 6px; color: var(--primary);">AI SEO Analyst Answer:</div>
            <div style="line-height: 1.6; font-size: 14px;">${res.answer.replace(/\n/g, '<br/>')}</div>
        `;
    } catch(e) {
        responseBox.innerHTML = '<span style="color: #ef4444;">AI Analyst unavailable. Ensure backend server is running on port 8020.</span>';
    }
};

export class Dashboard {
  constructor() {
      this.element = document.createElement('div');
  }
  
  render() {
      this.element.innerHTML = `
        <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
            Loading Dashboard...
        </div>
      `;
      return this.element;
  }

  async mounted() {
      try {
          await projectStore.fetchProjects();
          const selectedProj = projectStore.getSelectedProject();

          if (!selectedProj) {
              this.element.innerHTML = `
                <div class="hero-banner">
                    <div>
                        <div class="hero-title">Welcome to SEO Intelligence</div>
                        <div class="hero-subtitle">Create your first website project to begin automated crawlers, technical audits, and AI analysis.</div>
                    </div>
                </div>

                <div class="card" style="padding: 32px; max-width: 560px; margin: 0 auto;">
                    <h3 style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Create Your First Project</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 24px;">Enter your target business or website details to set up your workspace.</p>
                    <form onsubmit="window.createFirstProject(event)">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px;">Project Name</label>
                            <input id="new-proj-name" type="text" placeholder="e.g. Acme Corporation" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-card); color: var(--text-primary);">
                        </div>
                        <div style="margin-bottom: 24px;">
                            <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px;">Website URL</label>
                            <input id="new-proj-domain" type="url" placeholder="https://example.com/" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-card); color: var(--text-primary);">
                        </div>
                        <button type="submit" class="btn btn-primary" style="width: 100%;">Create Project Workspace</button>
                    </form>
                </div>
              `;
              return;
          }

          const summary = await dashboardService.getSummary(selectedProj.id);
          const targetUrl = selectedProj.domain || selectedProj.url || 'https://example.com/';
          
          if (summary.status === 'empty' || !summary.latest_crawl) {
              this.element.innerHTML = `
                <!-- HERO BANNER -->
                <div class="hero-banner">
                    <div>
                        <div class="hero-title">Project Workspace: ${selectedProj.name}</div>
                        <div class="hero-subtitle">Target domain: <strong>${targetUrl}</strong>. Run your first website crawl to generate SEO findings.</div>
                        <div style="display: flex; gap: 12px; margin-top: 20px;">
                            <button class="btn btn-primary" onclick="window.startCrawl()">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polygon points="10 8 16 12 10 16 10 8"></polygon></svg>
                                <span>Analyze Website (${targetUrl})</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 6 KPI CARDS (INTERACTIVE DATA-FIRST NAVIGATION) -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px;">
                    <a href="/pages" data-link class="kpi-card interactive-kpi" title="Click to view Crawled Pages">
                        <div class="kpi-header"><span class="kpi-label">Crawled Pages</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">No crawl data yet &rarr;</div>
                    </a>
                    <a href="/technical" data-link class="kpi-card interactive-kpi" title="Click to view All Technical Issues">
                        <div class="kpi-header"><span class="kpi-label">Total Issues</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">No audit run yet &rarr;</div>
                    </a>
                    <a href="/technical?severity=critical" data-link class="kpi-card interactive-kpi" title="Click to view Critical Issues filter">
                        <div class="kpi-header"><span class="kpi-label">Critical Issues</span></div>
                        <div class="kpi-value" style="color: var(--text-primary);">0</div>
                        <div class="kpi-status">No data yet &rarr;</div>
                    </a>
                    <a href="/technical?severity=warning" data-link class="kpi-card interactive-kpi" title="Click to view Warning Issues filter">
                        <div class="kpi-header"><span class="kpi-label">Warnings</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">No data yet &rarr;</div>
                    </a>
                    <a href="/internal-links" data-link class="kpi-card interactive-kpi" title="Click to view Internal Link Graph">
                        <div class="kpi-header"><span class="kpi-label">Internal Links</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">Link graph unmapped &rarr;</div>
                    </a>
                    <a href="/keywords" data-link class="kpi-card interactive-kpi" title="Click to view Keywords Tracked">
                        <div class="kpi-header"><span class="kpi-label">Keywords Tracked</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">No dataset imported &rarr;</div>
                    </a>
                </div>

                <!-- ELEGANT EMPTY STATE CARD -->
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                    </div>
                    <div class="empty-state-title">No Crawl Data Available</div>
                    <div class="empty-state-desc">Start your first website crawl to discover pages, extract HTML metadata, identify technical SEO findings, and build your internal link graph for <strong>${targetUrl}</strong>.</div>
                    
                    <div style="display: flex; gap: 12px; justify-content: center; max-width: 440px; margin: 0 auto 16px;">
                        <input id="project-url" type="url" value="${targetUrl}" style="flex: 1; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-card); color: var(--text-primary);">
                        <button class="btn btn-primary" onclick="window.startCrawl()">Start Crawl</button>
                    </div>

                    <div id="crawl-progress" style="display: none; margin: 24px auto 0; max-width: 440px; text-align: left;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
                            <span>Crawling...</span>
                            <span id="crawl-stats">0 pages</span>
                        </div>
                        <div style="width: 100%; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden;">
                            <div id="crawl-bar" style="width: 0%; height: 100%; background: var(--primary); transition: width 0.3s ease;"></div>
                        </div>
                    </div>
                </div>
              `;
          } else {
              const crawl = summary.latest_crawl;
              
              let aiInsightsHtml = '';
              try {
                  const aiRes = await aiService.getInsights(selectedProj.id);
                  if (aiRes.insights && aiRes.insights.length > 0) {
                      let cards = aiRes.insights.map(ins => `
                          <div class="card" style="padding: 20px; border-left: 4px solid var(--primary);">
                              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                  <span style="font-weight: 600; font-size: 15px;">${ins.finding}</span>
                                  <span class="badge badge-info">
                                      AI Confidence: ${(ins.confidence * 100).toFixed(0)}%
                                  </span>
                              </div>
                              <p style="font-size: 14px; color: var(--text-primary); margin-bottom: 8px;">${ins.impact}</p>
                              <div style="font-size: 13px; color: var(--text-secondary); background: var(--bg-subtle); padding: 10px 12px; border-radius: 6px;">
                                  <strong>AI Recommendation:</strong> ${ins.recommendation}
                              </div>
                          </div>
                      `).join('');
                      
                      aiInsightsHtml = `
                          <div style="margin-top: 32px;">
                              <h2 style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">Structured AI SEO Insights</h2>
                              <div style="display: flex; flex-direction: column; gap: 16px;">
                                  ${cards}
                              </div>
                          </div>
                      `;
                  }
              } catch (aierr) {
                  console.error("AI Insights load error:", aierr);
              }

              this.element.innerHTML = `
                <!-- HERO BANNER WITH RECENT CRAWL -->
                <div class="hero-banner">
                    <div>
                        <div class="hero-title">SEO Overview: ${selectedProj.name} (${crawl.website})</div>
                        <div class="hero-subtitle">Snapshot analyzed on <strong>${crawl.timestamp}</strong>. All data backed by actual crawl evidence.</div>
                        <div style="display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap;">
                            <button class="btn btn-primary btn-sm" onclick="window.startCrawl()">Run New Crawl</button>
                            <a href="${API_BASE_URL}/api/projects/${selectedProj.id}/report.pdf" target="_blank" class="btn btn-secondary btn-sm">Download PDF Report</a>
                            <a href="${API_BASE_URL}/api/projects/${selectedProj.id}/export" target="_blank" class="btn btn-secondary btn-sm">Download Project Data</a>
                            <a href="/pages" data-link class="btn btn-secondary btn-sm">View Pages</a>
                        </div>
                    </div>
                </div>
                
                <!-- 6 REAL INTERACTIVE KPI CARDS -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px;">
                    <a href="/pages" data-link class="kpi-card interactive-kpi" title="Click to open Crawled Pages view">
                        <div class="kpi-header"><span class="kpi-label">Crawled Pages</span></div>
                        <div class="kpi-value">${crawl.pages_crawled}</div>
                        <div class="kpi-status">Discovered & parsed &rarr;</div>
                    </a>
                    <a href="/technical" data-link class="kpi-card interactive-kpi" title="Click to open Technical SEO view">
                        <div class="kpi-header"><span class="kpi-label">Total Issues</span></div>
                        <div class="kpi-value">${crawl.total_issues || 0}</div>
                        <div class="kpi-status">Evidence-backed findings &rarr;</div>
                    </a>
                    <a href="/technical?severity=critical" data-link class="kpi-card interactive-kpi" title="Click to view Critical Technical Issues">
                        <div class="kpi-header"><span class="kpi-label">Critical Issues</span></div>
                        <div class="kpi-value" style="color: ${crawl.critical_issues > 0 ? 'var(--critical)' : 'inherit'};">${crawl.critical_issues || 0}</div>
                        <div class="kpi-status">Requires immediate fix &rarr;</div>
                    </a>
                    <a href="/technical?severity=warning" data-link class="kpi-card interactive-kpi" title="Click to view Technical Warnings">
                        <div class="kpi-header"><span class="kpi-label">Warnings</span></div>
                        <div class="kpi-value" style="color: ${crawl.warning_issues > 0 ? 'var(--warning)' : 'inherit'};">${crawl.warning_issues || 0}</div>
                        <div class="kpi-status">Audit recommendations &rarr;</div>
                    </a>
                    <a href="/internal-links" data-link class="kpi-card interactive-kpi" title="Click to open Internal Links graph view">
                        <div class="kpi-header"><span class="kpi-label">Internal Links</span></div>
                        <div class="kpi-value">${crawl.internal_links_count || 0}</div>
                        <div class="kpi-status">Mapped relationships &rarr;</div>
                    </a>
                    <a href="/keywords" data-link class="kpi-card interactive-kpi" title="Click to open Keywords dataset view">
                        <div class="kpi-header"><span class="kpi-label">Keywords Tracked</span></div>
                        <div class="kpi-value">${selectedProj.keywords_count || crawl.keywords_count || 0}</div>
                        <div class="kpi-status">${(selectedProj.keywords_count || crawl.keywords_count) > 0 ? 'Extracted topics & keywords &rarr;' : 'Import CSV dataset &rarr;'}</div>
                    </a>
                </div>

                ${aiInsightsHtml}

                <!-- INTERACTIVE AI ANALYST PANEL -->
                <div class="card" style="padding: 24px; margin-top: 32px; background: linear-gradient(to right, var(--bg-card), var(--bg-subtle));">
                    <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">AI SEO Analyst Assistant</h2>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 16px;">Ask questions directly against your actual website crawl evidence and technical audit findings for ${selectedProj.name}.</p>
                    <div style="display: flex; gap: 12px;">
                        <input id="ai-chat-input" type="text" placeholder="e.g. Which pages have critical technical issues?" style="flex: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-card); color: var(--text-primary);" onkeypress="if(event.key==='Enter') window.askAIChat()">
                        <button class="btn btn-primary" onclick="window.askAIChat()">Ask AI Analyst</button>
                    </div>
                    <div id="ai-chat-response" style="display: none; margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                </div>
                
                <div id="crawl-progress" style="display: none; margin-top: 24px; max-width: 400px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
                        <span>Crawling...</span>
                        <span id="crawl-stats">0 pages</span>
                    </div>
                    <div style="width: 100%; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden;">
                        <div id="crawl-bar" style="width: 0%; height: 100%; background: var(--primary); transition: width 0.3s ease;"></div>
                    </div>
                </div>

                <style>
                    .interactive-kpi {
                        text-decoration: none;
                        display: block;
                        transition: all 0.2s ease;
                    }
                    .interactive-kpi:hover {
                        transform: translateY(-2px);
                        border-color: var(--primary) !important;
                        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
                    }
                </style>
              `;
          }
      } catch (e) {
          if (e.isNetworkError || apiClient.status === 'OFFLINE') {
              renderBackendOfflineState(this.element, "Unable to connect to backend API server at http://127.0.0.1:8020.", () => this.mounted());
          } else {
              renderFeatureErrorState(this.element, "Dashboard Summary Error", e.message || "Failed to load dashboard metrics.", () => this.mounted());
          }
      }
  }
}
