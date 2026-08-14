import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import Aliment from './pages/Aliment.jsx';
import EnSavoirPlus from './pages/EnSavoirPlus.jsx';
import Authentification from './pages/Authentification.jsx';
import Analyser from './pages/Analyser.jsx';
import ProduitEmballe from './pages/ProduitEmballe.jsx';
import AlimentFrais from './pages/AlimentFrais.jsx';
import Home from './pages/Home.jsx';
import Chatbot from './pages/Chatbot.jsx';

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
      <Route path="/en-savoir-plus" element={<EnSavoirPlus />} />
      <Route path="/connexion" element={<Authentification />} />
      <Route path="/analyser" element={<Analyser />} />
      <Route path="/produit-emballe" element={<ProduitEmballe />} />
      <Route path="/aliment-frais" element={<AlimentFrais />} />
      <Route path="/" element={<Home />} />
      <Route path="/chatbot" element={<Chatbot />} />
    </Routes>
  );
}