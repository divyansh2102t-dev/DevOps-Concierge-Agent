'use client';
import { useEffect, useRef } from 'react';

export default function MermaidRenderer({ code }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!code || !containerRef.current) return;

    let cancelled = false;

    async function render() {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: 'dark',
          themeVariables: {
            primaryColor: '#4f46e5',
            primaryTextColor: '#e2e8f0',
            primaryBorderColor: '#6366f1',
            lineColor: '#64748b',
            secondaryColor: '#1a2035',
            tertiaryColor: '#131829',
          },
        });

        const id = `mermaid-${Date.now()}`;
        const { svg } = await mermaid.render(id, code);

        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (err) {
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = `<pre style="color: var(--accent-red); font-size: 12px;">${err.message}</pre>`;
        }
      }
    }

    render();
    return () => { cancelled = true; };
  }, [code]);

  return (
    <div
      ref={containerRef}
      style={{
        background: 'rgba(0,0,0,0.2)',
        borderRadius: 'var(--radius-md)',
        padding: '16px',
        margin: '8px 0',
        overflow: 'auto',
      }}
    />
  );
}
