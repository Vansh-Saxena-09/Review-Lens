'use strict';
// The supported deployment serves the interface and API from the same origin.
const API = '';
const $ = id => document.getElementById(id);
let batchRows = [], batchResults = [], offset = 0;
const pageSize = 10;
const percent = n => `${(Number(n) * 100).toFixed(1)}%`;
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, options) {
  const response = await fetch(API + path, options);
  let data;
  try { data = await response.json(); } catch { throw new Error(`Server returned an invalid response (${response.status}).`); }
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : Array.isArray(data.detail) ? data.detail.map(x => x.msg).join('; ') : `Request failed (${response.status}).`;
    throw new Error(detail);
  }
  return data;
}
function errorMessage(err) { return err instanceof TypeError ? 'Cannot reach the API. Start the backend and check the connection.' : err.message; }
function post(path, body) { return api(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}); }
function dateText(value) { const date = new Date(value); return Number.isNaN(date.valueOf()) ? value : date.toLocaleString(); }
function patternTag(item) { return `<span class="tag ${item.label === 'CG' ? 'cg' : ''}">${escapeHTML(item.display_label)}</span>`; }
async function loadModel() {
  try {
    const [health, model] = await Promise.all([api('/api/health'), api('/api/model')]);
    $('connection').className = `connection ${health.model_loaded ? 'online' : 'offline'}`;
    $('connection').innerHTML = `<span class="status-dot"></span> ${health.model_loaded ? 'Model available' : 'Model unavailable'}`;
    $('model-status').textContent = model.loaded ? 'Available' : 'Unavailable';
    $('model-architecture').textContent = model.architecture || 'Not available';
    $('model-version').textContent = model.model_version || 'Not available';
    $('model-limitations').innerHTML = (model.limitations || []).map(x => `<li>${escapeHTML(x)}</li>`).join('');
    // Show only metrics actually returned by the API, without inventing interpretations.
    const entries = Object.entries(model.metrics || {}).filter(([,v]) => ['string','number'].includes(typeof v));
    $('model-metrics').innerHTML = entries.length ? `<h4>Held-out evaluation and model metadata</h4><p>Scores reflect the recorded review-level test split, not guaranteed performance on new reviews.</p><dl>${entries.map(([k,v]) => `<div><dt>${escapeHTML(k.replace(/_/g,' '))}</dt><dd>${escapeHTML(v)}</dd></div>`).join('')}</dl>` : '';
    if (!health.model_loaded) $('analyze-error').textContent = 'No trained model is loaded. Predictions are unavailable until a model artifact is installed and the backend is restarted.';
  } catch (err) {
    $('connection').className = 'connection offline'; $('connection').innerHTML = '<span class="status-dot"></span> API unavailable';
    $('model-status').textContent = 'Unavailable'; $('model-limitations').innerHTML = '<li>Model information could not be loaded. Check that the backend is running.</li>';
    $('analyze-error').textContent = errorMessage(err);
  }
}
$('listing-form').addEventListener('submit', async event => {
  event.preventDefault();
  $('listing-error').textContent = '';
  $('listing-result').innerHTML = '<p>Checking the link and attempting to retrieve the listing…</p>';
  $('listing-button').disabled = true;
  const payload = {url: $('listing-url').value.trim(), title: $('listing-title').value.trim(), brand: $('listing-brand').value.trim(), seller: $('listing-seller').value.trim(), price: $('listing-price').value.trim(), seller_authorized: $('seller-authorized').value, review_text: $('listing-review').value.trim()};
  try {
    const result = await post('/api/assess-amazon', payload);
    const checks = result.checks.map(item => `<li><strong>${escapeHTML(item.title)}:</strong> ${escapeHTML(item.detail)}</li>`).join('');
    const review = result.review_signal ? `<h4>Separate review-writing estimate</h4><p>${escapeHTML(result.review_signal.label === 'CG' ? 'Computer-generated pattern' : 'Original-writing pattern')} (${percent(result.review_signal.confidence)} model confidence). ${escapeHTML(result.review_signal.explanation)}</p>` : '';
    const fetched = result.retrieval;
    const reviewRows = fetched.review_results.map(item => `<li><p>${escapeHTML(item.text)}</p><strong>${escapeHTML(item.label === 'CG' ? 'Computer-generated writing pattern' : 'Original writing pattern')}</strong> — ${percent(item.confidence)} model confidence</li>`).join('');
    const retrieved = `<h4>Amazon India listing retrieval</h4><p>${escapeHTML(fetched.message)}</p>${fetched.title ? `<p><strong>Listing title:</strong> ${escapeHTML(fetched.title)}</p>` : ''}${fetched.source ? `<p><strong>Source:</strong> ${escapeHTML(fetched.source)}</p>` : ''}<p>Review texts found: ${fetched.reviews_found}; analyzed: ${fetched.reviews_analyzed}.${!fetched.model_available && fetched.reviews_found ? ' Review model is unavailable.' : ''}</p>${reviewRows ? `<ul>${reviewRows}</ul><p>These estimates concern writing patterns in the retrieved sample, not whether reviews are truthful or the product is authentic.</p>` : ''}`;
    $('listing-result').innerHTML = `<div class="listing-output"><span class="listing-badge">Authenticity inconclusive</span><h3>Listing analysis</h3><p>${escapeHTML(result.warning)}</p><p><strong>Marketplace:</strong> ${escapeHTML(result.marketplace)}<br><strong>Product ID:</strong> ${escapeHTML(result.asin)}</p>${retrieved}<h4>Information provided</h4><ul>${checks}</ul>${review}<h4>What to check next</h4><ul>${result.next_steps.map(item => `<li>${escapeHTML(item)}</li>`).join('')}</ul><p class="result-warning">${result.limitations.map(escapeHTML).join(' ')}</p></div>`;
  } catch (err) {
    $('listing-result').innerHTML = '<div class="result-empty"><h3>No listing check yet</h3><p>Correct the link and try again.</p></div>';
    $('listing-error').textContent = errorMessage(err);
  } finally { $('listing-button').disabled = false; }
});
$('review-text').addEventListener('input', () => $('char-count').textContent = `${$('review-text').value.length.toLocaleString()} / 10,000`);
$('analyze-form').addEventListener('submit', async event => {
  event.preventDefault(); const text = $('review-text').value.trim();
  if (!text) { $('analyze-error').textContent = 'Enter a review before analyzing.'; return; }
  $('analyze-error').textContent = ''; $('analyze-button').disabled = true; $('analyze-button').textContent = 'Analyzing…';
  try {
    const item = await post('/api/predict', {text});
    $('result').innerHTML = `<div class="result-content"><span class="section-kicker">Estimated writing pattern</span><h3>${escapeHTML(item.display_label)}</h3><p>The model identified this as the more likely pattern.</p><div class="score">${percent(item.confidence)}</div><div class="score-label">Model confidence in the predicted label</div><p class="result-warning">${escapeHTML(item.warning)}</p></div>`;
    refreshActivity();
  } catch (err) { $('analyze-error').textContent = errorMessage(err); }
  finally { $('analyze-button').disabled = false; $('analyze-button').innerHTML = 'Analyze text <span aria-hidden="true">↗</span>'; }
});
// RFC-style CSV parsing, including quoted commas, newlines and escaped quotes.
function parseCSV(text) {
  text = text.replace(/^﻿/, ''); const rows = []; let row = [], field = '', quoted = false, closed = false;
  for (let i=0; i<text.length; i++) {
    const c = text[i];
    if (quoted) { if (c === '"') { if (text[i+1] === '"') { field += '"'; i++; } else { quoted = false; closed = true; } } else field += c; }
    else if (c === '"') { if (field || closed) throw new Error('Invalid quote in CSV.'); quoted = true; }
    else if (c === ',') { row.push(field); field = ''; closed = false; }
    else if (c === '\n' || c === '\r') { if (c === '\r' && text[i+1] === '\n') i++; row.push(field); rows.push(row); row = []; field = ''; closed = false; }
    else { if (closed) throw new Error('Unexpected character after a quoted CSV field.'); field += c; }
  }
  if (quoted) throw new Error('CSV contains an unclosed quoted field.');
  if (field || row.length || closed) { row.push(field); rows.push(row); }
  return rows;
}
async function loadFile(file) {
  batchRows = []; batchResults = []; $('batch-details').hidden = true; $('export-button').hidden = true; $('batch-error').textContent = ''; $('batch-message').textContent = '';
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.csv')) { $('batch-error').textContent = 'Choose a .csv file.'; return; }
  if (file.size > 6 * 1024 * 1024) { $('batch-error').textContent = 'CSV files must be 6 MB or smaller.'; return; }
  try {
    const rows = parseCSV(await file.text());
    if (!rows.length) throw new Error('The CSV is empty.');
    const headers = rows.shift().map(x => x.trim().toLowerCase());
    const textIndex = headers.includes('text') ? headers.indexOf('text') : headers.indexOf('text_'), sourceIndex = headers.indexOf('source');
    if (textIndex < 0) throw new Error('The CSV needs a column named text or text_.');
    rows.forEach((row, index) => {
      if (row.every(x => !x.trim())) return;
      const text = (row[textIndex] || '').trim(), source = sourceIndex < 0 ? '' : (row[sourceIndex] || '').trim();
      if (!text) throw new Error(`Row ${index+2} has no review text.`);
      if (text.length > 10000) throw new Error(`Row ${index+2} exceeds 10,000 characters.`);
      if (source.length > 120) throw new Error(`Row ${index+2} has a source longer than 120 characters.`);
      batchRows.push({text, ...(source ? {source} : {})});
      if (batchRows.length > 500) throw new Error('The CSV exceeds the 500-review batch limit.');
    });
    if (!batchRows.length) throw new Error('The CSV contains no reviews.');
    if (batchRows.length > 500) throw new Error('The CSV exceeds the 500-review batch limit.');
    $('file-name').textContent = file.name; $('file-count').textContent = `${batchRows.length} reviews ready · showing first ${Math.min(5,batchRows.length)}`;
    $('preview-body').innerHTML = batchRows.slice(0,5).map(r => `<tr><td title="${escapeHTML(r.text)}">${escapeHTML(r.text)}</td><td>${escapeHTML(r.source || '—')}</td><td>Not analyzed</td><td>—</td></tr>`).join('');
    $('batch-details').hidden = false;
  } catch(err) { batchRows = []; $('batch-error').textContent = errorMessage(err); }
}
$('csv-file').addEventListener('change', e => loadFile(e.target.files[0]));
const zone = document.querySelector('.upload-zone');
zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragging'); });
zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('dragging'); loadFile(e.dataTransfer.files[0]); });
$('clear-file').addEventListener('click', () => { $('csv-file').value = ''; loadFile(null); });
$('batch-button').addEventListener('click', async () => {
  if (!batchRows.length) return;
  $('batch-button').disabled = true; $('batch-error').textContent = ''; $('batch-message').textContent = 'Analyzing batch…'; $('export-button').hidden = true; batchResults = [];
  try {
    const result = await post('/api/predict/batch', {reviews: batchRows}); batchResults = result.items;
    $('batch-message').textContent = `Analyzed ${result.summary.total} reviews: ${result.summary.generated_count} computer-generated patterns and ${result.summary.original_count} original-writing patterns. These are estimates.`;
    $('preview-body').innerHTML = batchResults.map((item, i) => `<tr><td title="${escapeHTML(batchRows[i].text)}">${escapeHTML(batchRows[i].text)}</td><td>${escapeHTML(batchRows[i].source || '—')}</td><td>${patternTag(item)}</td><td>${percent(item.confidence)}</td></tr>`).join('');
    $('file-count').textContent = `${batchResults.length} results`;
    $('export-button').hidden = false; refreshActivity();
  } catch(err) { $('batch-error').textContent = `${errorMessage(err)} If the connection was interrupted, check history before retrying.`; $('batch-message').textContent = ''; refreshActivity(); }
  finally { $('batch-button').disabled = false; }
});
$('export-button').addEventListener('click', () => {
  // Prefix spreadsheet formula-like values to avoid formula execution on opening.
  const cell = value => { let s = String(value ?? ''); if (/^[\s]*[=+\-@\t\r]/.test(s)) s = "'" + s; return `"${s.replace(/"/g,'""')}"`; };
  const rows = [['text','source','id','created_at','label','display_label','probability_cg','confidence','warning'], ...batchResults.map((r,i) => [batchRows[i].text,batchRows[i].source || '',r.id,r.created_at,r.label,r.display_label,r.probability,r.confidence,r.warning])];
  const url = URL.createObjectURL(new Blob(['﻿'+rows.map(row => row.map(cell).join(',')).join('\r\n')], {type:'text/csv;charset=utf-8'}));
  const a = document.createElement('a'); a.href = url; a.download = 'review-lens-results.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
async function loadHistory() {
  try {
    const data = await api(`/api/history?limit=${pageSize}&offset=${offset}&label=${encodeURIComponent($('history-filter').value)}`);
    if (offset >= data.total && offset > 0) { offset = Math.max(0, Math.ceil(data.total / pageSize - 1) * pageSize); return loadHistory(); }
    $('history-body').innerHTML = data.items.length ? data.items.map(item => `<tr><td>${escapeHTML(dateText(item.created_at))}</td><td>${patternTag(item)}</td><td>${percent(item.confidence)}</td><td>${escapeHTML(item.source || '—')}</td><td>${item.text_length.toLocaleString()} characters</td></tr>`).join('') : '<tr><td colspan="5" class="empty-cell">No analyses found. Analyze a review to get started.</td></tr>';
    $('history-count').textContent = data.total ? `Showing ${offset+1}–${offset+data.items.length} of ${data.total}` : 'No results';
    $('previous').disabled = offset === 0; $('next').disabled = offset + data.items.length >= data.total;
  } catch(err) { $('history-body').innerHTML = `<tr><td colspan="5" class="empty-cell">${escapeHTML(errorMessage(err))}</td></tr>`; $('history-count').textContent = ''; $('previous').disabled = $('next').disabled = true; }
}
async function loadAnalytics() {
  try { const data = await api('/api/analytics'); $('stat-total').textContent = data.total.toLocaleString(); $('stat-generated').textContent = data.generated_count.toLocaleString(); $('stat-original').textContent = data.original_count.toLocaleString(); $('analytics-error').textContent = ''; }
  catch(err) { $('stat-total').textContent = $('stat-generated').textContent = $('stat-original').textContent = '—'; $('analytics-error').textContent = errorMessage(err); }
}
function refreshActivity() { loadAnalytics(); loadHistory(); }
$('refresh').addEventListener('click', () => { refreshActivity(); loadModel(); });
$('history-filter').addEventListener('change', () => { offset = 0; loadHistory(); });
$('previous').addEventListener('click', () => { offset = Math.max(0,offset-pageSize); loadHistory(); });
$('next').addEventListener('click', () => { offset += pageSize; loadHistory(); });
loadModel(); refreshActivity();
