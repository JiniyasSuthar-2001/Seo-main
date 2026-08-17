import { dashboardService } from '../services/dashboard.js';
import { crawlService } from '../services/crawlService.js';
import { aiService } from '../services/aiService.js';

window.startCrawl = async () => {
    const urlInput = document.getElementById('project-url');
    const url = urlInput ? urlInput.value : 'https://uisdigital.com/';
    
    const progressDiv = document.getElementById('crawl-progress');
    if (progressDiv) progressDiv.style.display = 'block';
    
    try {
        const data = await crawlService.startCrawl('1', url);
        
        const interval = setInterval(async () => {
            try {
                const statusData = await crawlService.getCrawlStatus('1', data.session_id);
                
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
                    alert('Crawl failed. Please check the backend logs.');
                    if (progressDiv) progressDiv.style.display = 'none';
                }
            } catch (pollError) {
                console.error("Status polling failed:", pollError);
                clearInterval(interval);
            }
        }, 1000);
        
    } catch(e) {
        alert("Backend unavailable. Please check that the server is running on port 8000.");
    }
};

window.askAIChat = async () => {
    const input = document.getElementById('ai-chat-input');
    const responseBox = document.getElementById('ai-chat-response');
    if (!input || !input.value.trim()) return;
    
    responseBox.style.display = 'block';
    responseBox.innerHTML = '<span style="color: var(--text-secondary);">Analyzing project crawl evidence...</span>';
    
    try {
        const res = await aiService.askChat('1', input.value.trim());
        responseBox.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 6px; color: var(--primary);">AI SEO Analyst Answer:</div>
            <div style="line-height: 1.6; font-size: 14px;">${res.answer.replace(/\n/g, '<br/>')}</div>
        `;
    } catch(e) {
        responseBox.innerHTML = '<span style="color: #ef4444;">AI Analyst unavailable. Ensure backend is running.</span>';
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
          const summary = await dashboardService.getSummary('1');
          
          if (summary.status === 'empty' || !summary.latest_crawl) {
              // BEAUTIFUL INTENTIONAL EMPTY STATE DASHBOARD
              this.element.innerHTML = `
                <!-- HERO BANNER -->
                <div class="hero-banner">
                    <div>
                        <div class="hero-title">Welcome to SEO Intelligence</div>
                        <div class="hero-subtitle">Analyze, monitor, and optimize your website search performance with evidence-backed SEO data.</div>
                        <div style="display: flex; gap: 12px; margin-top: 20px;">
                            <button class="btn btn-primary" onclick="window.startCrawl()">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polygon points="10 8 16 12 10 16 10 8"></polygon></svg>
                                <span>Analyze Website</span>
                            </button>
                            <a href="/import" data-link class="btn btn-secondary">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
                                <span>Import Datasets</span>
                            </a>
                        </div>
                    </div>
                </div>

                <!-- 6 KPI CARDS (DATA-FIRST EMPTY STATE) -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px;">
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Crawled Pages</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">No crawl data yet</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Total Issues</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">No audit run yet</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Critical Issues</span></div>
                        <div class="kpi-value" style="color: var(--text-primary);">0</div>
                        <div class="kpi-status">No data yet</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Warnings</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">No data yet</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Internal Links</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">Link graph unmapped</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Keywords Tracked</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">No dataset imported</div>
                    </div>
                </div>

                <!-- ELEGANT EMPTY STATE CARD -->
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                    </div>
                    <div class="empty-state-title">No Crawl Data Available</div>
                    <div class="empty-state-desc">Start your first website crawl to discover pages, extract HTML metadata, identify technical SEO findings, and build your internal link graph.</div>
                    <button class="btn btn-primary" onclick="window.startCrawl()">Start Website Crawl</button>
                    
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
              
              // Load AI insights for project
              let aiInsightsHtml = '';
              try {
                  const aiRes = await aiService.getInsights('1');
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
                        <div class="hero-title">SEO Overview: ${crawl.website}</div>
                        <div class="hero-subtitle">Snapshot analyzed on <strong>${crawl.timestamp}</strong>. All data backed by actual crawl evidence.</div>
                        <div style="display: flex; gap: 12px; margin-top: 16px;">
                            <button class="btn btn-primary btn-sm" onclick="window.startCrawl()">Run New Crawl</button>
                            <a href="/pages" data-link class="btn btn-secondary btn-sm">View Pages</a>
                        </div>
                    </div>
                </div>
                
                <!-- 6 REAL KPI CARDS -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px;">
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Crawled Pages</span></div>
                        <div class="kpi-value">${crawl.pages_crawled}</div>
                        <div class="kpi-status">Discovered & parsed</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Total Issues</span></div>
                        <div class="kpi-value">${crawl.total_issues || 0}</div>
                        <div class="kpi-status">Evidence-backed findings</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Critical Issues</span></div>
                        <div class="kpi-value" style="color: ${crawl.critical_issues > 0 ? 'var(--critical)' : 'inherit'};">${crawl.critical_issues || 0}</div>
                        <div class="kpi-status">Requires immediate fix</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Warnings</span></div>
                        <div class="kpi-value" style="color: ${crawl.warning_issues > 0 ? 'var(--warning)' : 'inherit'};">${crawl.warning_issues || 0}</div>
                        <div class="kpi-status">Audit recommendations</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Internal Links</span></div>
                        <div class="kpi-value">${crawl.internal_links_count || 0}</div>
                        <div class="kpi-status">Mapped relationships</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-header"><span class="kpi-label">Keywords Tracked</span></div>
                        <div class="kpi-value">0</div>
                        <div class="kpi-status">Import CSV dataset</div>
                    </div>
                </div>

                ${aiInsightsHtml}

                <!-- INTERACTIVE AI ANALYST PANEL -->
                <div class="card" style="padding: 24px; margin-top: 32px; background: linear-gradient(to right, var(--bg-card), var(--bg-subtle));">
                    <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">AI SEO Analyst Assistant</h2>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 16px;">Ask questions directly against your actual website crawl evidence and technical audit findings.</p>
                    <div style="display: flex; gap: 12px;">
                        <input id="ai-chat-input" type="text" placeholder="e.g. Which pages have critical technical issues?" style="flex: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px;" onkeypress="if(event.key==='Enter') window.askAIChat()">
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
              `;
          }
      } catch (e) {
          this.element.innerHTML = `<div class="card" style="padding: 24px; color: red;">Failed to load dashboard data. Ensure backend is running.</div>`;
      }
  }
}
