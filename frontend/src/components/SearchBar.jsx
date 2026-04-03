import React, { useState, useEffect, useRef } from 'react';
import { Search, X } from 'lucide-react';

const PLACEHOLDER_EXAMPLES = [
  'headphones',
  'laptops',
  'coffee makers',
  'running shoes',
  'smart watches',
  'gaming mice',
];

export default function SearchBar({ onSearch }) {
  const [value, setValue] = useState('');
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const [focused, setFocused] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    const id = setInterval(() => {
      setPlaceholderIdx((i) => (i + 1) % PLACEHOLDER_EXAMPLES.length);
    }, 3000);
    return () => clearInterval(id);
  }, []);

  const handleChange = (e) => {
    const val = e.target.value;
    setValue(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onSearch(val), 300);
  };

  const handleClear = () => {
    setValue('');
    onSearch('');
  };

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      {/* Search icon */}
      <div style={{
        position: 'absolute',
        left: 16,
        top: '50%',
        transform: 'translateY(-50%)',
        color: focused ? 'var(--amber)' : 'var(--text-muted)',
        pointerEvents: 'none',
        display: 'flex',
        alignItems: 'center',
        transition: 'color var(--t-base)',
      }}>
        <Search size={16} />
      </div>

      <input
        type="text"
        value={value}
        onChange={handleChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={`Search for ${PLACEHOLDER_EXAMPLES[placeholderIdx]}…`}
        style={{
          width: '100%',
          padding: '12px 44px',
          background: focused ? 'var(--bg-raised)' : 'var(--bg-surface)',
          border: `1px solid ${focused ? 'var(--amber)' : 'var(--border-dim)'}`,
          borderRadius: 'var(--r-md)',
          color: 'var(--text-primary)',
          fontSize: 14,
          fontFamily: 'DM Sans, sans-serif',
          fontWeight: 400,
          outline: 'none',
          transition: 'all var(--t-base)',
          boxSizing: 'border-box',
          boxShadow: focused ? '0 0 0 3px var(--amber-dim)' : 'none',
        }}
      />

      {value && (
        <button
          onClick={handleClear}
          style={{
            position: 'absolute',
            right: 12,
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            padding: 4,
            borderRadius: 'var(--r-sm)',
            transition: 'color var(--t-fast)',
          }}
          onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'}
          onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
