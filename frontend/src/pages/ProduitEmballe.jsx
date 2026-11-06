import { useId, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import BarcodeScanner from '../components/BarcodeScanner.jsx';
import { BARCODE_PATTERN } from '../services/score';
import './ProduitEmballe.css';

/** Barcode entry: validates the EAN, then opens /produit/:code. */
export default function ProduitEmballe() {
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const inputId = useId();
  const hintId = useId();
  const errorId = useId();

  function handleSubmit(e) {
    e.preventDefault();
    const clean = code.replace(/\s/g, '');
    if (!BARCODE_PATTERN.test(clean)) {
      setError('Le code-barre doit contenir entre 8 et 14 chiffres, sans lettres.');
      inputRef.current?.focus();
      return;
    }
    setError(null);
    navigate(`/produit/${clean}`);
  }

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

        <form className="manual" onSubmit={handleSubmit} noValidate>
          <label htmlFor={inputId} className="sr-only">Code-barre</label>
          <input
            id={inputId}
            ref={inputRef}
            type="text"
            inputMode="numeric"
            autoComplete="off"
            placeholder="Ex : 3760049790337"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            aria-invalid={Boolean(error)}
            aria-describedby={[hintId, error ? errorId : null].filter(Boolean).join(' ')}
          />
          <button type="submit" className="btn-primary">Valider</button>
        </form>
        <p id={hintId} className="emb-hint">8 à 14 chiffres. Données produit issues d’Open Food Facts.</p>
        {error && <p id={errorId} className="emb-error">{error}</p>}

        <p className="emb-note">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
      </main>
    </Layout>
  );
}