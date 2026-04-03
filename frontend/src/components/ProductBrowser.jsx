import React from 'react';
import { RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';
import SearchBar from './SearchBar';
import CategoryFilter from './CategoryFilter';
import ProductCard from './ProductCard';
import useProducts from '../hooks/useProducts';

function SkeletonCard() {
  return (
    <div style={{
      height: 310,
      borderRadius: 'var(--r-lg)',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-dim)',
      overflow: 'hidden',
    }}>
      <div className="skeleton" style={{ height: '62%' }} />
      <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div className="skeleton" style={{ height: 8, width: '40%', borderRadius: 2 }} />
        <div className="skeleton" style={{ height: 11, width: '90%', borderRadius: 2 }} />
        <div className="skeleton" style={{ height: 11, width: '65%', borderRadius: 2 }} />
        <div className="skeleton" style={{ height: 13, width: '30%', borderRadius: 2, marginTop: 6 }} />
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 20,
      padding: 48,
    }}>
      {/* Editorial empty state — large italic letter */}
      <div style={{
        fontFamily: 'Playfair Display, Georgia, serif',
        fontSize: 96,
        fontStyle: 'italic',
        fontWeight: 700,
        color: 'var(--border-dim)',
        lineHeight: 1,
        userSelect: 'none',
      }}>
        ∅
      </div>
      <div style={{ textAlign: 'center' }}>
        <p style={{
          margin: '0 0 6px',
          fontFamily: 'Playfair Display, Georgia, serif',
          fontSize: 20,
          fontWeight: 600,
          color: 'var(--text-secondary)',
        }}>
          No products found
        </p>
        <p style={{
          margin: 0,
          fontSize: 13,
          color: 'var(--text-muted)',
          fontFamily: 'DM Sans, sans-serif',
        }}>
          Adjust your search or category filter
        </p>
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 14,
      padding: 48,
    }}>
      <p style={{
        margin: 0,
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 11,
        color: 'var(--danger)',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
      }}>
        Connection error
      </p>
      <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
        {message}
      </p>
      <button
        onClick={onRetry}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 18px',
          borderRadius: 'var(--r-sm)',
          background: 'transparent',
          border: '1px solid var(--border-mid)',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          fontSize: 12,
          fontFamily: 'DM Sans, sans-serif',
          transition: 'all var(--t-fast)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'var(--amber)';
          e.currentTarget.style.color = 'var(--amber)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'var(--border-mid)';
          e.currentTarget.style.color = 'var(--text-secondary)';
        }}
      >
        <RefreshCw size={13} />
        Retry
      </button>
    </div>
  );
}

// Pagination button component
function PageBtn({ onClick, disabled, children }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: '6px 14px',
        borderRadius: 'var(--r-sm)',
        background: 'transparent',
        border: `1px solid ${disabled ? 'var(--border-dim)' : 'var(--border-mid)'}`,
        color: disabled ? 'var(--text-faint)' : 'var(--text-secondary)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontSize: 12,
        fontFamily: 'DM Sans, sans-serif',
        fontWeight: 500,
        transition: 'all var(--t-fast)',
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.currentTarget.style.borderColor = 'var(--amber)';
          e.currentTarget.style.color = 'var(--amber)';
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled) {
          e.currentTarget.style.borderColor = 'var(--border-mid)';
          e.currentTarget.style.color = 'var(--text-secondary)';
        }
      }}
    >
      {children}
    </button>
  );
}

export default function ProductBrowser({ onProductSelect, selectedProduct }) {
  const {
    products, total, page, pages,
    loading, error,
    setQuery, setCategory, setPage, refetch,
  } = useProducts();

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
    }}>
      {/* ── Filters bar ──────────────────────────────────────────────────── */}
      <div style={{
        padding: '16px 28px 14px',
        borderBottom: '1px solid var(--border-dim)',
        background: 'rgba(8,8,8,0.7)',
        flexShrink: 0,
      }}>
        <SearchBar onSearch={setQuery} />
        <div style={{ marginTop: 10 }}>
          <CategoryFilter onFilter={setCategory} />
        </div>
        {!loading && !error && (
          <p style={{
            margin: '8px 0 0',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: 'var(--text-faint)',
            letterSpacing: '0.06em',
          }}>
            {total.toLocaleString()} products
          </p>
        )}
      </div>

      {/* ── Content ──────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px' }}>
        {error ? (
          <ErrorState message={error} onRetry={refetch} />
        ) : loading ? (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))',
            gap: 16,
          }}>
            {Array.from({ length: 12 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : products.length === 0 ? (
          <EmptyState />
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))',
              gap: 16,
            }}
          >
            {products.map((product, i) => (
              <div
                key={product.asin || product.title}
                className={`animate-fade-up stagger-${Math.min(i + 1, 8)}`}
              >
                <ProductCard
                  product={product}
                  isSelected={selectedProduct?.asin === product.asin}
                  onClick={onProductSelect}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Pagination ───────────────────────────────────────────────────── */}
      {!loading && !error && pages > 1 && (
        <div style={{
          padding: '10px 28px',
          borderTop: '1px solid var(--border-dim)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 14,
          flexShrink: 0,
          background: 'rgba(8,8,8,0.5)',
        }}>
          <PageBtn onClick={() => setPage(page - 1)} disabled={page <= 1}>
            <ChevronLeft size={14} /> Prev
          </PageBtn>

          <span style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            color: 'var(--text-muted)',
            letterSpacing: '0.04em',
          }}>
            {page} <span style={{ color: 'var(--text-faint)' }}>/ {pages}</span>
          </span>

          <PageBtn onClick={() => setPage(page + 1)} disabled={page >= pages}>
            Next <ChevronRight size={14} />
          </PageBtn>
        </div>
      )}
    </div>
  );
}
