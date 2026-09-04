import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import AnalyseZone from '../components/AnalyseZone.jsx';
import './ProduitEmballe.css';

export default function ProduitEmballe() {
  return (
    <Layout>
      <p style={{ marginLeft: '2rem', marginTop: '2rem' }}>
          <Link to="/analyser" className="btn-back">
            &larr; Retour
          </Link>
        </p>
      <main className="emb-main">
        
        <h1 className="emb-title">Produit emballé</h1>
        <p className="emb-subtitle">Photographiez le code-barre, ou saisissez-le à la main.</p>

        <AnalyseZone
          dropzoneText="Déposer une photo du code-barre"
          dropzoneHint="JPG, PNG — 10 Mo max"
        />

        <div className="or-sep">ou saisie manuelle</div>

        <form className="manual" onSubmit={(e) => e.preventDefault()}>
          <input type="text" placeholder="Ex : 3760049790337" aria-label="Saisir un code-barre" />
          <Link to="/aliment" className="btn-primary">Valider</Link>
        </form>

        <p className="emb-note">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
      </main>
    </Layout>
  );
}