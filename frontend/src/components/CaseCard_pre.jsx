import { useNavigate } from 'react-router-dom';
import { FolderOpen, FileText, Clock } from 'lucide-react';

export default function CaseCard({ case: c }) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/case/${c.id}`)}
      className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 cursor-pointer hover:shadow-md hover:border-primary/30 transition group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <FolderOpen size={20} className="text-accent" />
          <h3 className="font-semibold text-primary group-hover:text-accent transition line-clamp-1">
            {c.title}
          </h3>
        </div>
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