import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderOpen, FileText, Clock, Trash2 } from 'lucide-react';
import { deleteCase } from '../api/client';

export default function CaseCard({ case: c, onDeleted }) {
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (e) => {
    e.stopPropagation(); // don't trigger the card's navigate
    const confirmed = window.confirm(
      `Delete "${c.title}"? This will permanently remove the case and all its documents.`
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await deleteCase(c.id);
      onDeleted?.(c.id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete case');
      setDeleting(false);
    }
  };

  return (
    <div
      onClick={() => navigate(`/case/${c.id}`)}
      className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 cursor-pointer hover:shadow-md hover:border-primary/30 transition group relative"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <FolderOpen size={20} className="text-accent" />
          <h3 className="font-semibold text-primary group-hover:text-accent transition line-clamp-1">
            {c.title}
          </h3>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          title="Delete case"
          className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 hover:bg-red-50 p-1.5 rounded-lg transition shrink-0 disabled:opacity-50"
        >
          <Trash2 size={15} />
        </button>
      </div>

      {c.description && (
        <p className="text-gray-500 text-sm mb-3 line-clamp-2">{c.description}</p>
      )}

      <div className="flex items-center gap-4 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <FileText size={12} />
          {c.document_count || 0} documents
        </span>
        <span className="flex items-center gap-1">
          <Clock size={12} />
          {c.last_activity
            ? new Date(c.last_activity).toLocaleDateString()
            : new Date(c.created_at).toLocaleDateString()}
        </span>
      </div>
    </div>
  );
}