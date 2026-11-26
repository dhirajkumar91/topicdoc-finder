import { BrowserRouter, Routes, Route } from 'react-router-dom'

import UserSearch from './pages/UserSearch'
import ResearchDiscovery from './pages/ResearchDiscovery'
import Documents from './pages/Documents'
import AdminLayout from './layouts/AdminLayout'
import UserLayout from './layouts/UserLayout'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* User workspace */}
        <Route element={<UserLayout />}>
          <Route path="/" element={<UserSearch />} />
        </Route>

        {/* Admin workspace */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<div>Admin Dashboard</div>} />
          <Route path="discovery" element={<ResearchDiscovery />} />
          <Route path="documents" element={<Documents />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App