import { CheckCircle, AlertTriangle, Scale, TrendingUp, ArrowRight } from 'lucide-react';

export default function AnalysisResult({ result }) {
  if (!result) return null;
  const { summary, classification, laws_suggested, future_scope, follow_up, extracted } = result;

  return (
    <div className="space-y-4 mt-4">
      {/* Summary */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle size={16} className="text-blue-600" />
          <span className="font-semibold text-blue-800 text-sm">Document Summary</span>
          <span className="ml-auto bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full capitalize">
            {classification}
          </span>
        </div>
        <p className="text-gray-700 text-sm">{summary}</p>
      </div>

      {/* Follow-up */}
      {follow_up && follow_up !== 'null' && (
        <div className="bg-amber-50 border border-amber-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <ArrowRight size={16} className="text-amber-600" />
            <span className="font-semibold text-amber-800 text-sm">Follow-up from Previous Docs</span>
          </div>
          <p className="text-gray-700 text-sm">{follow_up}</p>
        </div>
      )}

      {/* Laws suggested */}
      {laws_suggested?.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Scale size={16} className="text-primary" />
            <span className="font-semibold text-gray-800 text-sm">Suggested Laws</span>
          </div>
          <div className="space-y-2">
            {laws_suggested.map((law, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className="bg-primary/10 text-primary font-mono px-2 py-0.5 rounded text-xs whitespace-nowrap">
                  {law.act} §{law.section}
                </span>
                <span className="text-gray-600">{law.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Future scope */}
      {future_scope?.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={16} className="text-green-600" />
            <span className="font-semibold text-gray-800 text-sm">Future Scope</span>
          </div>
          <ul className="space-y-1.5">
            {future_scope.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <span className="text-green-500 mt-0.5">•</span>
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Entities */}
      {extracted?.entities && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <span className="font-semibold text-gray-700 text-sm block mb-2">Extracted Entities</span>
          <div className="flex flex-wrap gap-2">
            {Object.entries(extracted.entities).map(([type, names]) =>
              names.map((name, i) => (
                <span key={`${type}-${i}`}
                  className="bg-white border border-gray-200 text-xs px-2 py-1 rounded-full text-gray-600">
                  <span className="text-primary font-medium">{type}:</span> {name}
                </span>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}