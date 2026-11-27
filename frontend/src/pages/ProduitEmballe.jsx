import { Link, useNavigate } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import BarcodeScanner from '../components/BarcodeScanner.jsx';
import ManualBarcodeForm from '../components/ManualBarcodeForm.jsx';
import MobileBarcodeScan from '../components/analyse/MobileBarcodeScan.jsx';
import { MOBILE_QUERY } from '../config/breakpoints';
import { useMediaQuery } from '../components/useMediaQuery';
import './ProduitEmballe.css';

/** Barcode entry: camera, photo or typed code, then opens /produit/:code. */
export default function ProduitEmballe() {
  const navigate = useNavigate();
  const isMobile = useMediaQuery(MOBILE_QUERY);

  if (isMobile) return <MobileBarcodeScan />;

  return (
    <Layout>
      <p className="emb-back">
        <Link to="/analyser" className="btn-back">&larr; Retour</Link>
      </p>
      <main className="emb-main">
        <h1 className="emb-title">Produit emballé</h1>
        <p className="emb-subtitle">Scannez le code-barre, ou saisissez les chiffres inscrits dessous.</p>

        <BarcodeScanner onCode={(scanned) => navigate(`/produit/${scanned}`)} />

        <div className="or-sep">ou saisie manuelle</div>
        <ManualBarcodeForm />

        <p className="emb-note">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
      </main>
    </Layout>
  );
}
