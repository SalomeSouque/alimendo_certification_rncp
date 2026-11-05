import { Link, useSearchParams } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import FoodSearchForm from '../components/FoodSearchForm.jsx';
import { useApiResource } from '../components/useApiResource';
import { SEARCH_MIN_LENGTH, searchFoods } from '../services/score';
import './Recherche.css';

/** Search results page: /recherche?q=… (GET /search/aliments). */
export default function Recherche() {
  const [params] = useSearchParams();
  const term = (params.get('q') ?? '').trim();
  const valid = term.length >= SEARCH_MIN_LENGTH;
  const { status, data, error } = useApiResource(() => searchFoods(term), valid ? term : null);

  return (
    <Layout>
      <main className="search-main">
        <h1 className="search-title">Rechercher un aliment</h1>
        {/* key: reset the field when the URL term changes */}
        <FoodSearchForm key={term} initialTerm={term} />

        {!valid && <p className="search-hint">Saisissez le nom d’un aliment, par exemple « lentilles ».</p>}

        {valid && status === 'loading' && (
          <p className="search-status" role="status">Recherche en cours…</p>
        )}

        {valid && status === 'error' && (
          <p className="search-status search-status--error" role="alert">{error?.message}</p>
        )}

        {valid && status === 'success' && (
          <section aria-labelledby="results-title">
            <h2 id="results-title" className="search-count" aria-live="polite">
              {data.nombre_resultats === 0
                ? `Aucun aliment trouvé pour « ${term} »`
                : `${data.nombre_resultats} résultat${data.nombre_resultats > 1 ? 's' : ''} pour « ${term} »`}
            </h2>
            {data.nombre_resultats === 0 ? (
              <p className="search-hint">
                Vérifiez l’orthographe ou essayez un mot plus général. Pour un produit emballé,{' '}
                <Link to="/produit-emballe">saisissez son code-barre</Link>.
              </p>
            ) : (
              <ul className="search-results">
                {data.resultats.map((food) => (
                  <li key={food.id_aliment ?? food.nom}>
                    <Link to={`/aliment/${food.id_aliment}`} className="search-result">
                      {food.nom}
                      <img src="/assets/fleche_next.svg" alt="" aria-hidden="true" />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </main>
    </Layout>
  );
}
