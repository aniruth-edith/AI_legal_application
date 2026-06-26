import axios from 'axios';

const API = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 180000,
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

API.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const register     = (u, p) => API.post('/auth/register', { username: u, password: p });
export const login        = (u, p) => {
  const f = new FormData();
  f.append('username', u);
  f.append('password', p);
  return API.post('/auth/login', f);
};

// ── Cases ─────────────────────────────────────────────────────────────────────
export const getCases     = ()      => API.get('/cases');
export const createCase   = (t, d)  => API.post('/cases', { title: t, description: d });
export const deleteCase   = (cid)   => API.delete(`/cases/${cid}`);

// ── Upload ────────────────────────────────────────────────────────────────────
export const uploadDoc    = (cid, file, onProgress) => {
  const f = new FormData();
  f.append('file', file);
  return API.post(`/upload/${cid}`, f, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => onProgress && onProgress(Math.round(e.loaded * 100 / e.total)),
  });
};
export const listDocs     = cid  => API.get(`/upload/${cid}/documents`);
export const deleteDoc    = id   => API.delete(`/upload/${id}`);

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const getUserSummary  = ()    => API.get('/dashboard/summary');
export const getCaseDashboard= cid   => API.get(`/dashboard/${cid}`);
export const getCaseTimeline = cid   => API.get(`/dashboard/${cid}/timeline`);
export const getCaseLaws     = cid   => API.get(`/dashboard/${cid}/laws`);
export const getCaseFollowup = cid   => API.get(`/dashboard/${cid}/followup`);
export const exportCase      = cid   => API.get(`/dashboard/${cid}/export`);

// ── Analysis ──────────────────────────────────────────────────────────────────
export const getAnalysis     = id    => API.get(`/analysis/${id}`);
export const reanalyse       = id    => API.post(`/analysis/${id}/reanalyse`);
export const searchCase      = (cid, q) => API.post(`/analysis/${cid}/search`, { query: q });
export const askQuestion     = (cid, q) => API.post(`/analysis/${cid}/ask`, { question: q });
export const getCaseInsights = cid   => API.get(`/analysis/${cid}/insights`);