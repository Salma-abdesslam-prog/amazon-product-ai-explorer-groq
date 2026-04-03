import React, { useState } from 'react';
import { MessageCircle } from 'lucide-react';

// Muted editorial gradients for no-image fallback
const GRADIENTS = [
  ['#1a1612', '#2a2118'],
  ['#101820', '#192030'],
  ['#0f1a15', '#172a20'],
  ['#1a1510', '#28201a'],
  ['#14101a', '#211828'],
  ['#0e1a1a', '#162828'],
];

function hashAsin(asin) {
  let h = 0;
  for (let i = 0; i < asin.length; i++) {
    h = (h * 31 + asin.charCodeAt(i)) & 0xffffffff;
  }
  return Math.abs(h);
}

// Minimal star display — just dots and a number
function StarDots({ rating }) {
  const filled = Math.round(rating);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} style={{
          width: 5,
          height: 5,
          borderRadius: '50%',
          background: i < filled ? 'var(--amber)' : 'var(--border-mid)',
          transition: 'background var(--t-fast)',
        }} />
      ))}
    </div>
  );
}

export default function ProductCard({ product, isSelected, onClick }) {
  const [hovered, setHovered] = useState(false);
  const [imgError, setImgError] = useState(false);

  const idx = hashAsin(product.asin || product.title || '') % GRADIENTS.length;
  const [g1, g2] = GRADIENTS[idx];
  const showImage = product.image_url && !imgError;

  const active = isSelected || hovered;

  return (
    <div
      onClick={() => onClick(product)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        height: 310,
        borderRadius: 'var(--r-lg)',
        background: 'var(--bg-surface)',
        border: `1px solid ${isSelected
          ? 'var(--amber)'
          : hovered
          ? 'var(--border-bright)'
          : 'var(--border-dim)'}`,
        boxShadow: isSelected
          ? '0 0 0 1px var(--amber), 0 8px 32px rgba(232,163,32,0.15)'
          : hovered
          ? '0 12px 40px rgba(0,0,0,0.6), 0 0 0 1px var(--border-mid)'
          : '0 2px 8px rgba(0,0,0,0.3)',
        transform: hovered ? 'translateY(-3px)' : 'translateY(0)',
        transition: 'all var(--t-base)',
        cursor: 'pointer',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
      }}
    >
      {/* ── Image area ─────────────────────────────────────────────────── */}
      <div style={{
        height: '62%',
        position: 'relative',
        overflow: 'hidden',
        flexShrink: 0,
        background: `linear-gradient(145deg, ${g1}, ${g2})`,
      }}>
        {showImage ? (
          <img
            src={product.image_url}
            alt={product.title}
            onError={() => setImgError(true)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transition: 'transform var(--t-slow)',
              transform: hovered ? 'scale(1.06)' : 'scale(1)',
              filter: hovered ? 'brightness(1.05)' : 'brightness(0.95)',
            }}
          />
        ) : (
          <div style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <span style={{
              fontFamily: 'Playfair Display, Georgia, serif',
              fontSize: 56,
              fontWeight: 700,
              fontStyle: 'italic',
              color: 'rgba(242,237,228,0.12)',
              userSelect: 'none',
            }}>
              {(product.title || 'P')[0].toUpperCase()}
            </span>
          </div>
        )}

        {/* Gradient fade to card bg at the bottom */}
        <div style={{
          position: 'absolute',
          bottom: 0, left: 0, right: 0,
          height: 48,
          background: 'linear-gradient(to top, var(--bg-surface), transparent)',
        }} />

        {/* Selected indicator */}
        {isSelected && (
          <div style={{
            position: 'absolute',
            top: 10,
            right: 10,
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: 'var(--amber)',
            boxShadow: '0 0 8px var(--amber)',
          }} />
        )}
      </div>

      {/* ── Info strip ─────────────────────────────────────────────────── */}
      <div style={{
        flex: 1,
        padding: '8px 12px 10px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        overflow: 'hidden',
      }}>
        {/* Brand — small caps monospace */}
        {product.brand && (
          <span style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            fontWeight: 600,
            color: hovered ? 'var(--amber)' : 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.12em',
            transition: 'color var(--t-fast)',
          }}>
            {product.brand}
          </span>
        )}

        {/* Title */}
        <p className="line-clamp-2" style={{
          margin: 0,
          fontFamily: 'DM Sans, sans-serif',
          fontSize: 13,
          fontWeight: 400,
          color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
          lineHeight: 1.45,
          transition: 'color var(--t-fast)',
        }}>
          {product.title}
        </p>

        {/* Price + rating */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: 'auto',
        }}>
          <span style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 14,
            fontWeight: 600,
            color: 'var(--amber)',
          }}>
            {product.price || '—'}
          </span>
          {product.rating > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <StarDots rating={product.rating} />
              {product.review_count > 0 && (
                <span style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 9,
                  color: 'var(--text-faint)',
                }}>
                  {product.review_count >= 1000
                    ? `${(product.review_count / 1000).toFixed(1)}k`
                    : product.review_count}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── "Ask AI" hover overlay ──────────────────────────────────────── */}
      <div style={{
        position: 'absolute',
        bottom: 0, left: 0, right: 0,
        padding: '10px 12px',
        background: 'linear-gradient(to top, rgba(14,13,12,0.98) 55%, transparent)',
        transform: hovered ? 'translateY(0)' : 'translateY(105%)',
        transition: 'transform var(--t-base)',
        display: 'flex',
        justifyContent: 'center',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 7,
          padding: '7px 18px',
          borderRadius: 'var(--r-sm)',
          background: 'var(--amber)',
          color: '#080808',
          fontSize: 12,
          fontWeight: 600,
          fontFamily: 'DM Sans, sans-serif',
          letterSpacing: '0.03em',
          boxShadow: '0 4px 16px rgba(232,163,32,0.4)',
        }}>
          <MessageCircle size={13} />
          Ask AI
        </div>
      </div>
    </div>
  );
}
