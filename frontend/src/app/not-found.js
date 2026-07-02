'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function NotFound() {
  const router = useRouter();
  const [countdown, setCountdown] = useState(10);

  useEffect(() => {
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          if (typeof window !== 'undefined' && window.history.length > 1) {
            window.history.back();
          } else {
            router.push('/');
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [router]);

  const handleBack = () => {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      window.history.back();
    } else {
      router.push('/');
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(circle at center, #1e1b4b 0%, #030712 100%)',
      color: '#fff',
      fontFamily: 'Inter, system-ui, sans-serif',
      padding: '20px',
      overflow: 'hidden',
      position: 'relative'
    }}>
      {/* Background Neon Glows */}
      <div style={{
        position: 'absolute',
        width: '500px',
        height: '500px',
        background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)',
        top: '10%',
        left: '15%',
        filter: 'blur(40px)',
        pointerEvents: 'none'
      }} />
      <div style={{
        position: 'absolute',
        width: '400px',
        height: '400px',
        background: 'radial-gradient(circle, rgba(236, 72, 153, 0.1) 0%, transparent 70%)',
        bottom: '10%',
        right: '15%',
        filter: 'blur(40px)',
        pointerEvents: 'none'
      }} />

      {/* Decorative Grid Lines */}
      <div style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px)',
        backgroundSize: '40px 40px',
        backgroundPosition: 'center',
        maskImage: 'radial-gradient(circle, black 40%, transparent 80%)',
        pointerEvents: 'none'
      }} />

      {/* Main Glassmorphic Card */}
      <div style={{
        position: 'relative',
        background: 'rgba(17, 24, 39, 0.7)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '24px',
        padding: '60px 40px',
        textAlign: 'center',
        maxWidth: '500px',
        width: '100%',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        zIndex: 10
      }}>
        {/* Glowing 404 Title */}
        <h1 style={{
          fontSize: '120px',
          fontWeight: '900',
          margin: 0,
          background: 'linear-gradient(135deg, #a5b4fc 0%, #6366f1 50%, #ec4899 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          lineHeight: '1',
          letterSpacing: '-2px',
          filter: 'drop-shadow(0 0 20px rgba(99, 102, 241, 0.3))',
        }}>
          404
        </h1>

        <h2 style={{
          fontSize: '24px',
          fontWeight: '700',
          marginTop: '20px',
          marginBottom: '10px',
          color: '#f3f4f6'
        }}>
          Lost in HyperSpace
        </h2>

        <p style={{
          fontSize: '14px',
          color: '#9ca3af',
          lineHeight: '1.6',
          maxWidth: '380px',
          margin: '0 auto 30px'
        }}>
          The page you are looking for has migrated or does not exist. We are navigating you back to safety.
        </p>

        {/* Progress Countdown Bar */}
        <div style={{
          width: '100%',
          height: '6px',
          background: 'rgba(255, 255, 255, 0.05)',
          borderRadius: '3px',
          overflow: 'hidden',
          marginBottom: '30px',
          position: 'relative'
        }}>
          <div style={{
            height: '100%',
            width: `${(countdown / 10) * 100}%`,
            background: 'linear-gradient(90deg, #6366f1 0%, #ec4899 100%)',
            transition: 'width 1s linear',
            boxShadow: '0 0 8px rgba(99, 102, 241, 0.5)'
          }} />
        </div>

        {/* Action Button & Timer Label */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '12px'
        }}>
          <button 
            onClick={handleBack}
            style={{
              padding: '12px 28px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
              color: '#fff',
              fontSize: '14px',
              fontWeight: '600',
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)',
              outline: 'none'
            }}
          >
            Go Back Now
          </button>
          
          <span style={{
            fontSize: '12px',
            color: '#6b7280',
            fontWeight: '500'
          }}>
            Automatically redirecting in <span style={{ color: '#ec4899', fontWeight: '700' }}>{countdown}s</span>
          </span>
        </div>
      </div>
    </div>
  );
}
