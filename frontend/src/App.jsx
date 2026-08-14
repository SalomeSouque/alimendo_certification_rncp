import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import Aliment from './pages/Aliment.jsx';

function Placeholder({ titre }) {
  return (
    <Layout>
      <main style={{ padding: '160px 40px', textAlign: 'center' }}>
        <h1>{titre} — page à porter</h1>
      </main>
    </Layout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/aliment" element={<Aliment />} />

      {/* Routes pas encore portées : placeholder friendly au lieu d'un écran blanc */}
      <Route path="/" element={<Placeholder titre="Accueil" />} />
      <Route path="*" element={<Placeholder titre="Cette page" />} />
    </Routes>
  );
}