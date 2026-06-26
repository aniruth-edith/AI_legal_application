import { useState, useEffect } from 'react';
// import { useNavigate } from 'react-router-dom';
import { getCases, createCase } from '../api/client';
import { useAuth } from '../context/AuthContext';
import CaseCard from '../components/CaseCard';
import { Plus, Scale, X } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

export default function Dashboard() {
  const { user } = useAuth();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ title: '', description: '' });
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const fetchCases = async () => {
    try {
      const res = await getCases();
      setCases(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // useEffect(() => { fetchCases(); }, []);
  useEffect(() => { fetchCases(); }, [location.key]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const res = await createCase(form.title, form.description);
      setCases([res.data, ...cases]);
      setShowModal(false);
      setForm({ title: '', description: '' });
      navigate(`/case/${res.data.id}`);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create case');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-5 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-primary">
            Welcome back, {user} 
          </h1>
          <p className="text-gray-500 mt-1">
            {cases.length} case{cases.length !== 1 ? 's' : ''} in your workspace
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-primary text-white px-5 py-2.5 rounded-xl font-medium hover:bg-primary/90 transition shadow"
        >
          <Plus size={18} />
          New Case
        </button>
      </div>

      {/* Cases grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map(i => (
            <div key={i} className="bg-white rounded-xl h-32 animate-pulse border border-gray-100" />
          ))}
        </div>
      ) : cases.length === 0 ? (
        <div className="text-center py-20">
          <Scale size={48} className="text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-500">No cases yet</h3>
          <p className="text-gray-400 text-sm mt-1">Create your first case to start analysing documents</p>
          <button
            onClick={() => setShowModal(true)}
            className="mt-4 bg-primary text-white px-6 py-2.5 rounded-xl font-medium hover:bg-primary/90 transition"
          >
            Create Case
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cases.map(c => (
            <CaseCard
              key={c.id}
              case={c}
              onDeleted={(deletedId) => setCases(prev => prev.filter(p => p.id !== deletedId))}
            />
          ))}
        </div>
      )}

      {/* New case modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-primary">New Case</h2>
              <button onClick={() => setShowModal(false)}>
                <X size={20} className="text-gray-400 hover:text-gray-600" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Case title</label>
                <input
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="e.g. State vs Sharma 2024"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary"
                  rows={3}
                  placeholder="Brief description of the case..."
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 border border-gray-300 text-gray-600 py-2.5 rounded-lg hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-primary/90 transition disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Create Case'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}