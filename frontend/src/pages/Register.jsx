// import { useState } from 'react';
// import { useNavigate, Link } from 'react-router-dom';
// import { register } from '../api/client';
// import { useAuth } from '../context/AuthContext';
// import { Scale } from 'lucide-react';

// export default function Register() {
//   const [form, setForm] = useState({ username: '', password: '', confirm: '' });
//   const [error, setError] = useState('');
//   const [loading, setLoading] = useState(false);
//   const { loginSuccess } = useAuth();
//   const navigate = useNavigate();

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     if (form.password !== form.confirm) {
//       setError('Passwords do not match');
//       return;
//     }
//     setLoading(true);
//     setError('');
//     try {
//       const res = await register(form.username, form.password);
//       loginSuccess(res.data.access_token, form.username);
//       navigate('/');
//     } catch (err) {
//       setError(err.response?.data?.detail || 'Registration failed');
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div className="min-h-screen flex items-center justify-center bg-gray-50">
//       <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
//         <div className="flex flex-col items-center mb-8">
//           <Scale size={40} className="text-primary mb-2" />
//           <h1 className="text-2xl font-bold text-primary">Create Account</h1>
//           <p className="text-gray-500 text-sm mt-1">Start analysing legal documents</p>
//         </div>

//         <form onSubmit={handleSubmit} className="space-y-4">
//           {['username', 'password', 'confirm'].map((field) => (
//             <div key={field}>
//               <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">
//                 {field === 'confirm' ? 'Confirm Password' : field}
//               </label>
//               <input
//                 type={field !== 'username' ? 'password' : 'text'}
//                 value={form[field]}
//                 onChange={(e) => setForm({ ...form, [field]: e.target.value })}
//                 className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary"
//                 required
//               />
//             </div>
//           ))}
//           {error && <p className="text-red-500 text-sm">{error}</p>}
//           <button
//             type="submit"
//             disabled={loading}
//             className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-primary/90 transition disabled:opacity-50"
//           >
//             {loading ? 'Creating account...' : 'Register'}
//           </button>
//         </form>

//         <p className="text-center text-sm text-gray-500 mt-6">
//           Already have an account?{' '}
//           <Link to="/login" className="text-primary font-medium hover:underline">
//             Sign in
//           </Link>
//         </p>
//       </div>
//     </div>
//   );
// }

import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Scale, ArrowRight, Loader2, AlertCircle, Eye, EyeOff, Check, FileText, BarChart2, MessageCircle } from 'lucide-react';

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
  good:      '#3B6D11',
  goodBg:    '#EAF3DE',
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
  formCard: { width: '100%', maxWidth: '400px' },
  eyebrow: {
    fontSize: '11px', fontWeight: 600, letterSpacing: '0.12em',
    textTransform: 'uppercase', color: C.gold, marginBottom: '6px',
  },
  h1: { fontSize: '26px', fontWeight: 700, color: C.ink, letterSpacing: '-0.4px', margin: '0 0 6px' },
  sub: { fontSize: '13.5px', color: C.textMuted, marginBottom: '28px' },
  field: { marginBottom: '16px' },
  label: { display: 'block', fontSize: '12px', fontWeight: 600, color: C.textBody, marginBottom: '7px' },
  inputWrap: { position: 'relative' },
  input: (focused, state) => ({
    width: '100%',
    height: '46px',
    borderRadius: '11px',
    border: `1.5px solid ${state === 'error' ? C.error : state === 'good' ? C.good : focused ? C.gold : C.line}`,
    background: C.paper,
    padding: '0 14px',
    fontSize: '14.5px',
    color: C.ink,
    outline: 'none',
    boxShadow: focused ? `0 0 0 4px ${state === 'error' ? 'rgba(163,45,45,0.10)' : C.goldSoft}` : 'none',
    transition: 'border-color 0.18s, box-shadow 0.18s',
    boxSizing: 'border-box',
  }),
  eyeBtn: {
    position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
    background: 'none', border: 'none', cursor: 'pointer', color: C.textMuted, display: 'flex', padding: '4px',
  },
  matchIcon: {
    position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
    display: 'flex', pointerEvents: 'none',
  },
  strengthRow: { display: 'flex', gap: '4px', marginTop: '8px' },
  strengthSeg: (active, color) => ({
    height: '4px', flex: 1, borderRadius: '99px',
    background: active ? color : C.line, transition: 'background 0.25s',
  }),
  strengthLabel: { fontSize: '11px', color: C.textMuted, marginTop: '6px' },
  errorBox: {
    display: 'flex', alignItems: 'flex-start', gap: '8px',
    background: C.errorBg, border: '1px solid #F3C5C5', borderRadius: '10px',
    padding: '10px 12px', fontSize: '13px', color: C.error, marginBottom: '18px',
  },
  submitBtn: (loading, disabled) => ({
    width: '100%', height: '48px', borderRadius: '11px', border: 'none',
    background: disabled ? '#B7B5AC' : C.ink, color: '#fff', fontSize: '14.5px', fontWeight: 600,
    cursor: (loading || disabled) ? 'default' : 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
    transition: 'background 0.18s, transform 0.05s', marginTop: '8px',
  }),
  footerText: { textAlign: 'center', fontSize: '13.5px', color: C.textMuted, marginTop: '26px' },
  link: { color: C.gold, fontWeight: 600, textDecoration: 'none' },

  brandLogo: { display: 'flex', alignItems: 'center', gap: '10px', fontSize: '19px', fontWeight: 700 },
  featureList: { position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', gap: '20px' },
  featureRow: { display: 'flex', alignItems: 'flex-start', gap: '14px' },
  featureIconBox: {
    width: '38px', height: '38px', borderRadius: '11px', background: 'rgba(184,151,58,0.16)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  featureTitle: { fontSize: '14.5px', fontWeight: 600, color: '#fff', marginBottom: '2px' },
  featureDesc: { fontSize: '12.5px', color: 'rgba(255,255,255,0.6)', lineHeight: 1.5 },
  gridDots: { position: 'absolute', inset: 0, opacity: 0.06, pointerEvents: 'none' },
};

const GlobalStyles = () => (
  <style>{`
    @keyframes fadeUp { from { opacity:0; transform: translateY(14px); } to { opacity:1; transform: translateY(0); } }
    @keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
    @keyframes popIn { from { opacity:0; transform: scale(0.5); } to { opacity:1; transform: scale(1); } }
    @keyframes shake { 10%,90%{transform:translateX(-1px)} 20%,80%{transform:translateX(2px)} 30%,50%,70%{transform:translateX(-4px)} 40%,60%{transform:translateX(4px)} }
    @keyframes spin { to { transform: rotate(360deg); } }
    .fade-up { animation: fadeUp 0.5s cubic-bezier(0.22,1,0.36,1) both; }
    .fade-in { animation: fadeIn 0.4s ease both; }
    .pop-in { animation: popIn 0.25s cubic-bezier(0.34,1.56,0.64,1) both; }
    .shake { animation: shake 0.45s ease; }
    .spin { animation: spin 0.85s linear infinite; }
    .feature-row { animation: fadeUp 0.5s cubic-bezier(0.22,1,0.36,1) both; }
    .auth-submit:hover:not(:disabled) { background: #1a2a38 !important; }
    .auth-submit:active:not(:disabled) { transform: scale(0.985); }
    .auth-link:hover { text-decoration: underline; }
    @media (max-width: 860px) { .brand-panel { display: none !important; } }
    @media (prefers-reduced-motion: reduce) { .fade-up, .fade-in, .pop-in, .shake, .feature-row { animation: none !important; } }
  `}</style>
);

function passwordStrength(pw) {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return score; // 0-4
}
const STRENGTH_META = [
  { label: 'Too short', color: C.error },
  { label: 'Weak', color: C.error },
  { label: 'Fair', color: C.gold },
  { label: 'Good', color: '#185FA5' },
  { label: 'Strong', color: C.good },
];

function BrandPanel() {
  const features = [
    { icon: FileText, title: 'Upload once, analysed everywhere', desc: 'Every filing is read, classified, and cross-referenced automatically.' },
    { icon: BarChart2, title: 'Statutes surfaced, not searched for', desc: 'IPC and CrPC sections identified with confidence scores per document.' },
    { icon: MessageCircle, title: 'Ask your case a question', desc: 'Grounded answers with reasoning and source citations, not guesses.' },
  ];
  return (
    <div style={styles.brandPanel} className="brand-panel">
      <div style={styles.gridDots}>
        <svg width="100%" height="100%">
          <pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.4" fill="#fff" />
          </pattern>
          <rect width="100%" height="100%" fill="url(#dots)" />
        </svg>
      </div>

      <div style={styles.brandLogo} className="fade-up">
        <Scale size={22} color={C.gold} />
        Legal<span style={{ color: C.gold }}>AI</span>
      </div>

      <div style={styles.featureList}>
        {features.map((f, i) => {
          const Icon = f.icon;
          return (
            <div key={i} className="feature-row" style={{ ...styles.featureRow, animationDelay: `${0.1 + i * 0.1}s` }}>
              <div style={styles.featureIconBox}><Icon size={17} color={C.gold} /></div>
              <div>
                <div style={styles.featureTitle}>{f.title}</div>
                <div style={styles.featureDesc}>{f.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ position: 'relative', zIndex: 1, fontSize: '12px', color: 'rgba(255,255,255,0.45)' }}>
        Built for case teams who'd rather argue the law than chase the paperwork.
      </div>
    </div>
  );
}

export default function Register() {
  const [form, setForm] = useState({ username: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [focused, setFocused] = useState('');
  const [shake, setShake] = useState(false);
  const { loginSuccess } = useAuth();
  const navigate = useNavigate();

  const strength = passwordStrength(form.password);
  const confirmTouched = form.confirm.length > 0;
  const passwordsMatch = confirmTouched && form.confirm === form.password;
  const passwordsMismatch = confirmTouched && form.confirm !== form.password;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      setError('Passwords do not match');
      setShake(true);
      setTimeout(() => setShake(false), 450);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await register(form.username, form.password);
      loginSuccess(res.data.access_token, form.username);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed — try a different username');
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
        <BrandPanel />

        <div style={styles.formPanel}>
          <div style={styles.formCard} className={`fade-up ${shake ? 'shake' : ''}`}>
            <div style={styles.eyebrow}>Get started</div>
            <h1 style={styles.h1}>Create your account</h1>
            <p style={styles.sub}>Start analysing case documents in minutes.</p>

            <form onSubmit={handleSubmit}>
              <div style={styles.field}>
                <label style={styles.label}>Username</label>
                <input
                  type="text"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  onFocus={() => setFocused('username')}
                  onBlur={() => setFocused('')}
                  style={styles.input(focused === 'username', null)}
                  placeholder="Choose a username"
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
                    style={{ ...styles.input(focused === 'password', null), paddingRight: '42px' }}
                    autoComplete="new-password"
                    required
                  />
                  <button type="button" style={styles.eyeBtn} onClick={() => setShowPw(s => !s)} tabIndex={-1} aria-label={showPw ? 'Hide password' : 'Show password'}>
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {form.password.length > 0 && (
                  <div className="fade-in">
                    <div style={styles.strengthRow}>
                      {[0, 1, 2, 3].map(i => (
                        <div key={i} style={styles.strengthSeg(i < strength, STRENGTH_META[strength].color)} />
                      ))}
                    </div>
                    <div style={{ ...styles.strengthLabel, color: STRENGTH_META[strength].color }}>
                      {STRENGTH_META[strength].label}
                    </div>
                  </div>
                )}
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Confirm password</label>
                <div style={styles.inputWrap}>
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={form.confirm}
                    onChange={(e) => setForm({ ...form, confirm: e.target.value })}
                    onFocus={() => setFocused('confirm')}
                    onBlur={() => setFocused('')}
                    style={{
                      ...styles.input(focused === 'confirm', passwordsMismatch ? 'error' : passwordsMatch ? 'good' : null),
                      paddingRight: '42px',
                    }}
                    autoComplete="new-password"
                    required
                  />
                  {passwordsMatch && (
                    <span style={styles.matchIcon} className="pop-in">
                      <Check size={16} color={C.good} />
                    </span>
                  )}
                </div>
                {passwordsMismatch && (
                  <div style={{ fontSize: '11px', color: C.error, marginTop: '6px' }}>Passwords don't match yet</div>
                )}
              </div>

              {error && (
                <div style={styles.errorBox} className="fade-in">
                  <AlertCircle size={15} style={{ flexShrink: 0, marginTop: '1px' }} />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="auth-submit"
                style={styles.submitBtn(loading, false)}
              >
                {loading ? (
                  <><Loader2 size={16} className="spin" /> Creating account…</>
                ) : (
                  <>Create account <ArrowRight size={15} /></>
                )}
              </button>
            </form>

            <p style={styles.footerText}>
              Already have an account?{' '}
              <Link to="/login" className="auth-link" style={styles.link}>
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}