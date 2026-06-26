import { FileText, Calendar } from 'lucide-react';

const DOC_TYPE_COLORS = {
  judgment: 'bg-blue-100 text-blue-700',
  petition: 'bg-purple-100 text-purple-700',
  FIR: 'bg-red-100 text-red-700',
  chargesheet: 'bg-orange-100 text-orange-700',
  statute: 'bg-green-100 text-green-700',
  'bail order': 'bg-yellow-100 text-yellow-700',
  writ: 'bg-pink-100 text-pink-700',
  affidavit: 'bg-gray-100 text-gray-700',
  'legal document': 'bg-gray-100 text-gray-600',
};

export default function TimelineView({ events }) {
  if (!events?.length) return (
    <p className="text-gray-400 text-sm">No timeline events yet.</p>
  );

  return (
    <div className="relative">
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />
      <div className="space-y-5">
        {events.map((event, i) => (
          <div key={i} className="flex gap-4 relative">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold z-10 shrink-0">
              {event.index || i + 1}
            </div>
            <div className="bg-white border border-gray-100 rounded-xl p-4 flex-1 shadow-sm">
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="flex items-center gap-2">
                  <FileText size={14} className="text-gray-400" />
                  <span className="font-medium text-gray-800 text-sm">{event.filename}</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full capitalize shrink-0 ${DOC_TYPE_COLORS[event.doc_type] || 'bg-gray-100 text-gray-600'}`}>
                  {event.doc_type}
                </span>
              </div>
              <div className="flex items-center gap-1 text-xs text-gray-400 mb-2">
                <Calendar size={11} />
                {event.date}
              </div>
              {event.summary && (
                <p className="text-gray-600 text-xs line-clamp-2">{event.summary}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}