'use strict';

const CHART_COLORS = [
  '#7c6cf4',
  '#ff8c42',
  '#ff5f7e',
  '#4f7ef7',
  '#00d9a6',
  '#f6c84f',
];

let compareChart = null;
let activePeriod = '1mo';
let activeOptionTab = 'calls';
let currentOptionsData = null;
let currentOptionsTicker = null;
let focusTicker = null;
let refreshTimer = null;
const REFRESH_INTERVAL = 60000;

document.addEventListener('DOMContentLoaded', () => {
  const tickers = window.BQ?.tickers || ['NVDA', 'AMD', 'TSLA', 'JPM'];
  focusTicker = tickers[0];

  setMarketStatus();
  drawAllSparklines();
  initCompareChart();
  loadCompareData(activePeriod);
  setupTimeframeTabs();

  const page = window.BQ?.activePage || 'dashboard';

  if (page === 'dashboard') {
    setFocusTicker(tickers[0]);
    renderTickerTags(tickers);
  }

  if (page === 'compare') {
    renderCompareTable(tickers);
    renderTickerTags(tickers);
    loadComparePage(tickers);
  }

  refreshTimer = setInterval(() => refreshAll(true), REFRESH_INTERVAL);
});

function setMarketStatus() {
  const badge = document.getElementById('market-badge');
  const label = document.getElementById('market-status-text');
  if (!badge || !label) return;

  const now = new Date();
  const estOffset = -5;
  const est = new Date(now.getTime() + (now.getTimezoneOffset() + estOffset * 60) * 60000);
  const day = est.getDay();
  const h = est.getHours();
  const m = est.getMinutes();
  const mins = h * 60 + m;

  const isWeekday = day >= 1 && day <= 5;
  const isOpen = isWeekday && mins >= 570 && mins < 960;

  if (isOpen) {
    badge.classList.remove('closed');
    label.textContent = 'Market Open';
  } else {
    badge.classList.add('closed');
    label.textContent = isWeekday ? 'After Hours' : 'Market Closed';
  }
}

function drawAllSparklines() {
  const data = window.BQ_SPARKLINES || {};
  Object.entries(data).forEach(([ticker, prices]) => {
    drawSparkline(ticker, prices);
  });
}

function drawSparkline(ticker, prices) {
  const canvas = document.getElementById(`spark-${ticker}`);
  if (!canvas || !prices || prices.length < 2) return;

  const ctx = canvas.getContext('2d');
  const w = canvas.offsetWidth || 60;
  const h = canvas.offsetHeight || 28;
  canvas.width = w * window.devicePixelRatio;
  canvas.height = h * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const isPositive = prices[prices.length - 1] >= prices[0];
  const color = isPositive ? '#00d9a6' : '#ff5f7e';

  const xStep = w / (prices.length - 1);
  const points = prices.map((p, i) => ({
    x: i * xStep,
    y: h - ((p - min) / range) * (h - 8) - 4,
  }));

  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, isPositive ? 'rgba(0,217,166,0.2)' : 'rgba(255,95,126,0.2)');
  grad.addColorStop(1, 'rgba(0,0,0,0)');

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  points.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(w, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  points.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.stroke();
}

function drawHeroSparkline(prices, isPositive) {
  const canvas = document.getElementById('hero-sparkline');
  if (!canvas || !prices || prices.length < 2) return;

  const ctx = canvas.getContext('2d');
  const w = canvas.offsetWidth || 400;
  const h = canvas.offsetHeight || 80;
  canvas.width = w * window.devicePixelRatio;
  canvas.height = h * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const color = isPositive ? '#00d9a6' : '#ff5f7e';

  const xStep = w / (prices.length - 1);
  const points = prices.map((p, i) => ({
    x: i * xStep,
    y: h - ((p - min) / range) * (h - 8) - 4,
  }));

  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, isPositive ? 'rgba(0,217,166,0.25)' : 'rgba(255,95,126,0.25)');
  grad.addColorStop(1, 'rgba(0,0,0,0)');

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  points.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(w, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  points.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.stroke();
}

function initCompareChart() {
  const canvas = document.getElementById('compare-chart');
  if (!canvas) return;

  Chart.defaults.color = '#8fa3b8';
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";

  compareChart = new Chart(canvas, {
    type: 'line',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'top',
          align: 'start',
          labels: {
            boxWidth: 12, boxHeight: 12,
            borderRadius: 4, useBorderRadius: true,
            padding: 16, font: { size: 12, weight: '600' },
          },
        },
        tooltip: {
          backgroundColor: '#131920',
          borderColor: '#1e2d3d',
          borderWidth: 1,
          padding: 10,
          titleFont: { size: 12 },
          bodyFont: { size: 13, family: "'JetBrains Mono', monospace" },
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: '#1e2d3d', drawBorder: false },
          ticks: { maxTicksLimit: 8, maxRotation: 0 },
        },
        y: {
          grid: { color: '#1e2d3d', drawBorder: false },
          ticks: {
            callback: v => v.toFixed(1),
          },
        },
      },
      elements: {
        line: { tension: 0.35, borderWidth: 2 },
        point: { radius: 0, hitRadius: 20, hoverRadius: 4 },
      },
      animation: { duration: 600 },
    },
  });
}

function loadCompareData(period) {
  const tickers = window.BQ?.tickers || ['NVDA'];
  const params = tickers.map(t => `t=${t}`).join('&') + `&period=${period}`;

  fetch(`/api/compare/?${params}`)
    .then(r => r.json())
    .then(data => {
      if (!compareChart) return;

      const firstTicker = Object.keys(data)[0];
      if (!firstTicker) return;

      const labels = data[firstTicker]?.labels || [];

      compareChart.data.labels = labels;
      compareChart.data.datasets = Object.entries(data).map(([ticker, d], i) => ({
        label: ticker,
        data: d.normalised || [],
        borderColor: CHART_COLORS[i % CHART_COLORS.length],
        backgroundColor: hexToRgba(CHART_COLORS[i % CHART_COLORS.length], 0.08),
        fill: false,
      }));

      compareChart.update();
    })
    .catch(err => console.warn(err));
}

function setupTimeframeTabs() {
  const container = document.getElementById('tf-tabs');
  if (!container) return;

  container.addEventListener('click', e => {
    const btn = e.target.closest('.tf-tab');
    if (!btn) return;
    container.querySelectorAll('.tf-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activePeriod = btn.dataset.period;
    loadCompareData(activePeriod);
  });
}

function loadDrivers(ticker) {
  const list = document.getElementById('driver-list');
  if (!list) return;

  fetch(`/api/stock/${ticker}/`)
    .then(r => r.json())
    .then(data => {
      const drivers = data.drivers || [];
      if (!drivers.length) {
        list.innerHTML = `<div class="loading-overlay" style="color:var(--negative)">No driver data</div>`;
        return;
      }
      list.innerHTML = drivers.map(d => `
        <div class="driver-row">
          <div>
            <div class="driver-label">${d.name}</div>
            <div class="driver-evidence">${d.evidence}</div>
          </div>
          <div class="bar-track"><div class="bar-fill" style="width:${d.value}%"></div></div>
          <div class="driver-pct">${d.value}%</div>
        </div>
      `).join('');
    })
    .catch(() => {
      list.innerHTML = `<div class="loading-overlay" style="color:var(--negative)">Failed to load</div>`;
    });
}

function loadMetrics(ticker) {
  const grid = document.getElementById('metrics-grid');
  if (!grid) return;

  fetch(`/api/stock/${ticker}/`)
    .then(r => r.json())
    .then(data => {
      const metrics = data.intelligence_metrics || [];
      if (!metrics.length) {
        grid.innerHTML = `<div class="loading-overlay" style="grid-column:1/-1;color:var(--negative)">No data</div>`;
        return;
      }
      grid.innerHTML = metrics.map(m => {
        const tier = m.value >= 66 ? 'gauge-high' : m.value >= 33 ? 'gauge-mid' : 'gauge-low';
        return `
          <div class="metric-card ${tier}">
            <div class="metric-label">${m.label}</div>
            <div class="metric-value">${m.value}</div>
            <div class="mini-gauge"><div class="mini-fill" style="width:${m.value}%"></div></div>
            <div class="metric-note">${m.note}</div>
          </div>
        `;
      }).join('');
    })
    .catch(() => {
      grid.innerHTML = `<div class="loading-overlay" style="grid-column:1/-1;color:var(--negative)">Failed to load</div>`;
    });
}

function loadFocusCard(ticker) {
  const heroCard = document.getElementById('hero-card');
  const suggestionCard = document.getElementById('suggestion-card');

  if (heroCard) {
    heroCard.style.opacity = '0.6';
  }
  if (suggestionCard) {
    suggestionCard.style.opacity = '0.6';
  }

  fetch(`/api/stock/${ticker}/`)
    .then(r => r.json())
    .then(d => {
      if (heroCard) {
        heroCard.style.opacity = '1';
        const changeClass = d.is_positive ? 'pos' : 'neg';
        const changeColorClass = d.is_positive ? 'positive' : 'negative';
        
        heroCard.innerHTML = `
          <div class="hero-ticker-row">
            <div class="hero-ticker-info">
              <div class="hero-icon" style="background: var(--${d.color})">${d.ticker.substring(0, 2)}</div>
              <div>
                <div class="hero-ticker">${d.ticker}</div>
                <div class="hero-name">${d.name}</div>
              </div>
            </div>
            <span class="change-badge ${changeClass}" id="hero-badge">${d.change_pct}%</span>
          </div>
          <div class="hero-price" id="hero-price">$${d.price}</div>
          <div class="hero-change-row">
            <span class="hero-change ${changeColorClass}" id="hero-change-text">
              ${d.change_abs} today
            </span>
            <span class="hero-driver-tag" id="hero-driver-tag">
              Driver: ${d.primary_driver}
            </span>
          </div>
          <canvas class="hero-chart" id="hero-sparkline"></canvas>
          <div class="hero-meta">
            <div class="hero-meta-item">
              <span class="hero-meta-label">Market Cap</span>
              <span class="hero-meta-value" id="hero-mc">${d.market_cap}</span>
            </div>
            <div class="hero-meta-item">
              <span class="hero-meta-label">Volume</span>
              <span class="hero-meta-value" id="hero-vol">${d.volume}</span>
            </div>
            <div class="hero-meta-item">
              <span class="hero-meta-label">P/E Ratio</span>
              <span class="hero-meta-value" id="hero-pe">${d.pe_ratio || '—'}</span>
            </div>
            <div class="hero-meta-item">
              <span class="hero-meta-label">Beta</span>
              <span class="hero-meta-value" id="hero-beta">${d.beta}</span>
            </div>
          </div>
        `;
        if (d.sparkline && d.sparkline.length) {
          drawHeroSparkline(d.sparkline, d.is_positive);
        }
      }

      if (suggestionCard) {
        suggestionCard.style.opacity = '1';
        const s = d.suggestion || {};
        suggestionCard.className = `suggestion-card span-2 ${s.stance || 'neutral'}`;
        suggestionCard.innerHTML = `
          <div class="suggestion-badge ${s.stance || 'neutral'}">${s.action || 'Hold'}</div>
          <div class="suggestion-headline">${s.headline || 'Consolidating'}</div>
          <div class="suggestion-detail">${s.detail || 'No major catalyst.'}</div>
          <div class="suggestion-action">
            <div class="suggestion-action-icon">💡</div>
            <div>
              <div class="suggestion-action-label">What to do</div>
              <div class="suggestion-action-text">${s.what_to_do || 'Hold steady.'}</div>
            </div>
          </div>
        `;
      }
    })
    .catch(err => {
      console.error(err);
      if (heroCard) heroCard.style.opacity = '1';
      if (suggestionCard) suggestionCard.style.opacity = '1';
    });
}

function setFocusTicker(ticker) {
  focusTicker = ticker;
  loadFocusCard(ticker);
  loadNews(ticker);
  loadDrivers(ticker);
  loadMetrics(ticker);
  loadOptions(ticker, null);

  document.querySelectorAll('.watchlist-item').forEach(item => {
    item.classList.remove('active-item');
  });
  const activeItem = document.getElementById(`watchlist-${ticker}`);
  if (activeItem) {
    activeItem.classList.add('active-item');
  }
}

function loadNews(ticker) {
  const list = document.getElementById('news-list');
  if (!list) return;

  fetch(`/api/news/${ticker}/`)
    .then(r => r.json())
    .then(data => {
      const news = data.news || [];
      if (!news.length) {
        list.innerHTML = `<div class="loading-overlay" style="color:var(--text-3)">No news available</div>`;
        return;
      }
      list.innerHTML = news.slice(0, 8).map(n => `
        <a class="news-item" href="${n.url}" target="_blank" rel="noreferrer noopener">
          <div class="news-source-icon">${(n.source || '?').substring(0, 3).toUpperCase()}</div>
          <div class="news-body">
            <div class="news-title">${escHtml(n.title)}</div>
            <div class="news-meta">
              <span>${escHtml(n.source)}</span>
              <span>${n.time_ago}</span>
            </div>
          </div>
        </a>
      `).join('');
    })
    .catch(() => {
      list.innerHTML = `<div class="loading-overlay" style="color:var(--negative)">Failed to load news</div>`;
    });
}

function loadOptions(ticker, expiry) {
  if (ticker) currentOptionsTicker = ticker;
  const t = currentOptionsTicker || (window.BQ?.tickers?.[0]) || 'NVDA';

  const summaryEl = document.getElementById('options-summary');
  const tbody = document.getElementById('options-tbody');
  const expiryEl = document.getElementById('expiry-select');
  const sentLabel = document.getElementById('options-sentiment-label');
  const sentWrap = document.getElementById('options-sentiment-bar-wrap');

  const optsSel = document.getElementById('options-ticker-select');
  if (optsSel) optsSel.value = t;

  if (summaryEl) summaryEl.innerHTML = `<div class="loading-overlay" style="grid-column:1/-1"><div class="spinner"></div></div>`;
  if (tbody) tbody.innerHTML = `<tr><td colspan="7"><div class="loading-overlay"><div class="spinner"></div></div></td></tr>`;

  const url = expiry
    ? `/api/options/${t}/?expiry=${encodeURIComponent(expiry)}`
    : `/api/options/${t}/`;

  fetch(url)
    .then(r => r.json())
    .then(data => {
      currentOptionsData = data;

      if (data.error) {
        if (summaryEl) summaryEl.innerHTML = `<div class="loading-overlay" style="grid-column:1/-1;color:var(--negative)">${escHtml(data.error)}</div>`;
        return;
      }

      if (expiryEl && data.available_expiries) {
        expiryEl.innerHTML = data.available_expiries.map(e =>
          `<option value="${e}" ${e === data.expiry ? 'selected' : ''}>${e}</option>`
        ).join('');
      }

      const s = data.summary || {};
      if (summaryEl) {
        summaryEl.style.display = 'grid';
        summaryEl.innerHTML = `
          <div class="options-stat">
            <div class="options-stat-label">Put/Call Ratio</div>
            <div class="options-stat-value" style="color:${s.put_call_ratio < 0.7 ? 'var(--positive)' : s.put_call_ratio > 1.2 ? 'var(--negative)' : 'var(--warning)'}">
              ${s.put_call_ratio}
            </div>
          </div>
          <div class="options-stat">
            <div class="options-stat-label">Sentiment</div>
            <div class="options-stat-value" style="color:${s.sentiment === 'Bullish' ? 'var(--positive)' : s.sentiment === 'Bearish' ? 'var(--negative)' : 'var(--warning)'}">
              ${s.sentiment || '—'}
            </div>
          </div>
          <div class="options-stat">
            <div class="options-stat-label">Call OI</div>
            <div class="options-stat-value" style="color:var(--positive)">${fmtNum(s.call_oi)}</div>
          </div>
          <div class="options-stat">
            <div class="options-stat-label">Put OI</div>
            <div class="options-stat-value" style="color:var(--negative)">${fmtNum(s.put_oi)}</div>
          </div>
        `;
      }

      if (sentWrap) {
        sentWrap.style.display = 'block';
        const callBar = document.getElementById('calls-bar');
        const callLbl = document.getElementById('call-label');
        const putLbl = document.getElementById('put-label');
        if (callBar) callBar.style.width = `${s.call_pct || 50}%`;
        if (callLbl) callLbl.textContent = `Calls ${s.call_pct || 0}%`;
        if (putLbl) putLbl.textContent = `Puts ${s.put_pct || 0}%`;
      }

      if (sentLabel) sentLabel.textContent = s.sentiment || '';

      const title = document.getElementById('options-panel-title');
      if (title) title.textContent = `Options Chain — ${t} (${data.expiry})`;

      renderOptionTable(activeOptionTab);
    })
    .catch(err => {
      if (summaryEl) summaryEl.innerHTML = `<div class="loading-overlay" style="grid-column:1/-1;color:var(--negative)">Error: ${err.message}</div>`;
    });
}

function renderOptionTable(tab) {
  const tbody = document.getElementById('options-tbody');
  if (!tbody || !currentOptionsData) return;

  const rows = currentOptionsData[tab === 'calls' ? 'calls' : 'puts'] || [];
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--text-3);padding:24px">No data for this expiry</td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map(r => `
    <tr class="${r.inTheMoney ? 'itm' : ''}">
      <td>$${r.strike.toFixed(2)}</td>
      <td>$${r.lastPrice.toFixed(2)}</td>
      <td>$${r.bid.toFixed(2)}</td>
      <td>$${r.ask.toFixed(2)}</td>
      <td>${fmtNum(r.volume)}</td>
      <td>${fmtNum(r.openInterest)}</td>
      <td>${r.impliedVolatility.toFixed(1)}%</td>
    </tr>
  `).join('');
}

function switchOptionTab(tab) {
  activeOptionTab = tab;
  document.getElementById('tab-calls')?.classList.toggle('active', tab === 'calls');
  document.getElementById('tab-puts')?.classList.toggle('active', tab === 'puts');
  renderOptionTable(tab);
}

function renderTickerTags(tickers) {
  const container = document.getElementById('ticker-tags');
  if (!container) return;

  container.innerHTML = tickers.map(t => `
    <div class="ticker-tag" data-ticker="${t}">
      ${t}
      ${tickers.length > 1 ? `<span class="remove-tag" onclick="removeTicker('${t}')" title="Remove">×</span>` : ''}
    </div>
  `).join('') + `
    <button class="add-ticker-btn" onclick="promptAddTicker()" id="add-ticker-btn">
      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
      </svg>
      Add Stock
    </button>
  `;
}

function removeTicker(ticker) {
  let tickers = window.BQ?.tickers || [];
  tickers = tickers.filter(t => t !== ticker);
  if (!tickers.length) return;
  window.BQ.tickers = tickers;
  window.location.href = `/?${tickers.map(t => `t=${t}`).join('&')}`;
}

function promptAddTicker() {
  const val = prompt('Enter stock ticker symbol (e.g. AAPL, GOOGL, META):');
  if (!val) return;
  const ticker = val.trim().toUpperCase();
  if (!ticker) return;
  const tickers = [...(window.BQ?.tickers || [])];
  if (tickers.includes(ticker)) { showToast(`${ticker} is already in your watchlist`); return; }
  if (tickers.length >= 6) { showToast('Maximum 6 stocks at once'); return; }
  tickers.push(ticker);
  window.location.href = `/?${tickers.map(t => `t=${t}`).join('&')}`;
}

function handleSearch(event) {
  event.preventDefault();
  const input = document.getElementById('ticker-input');
  const val = (input?.value || '').trim().toUpperCase();
  if (!val) return;
  const tickers = window.BQ?.tickers || [];
  if (!tickers.includes(val)) {
    tickers.push(val);
  }
  window.location.href = `/?${tickers.slice(0, 6).map(t => `t=${t}`).join('&')}`;
}

function loadComparePage(tickers) {
  const cardsRow = document.getElementById('cards-row');
  if (cardsRow) {
    cardsRow.innerHTML = `<div class="loading-overlay" style="grid-column:1/-1"><div class="spinner"></div></div>`;
    Promise.all(tickers.map(t => fetch(`/api/stock/${t}/`).then(r => r.json())))
      .then(stocks => {
        cardsRow.innerHTML = stocks.map((d, i) => buildCardHtml(d, i)).join('');
      })
      .catch(() => {
        cardsRow.innerHTML = '';
      });
  }
}

function renderCompareTable(tickers) {
  const wrap = document.getElementById('compare-table-wrap');
  if (!wrap) return;
  wrap.innerHTML = `<div class="loading-overlay"><div class="spinner"></div></div>`;

  Promise.all(tickers.map(t => fetch(`/api/stock/${t}/`).then(r => r.json())))
    .then(stocks => {
      if (!stocks.length) { wrap.innerHTML = ''; return; }
      const rows = [
        { label: 'Price', key: s => `$${s.price}` },
        { label: 'Change', key: s => `${s.change_pct}%`, color: s => s.is_positive ? 'var(--positive)' : 'var(--negative)' },
        { label: 'Market Cap', key: s => s.market_cap },
        { label: 'Volume', key: s => s.volume },
        { label: 'Beta', key: s => s.beta },
        { label: 'P/E Ratio', key: s => s.pe_ratio || '—' },
        { label: '52W High', key: s => `$${s['52w_high']}` },
        { label: '52W Low', key: s => `$${s['52w_low']}` },
        { label: 'Dividend', key: s => `${s.dividend_yield}%` },
        { label: 'Confidence', key: s => `${s.confidence}%` },
        { label: 'Sector', key: s => s.sector },
        { label: 'Driver', key: s => s.primary_driver },
      ];

      wrap.innerHTML = `
        <div style="overflow-x:auto">
          <table class="options-table" style="min-width:600px">
            <thead>
              <tr>
                <th style="text-align:left">Metric</th>
                ${stocks.map(s => `<th style="text-align:right">${s.ticker}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${rows.map(r => `
                <tr>
                  <td style="text-align:left;color:var(--text-2)">${r.label}</td>
                  ${stocks.map(s => `<td ${r.color ? `style="color:${r.color(s)}"` : ''}>${r.key(s)}</td>`).join('')}
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    })
    .catch(() => {
      wrap.innerHTML = `<div class="loading-overlay" style="color:var(--negative)">Failed to load comparison data</div>`;
    });
}

function buildCardHtml(d, i) {
  const colors = ['purple', 'orange', 'coral', 'dark'];
  const color = colors[i % 4];
  const changeClass = d.is_positive ? 'pos' : 'neg';
  return `
    <div class="stock-card ${color}" id="card-${d.ticker}">
      <div class="card-header">
        <div class="card-ticker-wrap">
          <div class="card-icon">${(d.ticker || '??').substring(0, 2)}</div>
          <div>
            <div class="card-ticker">${d.ticker}</div>
            <div class="card-name">${(d.name || '').substring(0, 22)}</div>
          </div>
        </div>
        <span class="change-badge ${changeClass}">${d.change_pct}%</span>
      </div>
      <div class="card-price" id="price-${d.ticker}">$${d.price}</div>
      <canvas class="card-sparkline" id="spark-${d.ticker}" aria-label="${d.ticker} sparkline"></canvas>
      <div class="card-meta">
        <span>Vol ${d.vol_ratio}</span>
        <span>${d.sector}</span>
      </div>
    </div>
  `;
}

function refreshAll(silent = false) {
  const btn = document.getElementById('refresh-btn');
  if (btn) btn.classList.add('spinning');

  if (!silent) showToast('Refreshing market data…');

  const tickers = window.BQ?.tickers || [];

  tickers.forEach(ticker => {
    fetch(`/api/stock/${ticker}/`)
      .then(r => r.json())
      .then(d => {
        const itemEl = document.getElementById(`watchlist-${ticker}`);
        if (itemEl) {
          const priceEl = itemEl.querySelector('.watchlist-price');
          const badgeEl = itemEl.querySelector('.watchlist-change');

          if (priceEl) {
            const prev = parseFloat(priceEl.textContent.replace('$', '').replace(',', ''));
            const curr = parseFloat(d.price.replace(',', ''));
            if (!isNaN(prev) && prev !== curr) {
              priceEl.classList.remove('price-flash-up', 'price-flash-down');
              void priceEl.offsetWidth;
              priceEl.classList.add(curr > prev ? 'price-flash-up' : 'price-flash-down');
            }
            priceEl.textContent = `$${d.price}`;
          }

          if (badgeEl) {
            badgeEl.textContent = `${d.change_pct}%`;
            badgeEl.className = `watchlist-change ${d.is_positive ? 'pos' : 'neg'}`;
          }
        }

        fetch(`/api/sparkline/${ticker}/`)
          .then(r => r.json())
          .then(sp => { if (sp.data.length) drawSparkline(ticker, sp.data); })
          .catch(() => {});
      })
      .catch(() => {});
  });

  loadCompareData(activePeriod);

  if (focusTicker) {
    setFocusTicker(focusTicker);
  }

  setMarketStatus();

  setTimeout(() => {
    if (btn) btn.classList.remove('spinning');
    if (!silent) showToast('Data updated ✓');
  }, 2000);
}

function showToast(msg, duration = 3000) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function fmtNum(n) {
  if (!n || isNaN(n)) return '—';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toString();
}

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
