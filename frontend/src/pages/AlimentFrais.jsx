import Layout from '../components/Layout.jsx';
import AnalyseZone from '../components/AnalyseZone.jsx';
import './AlimentFrais.css';

export default function AlimentFrais() {
  return (
    <Layout>
      <main className="frais-main">
        <h1 className="frais-title">Aliment frais</h1>
        <p className="frais-subtitle">
          Identifiez un fruit, un légume, une viande ou un poisson à partir d'une photo.
        </p>

        <AnalyseZone
          dropzoneText="Déposer une photo de l'aliment"
          dropzoneHint="Aliment brut, non emballé et non transformé — un fruit, un légume, une viande ou un poisson."
        />

        <p className="frais-note">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
      </main>
    </Layout>
  );
}