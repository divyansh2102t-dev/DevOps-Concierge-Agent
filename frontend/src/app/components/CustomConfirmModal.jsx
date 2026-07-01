'use client';

export default function CustomConfirmModal({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDestructive = false
}) {
  if (!isOpen) return null;

  return (
    <div 
      className="modal-overlay" 
      style={{ 
        zIndex: 2000, 
        animation: 'fadeIn 0.2s ease-out',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(5, 7, 10, 0.85)',
        backdropFilter: 'blur(8px)'
      }}
    >
      <div 
        className="auth-modal" 
        style={{ 
          maxWidth: '420px', 
          width: '90%', 
          padding: '24px', 
          borderRadius: '16px',
          border: isDestructive ? '1px solid rgba(239, 68, 68, 0.25)' : '1px solid var(--border-glass)',
          background: 'linear-gradient(135deg, rgba(20, 26, 35, 0.95) 0%, rgba(13, 17, 23, 0.95) 100%)',
          boxShadow: isDestructive ? '0 10px 40px rgba(239, 68, 68, 0.12)' : '0 10px 40px rgba(6, 182, 212, 0.08)',
          transform: 'scale(1)',
          animation: 'scaleUp 0.25s cubic-bezier(0.34, 1.56, 0.64, 1)',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxSizing: 'border-box'
        }}
      >
        {/* ICON AND TITLE */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ 
            fontSize: '28px',
            filter: isDestructive ? 'drop-shadow(0 0 8px rgba(239, 68, 68, 0.4))' : 'none'
          }}>
            {isDestructive ? '⚠️' : '❓'}
          </span>
          <h3 style={{ 
            margin: 0, 
            fontSize: '18px', 
            fontWeight: '800',
            color: '#fff',
            letterSpacing: '-0.3px'
          }}>
            {title}
          </h3>
        </div>

        {/* MESSAGE */}
        <p style={{ 
          margin: 0, 
          fontSize: '13px', 
          color: 'var(--text-secondary)', 
          lineHeight: '1.6' 
        }}>
          {message}
        </p>

        {/* ACTIONS */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'flex-end', 
          gap: '10px',
          marginTop: '8px'
        }}>
          {/* CANCEL */}
          <button
            onClick={onCancel}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid var(--border-glass)',
              background: 'rgba(255, 255, 255, 0.03)',
              color: 'var(--text-secondary)',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
              e.currentTarget.style.color = '#fff';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
              e.currentTarget.style.color = 'var(--text-secondary)';
            }}
          >
            {cancelText}
          </button>

          {/* CONFIRM */}
          <button
            onClick={onConfirm}
            style={{
              padding: '8px 18px',
              borderRadius: '8px',
              border: 'none',
              background: isDestructive 
                ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)' 
                : 'var(--gradient-accent)',
              color: '#fff',
              fontSize: '12px',
              fontWeight: '700',
              cursor: 'pointer',
              transition: 'all 0.2s',
              boxShadow: isDestructive 
                ? '0 4px 12px rgba(239, 68, 68, 0.2)' 
                : 'var(--shadow-glow)'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.opacity = '0.9';
              if (isDestructive) {
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(239, 68, 68, 0.35)';
              } else {
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(6, 182, 212, 0.35)';
              }
            }}
            onMouseLeave={e => {
              e.currentTarget.style.opacity = '1';
              e.currentTarget.style.boxShadow = isDestructive 
                ? '0 4px 12px rgba(239, 68, 68, 0.2)' 
                : 'var(--shadow-glow)';
            }}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
