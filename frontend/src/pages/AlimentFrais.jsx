import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import AnalyseZone from '../components/AnalyseZone.jsx';
import MobilePhotoCapture from '../components/analyse/MobilePhotoCapture.jsx';
import { usePhotoAnalysis } from '../components/usePhotoAnalysis';
import { MOBILE_QUERY } from '../config/breakpoints';
import { useMediaQuery } from '../components/useMediaQuery';
import './AlimentFrais.css';

// Phones: these states are full screen (maquettes M3b, M3e). Loading, result and
// "access pending" stay in the site layout (M3f, M3g, M5d).
const MOBILE_CAPTURE_STATES = ['idle', 'notFound', 'error'];

export default function AlimentFrais() {
  const analysis = usePhotoAnalysis();
  const isMobile = useMediaQuery(MOBILE_QUERY);

  if (isMobile && MOBILE_CAPTURE_STATES.includes(analysis.status)) {
    return <MobilePhotoCapture analysis={analysis} />;
  }

  // Phones, recognised food (maquette M4b): "Retour" goes back to the camera, the page
  // title gives way to the result (kept for screen readers).
  const mobileResult = isMobile && analysis.status === 'result';

  return (
    <Layout>
      {!isMobile && (
        <p className="frais-back">
          <Link to="/analyser" className="btn-back">&larr; Retour</Link>
        </p>
      )}
      <main className={`frais-main${mobileResult ? ' frais-main--result' : ''}`}>
        {mobileResult && (
          <p className="frais-back-m">
            <button type="button" className="btn-back" onClick={analysis.reset}>&larr; Retour</button>
          </p>
        )}
        <h1 className={mobileResult ? 'sr-only' : 'frais-title'}>Aliment frais</h1>
        {!mobileResult && (
          <p className="frais-subtitle">
            Identifiez un fruit, un légume, une viande ou un poisson à partir d'une photo.
          </p>
        )}

        <AnalyseZone
          analysis={analysis}
          dropzoneText="Déposer une photo de l'aliment"
          dropzoneHint="Un seul aliment brut, non emballé : fruit, légume, viande ou poisson. JPEG, PNG ou WebP, 5 Mo maximum."
        />
        {/* Phones: already said on the capture screen. */}
        {!isMobile && (
          <p className="frais-privacy">La photo est analysée puis oubliée : elle n’est jamais enregistrée.</p>
        )}

        <p className="frais-note">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
      </main>
    </Layout>
  );
}
