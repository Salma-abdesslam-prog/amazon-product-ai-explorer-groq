import React, { useState, useRef, useEffect } from 'react';
import { Upload, X, CheckCircle, AlertCircle, Database, PlusCircle } from 'lucide-react';

const API_BASE = 'http://localhost:8080';

// Inline spinner since lucide Loader doesn't animate via CSS animation in all versions
function Spinner() {
  return (
    <div style={{
      width: 16, height: 16, borderRadius: '50%',
      border: '2px solid var(--border-mid)',
      borderTopColor: 'var(--amber)',
      animation: 'spin 0.8s linear infinite',
      flexShrink: 0,
    }} />
  );
}

export default function UploadPanel({ onClose, onIngested }) {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [append, setAppend] = useState(false);
  const [status, setStatus] = useState(null);
  const [dbStats, setDbStats] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then((d) => setDbStats({ products: d.products, indexed_docs: d.indexed_docs }))
      .catch(() => {});
  }, []);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile || status === 'uploading') return;
    setStatus('uploading');
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
      const res = await fetch(`${API_BASE}/ingest?append=${append}`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus({ error: data.detail || `Server error ${res.status}` });
        return;
      }
      setStatus(data);
      onIngested?.();
    } catch (err) {
      setStatus({ error: err.message || 'Upload failed' });
    }
  };

  const handleUploadAnother = () => {
    setSelectedFile(null);
    setStatus(null);
    setAppend(true);
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then((d) => setDbStats({ products: d.products, indexed_docs: d.indexed_docs }))
      .catch(() => {});
  };

  const isUploading = status === 'uploading';
  const isSuccess = status && typeof status === 'object' && !status.error;
  const isError = status && typeof status === 'object' && status.error;

  return (
    <div
      onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(0,0,0,0.82)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div style={{
        width: '100%',
        maxWidth: 480,
        background: 'var(--bg-surface)',
        borderRadius: 'var(--r-xl)',
        border: '1px solid var(--border-mid)',
        padding: '32px',
        animation: 'fadeUp 0.25s cubic-bezier(0.16,1,0.3,1) both',
        boxShadow: '0 32px 80px rgba(0,0,0,0.7)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Amber accent top line */}
        <div style={{
          position: 'absolute',
          top: 0, left: '20%', right: '20%',
          height: 1,
          background: 'linear-gradient(90deg, transparent, var(--amber), transparent)',
          opacity: 0.7,
        }} />

        {/* ── Header ─────────────────────────────────────────────────── */}
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: 24,
        }}>
          <div>
            <h2 style={{
              margin: 0,
              fontFamily: 'Playfair Display, Georgia, serif',
              fontSize: 22,
              fontWeight: 600,
              color: 'var(--text-primary)',
              lineHeight: 1.2,
            }}>
              Upload Dataset
            </h2>
            <p style={{
              margin: '4px 0 0',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              color: 'var(--text-muted)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}>
              UCSD Amazon product data
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: '1px solid var(--border-dim)',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              padding: 7,
              borderRadius: 'var(--r-sm)',
              display: 'flex',
              alignItems: 'center',
              transition: 'all var(--t-fast)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-mid)';
              e.currentTarget.style.color = 'var(--text-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-dim)';
              e.currentTarget.style.color = 'var(--text-muted)';
            }}
          >
            <X size={14} />
          </button>
        </div>

        {/* ── DB Stats ───────────────────────────────────────────────── */}
        {dbStats && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginBottom: 18,
            padding: '9px 14px',
            borderRadius: 'var(--r-md)',
            background: 'var(--bg-raised)',
            border: '1px solid var(--border-dim)',
          }}>
            <Database size={12} color="var(--text-muted)" />
            <span style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              color: 'var(--text-muted)',
              letterSpacing: '0.04em',
            }}>
              <span style={{ color: 'var(--amber)', fontWeight: 600 }}>
                {dbStats.products.toLocaleString()}
              </span>
              {' products · '}
              <span style={{ color: 'var(--amber)', fontWeight: 600 }}>
                {dbStats.indexed_docs.toLocaleString()}
              </span>
              {' indexed'}
            </span>
          </div>
        )}

        {/* ── Drop zone ──────────────────────────────────────────────── */}
        <div
          onClick={() => !isSuccess && fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          style={{
            border: `1px dashed ${
              dragOver ? 'var(--amber)'
              : selectedFile ? 'var(--success)'
              : 'var(--border-mid)'
            }`,
            borderRadius: 'var(--r-lg)',
            padding: '28px 20px',
            textAlign: 'center',
            cursor: isSuccess ? 'default' : 'pointer',
            background: dragOver
              ? 'var(--amber-dim)'
              : selectedFile
              ? 'var(--success-dim)'
              : 'var(--bg-raised)',
            transition: 'all var(--t-base)',
            marginBottom: 16,
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.jsonl,.gz"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          {selectedFile ? (
            <>
              <CheckCircle size={24} color="var(--success)" style={{ marginBottom: 8 }} />
              <p style={{
                margin: '0 0 3px',
                fontSize: 13,
                fontWeight: 500,
                color: 'var(--text-primary)',
                fontFamily: 'DM Sans, sans-serif',
              }}>
                {selectedFile.name}
              </p>
              <p style={{
                margin: 0,
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 10,
                color: 'var(--text-muted)',
              }}>
                {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                {!isSuccess && (
                  <span
                    style={{ color: 'var(--amber)', marginLeft: 8, cursor: 'pointer' }}
                    onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                  >
                    change
                  </span>
                )}
              </p>
            </>
          ) : (
            <>
              <Upload size={22} color="var(--text-muted)" style={{ marginBottom: 10 }} />
              <p style={{
                margin: '0 0 4px',
                fontSize: 14,
                fontWeight: 500,
                color: 'var(--text-secondary)',
                fontFamily: 'DM Sans, sans-serif',
              }}>
                Drop file or click to browse
              </p>
              <p style={{
                margin: 0,
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 10,
                color: 'var(--text-faint)',
                letterSpacing: '0.04em',
              }}>
                .json · .jsonl · .jsonl.gz
              </p>
            </>
          )}
        </div>

        {/* ── Append toggle ──────────────────────────────────────────── */}
        {!isSuccess && (
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            marginBottom: 16,
            cursor: 'pointer',
            padding: '10px 14px',
            borderRadius: 'var(--r-md)',
            background: append ? 'var(--success-dim)' : 'var(--danger-dim)',
            border: `1px solid ${append
              ? 'rgba(46,204,113,0.2)'
              : 'rgba(255,77,77,0.2)'}`,
            transition: 'all var(--t-base)',
          }}>
            <input
              type="checkbox"
              checked={append}
              onChange={(e) => setAppend(e.target.checked)}
              style={{ width: 14, height: 14, accentColor: 'var(--amber)', cursor: 'pointer' }}
            />
            <div>
              <p style={{
                margin: 0,
                fontSize: 12,
                fontWeight: 600,
                fontFamily: 'DM Sans, sans-serif',
                color: append ? 'var(--success)' : 'var(--danger)',
              }}>
                {append ? 'Append to database' : 'Replace database'}
              </p>
              <p style={{
                margin: '2px 0 0',
                fontSize: 11,
                color: 'var(--text-muted)',
                fontFamily: 'DM Sans, sans-serif',
              }}>
                {append
                  ? 'Merges new products in — use for multiple categories'
                  : 'Wipes all existing products and replaces with this file'}
              </p>
            </div>
          </label>
        )}

        {/* ── Status messages ────────────────────────────────────────── */}
        {isUploading && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            marginBottom: 16,
            padding: '11px 14px',
            borderRadius: 'var(--r-md)',
            background: 'var(--amber-dim)',
            border: '1px solid rgba(232,163,32,0.2)',
          }}>
            <Spinner />
            <span style={{
              fontSize: 12,
              color: 'var(--amber)',
              fontFamily: 'DM Sans, sans-serif',
            }}>
              Uploading and indexing — this may take a minute…
            </span>
          </div>
        )}
        {isSuccess && (
          <div style={{
            marginBottom: 16,
            padding: '11px 14px',
            borderRadius: 'var(--r-md)',
            background: 'var(--success-dim)',
            border: '1px solid rgba(46,204,113,0.2)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircle size={14} color="var(--success)" />
              <span style={{
                fontSize: 12,
                color: 'var(--success)',
                fontWeight: 600,
                fontFamily: 'DM Sans, sans-serif',
              }}>
                {status.new_products !== undefined
                  ? `+${status.new_products.toLocaleString()} new products added`
                  : `${status.products.toLocaleString()} products loaded`}
              </span>
            </div>
            {status.new_products !== undefined && (
              <p style={{
                margin: '4px 0 0 22px',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 10,
                color: 'var(--text-muted)',
              }}>
                total: {status.products.toLocaleString()} · indexed: {status.indexed_docs.toLocaleString()}
              </p>
            )}
          </div>
        )}
        {isError && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            marginBottom: 16,
            padding: '11px 14px',
            borderRadius: 'var(--r-md)',
            background: 'var(--danger-dim)',
            border: '1px solid rgba(255,77,77,0.2)',
          }}>
            <AlertCircle size={14} color="var(--danger)" />
            <span style={{
              fontSize: 12,
              color: 'var(--danger)',
              fontFamily: 'DM Sans, sans-serif',
            }}>
              {status.error}
            </span>
          </div>
        )}

        {/* ── Actions ────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: '10px 0',
              borderRadius: 'var(--r-sm)',
              background: 'transparent',
              border: '1px solid var(--border-mid)',
              color: 'var(--text-muted)',
              fontSize: 13,
              fontFamily: 'DM Sans, sans-serif',
              cursor: 'pointer',
              transition: 'all var(--t-fast)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-bright)';
              e.currentTarget.style.color = 'var(--text-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-mid)';
              e.currentTarget.style.color = 'var(--text-muted)';
            }}
          >
            {isSuccess ? 'Close' : 'Cancel'}
          </button>

          {isSuccess ? (
            <button
              onClick={handleUploadAnother}
              style={{
                flex: 2,
                padding: '10px 0',
                borderRadius: 'var(--r-sm)',
                background: 'var(--success)',
                border: 'none',
                color: '#080808',
                fontSize: 13,
                fontWeight: 600,
                fontFamily: 'DM Sans, sans-serif',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 7,
                transition: 'opacity var(--t-fast)',
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '0.85'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
            >
              <PlusCircle size={14} />
              Add Another Category
            </button>
          ) : (
            <button
              onClick={handleUpload}
              disabled={!selectedFile || isUploading}
              style={{
                flex: 2,
                padding: '10px 0',
                borderRadius: 'var(--r-sm)',
                background: selectedFile && !isUploading ? 'var(--amber)' : 'var(--bg-hover)',
                border: 'none',
                color: selectedFile && !isUploading ? '#080808' : 'var(--text-faint)',
                fontSize: 13,
                fontWeight: 600,
                fontFamily: 'DM Sans, sans-serif',
                cursor: selectedFile && !isUploading ? 'pointer' : 'not-allowed',
                transition: 'all var(--t-base)',
                boxShadow: selectedFile && !isUploading
                  ? '0 4px 16px rgba(232,163,32,0.3)'
                  : 'none',
              }}
              onMouseEnter={(e) => {
                if (selectedFile && !isUploading) e.currentTarget.style.opacity = '0.9';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = '1';
              }}
            >
              {isUploading ? 'Indexing…' : append ? 'Append & Index' : 'Upload & Index'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
