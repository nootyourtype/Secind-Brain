import { useState, useEffect, useCallback, useRef } from 'react';
import './index.css';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// ── Small helpers ──────────────────────────────────────────────────────────────

const FILE_TYPE_COLORS = {
  md:   { bg: 'rgba(56,189,248,0.15)',  border: 'rgba(56,189,248,0.4)',  label: 'MD'   },
  txt:  { bg: 'rgba(163,230,53,0.15)', border: 'rgba(163,230,53,0.4)', label: 'TXT'  },
  pdf:  { bg: 'rgba(251,146,60,0.15)', border: 'rgba(251,146,60,0.4)', label: 'PDF'  },
  docx: { bg: 'rgba(192,132,252,0.15)',border: 'rgba(192,132,252,0.4)',label: 'DOCX' },
};
const ftColor = (ext) => FILE_TYPE_COLORS[ext] || FILE_TYPE_COLORS.txt;

const formatBytes = (bytes) => {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

// ── Icons ──────────────────────────────────────────────────────────────────────

const SearchIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);
const LibraryIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
  </svg>
);
const BrainIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-1.66z"/>
    <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-1.66z"/>
  </svg>
);
const UploadIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="17 8 12 3 7 8"/>
    <line x1="12" y1="3" x2="12" y2="15"/>
  </svg>
);
const SettingsIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
);

// ── Toast Notification System ─────────────────────────────────────────────────

let _toastId = 0;

function ToastContainer({ toasts, onDismiss }) {
  return (
    <div className="toast-container" id="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`} onClick={() => onDismiss(t.id)}>
          <span className="toast-icon">
            {t.type === 'success' ? '✓' : t.type === 'error' ? '✗' : 'ℹ'}
          </span>
          <span className="toast-msg">{t.message}</span>
        </div>
      ))}
    </div>
  );
}

// ── File Upload Zone ──────────────────────────────────────────────────────────

function FileUploadZone({ onUploadComplete }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFiles = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);

    const results = [];
    for (const file of fileList) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${API}/upload`, { method: 'POST', body: formData });
        if (!res.ok) {
          const err = await res.json();
          results.push({ name: file.name, ok: false, error: err.detail || 'Failed' });
        } else {
          const data = await res.json();
          results.push({ name: data.file, ok: true, size: data.size });
        }
      } catch {
        results.push({ name: file.name, ok: false, error: 'Network error' });
      }
    }

    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
    onUploadComplete(results);
  };

  return (
    <div
      id="upload-zone"
      className={`upload-zone ${dragOver ? 'upload-active' : ''} ${uploading ? 'upload-busy' : ''}`}
      onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onClick={() => !uploading && fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".md,.txt,.pdf,.docx"
        style={{ display: 'none' }}
        onChange={(e) => handleFiles(e.target.files)}
      />
      {uploading ? (
        <>
          <div className="dot-elastic" style={{ marginBottom: '8px' }} />
          <span className="upload-text">Uploading…</span>
        </>
      ) : (
        <>
          <UploadIcon />
          <span className="upload-text">
            Drop files here or <span className="upload-browse">browse</span>
          </span>
          <span className="upload-hint">.md  .txt  .pdf  .docx</span>
        </>
      )}
    </div>
  );
}

// ── Stats Bar ─────────────────────────────────────────────────────────────────

function StatsBar({ stats }) {
  if (!stats) return null;
  return (
    <div className="stats-bar">
      <div className="stat-card">
        <div className="stat-value">{stats.file_count}</div>
        <div className="stat-label">Files</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.chunk_count}</div>
        <div className="stat-label">Chunks</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.unique_tags}</div>
        <div className="stat-label">Tags</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{formatBytes(stats.total_size_bytes)}</div>
        <div className="stat-label">Size</div>
      </div>
    </div>
  );
}

// ── Note Card ─────────────────────────────────────────────────────────────────

function NoteCard({ filename, data, activeTag, onTagClick, onReEnrich, onClick }) {
  const ft = ftColor(data.file_type);
  const hasEnrichment = data.summary || (data.tags && data.tags.length > 0);

  return (
    <div className="note-card" onClick={onClick} style={{ cursor: 'pointer' }}>
      <div className="note-card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0 }}>
          <span className="file-type-badge" style={{ background: ft.bg, border: `1px solid ${ft.border}` }}>
            {ft.label}
          </span>
          <span className="note-filename" title={filename}>{filename}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <span className="chunk-count">{data.chunk_count || 0} chunks</span>
          {onReEnrich && (
            <button className="re-enrich-btn" onClick={(e) => { e.stopPropagation(); onReEnrich(filename); }} title="Re-enrich with AI">
              ✦
            </button>
          )}
        </div>
      </div>

      {data.summary && (
        <p className="note-summary">{data.summary}</p>
      )}

      {data.tags && data.tags.length > 0 ? (
        <div className="tag-list">
          {data.tags.map(tag => (
            <button
              key={tag}
              className={`tag-pill ${activeTag === tag ? 'active' : ''}`}
              onClick={(e) => { e.stopPropagation(); onTagClick(tag); }}
            >
              #{tag}
            </button>
          ))}
        </div>
      ) : (
        !hasEnrichment && (
          <p className="note-pending">⏳ Enrichment pending (requires Ollama)</p>
        )
      )}

      {data.enriched_at && (
        <div className="note-enriched-at">
          Enriched {new Date(data.enriched_at).toLocaleDateString('en-GB', { day:'numeric', month:'short', hour:'2-digit', minute:'2-digit' })}
        </div>
      )}
    </div>
  );
}

// ── Note Viewer (Slide-in Panel) ─────────────────────────────────────────────────

function NoteViewer({ filename, data, onClose }) {
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!filename) return;
    setLoading(true);
    fetch(`${API}/notes/${encodeURIComponent(filename)}/content`)
      .then(r => r.json())
      .then(d => { setContent(d.content); setLoading(false); })
      .catch(() => { setContent('Error loading content.'); setLoading(false); });
  }, [filename]);

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!filename) return null;
  const ft = ftColor(data?.file_type);

  return (
    <>
      <div className="viewer-overlay" onClick={onClose} />
      <div className="note-viewer">
        <div className="viewer-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: 0 }}>
            <span className="file-type-badge" style={{ background: ft.bg, border: `1px solid ${ft.border}` }}>
              {ft.label}
            </span>
            <span className="viewer-filename">{filename}</span>
          </div>
          <button className="viewer-close" onClick={onClose} title="Close (Esc)">×</button>
        </div>

        {data?.summary && (
          <div className="viewer-summary">
            <div className="viewer-summary-label">✨ AI Summary</div>
            <p>{data.summary}</p>
          </div>
        )}

        {data?.tags?.length > 0 && (
          <div className="viewer-tags">
            {data.tags.map(tag => <span key={tag} className="tag-pill">#{tag}</span>)}
          </div>
        )}

        <div className="viewer-content">
          {loading ? (
            <div className="loader-container"><div className="dot-elastic" /></div>
          ) : (
            <pre className="viewer-text">{content}</pre>
          )}
        </div>
      </div>
    </>
  );
}

// ── Library View ──────────────────────────────────────────────────────────────

function LibraryView({ addToast }) {
  const [notes, setNotes]       = useState({});
  const [allTags, setAllTags]   = useState([]);
  const [activeTag, setActiveTag] = useState(null);
  const [loading, setLoading]   = useState(true);
  const [enrichMsg, setEnrichMsg] = useState('');
  const [selectedNote, setSelectedNote] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [notesRes, tagsRes] = await Promise.all([
        fetch(`${API}/notes`).then(r => r.json()),
        fetch(`${API}/tags`).then(r => r.json()),
      ]);
      setNotes(notesRes.notes || {});
      setAllTags(tagsRes.tags || []);
    } catch {
      setNotes({});
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleTagClick = (tag) => setActiveTag(prev => (prev === tag ? null : tag));

  const handleReEnrich = async (filename) => {
    setEnrichMsg(`Re-enriching ${filename}...`);
    try {
      await fetch(`${API}/notes/${encodeURIComponent(filename)}/enrich`, { method: 'POST' });
      setEnrichMsg(`Queued! Tags & summary will update in ~30s (requires Ollama).`);
      addToast(`Enrichment queued for ${filename}`, 'success');
      setTimeout(() => { fetchData(); setEnrichMsg(''); }, 35000);
    } catch {
      setEnrichMsg('Error triggering enrichment.');
      addToast('Failed to trigger enrichment', 'error');
    }
  };

  const handleUploadComplete = (results) => {
    const ok = results.filter(r => r.ok);
    const fail = results.filter(r => !r.ok);
    if (ok.length > 0) addToast(`Uploaded ${ok.length} file${ok.length > 1 ? 's' : ''} — auto-indexing shortly`, 'success');
    if (fail.length > 0) addToast(`${fail.length} upload${fail.length > 1 ? 's' : ''} failed: ${fail[0].error}`, 'error');
    // Refresh library after a delay for the watcher to pick up
    setTimeout(() => fetchData(), 5000);
  };

  const filtered = activeTag
    ? Object.fromEntries(Object.entries(notes).filter(([, d]) => d.tags?.includes(activeTag)))
    : notes;

  const entriesArr = Object.entries(filtered);

  return (
    <div className="library-view">
      {/* File Upload Zone */}
      <FileUploadZone onUploadComplete={handleUploadComplete} />

      {/* Tag filter bar */}
      {allTags.length > 0 && (
        <div className="tag-filter-bar">
          <span className="tag-filter-label">Filter by tag:</span>
          <div className="tag-filter-pills">
            {allTags.map(tag => (
              <button
                key={tag}
                className={`tag-pill ${activeTag === tag ? 'active' : ''}`}
                onClick={() => handleTagClick(tag)}
              >
                #{tag}
              </button>
            ))}
          </div>
        </div>
      )}

      {enrichMsg && <div className="enrich-msg">✦ {enrichMsg}</div>}

      {loading ? (
        <div className="loader-container"><div className="dot-elastic" /></div>
      ) : entriesArr.length === 0 ? (
        <div className="empty-library">
          <div style={{ fontSize: '3rem', opacity: 0.2, marginBottom: '1rem' }}>🧠</div>
          {Object.keys(notes).length === 0
            ? <><p>No enriched notes yet.</p><p style={{ fontSize: '0.85rem', opacity: 0.6 }}>
                Upload files above or install Ollama — tags & summaries will auto-generate.
              </p></>
            : <p>No notes match tag <strong>#{activeTag}</strong>.</p>
          }
        </div>
      ) : (
        <div className="notes-grid">
          {entriesArr.map(([filename, data]) => (
            <NoteCard
              key={filename}
              filename={filename}
              data={data}
              activeTag={activeTag}
              onTagClick={handleTagClick}
              onReEnrich={handleReEnrich}
              onClick={() => setSelectedNote({ filename, data })}
            />
          ))}
        </div>
      )}

      <button className="refresh-btn" onClick={fetchData} title="Refresh library">
        ↺ Refresh
      </button>

      {/* Note Viewer */}
      {selectedNote && (
        <NoteViewer
          filename={selectedNote.filename}
          data={selectedNote.data}
          onClose={() => setSelectedNote(null)}
        />
      )}
    </div>
  );
}

// ── Search View ───────────────────────────────────────────────────────────────

function SearchView({ ollamaAvailable }) {
  const [query, setQuery]     = useState('');
  const [mode, setMode]       = useState('search');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [insight, setInsight] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setResults([]);
    setInsight(null);

    const endpoint = mode === 'chat' ? '/chat' : '/search';
    try {
      const res  = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: 5 }),
      });
      if (!res.ok) throw new Error('API Error');
      const data = await res.json();
      if (mode === 'chat') { setInsight(data.insight); setResults(data.sources || []); }
      else                 { setResults(data.results || []); }
    } catch (err) {
      setInsight('Error communicating with the Second Brain API.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="search-view">
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-row">
          <input
            id="search-input"
            type="text"
            className="text-input search-input"
            placeholder="Ask your brain anything..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <button type="submit" className="primary-btn search-btn" disabled={loading || !query.trim()}>
            {loading ? '…' : 'Search'}
          </button>
        </div>
        <div className="mode-toggle">
          <label className={`mode-label ${mode === 'search' ? 'mode-active' : ''}`}>
            <input type="radio" name="mode" checked={mode === 'search'} onChange={() => setMode('search')} />
            Vector Search
          </label>
          <label className={`mode-label ${mode === 'chat' ? 'mode-active' : ''} ${!ollamaAvailable ? 'mode-disabled' : ''}`}>
            <input type="radio" name="mode" checked={mode === 'chat'}
              onChange={() => setMode('chat')} disabled={!ollamaAvailable} />
            AI Synthesis {!ollamaAvailable && <span style={{ opacity: 0.5 }}>(Ollama off)</span>}
          </label>
        </div>
      </form>

      <div className="results-area">
        {loading ? (
          <div className="loader-container"><div className="dot-elastic" /></div>
        ) : (
          <>
            {insight && (
              <div className="insight-card">
                <h3>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 8 }}>
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                  </svg>
                  AI Synthesis
                </h3>
                <div className="insight-text">{insight}</div>
              </div>
            )}

            {results.length > 0 && (
              <>
                <h3 className="results-heading">
                  {mode === 'chat' ? 'Supporting Sources' : `${results.length} Result${results.length > 1 ? 's' : ''}`}
                </h3>
                <div className="results-list">
                  {results.map((r, i) => (
                    <div className="result-item" key={i}>
                      <div className="result-meta">
                        <span className="result-source">{r.source}</span>
                        <span className="result-score">{Math.round(r.score * 100)}% match</span>
                      </div>
                      <div className="result-excerpt">{r.excerpt}</div>
                    </div>
                  ))}
                </div>
              </>
            )}

            {!insight && results.length === 0 && (
              <div className="empty-search">
                <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     strokeWidth="0.8" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <p>Your Second Brain is ready.</p>
                <p>Search your notes or synthesize answers with AI.</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ── Settings View ─────────────────────────────────────────────────────────────

function SettingsView({ status, stats, addToast, onRefresh }) {
  const [config, setConfig]       = useState(null);
  const [reindexing, setReindexing] = useState(false);
  const [testing, setTesting]     = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    fetch(`${API}/config`).then(r => r.json()).then(setConfig).catch(() => {});
  }, []);

  const handleReindex = async () => {
    setReindexing(true);
    addToast('Reindexing brain — this may take a moment…', 'info');
    try {
      const res = await fetch(`${API}/reindex`, { method: 'POST' });
      const data = await res.json();
      addToast(`Reindex complete — ${data.chunks} chunks indexed`, 'success');
      onRefresh();
    } catch {
      addToast('Reindex failed — is the backend running?', 'error');
    } finally {
      setReindexing(false);
    }
  };

  const handleTestOllama = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API}/ollama/test`, { method: 'POST' });
      const data = await res.json();
      setTestResult(data);
      if (data.success) addToast(`AI responded via ${data.model}`, 'success');
      else addToast(`AI test failed: ${data.error}`, 'error');
    } catch {
      setTestResult({ success: false, error: 'Could not reach the API server.' });
      addToast('AI test failed — is the backend running?', 'error');
    } finally {
      setTesting(false);
    }
  };

  const ollamaStatus = config?.ollama || {};

  return (
    <div className="settings-view">
      {/* System Health */}
      <section className="settings-section">
        <h3 className="settings-title">
          <span className="settings-title-dot" style={{ background: status.state === 'online' ? 'var(--green)' : '#ef4444' }} />
          System Health
        </h3>
        <div className="config-grid">
          <div className="config-card">
            <div className="config-icon">⚡</div>
            <div className="config-key">API Server</div>
            <div className={`config-val ${status.state === 'online' ? 'val-green' : 'val-red'}`}>
              {status.state === 'online' ? 'Online' : 'Offline'}
            </div>
          </div>
          <div className="config-card">
            <div className="config-icon">🤖</div>
            <div className="config-key">Ollama LLM</div>
            <div className={`config-val ${ollamaStatus.available ? 'val-green' : 'val-dim'}`}>
              {ollamaStatus.available ? (ollamaStatus.model || 'Connected') : 'Unavailable'}
            </div>
          </div>
          <div className="config-card">
            <div className="config-icon">🧬</div>
            <div className="config-key">Embedding Model</div>
            <div className="config-val">{config?.embedding_model || '—'}</div>
          </div>
          <div className="config-card">
            <div className="config-icon">📊</div>
            <div className="config-key">Brain Stats</div>
            <div className="config-val">
              {stats ? `${stats.file_count} files · ${stats.chunk_count} chunks` : '—'}
            </div>
          </div>
        </div>
      </section>

      {/* Configuration */}
      <section className="settings-section">
        <h3 className="settings-title">Configuration</h3>
        <div className="config-table">
          <div className="config-row">
            <span className="config-row-key">Notes Directory</span>
            <span className="config-row-val">{config?.notes_dir || '—'}</span>
          </div>
          <div className="config-row">
            <span className="config-row-key">Database Path</span>
            <span className="config-row-val">{config?.db_path || '—'}</span>
          </div>
          <div className="config-row">
            <span className="config-row-key">Supported Types</span>
            <span className="config-row-val">{config?.supported_extensions?.join('  ') || '—'}</span>
          </div>
          <div className="config-row">
            <span className="config-row-key">Enriched Notes</span>
            <span className="config-row-val">{stats?.enriched_count ?? '—'} / {stats?.file_count ?? '—'}</span>
          </div>
          <div className="config-row">
            <span className="config-row-key">Unique Tags</span>
            <span className="config-row-val">{stats?.unique_tags ?? '—'}</span>
          </div>
        </div>
      </section>

      {/* AI Engine (Ollama) */}
      <section className="settings-section">
        <h3 className="settings-title">
          <span className="settings-title-dot" style={{ background: ollamaStatus.available ? 'var(--green)' : '#ef4444' }} />
          AI Engine (Ollama)
        </h3>

        {ollamaStatus.available ? (
          <div className="ollama-connected">
            <div className="config-grid">
              <div className="config-card">
                <div className="config-icon">✅</div>
                <div className="config-key">Status</div>
                <div className="config-val val-green">Connected</div>
              </div>
              <div className="config-card">
                <div className="config-icon">🧠</div>
                <div className="config-key">Active Model</div>
                <div className="config-val">{ollamaStatus.model || '—'}</div>
              </div>
            </div>
            {ollamaStatus.all_models && ollamaStatus.all_models.length > 0 && (
              <div className="ollama-models">
                <div className="config-row-key" style={{ marginBottom: '6px' }}>Available Models</div>
                <div className="about-stack">
                  {ollamaStatus.all_models.map(m => (
                    <span key={m} className={`stack-tag ${m === ollamaStatus.model ? 'stack-tag-active' : ''}`}>{m}</span>
                  ))}
                </div>
              </div>
            )}
            <div className="settings-actions" style={{ marginTop: '12px' }}>
              <button
                className="action-btn action-primary"
                onClick={handleTestOllama}
                disabled={testing}
              >
                {testing ? '⏳ Testing…' : '🧪 Test AI Connection'}
              </button>
              {testResult && (
                <div className={`ollama-test-result ${testResult.success ? 'test-ok' : 'test-fail'}`}>
                  {testResult.success
                    ? <>✓ <strong>{testResult.model}</strong> responded: "{testResult.response}"</>
                    : <>✗ {testResult.error}</>
                  }
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="ollama-setup">
            <div className="ollama-setup-header">
              <span style={{ fontSize: '2rem' }}>🔌</span>
              <div>
                <div className="ollama-setup-title">Ollama Not Detected</div>
                <p className="ollama-setup-desc">
                  Ollama is required for AI Synthesis, auto-tagging, and document summarization. Without it, only vector search is available.
                </p>
              </div>
            </div>
            <div className="ollama-steps">
              <div className="ollama-step">
                <span className="ollama-step-num">1</span>
                <div>
                  <strong>Install Ollama</strong>
                  <p>Download from <a href="https://ollama.com/download" target="_blank" rel="noopener" className="ollama-link">ollama.com/download</a></p>
                </div>
              </div>
              <div className="ollama-step">
                <span className="ollama-step-num">2</span>
                <div>
                  <strong>Pull a model</strong>
                  <p><code className="ollama-code">ollama pull phi3:mini</code></p>
                </div>
              </div>
              <div className="ollama-step">
                <span className="ollama-step-num">3</span>
                <div>
                  <strong>Install Python package</strong>
                  <p><code className="ollama-code">pip install ollama</code></p>
                </div>
              </div>
              <div className="ollama-step">
                <span className="ollama-step-num">4</span>
                <div>
                  <strong>Restart the app</strong>
                  <p>Run <code className="ollama-code">python main.py</code> again</p>
                </div>
              </div>
            </div>
            <p className="action-hint" style={{ marginTop: '8px' }}>
              Or run <code className="ollama-code">setup_ai.bat</code> in the project root to set up everything automatically.
            </p>
          </div>
        )}
      </section>

      {/* Actions */}
      <section className="settings-section">
        <h3 className="settings-title">Actions</h3>
        <div className="settings-actions">
          <button
            className="action-btn action-primary"
            onClick={handleReindex}
            disabled={reindexing}
          >
            {reindexing ? '⟳ Reindexing…' : '⟳ Force Full Reindex'}
          </button>
          <p className="action-hint">
            Re-scans all files in the notes directory, rebuilds embeddings, and refreshes the vector database.
          </p>
        </div>
      </section>

      {/* About */}
      <section className="settings-section">
        <h3 className="settings-title">About</h3>
        <div className="about-block">
          <div className="about-brand">🧠 Second Brain</div>
          <p className="about-desc">A local-first, privacy-preserving AI knowledge assistant.</p>
          <div className="about-stack">
            <span className="stack-tag">Python</span>
            <span className="stack-tag">FastAPI</span>
            <span className="stack-tag">ChromaDB</span>
            <span className="stack-tag">Ollama</span>
            <span className="stack-tag">React</span>
            <span className="stack-tag">Vite</span>
          </div>
        </div>
      </section>
    </div>
  );
}

// ── Root App ──────────────────────────────────────────────────────────────────

export default function App() {
  const [tab, setTab]         = useState('search');
  const [status, setStatus]   = useState({ state: 'loading', chunks: 0, model: 'unavailable' });
  const [stats, setStats]     = useState(null);
  const [urlToIngest, setUrlToIngest] = useState('');
  const [ingesting, setIngesting]     = useState(false);
  const [ingestMsg, setIngestMsg]     = useState('');
  const [toasts, setToasts]   = useState([]);

  // ── Toast helpers ──
  const addToast = useCallback((message, type = 'info') => {
    const id = ++_toastId;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4500);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  // ── Data fetching ──
  const fetchStatus = useCallback(() => {
    fetch(`${API}/status`)
      .then(r => r.json())
      .then(d => setStatus({
        state:  d.status === 'online' ? 'online' : 'offline',
        chunks: d.chunks || 0,
        model:  d.ollama_model || 'unavailable',
      }))
      .catch(() => setStatus(s => ({ ...s, state: 'offline' })));
  }, []);

  const fetchStats = useCallback(() => {
    fetch(`${API}/stats`)
      .then(r => r.json())
      .then(d => setStats(d))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchStats();
    const iv = setInterval(() => { fetchStatus(); fetchStats(); }, 30000);
    return () => clearInterval(iv);
  }, [fetchStatus, fetchStats]);

  // ── Keyboard shortcuts ──
  useEffect(() => {
    const handler = (e) => {
      const inInput = e.target.closest('input, textarea');
      // Ctrl+K to focus search
      if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        setTab('search');
        setTimeout(() => document.getElementById('search-input')?.focus(), 100);
      }
      // Number keys to switch tabs (when not in input)
      if (!inInput) {
        if (e.key === '1') setTab('search');
        if (e.key === '2') setTab('library');
        if (e.key === '3') setTab('settings');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // ── URL ingest ──
  const handleIngestUrl = async (e) => {
    e.preventDefault();
    if (!urlToIngest.trim()) return;
    setIngesting(true);
    setIngestMsg('Fetching & saving…');
    try {
      const res  = await fetch(`${API}/ingest_url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlToIngest }),
      });
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      setIngestMsg(`✓ Saved as ${data.file}`);
      setUrlToIngest('');
      addToast(`Ingested web article as ${data.file}`, 'success');
      setTimeout(() => { fetchStatus(); fetchStats(); }, 4000);
    } catch {
      setIngestMsg('✗ Error fetching URL');
      addToast('Failed to fetch URL', 'error');
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="app-shell">

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="sidebar glass-panel">
        <div className="brand">
          <div className="brand-icon"><BrainIcon /></div>
          <div>
            <div className="brand-name">Second Brain</div>
            <div className="brand-tagline">Local · Private · Proactive</div>
          </div>
        </div>

        <nav className="nav-links">
          <button className={`nav-btn ${tab === 'search' ? 'nav-active' : ''}`} onClick={() => setTab('search')}>
            <SearchIcon /> Search
          </button>
          <button className={`nav-btn ${tab === 'library' ? 'nav-active' : ''}`} onClick={() => setTab('library')}>
            <LibraryIcon /> Library
          </button>
          <button className={`nav-btn ${tab === 'settings' ? 'nav-active' : ''}`} onClick={() => setTab('settings')}>
            <SettingsIcon /> Settings
          </button>
        </nav>

        {/* Stats */}
        <StatsBar stats={stats} />

        <div className="sidebar-spacer" />

        {/* Status */}
        <div className="status-block">
          <div className="status-row">
            <div className={`orb ${status.state === 'online' ? 'online' : ''}`} />
            <span className="status-label">{status.state === 'online' ? 'Online' : status.state === 'loading' ? 'Connecting…' : 'Offline'}</span>
            <span className="status-chunks">{status.chunks} chunks</span>
          </div>
          {status.model !== 'unavailable' && (
            <div className="status-model">🤖 {status.model}</div>
          )}
        </div>

        {/* URL Ingest */}
        <div className="ingest-block">
          <div className="ingest-label">Add Web Article</div>
          <form onSubmit={handleIngestUrl}>
            <input
              id="url-input"
              type="url"
              className="text-input ingest-input"
              placeholder="https://..."
              value={urlToIngest}
              onChange={(e) => setUrlToIngest(e.target.value)}
            />
            <button type="submit" className="primary-btn ingest-btn"
              disabled={ingesting || !urlToIngest.trim()}>
              {ingesting ? 'Fetching…' : '+ Add to Brain'}
            </button>
          </form>
          {ingestMsg && <div className="ingest-msg">{ingestMsg}</div>}
        </div>
      </aside>

      {/* ── Main Panel ───────────────────────────────────────────────────── */}
      <main className="main-panel glass-panel">
        <div className="panel-header">
          <h2 className="panel-title">
            {tab === 'search' ? 'Search & Synthesize' : tab === 'library' ? 'Knowledge Library' : 'Settings'}
          </h2>
          <div className="panel-tab-bar">
            <button className={`tab-btn ${tab === 'search' ? 'tab-active' : ''}`} onClick={() => setTab('search')}>
              <SearchIcon /> Search
            </button>
            <button className={`tab-btn ${tab === 'library' ? 'tab-active' : ''}`} onClick={() => setTab('library')}>
              <LibraryIcon /> Library
            </button>
            <button className={`tab-btn ${tab === 'settings' ? 'tab-active' : ''}`} onClick={() => setTab('settings')}>
              <SettingsIcon /> Settings
            </button>
          </div>
        </div>

        <div className="panel-body">
          {tab === 'search'
            ? <SearchView ollamaAvailable={status.model !== 'unavailable'} />
            : tab === 'library'
            ? <LibraryView addToast={addToast} />
            : <SettingsView status={status} stats={stats} addToast={addToast} onRefresh={() => { fetchStatus(); fetchStats(); }} />
          }
        </div>
      </main>

      {/* ── Toast Overlay ─────────────────────────────────────────────────── */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
