import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = 'http://localhost:8080';

export default function useProducts() {
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [query, setQueryState] = useState('');
  const [category, setCategoryState] = useState('');

  const debounceRef = useRef(null);

  const fetchProducts = useCallback(async (q, cat, pg) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (q) params.set('search', q);
      if (cat) params.set('category', cat);
      params.set('page', pg);
      params.set('limit', 20);

      const res = await fetch(`${API_BASE}/products?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setProducts(data.products || []);
      setTotal(data.total || 0);
      setPage(data.page || 1);
      setPages(data.pages || 1);
    } catch (err) {
      setError(err.message || 'Failed to load products');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounce query changes
  const setQuery = useCallback((q) => {
    setQueryState(q);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      fetchProducts(q, category, 1);
    }, 300);
  }, [category, fetchProducts]);

  const setCategory = useCallback((cat) => {
    setCategoryState(cat);
    setPage(1);
    fetchProducts(query, cat, 1);
  }, [query, fetchProducts]);

  const goToPage = useCallback((pg) => {
    setPage(pg);
    fetchProducts(query, category, pg);
  }, [query, category, fetchProducts]);

  const refetch = useCallback(() => {
    fetchProducts(query, category, page);
  }, [query, category, page, fetchProducts]);

  // Initial load
  useEffect(() => {
    fetchProducts('', '', 1);
  }, [fetchProducts]);

  return {
    products,
    total,
    page,
    pages,
    loading,
    error,
    query,
    category,
    setQuery,
    setCategory,
    setPage: goToPage,
    refetch,
  };
}
