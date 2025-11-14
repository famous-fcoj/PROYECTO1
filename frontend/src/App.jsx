import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import OrdenTrabajoForm from './components/OrdenTrabajoForm';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Layout>
          <Routes>
            <Route path="/" element={
              <iframe
                src="/ot_form.html"
                style={{ width: '100%', height: 'calc(100vh - 160px)', border: 'none' }}
                title="Formulario OT"
              />
            } />
            <Route path="/carga-excel" element={<OrdenTrabajoForm />} />
          </Routes>

          <footer className="app-footer">
            <p>© 2025 CONMETAL</p>
          </footer>
        </Layout>
      </div>
    </Router>
  );
}

export default App;