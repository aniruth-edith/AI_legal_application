// import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
// import { AuthProvider } from './context/AuthContext';
// import ProtectedRoute from './components/ProtectedRoute';
// import Navbar from './components/Navbar';
// import Login from './pages/Login';
// import Register from './pages/Register';
// import Dashboard from './pages/Dashboard';
// import CaseView from './pages/CaseView';

// export default function App() {
//   return (
//     <AuthProvider>
//       <BrowserRouter>
//         <div className="min-h-screen bg-gray-50">
//           <Navbar />
//           <Routes>
//             {/* <Route path="/login" element={<Login />} />
//             <Route path="/register" element={<Register />} /> */}
//             <Route path="/" element={
//               <ProtectedRoute><Dashboard /></ProtectedRoute>
//             } />
//             <Route path="/case/:caseId" element={
//               <ProtectedRoute><CaseView /></ProtectedRoute>
//             } />
//             <Route path="*" element={<Navigate to="/" replace />} />
//           </Routes>
//         </div>
//       </BrowserRouter>
//     </AuthProvider>
//   );
// }

// import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
// import ProtectedRoute from './components/ProtectedRoute';
// import Login from './pages/Login';
// import Register from './pages/Register';
// import Dashboard from './pages/Dashboard';
// import CaseView from './pages/CaseView';

// export default function App() {
//   return (
//     <BrowserRouter>
//       <Routes>
//         <Route path="/login"        element={<Login />} />
//         <Route path="/register"     element={<Register />} />
//         <Route path="/"             element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
//         <Route path="/case/:caseId" element={<ProtectedRoute><CaseView /></ProtectedRoute>} />
//         <Route path="*"             element={<Navigate to="/" replace />} />
//       </Routes>
//     </BrowserRouter>
//   );
// }

import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import CaseView from './pages/CaseView';

const NO_NAVBAR_ROUTES = ['/login', '/register'];

function Layout() {
  const location = useLocation();
  const hideNavbar = NO_NAVBAR_ROUTES.includes(location.pathname);

  return (
    <div className="min-h-screen bg-gray-50">
      {!hideNavbar && <Navbar />}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/" element={
          <ProtectedRoute><Dashboard /></ProtectedRoute>
        } />
        <Route path="/case/:caseId" element={
          <ProtectedRoute><CaseView /></ProtectedRoute>
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    </AuthProvider>
  );
}