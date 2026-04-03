module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['Playfair Display', 'Georgia', 'serif'],
        sans:    ['DM Sans', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        void:    '#080808',
        base:    '#0e0d0c',
        surface: '#141312',
        raised:  '#1c1a18',
        hover:   '#232120',
        amber:   '#E8A320',
        teal:    '#3DFFF0',
        muted:   '#6B6560',
        faint:   '#3D3B38',
      },
      animation: {
        shimmer:      'shimmer 1.8s ease-in-out infinite',
        fadeUp:       'fadeUp 0.45s cubic-bezier(0.16,1,0.3,1) both',
        slideInRight: 'slideInRight 0.35s cubic-bezier(0.16,1,0.3,1) both',
        spin:         'spin 0.8s linear infinite',
        pulseAmber:   'pulse-amber 2s ease-in-out infinite',
      }
    }
  },
  plugins: []
}
