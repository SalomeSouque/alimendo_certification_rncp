import { Link, useParams } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import FoodScore from '../components/FoodScore.jsx';
import { useApiResource } from '../components/useApiResource';
import { getBarcodeScore, getCategories, getFoodScore } from '../services/score';
import './Aliment.css';

/** Loads the food and, for a CIQUAL food, the name of its category (optional). */
async function loadFood({ id, code }) {
  const detail = code ? await getBarcodeScore(code) : await getFoodScore(id);
  let categoryName;
  if (detail.aliment.id_categorie != null) {
    try {
      const categories = await getCategories();
      categoryName = categories.find((c) => c.id_categorie === detail.aliment.id_categorie)?.nom;
    } catch {
      // The category is only a label: its absence must not hide the score.
    }
  }
  return { detail, categoryName };
}

function errorText(err, isBarcode) {
  if (err?.status === 404) {
    return isBarcode
      ? 'Ce code-barre est inconnu d’Open Food Facts. Vérifiez-le, ou recherchez l’aliment par son nom.'
      : 'Cet aliment est introuvable.';
  }
  return err?.message ?? 'Une erreur est survenue. Réessayez.';
}

/**
 * Score page of a food: /aliment/:id (CIQUAL) or /produit/:code (barcode, Open Food Facts).
 */
export default function Aliment() {
  const { id, code } = useParams();
  const isBarcode = Boolean(code);
  const { status, data, error } = useApiResource(() => loadFood({ id, code }), code ?? id);

  return (
    <Layout>
      <main className="aliment-wrap">
        <p className="aliment-back">
          <Link to={isBarcode ? '/produit-emballe' : '/analyser'} className="btn-back">&larr; Retour</Link>
        </p>

        {status === 'loading' && (
          <div className="aliment-state" role="status">
            <div className="spinner" aria-hidden="true" />
            <p>{isBarcode ? 'Recherche du produit…' : 'Chargement du score…'}</p>
          </div>
        )}

        {status === 'error' && (
          <div className="aliment-state" role="alert">
            <img src="/assets/food_not_found.svg" alt="" aria-hidden="true" className="aliment-state-icon" />
            <h1 className="aliment-state-title">
              {error?.status === 404 ? 'Aliment non trouvé' : 'Score indisponible pour le moment'}
            </h1>
            <p>{errorText(error, isBarcode)}</p>
            <Link to="/analyser" className="btn-primary">Rechercher un aliment</Link>
          </div>
        )}

        {status === 'success' && <FoodScore detail={data.detail} categoryName={data.categoryName} />}
      </main>
    </Layout>
  );
}