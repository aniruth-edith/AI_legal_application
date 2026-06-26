import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getCaseDashboard, uploadDocument, deleteDocument,
  askQuestion, getCaseFollowup
} from '../api/client';
import AnalysisResult from '../components/AnalysisResult';
import LawsChart from '../components/LawsChart';
import TimelineView from '../components/TimelineView';
import {
  Upload, Trash2, ArrowLeft, RefreshCw,
  Scale, TrendingUp, Bell, FileText, MessageCircle, Send
} from 'lucide-react';

const TABS = ['Overview', 'Laws', 'Future Scope', 'Follow-up', 'Ask AI'];

export default function CaseView() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const fileRef = useRef();

  const [dash, setDash] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('Overview');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState('');
  const [followup, setFollowup] = useState(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const res = await getCaseDashboard(caseId);
      setDash(res.data);
    } catch (err) {
      if (err.response?.status !== 404) console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFollowup = async () => {
    try {
      const res = await getCaseFollowup(caseId);
      setFollowup(res.data);
    } catch (err) { console.error(err); }
  };

  useEffect(() => {
    fetchDashboard();
    fetchFollowup();
  }, [caseId]);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);
    setUploadError('');
    setUploadProgress(0);
    try {
      const res = await uploadDocument(caseId, file, setUploadProgress);
      setUploadResult(res.data);
      await fetchDashboard();
      await fetchFollowup();
    } catch (err) {
      setUploadError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Delete "${filename}"?`)) return;
    try {
      await deleteDocument(docId);
      await fetchDashboard();
    } catch (err) {
      alert(err.response?.data?.detail || 'Delete failed');
    }
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    setAsking(true);
    setAnswer(null);
    try {
      const res = await askQuestion(caseId, question);
      setAnswer(res.data);
    } catch (err) {
      setAnswer({ answer: 'Failed to get answer. Please try again.', reasoning: '', relevant_laws: [] });
    } finally {
      setAsking(false);
    }
  };

  const llm = dash?.llm_dashboard || {};
  const analytics = dash?.analytics || {};

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Back + title */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate('/')}
          className="p-2 rounded-lg hover:bg-gray-100 transition">
          <ArrowLeft size={20} className="text-gray-600" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-primary">
            {dash?.case?.title || 'Loading...'}
          </h1>
          {dash?.case?.description && (
            <p className="text-gray-500 text-sm">{dash.case.description}</p>
          )}
        </div>
        <button onClick={fetchDashboard}
          className="ml-auto p-2 rounded-lg hover:bg-gray-100 transition" title="Refresh">
          <RefreshCw size={18} className={`text-gray-500 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Upload section */}
      <div className="bg-white border-2 border-dashed border-gray-200 rounded-2xl p-6 mb-6 hover:border-primary/40 transition">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Upload size={18} className="text-primary" />
            <span className="font-semibold text-gray-700">Upload Document</span>
          </div>
          <span className="text-xs text-gray-400">PDF, DOCX, TXT</span>
        </div>

        <input ref={fileRef} type="file" accept=".pdf,.docx,.txt"
          onChange={handleUpload} className="hidden" id="file-upload" />
        <label htmlFor="file-upload"
          className={`flex items-center justify-center gap-2 w-full py-3 rounded-xl cursor-pointer transition font-medium text-sm
            ${uploading
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-primary/5 text-primary hover:bg-primary/10 border border-primary/20'}`}>
          {uploading ? (
            <>
              <RefreshCw size={16} className="animate-spin" />
              Analysing... {uploadProgress > 0 ? `(${uploadProgress}%)` : ''}
            </>
          ) : (
            <>
              <Upload size={16} />
              Choose file to upload & analyse
            </>
          )}
        </label>

        {uploadError && (
          <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-red-600 text-sm">
            {uploadError}
          </div>
        )}
        {uploadResult && <AnalysisResult result={uploadResult} />}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6 overflow-x-auto">
        {TABS.map(tab => (
          <button key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition whitespace-nowrap
              ${activeTab === tab
                ? 'bg-white text-primary shadow-sm'
                : 'text-gray-500 hover:text-gray-700'}`}>
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {loading ? (
        <div className="space-y-4">
          {[1,2,3].map(i => <div key={i} className="bg-white rounded-xl h-24 animate-pulse" />)}
        </div>
      ) : !dash ? (
        <div className="text-center py-16 text-gray-400">
          <FileText size={40} className="mx-auto mb-3 opacity-50" />
          <p>Upload your first document to see the case dashboard</p>
        </div>
      ) : (
        <>
          {/* Overview Tab */}
          {activeTab === 'Overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-2 space-y-4">
                <div className="bg-white rounded-xl p-5 border border-gray-100">
                  <h3 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                    <Scale size={16} className="text-primary" /> Case Summary
                  </h3>
                  <p className="text-gray-600 text-sm leading-relaxed">
                    {llm.cumulative_summary || 'No summary available yet.'}
                  </p>
                </div>
                <div className="bg-white rounded-xl p-5 border border-gray-100">
                  <h3 className="font-semibold text-gray-800 mb-2">Case Trajectory</h3>
                  <p className="text-gray-600 text-sm">{llm.case_trajectory || '—'}</p>
                </div>
                <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
                  <h3 className="font-semibold text-amber-800 mb-2 flex items-center gap-2">
                    <Bell size={16} /> Risk Assessment
                  </h3>
                  <p className="text-gray-700 text-sm">{llm.risk_assessment || '—'}</p>
                </div>
              </div>

              <div className="space-y-4">
                {/* Progress */}
                {analytics.progress && (
                  <div className="bg-white rounded-xl p-5 border border-gray-100">
                    <h3 className="font-semibold text-gray-800 mb-3 text-sm">Case Progress</h3>
                    <div className="flex items-end gap-2 mb-2">
                      <span className="text-3xl font-bold text-primary">
                        {analytics.progress.score}
                      </span>
                      <span className="text-gray-400 text-sm mb-1">/100</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2 mb-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${analytics.progress.score}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">{analytics.progress.stage}</span>
                  </div>
                )}

                {/* Doc list */}
                <div className="bg-white rounded-xl p-5 border border-gray-100">
                  <h3 className="font-semibold text-gray-800 mb-3 text-sm">Documents</h3>
                  <div className="space-y-2">
                    {dash.documents?.map(doc => (
                      <div key={doc.id}
                        className="flex items-center justify-between gap-2 text-sm group">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText size={13} className="text-gray-400 shrink-0" />
                          <span className="text-gray-700 truncate">{doc.filename}</span>
                        </div>
                        <button
                          onClick={() => handleDelete(doc.id, doc.filename)}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-50 transition">
                          <Trash2 size={13} className="text-red-400" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Laws Tab */}
          {activeTab === 'Laws' && (
            <div className="space-y-5">
              <div className="bg-white rounded-xl p-5 border border-gray-100">
                <h3 className="font-semibold text-gray-800 mb-4">Citation Frequency</h3>
                <LawsChart data={analytics.citation_frequency} />
              </div>
              <div className="bg-white rounded-xl p-5 border border-gray-100">
                <h3 className="font-semibold text-gray-800 mb-4">Consolidated Laws</h3>
                <div className="space-y-3">
                  {llm.consolidated_laws?.map((law, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                      <span className="bg-primary text-white font-mono text-xs px-2 py-1 rounded shrink-0">
                        {law.act} §{law.section}
                      </span>
                      <div>
                        <div className="text-xs text-gray-400 mb-0.5">
                          Cited {law.frequency}x
                        </div>
                        <p className="text-sm text-gray-600">{law.significance}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Future Scope Tab */}
          {activeTab === 'Future Scope' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="bg-white rounded-xl p-5 border border-gray-100">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <TrendingUp size={16} className="text-green-600" /> Future Scope
                </h3>
                <ul className="space-y-2">
                  {llm.future_scope?.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                      <span className="text-green-500 mt-1 shrink-0">→</span> {s}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="bg-white rounded-xl p-5 border border-gray-100">
                <h3 className="font-semibold text-gray-800 mb-4">Recommended Actions</h3>
                <ul className="space-y-2">
                  {llm.recommended_actions?.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                      <span className="text-primary mt-1 shrink-0">✓</span> {a}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Follow-up Tab */}
          {activeTab === 'Follow-up' && (
            <div className="space-y-5">
              <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
                <h3 className="font-semibold text-amber-800 mb-2 flex items-center gap-2">
                  <Bell size={16} /> Latest Follow-up Brief
                </h3>
                <p className="text-gray-700 text-sm">
                  {followup?.follow_up_brief || llm.follow_up_brief || 'No follow-up data yet.'}
                </p>
              </div>
              <div className="bg-white rounded-xl p-5 border border-gray-100">
                <h3 className="font-semibold text-gray-800 mb-4">Document Timeline</h3>
                <TimelineView events={dash.timeline} />
              </div>
              {followup?.history?.length > 0 && (
                <div className="bg-white rounded-xl p-5 border border-gray-100">
                  <h3 className="font-semibold text-gray-800 mb-4">Follow-up History</h3>
                  <div className="space-y-3">
                    {followup.history.map((h, i) => (
                      <div key={i} className="border-l-2 border-primary/30 pl-4 py-1">
                        <div className="text-xs text-gray-400 mb-1">{h.date} — {h.filename}</div>
                        <p className="text-sm text-gray-600">{h.follow_up}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Ask AI Tab */}
          {activeTab === 'Ask AI' && (
            <div className="space-y-5">
              <div className="bg-white rounded-xl p-5 border border-gray-100">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <MessageCircle size={16} className="text-primary" />
                  Ask a Legal Question
                </h3>
                <form onSubmit={handleAsk} className="flex gap-3">
                  <input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="e.g. What are the bail grounds in this case?"
                    className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <button type="submit" disabled={asking}
                    className="bg-primary text-white px-5 py-2.5 rounded-lg font-medium hover:bg-primary/90 transition disabled:opacity-50 flex items-center gap-2">
                    {asking ? <RefreshCw size={16} className="animate-spin" /> : <Send size={16} />}
                    Ask
                  </button>
                </form>
                <div className="flex flex-wrap gap-2 mt-3">
                  {['What are the bail grounds?', 'Which IPC sections apply?',
                    'What is the outcome likelihood?', 'What should we do next?'].map(q => (
                    <button key={q} onClick={() => setQuestion(q)}
                      className="text-xs bg-gray-100 hover:bg-primary/10 text-gray-600 hover:text-primary px-3 py-1.5 rounded-full transition">
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {answer && (
                <div className="bg-white rounded-xl p-5 border border-gray-100 space-y-3">
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Answer</div>
                    <p className="text-gray-800 text-sm">{answer.answer}</p>
                  </div>
                  {answer.reasoning && (
                    <div>
                      <div className="text-xs text-gray-400 mb-1">Reasoning</div>
                      <p className="text-gray-600 text-sm">{answer.reasoning}</p>
                    </div>
                  )}
                  {answer.relevant_laws?.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {answer.relevant_laws.map((l, i) => (
                        <span key={i}
                          className="bg-primary/10 text-primary text-xs px-2 py-1 rounded-full font-mono">
                          {l}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-2 pt-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full
                      ${answer.confidence === 'high' ? 'bg-green-100 text-green-700' :
                        answer.confidence === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-600'}`}>
                      {answer.confidence} confidence
                    </span>
                    {answer.caveats && (
                      <span className="text-xs text-gray-400">{answer.caveats}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

