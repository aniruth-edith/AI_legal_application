import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Scale, LogOut, User } from 'lucide-react';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  
  return (
    <nav className="bg-primary text-white px-6 py-7 flex items-center justify-between shadow-lg new">
      <Link to="/" className="flex items-center gap-2 text-xl font-bold tracking-wide">
        <Scale size={24} className="text-accent" />
        <span>Legal <span className="text-accent">AI</span></span>
      </Link>
      {user && (
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <User size={16} />
            <span>{user}</span>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 text-sm bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition"
          >
            <LogOut size={15} />
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}