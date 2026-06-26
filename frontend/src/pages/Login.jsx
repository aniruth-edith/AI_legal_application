// import { useState } from 'react';
// import { useNavigate, Link } from 'react-router-dom';
// import { login } from '../api/client';
// import { useAuth } from '../context/AuthContext';
// import { Scale } from 'lucide-react';

// export default function Login() {
//   const [form, setForm] = useState({ username: '', password: '' });
//   const [error, setError] = useState('');
//   const [loading, setLoading] = useState(false);
//   const { loginSuccess } = useAuth();
//   const navigate = useNavigate();

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     setLoading(true);
//     setError('');
//     try {
//       const res = await login(form.username, form.password);
//       loginSuccess(res.data.access_token, form.username);
//       navigate('/');
//     } catch (err) {
//       setError(err.response?.data?.detail || 'Login failed');
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div className="min-h-screen flex items-center justify-center bg-gray-50">
//       <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
//         <div className="flex flex-col items-center mb-8">
//           <Scale size={40} className="text-primary mb-2" />
//           <h1 className="text-2xl font-bold text-primary">Judiciary AI</h1>
//           <p className="text-gray-500 text-sm mt-1">Sign in to your account</p>
//         </div>

//         <form onSubmit={handleSubmit} className="space-y-4">
//           <div>
//             <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
//             <input
//               type="text"
//               value={form.username}
//               onChange={(e) => setForm({ ...form, username: e.target.value })}
//               className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary"
//               required
//             />
//           </div>
//           <div>
//             <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
//             <input
//               type="password"
//               value={form.password}
//               onChange={(e) => setForm({ ...form, password: e.target.value })}
//               className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary"
//               required
//             />
//           </div>
//           {error && <p className="text-red-500 text-sm">{error}</p>}
//           <button
//             type="submit"
//             disabled={loading}
//             className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-primary/90 transition disabled:opacity-50"
//           >
//             {loading ? 'Signing in...' : 'Sign In'}
//           </button>
//         </form>

//         <p className="text-center text-sm text-gray-500 mt-6">
//           Don't have an account?{' '}
//           <Link to="/register" className="text-primary font-medium hover:underline">
//             Register
//           </Link>
//         </p>
//       </div>
//     </div>
//   );
// }

import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { login } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Scale, ArrowRight, Loader2, AlertCircle, Eye, EyeOff, Gavel } from 'lucide-react';

// ── Design tokens — shared judicial system (navy / parchment / gold) ──────────
const C = {
  ink:       '#0F1923',
  inkSoft:   '#1E3A5F',
  parchment: '#F7F6F2',
  paper:     '#FFFFFF',
  gold:      '#B8973A',
  goldSoft:  'rgba(184,151,58,0.14)',
  line:      '#E8E6DD',
  textMuted: '#8C8B84',
  textBody:  '#3C3A33',
  error:     '#A32D2D',
  errorBg:   '#FCEBEB',
};

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    background: C.parchment,
    fontFamily: "'Inter', -apple-system, sans-serif",
  },
  brandPanel: {
    flex: '0 0 44%',
    position: 'relative',
    background: `linear-gradient(165deg, ${C.ink} 0%, ${C.inkSoft} 100%)`,
    color: '#fff',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    padding: '56px 52px',
    overflow: 'hidden',
  },
  formPanel: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
  },
  formCard: {
    width: '100%',
    maxWidth: '400px',
  },
  eyebrow: {
    fontSize: '11px',
    fontWeight: 600,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: C.gold,
    marginBottom: '6px',
  },
  h1: {
    fontSize: '26px',
    fontWeight: 700,
    color: C.ink,
    letterSpacing: '-0.4px',
    margin: '0 0 6px',
  },
  sub: {
    fontSize: '13.5px',
    color: C.textMuted,
    marginBottom: '32px',
  },
  field: { marginBottom: '18px' },
  label: {
    display: 'block',
    fontSize: '12px',
    fontWeight: 600,
    color: C.textBody,
    marginBottom: '7px',
    letterSpacing: '0.01em',
  },
  inputWrap: { position: 'relative' },
  input: (focused, hasError) => ({
    width: '100%',
    height: '46px',
    borderRadius: '11px',
    border: `1.5px solid ${hasError ? C.error : focused ? C.gold : C.line}`,
    background: C.paper,
    padding: '0 14px',
    fontSize: '14.5px',
    color: C.ink,
    outline: 'none',
    boxShadow: focused ? `0 0 0 4px ${hasError ? 'rgba(163,45,45,0.10)' : C.goldSoft}` : 'none',
    transition: 'border-color 0.18s, box-shadow 0.18s',
    boxSizing: 'border-box',
  }),
  eyeBtn: {
    position: 'absolute',
    right: '12px',
    top: '50%',
    transform: 'translateY(-50%)',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: C.textMuted,
    display: 'flex',
    padding: '4px',
  },
  errorBox: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
    background: C.errorBg,
    border: '1px solid #F3C5C5',
    borderRadius: '10px',
    padding: '10px 12px',
    fontSize: '13px',
    color: C.error,
    marginBottom: '18px',
  },
  submitBtn: (loading) => ({
    width: '100%',
    height: '48px',
    borderRadius: '11px',
    border: 'none',
    background: C.ink,
    color: '#fff',
    fontSize: '14.5px',
    fontWeight: 600,
    cursor: loading ? 'default' : 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    transition: 'background 0.18s, transform 0.05s',
    marginTop: '6px',
  }),
  footerText: {
    textAlign: 'center',
    fontSize: '13.5px',
    color: C.textMuted,
    marginTop: '28px',
  },
  link: { color: C.gold, fontWeight: 600, textDecoration: 'none' },

  // Brand panel decoration
  sealWrap: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -56%)',
    opacity: 0.10,
    pointerEvents: 'none',
  },
  brandTop: { position: 'relative', zIndex: 1 },
  brandLogo: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '19px',
    fontWeight: 700,
    letterSpacing: '0.01em',
  },
  brandQuoteWrap: { position: 'relative', zIndex: 1, maxWidth: '380px' },
  brandQuote: {
    fontSize: '22px',
    lineHeight: 1.45,
    fontWeight: 500,
    letterSpacing: '-0.2px',
    color: '#F2F1EC',
  },
  brandQuoteAccent: { color: C.gold },
  brandMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginTop: '20px',
    fontSize: '12px',
    color: 'rgba(255,255,255,0.55)',
    letterSpacing: '0.03em',
  },
  dot: (active) => ({
    width: active ? '18px' : '6px',
    height: '6px',
    borderRadius: '99px',
    background: active ? C.gold : 'rgba(255,255,255,0.25)',
    transition: 'all 0.4s ease',
  }),
};

const GlobalStyles = () => (
  <style>{`
    @keyframes fadeUp { from { opacity:0; transform: translateY(14px); } to { opacity:1; transform: translateY(0); } }
    @keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
    @keyframes shake { 10%,90%{transform:translateX(-1px)} 20%,80%{transform:translateX(2px)} 30%,50%,70%{transform:translateX(-4px)} 40%,60%{transform:translateX(4px)} }
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes drift { 0%{transform:translate(-50%,-56%) rotate(0deg)} 100%{transform:translate(-50%,-56%) rotate(360deg)} }
    @keyframes scalesTilt { 0%,100%{transform:rotate(0deg)} 50%{transform:rotate(-4deg)} }
    .fade-up { animation: fadeUp 0.5s cubic-bezier(0.22,1,0.36,1) both; }
    .fade-in { animation: fadeIn 0.4s ease both; }
    .shake { animation: shake 0.45s ease; }
    .spin { animation: spin 0.85s linear infinite; }
    .seal-spin { animation: drift 60s linear infinite; }
    .auth-submit:hover:not(:disabled) { background: #1a2a38 !important; }
    .auth-submit:active:not(:disabled) { transform: scale(0.985); }
    .auth-link:hover { text-decoration: underline; }
    @media (max-width: 860px) {
      .brand-panel { display: none !important; }
    }
    @media (prefers-reduced-motion: reduce) {
      .fade-up, .fade-in, .seal-spin, .shake { animation: none !important; }
    }
  `}</style>
);

function BrandPanel({ quoteIndex }) {
  const quotes = [
    { text: 'Justice delayed is documentation lost. Build the timeline as the case happens.', tag: 'Case continuity' },
    { text: 'Every filing carries a thread to the next. The system should see it before you do.', tag: 'Follow-up intelligence' },
    { text: 'Statutes, entities, risk — read once, surfaced everywhere they matter.', tag: 'Structured analysis' },
  ];
  const q = quotes[quoteIndex % quotes.length];

  return (
    <div style={styles.brandPanel} className="brand-panel">
      <div style={styles.sealWrap} className="seal-spin">
        <svg width="420" height="420" viewBox="0 0 420 420" fill="none">
          <circle cx="210" cy="210" r="200" stroke="#fff" strokeWidth="1" strokeDasharray="2 6" />
          <circle cx="210" cy="210" r="160" stroke="#fff" strokeWidth="1" />
          {Array.from({ length: 24 }).map((_, i) => {
            const angle = (i / 24) * Math.PI * 2;
            const x1 = 210 + Math.cos(angle) * 160;
            const y1 = 210 + Math.sin(angle) * 160;
            const x2 = 210 + Math.cos(angle) * 172;
            const y2 = 210 + Math.sin(angle) * 172;
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#fff" strokeWidth="1.5" />;
          })}
        </svg>
      </div>

      <div style={styles.brandTop} className="fade-up">
        <div style={styles.brandLogo}>
          <Scale size={22} color={C.gold} />
          Legal<span style={{ color: C.gold }}>AI</span>
        </div>
      </div>

      <div style={styles.brandQuoteWrap} className="fade-up" key={quoteIndex}>
        <Gavel size={20} color={C.gold} style={{ marginBottom: '18px', opacity: 0.8 }} />
        <p style={styles.brandQuote}>{q.text}</p>
        <div style={styles.brandMeta}>
          <span>{q.tag}</span>
          <span style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.15)' }} />
          <div style={{ display: 'flex', gap: '5px' }}>
            {quotes.map((_, i) => <span key={i} style={styles.dot(i === quoteIndex)} />)}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Login() {
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [focused, setFocused] = useState('');
  const [shake, setShake] = useState(false);
  const [quoteIndex, setQuoteIndex] = useState(0);
  const { loginSuccess } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const t = setInterval(() => setQuoteIndex(i => i + 1), 5000);
    return () => clearInterval(t);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await login(form.username, form.password);
      loginSuccess(res.data.access_token, form.username);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid username or password');
      setShake(true);
      setTimeout(() => setShake(false), 450);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <GlobalStyles />
      <div style={styles.page}>
        <BrandPanel quoteIndex={quoteIndex} />

        <div style={styles.formPanel}>
          <div style={styles.formCard} className={`fade-up ${shake ? 'shake' : ''}`}>
            <div style={styles.eyebrow}>Welcome back</div>
            <h1 style={styles.h1}>Sign in to your workspace</h1>
            <p style={styles.sub}>Pick up your cases right where you left off.</p>

            <form onSubmit={handleSubmit}>
              <div style={styles.field}>
                <label style={styles.label}>Username</label>
                <input
                  type="text"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  onFocus={() => setFocused('username')}
                  onBlur={() => setFocused('')}
                  style={styles.input(focused === 'username', false)}
                  placeholder="e.g. adv.sharma"
                  autoComplete="username"
                  required
                />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Password</label>
                <div style={styles.inputWrap}>
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    onFocus={() => setFocused('password')}
                    onBlur={() => setFocused('')}
                    style={{ ...styles.input(focused === 'password', false), paddingRight: '42px' }}
                    autoComplete="current-password"
                    required
                  />
                  <button type="button" style={styles.eyeBtn} onClick={() => setShowPw(s => !s)} tabIndex={-1} aria-label={showPw ? 'Hide password' : 'Show password'}>
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {error && (
                <div style={styles.errorBox} className="fade-in">
                  <AlertCircle size={15} style={{ flexShrink: 0, marginTop: '1px' }} />
                  <span>{error}</span>
                </div>
              )}

              <button type="submit" disabled={loading} className="auth-submit" style={styles.submitBtn(loading)}>
                {loading ? (
                  <><Loader2 size={16} className="spin" /> Signing in…</>
                ) : (
                  <>Sign in <ArrowRight size={15} /></>
                )}
              </button>
            </form>

            <p style={styles.footerText}>
              Don't have an account?{' '}
              <Link to="/register" className="auth-link" style={styles.link}>
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}