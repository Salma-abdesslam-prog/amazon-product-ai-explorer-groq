import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8080';

export default function CategoryFilter({ onFilter }) {
  const [categories, setCategories] = useState([]);
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/categories`)
      .then((r) => r.json())
      .then((data) => {
        setCategories(data.categories || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleSelect = (cat) => {
    const next = cat === selected ? '' : cat;
    setSelected(next);
    onFilter(next || null);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 2 }}>
        {Array.from({ length: 7 }).map((_, i) => (
          <div
            key={i}
            className="skeleton"
            style={{
              height: 28,
              width: 72 + (i % 3) * 24,
              borderRadius: 'var(--r-sm)',
              flexShrink: 0,
            }}
          />
        ))}
      </div>
    );
  }

  const allCats = ['All', ...categories];

  return (
    <div style={{
      display: 'flex',
      gap: 6,
      overflowX: 'auto',
      paddingBottom: 2,
    }}>
      {allCats.map((cat) => {
        const catKey = cat === 'All' ? '' : cat;
        const isActive = selected === catKey;

        return (
          <button
            key={cat}
            onClick={() => handleSelect(catKey)}
            style={{
              padding: '5px 14px',
              borderRadius: 'var(--r-sm)',
              fontSize: 11,
              fontWeight: isActive ? 600 : 400,
              fontFamily: 'JetBrains Mono, monospace',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              cursor: 'pointer',
              border: `1px solid ${isActive ? 'var(--amber)' : 'var(--border-dim)'}`,
              background: isActive ? 'var(--amber-dim)' : 'transparent',
              color: isActive ? 'var(--amber)' : 'var(--text-muted)',
              whiteSpace: 'nowrap',
              flexShrink: 0,
              transition: 'all var(--t-fast)',
              boxShadow: isActive ? '0 0 10px var(--amber-dim)' : 'none',
            }}
            onMouseEnter={(e) => {
              if (!isActive) {
                e.currentTarget.style.borderColor = 'var(--border-mid)';
                e.currentTarget.style.color = 'var(--text-secondary)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isActive) {
                e.currentTarget.style.borderColor = 'var(--border-dim)';
                e.currentTarget.style.color = 'var(--text-muted)';
              }
            }}
          >
            {cat}
          </button>
        );
      })}
    </div>
  );
}
