import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Scale, LayoutDashboard, FolderOpen, LogOut, ChevronRight, Gavel } from 'lucide-react';

export default function Sidebar({ cases = [], onNewCase }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => { logout(); navigate('/login'); };

  const initials = user ? user.slice(0, 2).toUpperCase() : 'JA';

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="px-5 py-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-ink to-slate flex items-center justify-center shadow-ink">
            <Scale size={18} className="text-gold" />
          </div>
          <div>
            <div className="font-display text-lg font-semibold text-ink leading-none">Judiciary</div>
            <div className="text-[10px] font-mono text-gold tracking-widest uppercase leading-none mt-0.5">AI Analytics</div>
          </div>
        </div>
      </div>

      <div className="divider-gold mx-5 mb-4" />

      {/* Main nav */}
      <div className="px-3 mb-6">
        <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest px-3 mb-2">Workspace</div>
        <NavLink to="/"
          className={({ isActive }) => `nav-item ${isActive && location.pathname === '/' ? 'active' : ''}`}>
          <LayoutDashboard size={15} />
          Dashboard
        </NavLink>
      </div>

      {/* Cases list */}
      <div className="px-3 flex-1 overflow-y-auto">
        <div className="flex items-center justify-between px-3 mb-2">
          <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest">Cases</div>
          <button onClick={onNewCase}
            className="w-5 h-5 rounded-full bg-gold/10 hover:bg-gold/20 text-gold flex items-center justify-center transition text-xs font-bold">
            +
          </button>
        </div>

        {cases.length === 0 ? (
          <div className="text-center py-6 text-gray-400 text-xs px-3">
            No cases yet.<br/>
            <button onClick={onNewCase} className="text-gold hover:underline mt-1">Create one →</button>
          </div>
        ) : (
          <div className="space-y-0.5">
            {cases.map(c => (
              <NavLink key={c.id} to={`/case/${c.id}`}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                <FolderOpen size={14} className="shrink-0" />
                <span className="truncate flex-1">{c.title}</span>
                <ChevronRight size={12} className="shrink-0 opacity-40" />
              </NavLink>
            ))}
          </div>
        )}
      </div>

      {/* User footer */}
      <div className="p-4 border-t border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gold to-amber-600 flex items-center justify-center text-white text-xs font-bold">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-ink truncate">{user}</div>
            <div className="text-[11px] text-gray-400">Legal Analyst</div>
          </div>
          <button onClick={handleLogout}
            className="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition" title="Sign out">
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}