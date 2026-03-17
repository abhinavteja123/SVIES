import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Sidebar';

import Overview from './pages/Overview';
import LiveDetection from './pages/LiveDetection';
import ImageVerify from './pages/ImageVerify';
import VehicleLookup from './pages/VehicleLookup';
import Violations from './pages/Violations';
import Analytics from './pages/Analytics';
import Offenders from './pages/Offenders';
import ZoneMap from './pages/ZoneMap';
import ActiveLearning from './pages/ActiveLearning';
import UserManagement from './pages/UserManagement';
import VehicleManagement from './pages/VehicleManagement';
import Login from './pages/Login';

function AuthenticatedLayout() {
  return (
    <ProtectedRoute>
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/detect" element={<LiveDetection />} />
          <Route path="/verify" element={<ImageVerify />} />
          <Route path="/lookup" element={<VehicleLookup />} />
          <Route path="/violations" element={<Violations />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/offenders" element={<Offenders />} />
          <Route
            path="/zones"
            element={
              <ProtectedRoute requiredRole="VIEWER">
                <ZoneMap />
              </ProtectedRoute>
            }
          />
          <Route
            path="/learning"
            element={
              <ProtectedRoute requiredRole="ADMIN">
                <ActiveLearning />
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute requiredRole="POLICE">
                <UserManagement />
              </ProtectedRoute>
            }
          />
          <Route
            path="/vehicle-management"
            element={
              <ProtectedRoute requiredRole="RTO">
                <VehicleManagement />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<AuthenticatedLayout />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
