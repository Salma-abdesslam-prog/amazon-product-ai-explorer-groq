import React, { useState } from 'react';
import { Upload } from 'lucide-react';
import ProductBrowser from './components/ProductBrowser';
import ChatBot from './components/ChatBot';
import UploadPanel from './components/UploadPanel';

export default function App() {
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleProductSelect = (product) => {
    setSelectedProduct(product);
    setIsChatOpen(true);
  };

  const handleChatClose = () => setIsChatOpen(false);

  const handleIngested = () => {
    setShowUpload(false);
    setRefreshKey((k) => k + 1);
  };

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg-void)',
      overflow: 'hidden',
    }}>
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header style={{
        padding: '0 40px',
        height: 64,
        borderBottom: '1px solid var(--border-dim)',
        background: 'rgba(8,8,8,0.96)',
        backdropFilter: 'blur(20px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
        position: 'relative',
        zIndex: 10,
      }}>
        {/* Amber accent line along the bottom of header */}
        <div style={{
          position: 'absolute',
          bottom: 0, left: 0, right: 0,
          height: 1,
          background: 'linear-gradient(90deg, transparent, var(--amber) 30%, var(--teal) 70%, transparent)',
          opacity: 0.5,
        }} />

        {/* Logo + wordmark */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {/* Logo mark */}
          <div style={{
            width: 32,
            height: 32,
            position: 'relative',
            flexShrink: 0,
          }}>
            {/* Outer ring */}
            <div style={{
              position: 'absolute',
              inset: 0,
              borderRadius: '50%',
              border: '1px solid var(--amber)',
              opacity: 0.7,
            }} />
            {/* Inner dot */}
            <div style={{
              position: 'absolute',
              inset: '30%',
              borderRadius: '50%',
              background: 'var(--amber)',
              boxShadow: '0 0 8px var(--amber-glow)',
            }} />
          </div>

          <div>
            <h1 style={{
              margin: 0,
              fontFamily: 'Playfair Display, Georgia, serif',
              fontSize: 19,
              fontWeight: 600,
              color: 'var(--text-primary)',
              letterSpacing: '0.01em',
              lineHeight: 1.1,
            }}>
              Amazone Product AI Explorer
            </h1>
            <p style={{
              margin: 0,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              color: 'var(--text-muted)',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              marginTop: 2,
            }}>
              RAG-powered catalogue
            </p>
          </div>
        </div>

        {/* Upload button */}
        <button
          onClick={() => setShowUpload(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 20px',
            borderRadius: 'var(--r-sm)',
            background: 'transparent',
            border: '1px solid var(--border-mid)',
            cursor: 'pointer',
            color: 'var(--text-secondary)',
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: '0.02em',
            transition: 'all var(--t-base)',
            fontFamily: 'DM Sans, sans-serif',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--amber)';
            e.currentTarget.style.color = 'var(--amber)';
            e.currentTarget.style.background = 'var(--amber-dim)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-mid)';
            e.currentTarget.style.color = 'var(--text-secondary)';
            e.currentTarget.style.background = 'transparent';
          }}
        >
          <Upload size={13} />
          Upload Data
        </button>
      </header>

      {/* ── Main content ────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Product browser */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <ProductBrowser
            key={refreshKey}
            onProductSelect={handleProductSelect}
            selectedProduct={selectedProduct}
          />
        </div>

        {/* Chat panel — slides in from right */}
        <div style={{
          width: isChatOpen ? 400 : 0,
          flexShrink: 0,
          overflow: 'hidden',
          transition: 'width 360ms cubic-bezier(0.16,1,0.3,1)',
          borderLeft: isChatOpen ? '1px solid var(--border-dim)' : 'none',
        }}>
          {selectedProduct && (
            <ChatBot product={selectedProduct} onClose={handleChatClose} />
          )}
        </div>
      </div>

      {/* ── Upload modal ────────────────────────────────────────────────────── */}
      {showUpload && (
        <UploadPanel
          onClose={() => setShowUpload(false)}
          onIngested={handleIngested}
        />
      )}
    </div>
  );
}
