// src/components/AdminRoute.jsx
// Route guard for the admin space. The frontend check only hides the page:
// the real protection is require_role(ROLE_ADMIN) on the /admin/* endpoints.
//
//   - session still being restored: render nothing (avoids a redirect flash);
//   - logged out: redirect to the login page, then back here after login;
//   - logged in without the admin role: redirect to the home page.

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { isAdmin } from '../services/admin';

export default function AdminRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return null;
  if (!user) return <Navigate to="/connexion" replace state={{ from: location.pathname }} />;
  if (!isAdmin(user)) return <Navigate to="/" replace />;
  return children;
}
