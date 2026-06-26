import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getCaseDashboard, getCaseTimeline, uploadDoc,
  deleteDoc, askQuestion, getCaseFollowup, getAnalysis
} from '../api/client';
import { useToast } from '../context/ToastContext';
import Sidebar from '../components/Sidebar';
import { getCases } from '../api/client';
import {
  ArrowLeft, Upload, FileText, ChevronDown, ChevronUp,
  Scale, TrendingUp, Bell, AlertTriangle, User, Building,
  Calendar, MapPin, RefreshCw, Trash2, Eye, MessageCircle,
  Send, X, CheckCircle, Clock, Download, ExternalLink,
  BookOpen, Gavel, Shield, ArrowRight, BarChart2, Layers,
  Sparkles, FolderOpen
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts';


// ── Design Tokens ──────────────────────────────────────────────────────────────
// Palette: deep navy ink, warm parchment, judicial gold, soft grays
// Signature: animated document-state "pulse" on the timeline connector

const DOC_TYPE_BADGE = {
  judgment:    { cls: 'badge-judgment',    label: 'Judgment' },
  petition:    { cls: 'badge-petition',    label: 'Petition' },
  FIR:         { cls: 'badge-fir',         label: 'FIR' },
  chargesheet: { cls: 'badge-chargesheet', label: 'Chargesheet' },
  statute:     { cls: 'badge-statute',     label: 'Statute' },
  'bail order':{ cls: 'badge-bail',        label: 'Bail Order' },
  writ:        { cls: 'badge-writ',        label: 'Writ' },
  affidavit:   { cls: 'badge-default',     label: 'Affidavit' },
};

const ENTITY_ICONS = {
  PERSON:   { icon: User,     color: '#185FA5',  bg: '#E6F1FB' },
  ORG:      { icon: Building, color: '#534AB7',  bg: '#EEEDFE' },
  COURT:    { icon: Gavel,    color: '#854F0B',  bg: '#FAEEDA' },
  DATE:     { icon: Calendar, color: '#3B6D11',  bg: '#EAF3DE' },
  LOCATION: { icon: MapPin,   color: '#993C1D',  bg: '#FAECE7' },
};

const CHART_COLORS = ['#0f1923', '#1e3a5f', '#b8973a', '#2d5494', '#534AB7', '#3B6D11'];

// ── Inline Styles ──────────────────────────────────────────────────────────────

const styles = {
  // Layout
  page: {
    display: 'flex',
    minHeight: '100vh',
    background: '#F7F6F2',
    fontFamily: "'Inter', -apple-system, sans-serif",
  },
  main: {
    flex: 1,
    maxWidth: '1500px',
    margin: '0 auto',
    padding: '32px 28px 64px',
    width: '100%',
  },

  // Header
  pageHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    marginBottom: '24px',
  },
  backBtn: {
    width: '36px',
    height: '36px',
    borderRadius: '10px',
    border: '1px solid #E5E3DA',
    background: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    flexShrink: 0,
    marginTop: '4px',
    transition: 'background 0.15s, border-color 0.15s',
  },
  eyebrow: {
    fontSize: '11px',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: '#B8973A',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '4px',
  },
  pageTitle: {
    fontSize: '26px',
    fontWeight: 700,
    color: '#0F1923',
    letterSpacing: '-0.4px',
    lineHeight: 1.2,
    margin: 0,
  },
  pageDesc: {
    fontSize: '13px',
    color: '#8C8B84',
    marginTop: '4px',
  },
  refreshBtn: {
    width: '36px',
    height: '36px',
    borderRadius: '10px',
    border: '1px solid #E5E3DA',
    background: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    flexShrink: 0,
    marginTop: '4px',
    marginLeft: 'auto',
    transition: 'background 0.15s',
  },

  // Stats strip
  statsStrip: {
    display: 'flex',
    gap: '10px',
    marginBottom: '24px',
    flexWrap: 'wrap',
  },
  statCard: {
    background: '#fff',
    border: '1px solid #E8E6DD',
    borderRadius: '14px',
    padding: '14px 18px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    minWidth: '150px',
    flex: '1 1 140px',
    boxShadow: '0 1px 3px rgba(15,25,35,0.04)',
  },
  statIcon: (bg) => ({
    width: '36px',
    height: '36px',
    borderRadius: '10px',
    background: bg,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  }),
  statValue: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#0F1923',
    lineHeight: 1,
  },
  statLabel: {
    fontSize: '11px',
    color: '#9B9A93',
    marginTop: '2px',
  },

  // Upload zone
  uploadZone: (uploading) => ({
    border: `1.5px dashed ${uploading ? '#B8973A' : '#CCCAB9'}`,
    borderRadius: '16px',
    background: uploading ? 'rgba(184,151,58,0.04)' : '#fff',
    padding: '20px 24px',
    marginBottom: '24px',
    cursor: uploading ? 'default' : 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    transition: 'all 0.2s',
  }),
  uploadIconBox: (uploading) => ({
    width: '44px',
    height: '44px',
    borderRadius: '12px',
    background: uploading ? 'rgba(184,151,58,0.15)' : '#F5F3EB',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  }),
  uploadTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#0F1923',
  },
  uploadSub: {
    fontSize: '12px',
    color: '#9B9A93',
    marginTop: '2px',
  },
  uploadCta: {
    marginLeft: 'auto',
    fontSize: '12px',
    color: '#CCCAB9',
    border: '1px solid #E8E6DD',
    borderRadius: '8px',
    padding: '5px 12px',
    background: 'none',
    flexShrink: 0,
  },

  // Upload result banner
  resultBanner: {
    background: '#fff',
    border: '1px solid #C0DDB3',
    borderLeft: '3px solid #3B6D11',
    borderRadius: '14px',
    padding: '16px 20px',
    marginBottom: '24px',
  },
  resultHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '8px',
  },
  resultTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    fontWeight: 600,
    color: '#3B6D11',
  },
  dismissBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#9B9A93',
    padding: '2px',
    display: 'flex',
    alignItems: 'center',
  },

  // Tabs
  tabBar: {
    display: 'flex',
    gap: '4px',
    background: '#ECEADE',
    borderRadius: '14px',
    padding: '4px',
    marginBottom: '28px',
  },
  tab: (active) => ({
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    padding: '9px 12px',
    borderRadius: '11px',
    border: 'none',
    fontSize: '13px',
    fontWeight: active ? 600 : 500,
    cursor: 'pointer',
    background: active ? '#fff' : 'transparent',
    color: active ? '#0F1923' : '#6B6A63',
    boxShadow: active ? '0 1px 4px rgba(15,25,35,0.10)' : 'none',
    transition: 'all 0.18s',
  }),

  // Timeline
  timelineWrap: {
    position: 'relative',
  },
  timelineHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '20px',
  },
  timelineTitle: {
    fontSize: '15px',
    fontWeight: 700,
    color: '#0F1923',
  },
  timelineHint: {
    fontSize: '11px',
    color: '#A8A79F',
    fontFamily: 'monospace',
  },

  // Timeline node
  nodeRow: {
    display: 'flex',
    gap: '16px',
    position: 'relative',
    paddingBottom: '20px',
  },
  nodeDotWrap: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    flexShrink: 0,
    zIndex: 1,
  },
  nodeDot: (isNew) => ({
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    background: isNew ? '#B8973A' : '#0F1923',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: 700,
    boxShadow: isNew ? '0 0 0 4px rgba(184,151,58,0.18)' : 'none',
    transition: 'box-shadow 0.3s',
    flexShrink: 0,
  }),
  nodeLine: {
    flex: 1,
    width: '2px',
    background: 'linear-gradient(to bottom, rgba(15,25,35,0.12), rgba(15,25,35,0.0))',
    marginTop: '6px',
    minHeight: '24px',
  },
  nodeCard: (isNew) => ({
    flex: 1,
    background: '#fff',
    border: `1px solid ${isNew ? 'rgba(184,151,58,0.35)' : '#E8E6DD'}`,
    borderRadius: '16px',
    padding: '18px 20px',
    boxShadow: isNew
      ? '0 0 0 3px rgba(184,151,58,0.08), 0 2px 8px rgba(15,25,35,0.06)'
      : '0 1px 4px rgba(15,25,35,0.04)',
    transition: 'box-shadow 0.2s, transform 0.2s',
  }),
  nodeCardTop: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '12px',
    marginBottom: '10px',
  },
  nodeFilename: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#0F1923',
    margin: 0,
  },
  nodeMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginTop: '4px',
    fontSize: '11px',
    color: '#9B9A93',
  },
  nodeActions: {
    display: 'flex',
    gap: '4px',
    flexShrink: 0,
  },
  iconBtn: (color) => ({
    width: '30px',
    height: '30px',
    borderRadius: '8px',
    border: 'none',
    background: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    color: color || '#C0BEB5',
    transition: 'background 0.15s, color 0.15s',
  }),
  nodeSummary: {
    fontSize: '12px',
    color: '#6B6A63',
    lineHeight: 1.6,
    marginBottom: '12px',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  nodePills: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
  },
  pill: (bg, color) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    fontWeight: 500,
    padding: '3px 9px',
    borderRadius: '20px',
    background: bg,
    color: color,
  }),
  followupBar: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
    marginTop: '12px',
    paddingTop: '12px',
    borderTop: '1px solid #F0EDE4',
  },
  followupText: {
    fontSize: '12px',
    color: '#854F0B',
    lineHeight: 1.5,
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },

  // Empty state
  emptyState: {
    textAlign: 'center',
    padding: '56px 24px',
    border: '1.5px dashed #CCCAB9',
    borderRadius: '20px',
    background: '#FAFAF7',
  },
  emptyIcon: {
    width: '56px',
    height: '56px',
    borderRadius: '16px',
    background: '#F5F3EB',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px',
  },
  emptyTitle: {
    fontSize: '17px',
    fontWeight: 700,
    color: '#3C3A33',
    marginBottom: '6px',
  },
  emptyDesc: {
    fontSize: '13px',
    color: '#9B9A93',
    marginBottom: '20px',
  },

  // Skeleton
  skeleton: (w, h) => ({
    background: 'linear-gradient(90deg, #F0EDE4 25%, #E8E5DC 50%, #F0EDE4 75%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.4s infinite',
    borderRadius: '6px',
    width: w,
    height: h || '12px',
    display: 'block',
  }),

  // Badges
  badge: (type) => {
    const map = {
      judgment:    { bg: '#EAF3DE', color: '#3B6D11' },
      petition:    { bg: '#E6F1FB', color: '#185FA5' },
      FIR:         { bg: '#FCEBEB', color: '#A32D2D' },
      chargesheet: { bg: '#FAEEDA', color: '#854F0B' },
      statute:     { bg: '#EEEDFE', color: '#534AB7' },
      'bail order':{ bg: '#E1F5EE', color: '#0F6E56' },
      writ:        { bg: '#FBEAF0', color: '#993556' },
      default:     { bg: '#F1EFE8', color: '#5F5E5A' },
    };
    const cfg = map[type] || map.default;
    return {
      display: 'inline-flex',
      alignItems: 'center',
      fontSize: '11px',
      fontWeight: 600,
      padding: '3px 8px',
      borderRadius: '6px',
      background: cfg.bg,
      color: cfg.color,
      letterSpacing: '0.01em',
    };
  },
  latestBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '3px',
    fontSize: '11px',
    fontWeight: 600,
    padding: '3px 8px',
    borderRadius: '6px',
    background: '#FEF9C3',
    color: '#854D0E',
  },

  // Cards (overview / general)
  card: {
    background: '#fff',
    border: '1px solid #E8E6DD',
    borderRadius: '16px',
    padding: '20px 24px',
    boxShadow: '0 1px 4px rgba(15,25,35,0.04)',
  },
  cardGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '16px',
    marginBottom: '16px',
  },

  // Section title
  sectionTitle: (color) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '14px',
    fontSize: '13px',
    fontWeight: 700,
    color: color || '#0F1923',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  }),

  // Progress bar
  progressBar: {
    height: '6px',
    background: '#EAE8DF',
    borderRadius: '99px',
    overflow: 'hidden',
    marginTop: '8px',
  },
  progressFill: (pct) => ({
    height: '100%',
    width: `${pct}%`,
    background: 'linear-gradient(90deg, #0F1923, #B8973A)',
    borderRadius: '99px',
    transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
  }),

  // Ask AI
  inputRow: {
    display: 'flex',
    gap: '8px',
    marginBottom: '14px',
  },
  input: {
    flex: 1,
    height: '42px',
    borderRadius: '11px',
    border: '1px solid #CCCAB9',
    padding: '0 14px',
    fontSize: '14px',
    color: '#0F1923',
    background: '#FAFAF7',
    outline: 'none',
    transition: 'border-color 0.15s',
  },
  sendBtn: (disabled) => ({
    height: '42px',
    padding: '0 18px',
    borderRadius: '11px',
    border: 'none',
    background: disabled ? '#D4D2C9' : '#0F1923',
    color: '#fff',
    fontSize: '13px',
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexShrink: 0,
    transition: 'background 0.15s',
  }),
  chipRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
  },
  chip: {
    background: '#F5F3EB',
    border: '1px solid #E8E6DD',
    borderRadius: '20px',
    padding: '5px 12px',
    fontSize: '12px',
    color: '#6B6A63',
    cursor: 'pointer',
    transition: 'background 0.15s, color 0.15s',
  },

  // AI answer card
  aiCard: {
    background: '#fff',
    border: '1px solid rgba(184,151,58,0.3)',
    borderLeft: '3px solid #B8973A',
    borderRadius: '16px',
    padding: '20px 24px',
    marginTop: '16px',
  },
  aiAvatar: {
    width: '34px',
    height: '34px',
    borderRadius: '50%',
    background: '#0F1923',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  aiMeta: {
    fontSize: '11px',
    fontWeight: 700,
    color: '#9B9A93',
    letterSpacing: '0.07em',
    textTransform: 'uppercase',
    marginBottom: '6px',
  },
  aiText: {
    fontSize: '14px',
    color: '#1A1A17',
    lineHeight: 1.7,
  },
  confidenceBadge: (level) => {
    const map = { high: ['#EAF3DE','#3B6D11'], medium: ['#FAEEDA','#854F0B'], low: ['#FCEBEB','#A32D2D'] };
    const [bg, color] = map[level] || map.low;
    return { display: 'inline-flex', alignItems: 'center', padding: '3px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: 600, background: bg, color };
  },

  // Document Detail Modal
  overlay: {
    position: 'fixed',
    inset: 0,
    zIndex: 50,
    background: 'rgba(15,25,35,0.60)',
    backdropFilter: 'blur(5px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
  },
  modal: {
    background: '#fff',
    width: '100%',
    maxWidth: '740px',
    borderRadius: '22px',
    boxShadow: '0 24px 80px rgba(15,25,35,0.22)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    maxHeight: '88vh',
    animation: 'modalIn 0.22s cubic-bezier(0.34,1.56,0.64,1)',
  },
  modalHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '14px',
    padding: '20px 22px',
    borderBottom: '1px solid #EEF0EA',
    background: '#FAFAF7',
    flexShrink: 0,
  },
  modalIconBox: {
    width: '44px',
    height: '44px',
    borderRadius: '12px',
    background: '#0F1923',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  modalTitle: {
    fontSize: '15px',
    fontWeight: 700,
    color: '#0F1923',
    margin: 0,
  },
  modalNav: {
    display: 'flex',
    gap: '2px',
    padding: '8px 14px',
    borderBottom: '1px solid #F0EDE4',
    overflowX: 'auto',
    flexShrink: 0,
    background: '#fff',
  },
  navBtn: (active) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '7px 14px',
    borderRadius: '9px',
    border: 'none',
    background: active ? '#0F1923' : 'none',
    color: active ? '#fff' : '#6B6A63',
    fontSize: '12px',
    fontWeight: active ? 600 : 500,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    transition: 'all 0.15s',
  }),
  modalBody: {
    flex: 1,
    overflowY: 'auto',
    padding: '22px',
    background: '#FAFAF7',
  },

  // Law tags
  lawTag: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '4px 10px',
    borderRadius: '7px',
    background: '#EEEDFE',
    color: '#3C3489',
    fontSize: '11px',
    fontWeight: 700,
    fontFamily: 'monospace',
    letterSpacing: '0.02em',
  },
  extractedTag: {
    display: 'inline-flex',
    padding: '3px 9px',
    borderRadius: '20px',
    background: '#F1EFE8',
    color: '#5F5E5A',
    fontSize: '11px',
    fontFamily: 'monospace',
  },
};

// ── Keyframes via style tag ────────────────────────────────────────────────────

const GlobalStyles = () => (
  <style>{`
    @keyframes shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(10px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
    @keyframes modalIn {
      from { opacity: 0; transform: scale(0.94) translateY(12px); }
      to   { opacity: 1; transform: scale(1) translateY(0); }
    }
    @keyframes slideRight {
      from { opacity: 0; transform: translateX(-8px); }
      to   { opacity: 1; transform: translateX(0); }
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .fade-up { animation: fadeUp 0.3s ease both; }
    .fade-in { animation: fadeIn 0.25s ease both; }
    .stagger-1 { animation-delay: 0.05s; }
    .stagger-2 { animation-delay: 0.1s; }
    .stagger-3 { animation-delay: 0.15s; }
    .spinning { animation: spin 0.9s linear infinite; }
    .node-card:hover {
      box-shadow: 0 4px 20px rgba(15,25,35,0.10) !important;
      transform: translateY(-1px);
      transition: box-shadow 0.2s, transform 0.2s;
    }
    .icon-btn:hover { background: #F0EDE4 !important; color: #0F1923 !important; }
    .icon-btn-red:hover { background: #FCEBEB !important; color: #A32D2D !important; }
    .back-btn:hover { background: #F5F3EB !important; border-color: #CCCAB9 !important; }
    .upload-zone:hover { border-color: #B8973A !important; background: rgba(184,151,58,0.03) !important; }
    .chip:hover { background: #EAE8DF !important; color: #0F1923 !important; }
    .tab-btn:hover:not([data-active='true']) { background: rgba(255,255,255,0.55) !important; }
    .view-btn:hover { background: #F5F3EB !important; color: #0F1923 !important; }
    .modal-dismiss:hover { background: #F0EDE4 !important; color: #0F1923 !important; }
    .nav-btn:hover:not([data-active='true']) { background: #F0EDE4 !important; color: #0F1923 !important; }
    .insight-card {
      padding: 12px 14px;
      border-radius: 12px;
      border-left: 3px solid #B8973A;
      background: #fff;
      border: 1px solid #E8E6DD;
      border-left: 3px solid #B8973A;
      font-size: 13px;
      color: #3C3A33;
      line-height: 1.6;
      animation: slideRight 0.28s ease both;
    }
    .risk-card {
      padding: 13px 16px;
      border-radius: 12px;
      background: #fff;
      border: 1px solid #F7C1C1;
      border-left: 3px solid #E24B4A;
      font-size: 13px;
      color: #3C3A33;
      line-height: 1.6;
    }
    .scope-card {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 12px 14px;
      border-radius: 12px;
      background: #F0FAF4;
      border: 1px solid #C0DDB3;
      font-size: 13px;
      color: #27500A;
      line-height: 1.6;
      animation: slideRight 0.28s ease both;
    }
    .law-row {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 12px;
      border-radius: 11px;
      background: #F7F6F2;
      border: 1px solid #ECEADE;
      transition: border-color 0.15s;
    }
    .law-row:hover { border-color: #B8973A; }
    input:focus { border-color: #B8973A !important; box-shadow: 0 0 0 3px rgba(184,151,58,0.12) !important; }
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #D4D2C9; border-radius: 99px; }
  `}</style>
);

// ── Micro components ───────────────────────────────────────────────────────────

function DocBadge({ docType }) {
  return <span style={styles.badge(docType)}>{DOC_TYPE_BADGE[docType]?.label || docType || 'Document'}</span>;
}

function EntityPill({ name, type }) {
  const cfg = ENTITY_ICONS[type] || { icon: FileText, color: '#5F5E5A', bg: '#F1EFE8' };
  const Icon = cfg.icon;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      padding: '4px 10px', borderRadius: '20px',
      background: cfg.bg, color: cfg.color,
      fontSize: '12px', fontWeight: 500,
      border: `1px solid ${cfg.bg}`,
    }}>
      <Icon size={10} />
      {name}
    </span>
  );
}

function SectionLabel({ icon: Icon, title, color }) {
  return (
    <div style={styles.sectionTitle(color)}>
      <Icon size={13} />
      {title}
    </div>
  );
}

function StatTile({ icon: Icon, label, value, iconBg, iconColor }) {
  return (
    <div style={styles.statCard}>
      <div style={styles.statIcon(iconBg)}>
        <Icon size={15} color={iconColor} />
      </div>
      <div>
        <div style={styles.statValue}>{value}</div>
        <div style={styles.statLabel}>{label}</div>
      </div>
    </div>
  );
}

// ── Document Detail Modal ──────────────────────────────────────────────────────

function DocumentDetail({ doc, analysis, previousFollowups, onClose, onDelete }) {
  const [activeSection, setActiveSection] = useState('summary');
  const nlpMeta  = analysis?.nlp_meta || {};
  const entities = nlpMeta.entities || {};
  const actSecs  = nlpMeta.act_sections || [];
  const statutes = analysis?.identified_statutes || [];

  const sections = [
    { id: 'summary',  label: 'Summary',     icon: BookOpen   },
    { id: 'laws',     label: 'Laws',         icon: Scale      },
    { id: 'entities', label: 'Entities',     icon: User       },
    { id: 'followup', label: 'Follow-up',    icon: Bell       },
    { id: 'scope',    label: 'Future Scope', icon: TrendingUp },
    { id: 'risks',    label: 'Risk Flags',   icon: Shield     },
  ];

  const chartData = statutes.slice(0, 6).map(s => ({
    name: s.display_name?.replace('IPC Section ', 'S.') || s.section_id,
    score: Math.round((s.confidence || 0) * 100),
  }));

  return (
    <div style={styles.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={styles.modal}>
        {/* Modal Header */}
        <div style={styles.modalHeader}>
          <div style={styles.modalIconBox}>
            <FileText size={18} color="#B8973A" />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={styles.modalTitle}>{doc.filename}</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px', flexWrap: 'wrap' }}>
              <DocBadge docType={doc.doc_type} />
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: '#9B9A93' }}>
                <Clock size={10} />
                {new Date(doc.uploaded_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
            <button
              className="icon-btn icon-btn-red"
              style={{ ...styles.iconBtn('#C0BEB5'), borderRadius: '9px', width: '32px', height: '32px', border: 'none' }}
              onClick={() => onDelete(doc.id, doc.filename)}
              title="Delete"
            >
              <Trash2 size={14} />
            </button>
            <button
              className="modal-dismiss"
              style={{ ...styles.iconBtn('#9B9A93'), borderRadius: '9px', width: '32px', height: '32px', border: 'none' }}
              onClick={onClose}
              title="Close"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Nav */}
        <div style={styles.modalNav}>
          {sections.map(s => {
            const Icon = s.icon;
            const active = activeSection === s.id;
            return (
              <button
                key={s.id}
                className="nav-btn"
                data-active={active}
                style={styles.navBtn(active)}
                onClick={() => setActiveSection(s.id)}
              >
                <Icon size={11} /> {s.label}
              </button>
            );
          })}
        </div>

        {/* Body */}
        <div style={styles.modalBody} className="fade-in">
          {activeSection === 'summary' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ background: '#fff', border: '1px solid #E8E6DD', borderLeft: '3px solid #B8973A', borderRadius: '14px', padding: '18px' }}>
                <SectionLabel icon={BookOpen} title="Document Summary" />
                <p style={{ fontSize: '14px', color: '#3C3A33', lineHeight: 1.75, margin: 0 }}>
                  {analysis?.case_summary || 'No summary available.'}
                </p>
              </div>

              {analysis?.key_insights?.length > 0 && (
                <div>
                  <SectionLabel icon={Layers} title="Key Insights" />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {analysis.key_insights.map((insight, i) => (
                      <div key={i} className="insight-card" style={{ animationDelay: `${i * 0.06}s` }}>
                        {insight}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {analysis?.outcome_likelihood && (
                <div style={{ background: '#E6F1FB', border: '1px solid #B5D4F4', borderRadius: '14px', padding: '16px' }}>
                  <SectionLabel icon={BarChart2} title="Outcome Likelihood" color="#185FA5" />
                  <p style={{ fontSize: '13px', color: '#0C447C', margin: 0 }}>{analysis.outcome_likelihood}</p>
                </div>
              )}
            </div>
          )}

          {activeSection === 'laws' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {statutes.length > 0 && (
                <div style={styles.card}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <SectionLabel icon={Scale} title="LeSICiN Identified Statutes" />
                    <span style={{ ...styles.badge('statute'), fontSize: '10px' }}>AI Model</span>
                  </div>
                  {chartData.length > 0 && (
                    <div style={{ marginBottom: '14px' }}>
                      <ResponsiveContainer width="100%" height={140}>
                        <BarChart data={chartData} margin={{ top: 4, right: 8, left: -22, bottom: 36 }}>
                          <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9B9A93' }} angle={-28} textAnchor="end" interval={0} />
                          <YAxis tick={{ fontSize: 10, fill: '#9B9A93' }} domain={[0, 100]} />
                          <Tooltip formatter={v => [`${v}%`, 'Confidence']} contentStyle={{ fontSize: 12, borderRadius: '10px', border: '1px solid #E8E6DD' }} />
                          <Bar dataKey="score" radius={[5,5,0,0]}>
                            {chartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {statutes.map((s, i) => (
                      <div key={i} className="law-row">
                        <span style={styles.lawTag}>{s.display_name}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          {s.description && <p style={{ fontSize: '12px', color: '#6B6A63', margin: 0 }}>{s.description}</p>}
                        </div>
                        <span style={{ fontSize: '12px', fontFamily: 'monospace', color: '#B8973A', fontWeight: 700, flexShrink: 0 }}>
                          {Math.round((s.confidence || 0) * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {analysis?.applicable_laws?.length > 0 && (
                <div style={styles.card}>
                  <SectionLabel icon={Scale} title="Applicable Laws" />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {analysis.applicable_laws.map((law, i) => (
                      <div key={i} className="law-row">
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <span style={styles.lawTag}>{law.act} §{law.section}</span>
                            {law.confidence_source && <span style={{ fontSize: '10px', color: '#9B9A93' }}>{law.confidence_source}</span>}
                          </div>
                          {law.relevance && <p style={{ fontSize: '12px', color: '#6B6A63', margin: 0 }}>{law.relevance}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {analysis?.suggested_laws?.length > 0 && (
                <div style={{ background: '#FAEEDA', border: '1px solid #FAC775', borderRadius: '14px', padding: '18px' }}>
                  <SectionLabel icon={TrendingUp} title="Suggested Additional Laws" color="#854F0B" />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {analysis.suggested_laws.map((law, i) => (
                      <div key={i} style={{ background: '#fff', border: '1px solid #FAC775', borderRadius: '10px', padding: '12px' }}>
                        <span style={styles.lawTag}>{law.act} §{law.section}</span>
                        {law.reason && <p style={{ fontSize: '12px', color: '#854F0B', marginTop: '6px', marginBottom: 0 }}>{law.reason}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {actSecs.length > 0 && (
                <div>
                  <SectionLabel icon={FileText} title="Regex-Extracted Citations" color="#9B9A93" />
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {actSecs.map((s, i) => <span key={i} style={styles.extractedTag}>{s}</span>)}
                  </div>
                </div>
              )}

              {statutes.length === 0 && !analysis?.applicable_laws?.length && (
                <p style={{ textAlign: 'center', color: '#9B9A93', fontSize: '13px', padding: '32px' }}>No laws identified for this document.</p>
              )}
            </div>
          )}

          {activeSection === 'entities' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {Object.entries(entities).map(([type, names]) =>
                names?.length > 0 ? (
                  <div key={type} style={styles.card}>
                    <div style={{ fontSize: '10px', fontWeight: 700, color: '#9B9A93', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '10px' }}>{type}</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {names.map((name, i) => <EntityPill key={i} name={name} type={type} />)}
                    </div>
                  </div>
                ) : null
              )}
              {Object.values(entities).every(v => !v?.length) && (
                <p style={{ textAlign: 'center', color: '#9B9A93', fontSize: '13px', padding: '32px' }}>No entities extracted.</p>
              )}
            </div>
          )}

          {activeSection === 'followup' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <SectionLabel icon={ArrowRight} title="Follow-up from Previous Documents" />
                {analysis?.follow_up && analysis.follow_up !== 'null' ? (
                  <div style={{ background: '#FAEEDA', border: '1px solid #FAC775', borderLeft: '3px solid #B8973A', borderRadius: '14px', padding: '16px', fontSize: '13px', color: '#3C3A33', lineHeight: 1.7 }}>
                    {analysis.follow_up}
                  </div>
                ) : (
                  <div style={{ background: '#fff', border: '1px solid #E8E6DD', borderRadius: '14px', padding: '16px', fontSize: '13px', color: '#9B9A93' }}>
                    This is the first document in the case — no follow-up context yet.
                  </div>
                )}
              </div>

              {previousFollowups?.length > 0 && (
                <div style={styles.card}>
                  <SectionLabel icon={Clock} title="Previous Follow-up History" color="#9B9A93" />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {previousFollowups.map((fu, i) => (
                      <div key={i} style={{ borderLeft: '2px solid #FAC775', paddingLeft: '14px' }}>
                        <div style={{ fontSize: '11px', color: '#9B9A93', fontFamily: 'monospace', marginBottom: '4px' }}>
                          {fu.date} · {fu.filename}
                        </div>
                        <p style={{ fontSize: '13px', color: '#3C3A33', margin: 0 }}>{fu.follow_up}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {analysis?.recommended_actions?.length > 0 && (
                <div style={{ background: '#F0FAF4', border: '1px solid #C0DDB3', borderRadius: '14px', padding: '18px' }}>
                  <SectionLabel icon={CheckCircle} title="Recommended Actions" color="#3B6D11" />
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {analysis.recommended_actions.map((a, i) => (
                      <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '13px', color: '#27500A' }}>
                        <CheckCircle size={14} color="#3B6D11" style={{ marginTop: '2px', flexShrink: 0 }} /> {a}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {activeSection === 'scope' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <SectionLabel icon={TrendingUp} title="Future Scope & Legal Strategy" color="#3B6D11" />
              {analysis?.future_scope?.length > 0 ? (
                analysis.future_scope.map((s, i) => (
                  <div key={i} className="scope-card" style={{ animationDelay: `${i * 0.05}s` }}>
                    <ArrowRight size={14} color="#3B6D11" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <p style={{ margin: 0 }}>{s}</p>
                  </div>
                ))
              ) : (
                <p style={{ textAlign: 'center', color: '#9B9A93', fontSize: '13px', padding: '32px' }}>No future scope data available.</p>
              )}
            </div>
          )}

          {activeSection === 'risks' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <SectionLabel icon={AlertTriangle} title="Risk Flags" color="#A32D2D" />
              {analysis?.risk_flags?.length > 0 ? (
                analysis.risk_flags.map((r, i) => (
                  <div key={i} className="risk-card">
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <AlertTriangle size={13} color="#E24B4A" style={{ marginTop: '2px', flexShrink: 0 }} />
                      <p style={{ margin: 0 }}>{r}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#F0FAF4', border: '1px solid #C0DDB3', borderRadius: '14px', padding: '16px' }}>
                  <CheckCircle size={16} color="#3B6D11" />
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#3B6D11' }}>No risk flags identified for this document.</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Timeline Node ──────────────────────────────────────────────────────────────

function TimelineNode({ doc, index, isLast, onView, onDelete, isNew }) {
  const analysis   = doc.analysis || {};
  const hasFollowup = analysis.follow_up && analysis.follow_up !== 'null';
  const lawCount   = (analysis.identified_statutes?.length || 0) + (analysis.applicable_laws?.length || 0);
  const riskCount  = analysis.risk_flags?.length || 0;

  return (
    <div style={{ ...styles.nodeRow, paddingBottom: isLast ? '4px' : '20px' }}>
      {!isLast && (
        <div style={{ position: 'absolute', left: '15px', top: '36px', bottom: 0, width: '2px', background: 'linear-gradient(to bottom, rgba(15,25,35,0.10), rgba(15,25,35,0))', zIndex: 0 }} />
      )}
      <div style={styles.nodeDotWrap}>
        <div style={styles.nodeDot(isNew)}>{index + 1}</div>
      </div>

      <div className="node-card" style={styles.nodeCard(isNew)}>
        <div style={styles.nodeCardTop}>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '5px' }}>
              <DocBadge docType={doc.doc_type} />
              {isNew && (
                <span style={styles.latestBadge}>
                  <Sparkles size={9} style={{ marginRight: '2px' }} /> Latest
                </span>
              )}
            </div>
            <p style={styles.nodeFilename}>{doc.filename}</p>
            <div style={styles.nodeMeta}>
              <Calendar size={10} />
              {new Date(doc.uploaded_at).toLocaleDateString('en-IN', {
                day: 'numeric', month: 'short', year: 'numeric',
                hour: '2-digit', minute: '2-digit'
              })}
            </div>
          </div>
          <div style={styles.nodeActions}>
            <button
              className="icon-btn icon-btn-red"
              style={{ ...styles.iconBtn(), border: 'none', borderRadius: '8px', width: '30px', height: '30px' }}
              onClick={() => onDelete(doc.id, doc.filename)}
              title="Delete"
            >
              <Trash2 size={13} />
            </button>
            <button
              className="view-btn"
              style={{
                height: '30px',
                padding: '0 12px',
                borderRadius: '8px',
                border: '1px solid #E8E6DD',
                background: '#fff',
                color: '#3C3A33',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
              }}
              onClick={() => onView(doc)}
            >
              <Eye size={12} /> View
            </button>
          </div>
        </div>

        {analysis.case_summary && (
          <p style={styles.nodeSummary}>{analysis.case_summary}</p>
        )}

        <div style={styles.nodePills}>
          {lawCount > 0 && (
            <span style={styles.pill('#E6F1FB', '#185FA5')}>
              <Scale size={9} /> {lawCount} law{lawCount !== 1 ? 's' : ''}
            </span>
          )}
          {riskCount > 0 && (
            <span style={styles.pill('#FCEBEB', '#A32D2D')}>
              <AlertTriangle size={9} /> {riskCount} risk{riskCount !== 1 ? 's' : ''}
            </span>
          )}
          {hasFollowup && (
            <span style={styles.pill('#FAEEDA', '#854F0B')}>
              <Bell size={9} /> Follow-up
            </span>
          )}
          {analysis.identified_statutes?.length > 0 && (
            <span style={styles.pill('#EEEDFE', '#534AB7')}>
              <Gavel size={9} /> {analysis.identified_statutes.length} statute{analysis.identified_statutes.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {hasFollowup && (
          <div style={styles.followupBar}>
            <ArrowRight size={12} color="#B8973A" style={{ flexShrink: 0, marginTop: '2px' }} />
            <p style={styles.followupText}>{analysis.follow_up}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Upload Result Banner ───────────────────────────────────────────────────────

function UploadResultBanner({ result, onDismiss }) {
  if (!result) return null;
  return (
    <div style={styles.resultBanner} className="fade-up">
      <div style={styles.resultHeader}>
        <div style={styles.resultTitle}>
          <CheckCircle size={15} />
          Analysis complete
          <DocBadge docType={result.classification} />
        </div>
        <button className="modal-dismiss" style={{ ...styles.dismissBtn, borderRadius: '7px', width: '26px', height: '26px', border: 'none', cursor: 'pointer' }} onClick={onDismiss}>
          <X size={13} />
        </button>
      </div>
      <p style={{ fontSize: '13px', color: '#3C3A33', marginBottom: result.laws_suggested?.length ? '10px' : 0, lineHeight: 1.6 }}>
        {result.summary}
      </p>
      {result.laws_suggested?.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {result.laws_suggested.slice(0, 4).map((l, i) => (
            <span key={i} style={styles.lawTag}>{l.act} §{l.section}</span>
          ))}
          {result.laws_suggested.length > 4 && (
            <span style={{ fontSize: '12px', color: '#9B9A93', alignSelf: 'center' }}>+{result.laws_suggested.length - 4} more</span>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main CaseView ──────────────────────────────────────────────────────────────

export default function CaseView() {
  const { caseId }  = useParams();
  const navigate    = useNavigate();
  const toast       = useToast();
  const fileRef     = useRef();

  const [cases, setCases]             = useState([]);
  const [dash, setDash]               = useState(null);
  const [timeline, setTimeline]       = useState([]);
  const [followupHistory, setFollowupHistory] = useState([]);
  const [loading, setLoading]         = useState(true);
  const [uploading, setUploading]     = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [activeTab, setActiveTab]     = useState('timeline');
  const [question, setQuestion]       = useState('');
  const [aiAnswer, setAiAnswer]       = useState(null);
  const [asking, setAsking]           = useState(false);
  const [newDocId, setNewDocId]       = useState(null);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [dashRes, fuRes, casesRes] = await Promise.all([
        getCaseDashboard(caseId).catch(() => null),
        getCaseFollowup(caseId).catch(() => null),
        getCases().catch(() => ({ data: [] })),
      ]);
      if (dashRes) {
        setDash(dashRes.data);
        const docs = dashRes.data.documents || [];
        const tl   = dashRes.data.timeline   || [];
        const enriched = docs.map(doc => {
          const tlEntry = tl.find(t => t.doc_id === doc.id) || {};
          return { ...doc, ...tlEntry };
        });
        setTimeline(enriched);
      }
      if (fuRes) setFollowupHistory(fuRes.data.history || []);
      setCases(casesRes.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, [caseId]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);
    try {
      const res = await uploadDoc(caseId, file);
      setUploadResult(res.data);
      setNewDocId(res.data.doc_id);
      toast.show('Document analysed successfully', 'success');
      await fetchAll();
    } catch (err) {
      toast.show(err.response?.data?.detail || 'Upload failed', 'error');
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    try {
      await deleteDoc(docId);
      toast.show('Document deleted', 'info');
      if (selectedDoc?.id === docId) setSelectedDoc(null);
      await fetchAll();
    } catch (err) {
      toast.show('Delete failed', 'error');
    }
  };

  const handleViewDoc = async (doc) => {
    if (!doc.analysis) {
      try {
        const res = await getAnalysis(doc.id);
        setSelectedDoc({ ...doc, analysis: res.data.analysis });
      } catch {
        setSelectedDoc(doc);
      }
    } else {
      setSelectedDoc(doc);
    }
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    setAsking(true);
    setAiAnswer(null);
    try {
      const res = await askQuestion(caseId, question);
      setAiAnswer(res.data);
    } catch {
      setAiAnswer({ answer: 'Request failed — please try again.', reasoning: '', relevant_laws: [], confidence: 'low' });
    } finally {
      setAsking(false);
    }
  };

  const llm       = dash?.llm_dashboard || {};
  const analytics = dash?.analytics     || {};
  const caseInfo  = dash?.case          || {};

  const totalLaws  = timeline.reduce((sum, d) => {
    const a = d.analysis || {};
    return sum + (a.identified_statutes?.length || 0) + (a.applicable_laws?.length || 0);
  }, 0);
  const totalRisks = timeline.reduce((sum, d) => sum + (d.analysis?.risk_flags?.length || 0), 0);
  const lastUpdated = timeline.length
    ? new Date(timeline[timeline.length - 1].uploaded_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
    : '—';

  const TABS = [
    { id: 'timeline', label: 'Timeline',     icon: Layers      },
    { id: 'overview', label: 'Case Overview', icon: BarChart2   },
    { id: 'ask',      label: 'Ask AI',        icon: MessageCircle },
  ];

  return (
    <>
      <GlobalStyles />
      <div style={styles.page}>
        {/* <Sidebar cases={cases} onNewCase={() => navigate('/')} /> */}

        <main style={styles.main}>
          {/* ── Page Header ── */}
          <div style={styles.pageHeader} className="fade-up">
            <button className="back-btn" style={styles.backBtn} onClick={() => navigate('/')}>
              <ArrowLeft size={16} color="#6B6A63" />
            </button>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={styles.eyebrow}>
                <FolderOpen size={10} /> Case
              </div>
              <h1 style={styles.pageTitle}>{caseInfo.title || 'Loading…'}</h1>
              {caseInfo.description && (
                <p style={styles.pageDesc}>{caseInfo.description}</p>
              )}
            </div>
            <button
              className="back-btn"
              style={styles.refreshBtn}
              onClick={fetchAll}
              title="Refresh"
            >
              <RefreshCw size={15} color="#9B9A93" className={loading ? 'spinning' : ''} />
            </button>
          </div>

          {/* ── Stats Strip ── */}
          {!loading && timeline.length > 0 && (
            <div style={styles.statsStrip} className="fade-up stagger-1">
              <StatTile icon={FileText}      label="Documents"       value={timeline.length} iconBg="#F1EFE8" iconColor="#5F5E5A" />
              <StatTile icon={Scale}         label="Laws identified" value={totalLaws}       iconBg="#E6F1FB" iconColor="#185FA5" />
              <StatTile icon={AlertTriangle} label="Risk flags"      value={totalRisks}      iconBg="#FCEBEB" iconColor="#A32D2D" />
              <StatTile icon={Clock}         label="Last updated"    value={lastUpdated}     iconBg="#FAEEDA" iconColor="#854F0B" />
            </div>
          )}

          {/* ── Upload Zone ── */}
          <div
            className={uploading ? '' : 'upload-zone'}
            style={styles.uploadZone(uploading)}
            onClick={() => !uploading && fileRef.current?.click()}
          >
            <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" onChange={handleUpload} style={{ display: 'none' }} />
            <div style={styles.uploadIconBox(uploading)}>
              {uploading
                ? <RefreshCw size={18} color="#B8973A" className="spinning" />
                : <Upload size={18} color="#B8973A" />}
            </div>
            <div>
              <div style={styles.uploadTitle}>
                {uploading ? 'Analysing document…' : 'Upload a document'}
              </div>
              <div style={styles.uploadSub}>
                {uploading ? 'Running NLP pipeline + AI analysis' : 'PDF, DOCX, or TXT — click or drag'}
              </div>
            </div>
            {!uploading && <span style={styles.uploadCta}>Browse files</span>}
          </div>

          {/* ── Upload Result ── */}
          <UploadResultBanner result={uploadResult} onDismiss={() => setUploadResult(null)} />

          {/* ── Tabs ── */}
          <div style={styles.tabBar} className="fade-up stagger-2">
            {TABS.map(tab => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  className="tab-btn"
                  data-active={active}
                  style={styles.tab(active)}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <Icon size={13} /> {tab.label}
                </button>
              );
            })}
          </div>

          {/* ── Timeline Tab ── */}
          {activeTab === 'timeline' && (
            <div className="fade-in" style={styles.timelineWrap}>
              {loading ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {[1,2,3].map(i => (
                    <div key={i} style={{ display: 'flex', gap: '16px' }}>
                      <span style={{ ...styles.skeleton('32px', '32px'), borderRadius: '50%', flexShrink: 0 }} />
                      <div style={{ ...styles.card, flex: 1, padding: '16px' }}>
                        <span style={{ ...styles.skeleton('30%', '12px'), display: 'block', marginBottom: '10px' }} />
                        <span style={{ ...styles.skeleton('60%', '10px'), display: 'block' }} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : timeline.length === 0 ? (
                <div style={styles.emptyState}>
                  <div style={styles.emptyIcon}>
                    <FileText size={26} color="#B8973A" />
                  </div>
                  <p style={styles.emptyTitle}>No documents yet</p>
                  <p style={styles.emptyDesc}>Upload your first document to begin the case timeline.</p>
                  <button
                    onClick={() => fileRef.current?.click()}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '7px', height: '38px', padding: '0 18px', borderRadius: '10px', border: 'none', background: '#0F1923', color: '#fff', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
                  >
                    <Upload size={13} /> Upload document
                  </button>
                </div>
              ) : (
                <div>
                  <div style={styles.timelineHeader}>
                    <span style={styles.timelineTitle}>
                      {timeline.length} Document{timeline.length !== 1 ? 's' : ''} · Case Timeline
                    </span>
                    <span style={styles.timelineHint}>Oldest → Latest</span>
                  </div>
                  {timeline.map((doc, i) => (
                    <TimelineNode
                      key={doc.id}
                      doc={doc}
                      index={i}
                      isLast={i === timeline.length - 1}
                      isNew={doc.id === newDocId}
                      onView={handleViewDoc}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Overview Tab ── */}
          {activeTab === 'overview' && (
            <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {!dash ? (
                <div style={styles.emptyState}>
                  <p style={{ color: '#9B9A93', fontSize: '13px' }}>Upload documents to see case overview.</p>
                </div>
              ) : (
                <>
                  <div style={styles.cardGrid}>
                    <div style={styles.card}>
                      <SectionLabel icon={BookOpen} title="Cumulative Summary" />
                      <p style={{ fontSize: '14px', color: '#3C3A33', lineHeight: 1.75, margin: 0 }}>
                        {llm.cumulative_summary || '—'}
                      </p>
                    </div>
                    <div style={styles.card}>
                      <SectionLabel icon={TrendingUp} title="Case Trajectory" />
                      <p style={{ fontSize: '14px', color: '#3C3A33', lineHeight: 1.75, margin: 0 }}>
                        {llm.case_trajectory || '—'}
                      </p>
                      {analytics.progress && (
                        <div style={{ marginTop: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#9B9A93', marginBottom: '6px' }}>
                            <span>{analytics.progress.stage}</span>
                            <span style={{ fontWeight: 600, color: '#0F1923' }}>{analytics.progress.score}/100</span>
                          </div>
                          <div style={styles.progressBar}>
                            <div style={styles.progressFill(analytics.progress.score)} />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {llm.risk_assessment && (
                    <div style={{ ...styles.card, borderLeft: '3px solid #E24B4A', background: '#FFF8F8' }}>
                      <SectionLabel icon={AlertTriangle} title="Risk Assessment" color="#A32D2D" />
                      <p style={{ fontSize: '14px', color: '#3C3A33', lineHeight: 1.7, margin: 0 }}>{llm.risk_assessment}</p>
                    </div>
                  )}

                  {llm.follow_up_brief && (
                    <div style={{ ...styles.card, borderLeft: '3px solid #B8973A', background: '#FFFDF5' }}>
                      <SectionLabel icon={Bell} title="Latest Follow-up Brief" color="#854F0B" />
                      <p style={{ fontSize: '14px', color: '#3C3A33', lineHeight: 1.7, margin: 0 }}>{llm.follow_up_brief}</p>
                    </div>
                  )}

                  {analytics.citation_frequency?.length > 0 && (
                    <div style={styles.card}>
                      <SectionLabel icon={BarChart2} title="Citation Frequency Across All Documents" />
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart
                          data={analytics.citation_frequency.slice(0, 8).map(c => ({
                            name: c.display_label?.slice(0, 20) || c.citation?.slice(0, 20),
                            count: c.count,
                          }))}
                          margin={{ top: 4, right: 8, left: -22, bottom: 50 }}
                        >
                          <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9B9A93' }} angle={-28} textAnchor="end" interval={0} />
                          <YAxis tick={{ fontSize: 10, fill: '#9B9A93' }} allowDecimals={false} />
                          <Tooltip contentStyle={{ fontSize: 12, borderRadius: '10px', border: '1px solid #E8E6DD' }} />
                          <Bar dataKey="count" radius={[5,5,0,0]}>
                            {analytics.citation_frequency.slice(0,8).map((_, i) => (
                              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ── Ask AI Tab ── */}
          {activeTab === 'ask' && (
            <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={styles.card}>
                <SectionLabel icon={MessageCircle} title="Ask about this case" />
                <form onSubmit={handleAsk} style={styles.inputRow}>
                  <input
                    value={question}
                    onChange={e => setQuestion(e.target.value)}
                    placeholder="e.g. What are the strongest bail grounds?"
                    style={styles.input}
                  />
                  <button type="submit" disabled={asking || !question.trim()} style={styles.sendBtn(asking || !question.trim())}>
                    {asking
                      ? <RefreshCw size={14} className="spinning" />
                      : <Send size={14} />}
                    Ask
                  </button>
                </form>
                <div style={styles.chipRow}>
                  {[
                    'What are the bail grounds?',
                    'Which IPC sections apply?',
                    'What is the outcome likelihood?',
                    'What should we do next?',
                    'Summarise all risk flags',
                  ].map(q => (
                    <button key={q} className="chip" style={styles.chip} onClick={() => setQuestion(q)}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {asking && !aiAnswer && (
                <div style={styles.card}>
                  <span style={{ ...styles.skeleton('25%', '11px'), display: 'block', marginBottom: '12px' }} />
                  <span style={{ ...styles.skeleton('100%', '11px'), display: 'block', marginBottom: '8px' }} />
                  <span style={{ ...styles.skeleton('80%', '11px'), display: 'block' }} />
                </div>
              )}

              {aiAnswer && (
                <div style={styles.aiCard} className="fade-up">
                  <div style={{ display: 'flex', gap: '14px', marginBottom: '14px' }}>
                    <div style={styles.aiAvatar}>
                      <Sparkles size={14} color="#B8973A" />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={styles.aiMeta}>Answer</div>
                      <p style={styles.aiText}>{aiAnswer.answer}</p>
                    </div>
                  </div>
                  {aiAnswer.reasoning && (
                    <div style={{ paddingLeft: '48px', marginBottom: '12px' }}>
                      <div style={styles.aiMeta}>Reasoning</div>
                      <p style={{ fontSize: '13px', color: '#6B6A63', lineHeight: 1.7, margin: 0 }}>{aiAnswer.reasoning}</p>
                    </div>
                  )}
                  {aiAnswer.relevant_laws?.length > 0 && (
                    <div style={{ paddingLeft: '48px', display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
                      {aiAnswer.relevant_laws.map((l, i) => <span key={i} style={styles.lawTag}>{l}</span>)}
                    </div>
                  )}
                  <div style={{ paddingLeft: '48px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={styles.confidenceBadge(aiAnswer.confidence)}>
                      {aiAnswer.confidence} confidence
                    </span>
                    {aiAnswer.caveats && (
                      <span style={{ fontSize: '12px', color: '#9B9A93' }}>{aiAnswer.caveats}</span>
                    )}
                  </div>
                </div>
              )}

              {!aiAnswer && !asking && (
                <div style={styles.emptyState}>
                  <div style={styles.emptyIcon}>
                    <MessageCircle size={22} color="#B8973A" />
                  </div>
                  <p style={{ ...styles.emptyDesc, marginBottom: 0 }}>
                    Ask a question above to get AI-backed insights on this case.
                  </p>
                </div>
              )}
            </div>
          )}
        </main>

        {/* ── Document Detail Modal ── */}
        {selectedDoc && (
          <DocumentDetail
            doc={selectedDoc}
            analysis={selectedDoc.analysis}
            previousFollowups={followupHistory.filter(f => f.filename !== selectedDoc.filename)}
            onClose={() => setSelectedDoc(null)}
            onDelete={(id, name) => { setSelectedDoc(null); handleDelete(id, name); }}
          />
        )}
      </div>
    </>
  );
}