import React, { useState, useEffect, useRef } from 'react';
import { X, Send } from 'lucide-react';
import useChat from '../hooks/useChat';

const GRADIENTS = [
  ['#1a1612', '#2a2118'],
  ['#101820', '#192030'],
  ['#0f1a15', '#172a20'],
  ['#1a1510', '#28201a'],
  ['#14101a', '#211828'],
  ['#0e1a1a', '#162828'],
];

function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) & 0xffffffff;
  return Math.abs(h);
}

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: 4, padding: '6px 0', alignItems: 'center' }}>
      {[0, 1, 2].map((i) => (
        <div key={i} className="typing-dot" style={{ animationDelay: `${i * 0.2}s` }} />
      ))}
    </div>
  );
}

function Message({ msg, isLast, isStreaming }) {
  const isUser = msg.role === 'user';
  const showTyping = isLast && !isUser && isStreaming && !msg.content;

  return (
    <div style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      gap: 8,
      alignItems: 'flex-end',
      marginBottom: 14,
      animation: 'fadeUp 0.3s cubic-bezier(0.16,1,0.3,1) both',
    }}>
      {/* AI indicator dot */}
      {!isUser && (
        <div style={{
          width: 22,
          height: 22,
          borderRadius: '50%',
          border: '1px solid var(--teal)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          boxShadow: '0 0 8px var(--teal-glow)',
        }}>
          <div style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: 'var(--teal)',
          }} />
        </div>
      )}

      <div style={{
        maxWidth: '82%',
        padding: isUser ? '9px 14px' : '10px 14px',
        borderRadius: isUser
          ? 'var(--r-md) var(--r-md) var(--r-sm) var(--r-md)'
          : 'var(--r-md) var(--r-md) var(--r-md) var(--r-sm)',
        background: isUser
          ? 'var(--amber)'
          : 'var(--bg-raised)',
        border: isUser ? 'none' : '1px solid var(--border-dim)',
        color: isUser ? '#080808' : 'var(--text-secondary)',
        fontSize: 13,
        fontFamily: 'DM Sans, sans-serif',
        fontWeight: isUser ? 500 : 400,
        lineHeight: 1.6,
        wordBreak: 'break-word',
        whiteSpace: 'pre-wrap',
      }}>
        {showTyping ? <TypingIndicator /> : msg.content}
      </div>
    </div>
  );
}

export default function ChatBot({ product, onClose }) {
  const { messages, isStreaming, sendMessage, clearMessages } = useChat();
  const [input, setInput] = useState('');
  const [imgError, setImgError] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const idx = hashStr(product.asin || product.title || '') % GRADIENTS.length;
  const [g1, g2] = GRADIENTS[idx];
  const showImage = product.image_url && !imgError;

  useEffect(() => {
    clearMessages();
    setImgError(false);
    setTimeout(() => inputRef.current?.focus(), 100);
  }, [product.asin]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput('');
    sendMessage(text, product);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = input.trim() && !isStreaming;

  return (
    <div
      className="animate-slide-in-right"
      style={{
        height: '100%',
        width: 400,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-base)',
      }}
    >
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{
        padding: '14px 16px',
        borderBottom: '1px solid var(--border-dim)',
        background: 'var(--bg-surface)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexShrink: 0,
      }}>
        {/* Product thumbnail */}
        <div style={{
          width: 44,
          height: 44,
          borderRadius: 'var(--r-md)',
          overflow: 'hidden',
          flexShrink: 0,
          border: '1px solid var(--border-dim)',
          background: `linear-gradient(145deg, ${g1}, ${g2})`,
        }}>
          {showImage ? (
            <img
              src={product.image_url}
              alt=""
              onError={() => setImgError(true)}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <div style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontFamily: 'Playfair Display, serif',
              fontSize: 20,
              fontStyle: 'italic',
              color: 'rgba(242,237,228,0.2)',
            }}>
              {(product.title || 'P')[0]}
            </div>
          )}
        </div>

        {/* Title + meta */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <p className="line-clamp-1" style={{
            margin: 0,
            fontSize: 13,
            fontWeight: 500,
            fontFamily: 'DM Sans, sans-serif',
            color: 'var(--text-primary)',
            lineHeight: 1.3,
          }}>
            {product.title}
          </p>
          <p style={{
            margin: '3px 0 0',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: 'var(--text-muted)',
            letterSpacing: '0.06em',
          }}>
            {[product.brand, product.price].filter(Boolean).join(' · ')}
          </p>
        </div>

        {/* Close */}
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: '1px solid var(--border-dim)',
            cursor: 'pointer',
            color: 'var(--text-muted)',
            padding: 6,
            borderRadius: 'var(--r-sm)',
            display: 'flex',
            alignItems: 'center',
            transition: 'all var(--t-fast)',
            flexShrink: 0,
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

      {/* ── AI label strip ───────────────────────────────────────────────── */}
      <div style={{
        padding: '6px 16px',
        background: 'var(--teal-dim)',
        borderBottom: '1px solid rgba(61,255,240,0.08)',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        flexShrink: 0,
      }}>
        <div style={{
          width: 5,
          height: 5,
          borderRadius: '50%',
          background: 'var(--teal)',
          boxShadow: '0 0 6px var(--teal)',
          animation: 'pulse-amber 2s ease-in-out infinite',
        }} />
        <span style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9,
          color: 'var(--teal)',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
        }}>
          Phi-3 · RAG context active
        </span>
      </div>

      {/* ── Messages ─────────────────────────────────────────────────────── */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px 16px 12px',
      }}>
        {messages.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '32px 16px',
            animation: 'fadeUp 0.4s ease both',
          }}>
            {/* Large italic initial */}
            <div style={{
              fontFamily: 'Playfair Display, Georgia, serif',
              fontSize: 64,
              fontStyle: 'italic',
              fontWeight: 700,
              color: 'var(--border-mid)',
              lineHeight: 1,
              marginBottom: 16,
              userSelect: 'none',
            }}>
              ?
            </div>
            <p style={{
              margin: '0 0 6px',
              fontFamily: 'Playfair Display, Georgia, serif',
              fontSize: 16,
              fontWeight: 600,
              color: 'var(--text-secondary)',
            }}>
              Ask me anything
            </p>
            <p className="line-clamp-2" style={{
              margin: 0,
              fontSize: 12,
              color: 'var(--text-muted)',
              padding: '0 20px',
              lineHeight: 1.5,
            }}>
              {product.title}
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <Message
            key={i}
            msg={msg}
            isLast={i === messages.length - 1}
            isStreaming={isStreaming}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Input area ───────────────────────────────────────────────────── */}
      <div style={{
        padding: '12px 16px 14px',
        borderTop: '1px solid var(--border-dim)',
        background: 'var(--bg-surface)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            placeholder="Ask about this product…"
            rows={1}
            style={{
              flex: 1,
              padding: '10px 14px',
              background: 'var(--bg-raised)',
              border: '1px solid var(--border-dim)',
              borderRadius: 'var(--r-md)',
              color: 'var(--text-primary)',
              fontSize: 13,
              fontFamily: 'DM Sans, sans-serif',
              resize: 'none',
              outline: 'none',
              lineHeight: 1.45,
              minHeight: 42,
              maxHeight: 100,
              transition: 'border-color var(--t-fast)',
              opacity: isStreaming ? 0.5 : 1,
            }}
            onFocus={(e) => e.target.style.borderColor = 'var(--border-bright)'}
            onBlur={(e) => e.target.style.borderColor = 'var(--border-dim)'}
          />
          <button
            onClick={handleSend}
            disabled={!canSend}
            style={{
              width: 42,
              height: 42,
              borderRadius: 'var(--r-sm)',
              background: canSend ? 'var(--amber)' : 'var(--bg-hover)',
              border: 'none',
              cursor: canSend ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'all var(--t-fast)',
              boxShadow: canSend ? '0 4px 12px rgba(232,163,32,0.3)' : 'none',
            }}
          >
            <Send size={15} color={canSend ? '#080808' : 'var(--text-faint)'} />
          </button>
        </div>
        <p style={{
          margin: '6px 0 0',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9,
          color: 'var(--text-faint)',
          textAlign: 'center',
          letterSpacing: '0.06em',
        }}>
          ↵ send · ⇧↵ newline
        </p>
      </div>
    </div>
  );
}
