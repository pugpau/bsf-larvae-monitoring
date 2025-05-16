import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './styles/App.css';

// Import components
import Dashboard from './components/dashboard/Dashboard';
import SensorList from './components/sensors/SensorList';
import SensorDetail from './components/sensors/SensorDetail';
import SubstrateList from './components/substrate/SubstrateList';
import SubstrateDetail from './components/substrate/SubstrateDetail';

function App() {
  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <h1>BSF幼虫養殖環境監視システム</h1>
          <nav>
            <ul>
              <li><Link to="/">ダッシュボード</Link></li>
              <li><Link to="/sensors">センサー</Link></li>
              <li><Link to="/substrate">基質管理</Link></li>
            </ul>
          </nav>
        </header>
        <main className="app-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/sensors" element={<SensorList />} />
            <Route path="/sensors/:id" element={<SensorDetail />} />
            <Route path="/substrate" element={<SubstrateList />} />
            <Route path="/substrate/:id" element={<SubstrateDetail />} />
          </Routes>
        </main>
        <footer className="app-footer">
          <p>© 2025 BSF-LoopTech</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
