// src/components/FoodScore.jsx
// Displays an AlimentDetail (score, badges, alternatives, disclaimers).
// Shared by the three score paths: search (/aliment/:id), barcode
// (/produit/:code) and, at step 4, the photo result.
// Every medical wording comes from the API (validated texts in
// backend/app/core/disclaimers.py): nothing medical is written here.

import { Link } from 'react-router-dom';
import ScoreBar from './ScoreBar';
import './FoodScore.css';

const FALLBACK_IMAGE = '/assets/couvert.svg';

function FoodImage({ food, className }) {
  if (food.url_image) {
    return <img className={className} src={food.url_image} alt="" />;
  }
  return <img className={`${className} food-img--placeholder`} src={FALLBACK_IMAGE} alt="" aria-hidden="true" />;
}

function ScoreCard({ score }) {
  return (
    <div className="score-card">
      <p className="kicker">Potentiel inflammatoire estimé</p>
      {score.disponible ? (
        <>
          <ScoreBar level={score.niveau} label={score.libelle} />
          <div className="score-scale" aria-hidden="true">
            <span>Anti-inflammatoire</span>
            <span>Neutre</span>
            <span>Pro-inflammatoire</span>
          </div>
          <p className="score-verdict">{score.libelle}</p>
        </>
      ) : (
        <p className="score-unavailable">{score.message}</p>
      )}
    </div>
  );
}

/**
 * @param {{ detail: object, categoryName?: string }} props
 *   detail: AlimentDetail returned by /score/aliment/{id} or /score/code-barre/{code}
 */
export default function FoodScore({ detail, categoryName }) {
  const { aliment, score, badges = [], alternatives = [] } = detail;
  const shownBadges = badges.filter((b) => b.libelle);
  const kicker = aliment.source === 'OFF' ? 'Produit emballé' : categoryName;

  return (
    <article className="food-score" aria-labelledby="food-title">
      <div className="top-row">
        <div className="col-left">
          <FoodImage food={aliment} className="food-img" />
        </div>

        <div className="col-right">
          {kicker && <p className="food-kicker">{kicker}</p>}
          <h1 className="food-title" id="food-title">{aliment.nom}</h1>

          <ScoreCard score={score} />

          {shownBadges.length > 0 && (
            <ul className="tags food-badges" aria-label="Repères nutritionnels">
              {shownBadges.map((b) => (
                <li key={b.nutriment} className="tag pos">{b.libelle}</li>
              ))}
            </ul>
          )}

          <p className="doc-line">
            Pour plus d'information sur la lecture du score,{' '}
            <Link to="/en-savoir-plus">consulter la documentation</Link>.
          </p>

          <div className="disclaimer-card">
            <p><b>{detail.disclaimer}</b></p>
            <p>{detail.citation_source}</p>
            <p className="disclaimer-mention">{detail.mention_projet_etudiant}</p>
          </div>
        </div>
      </div>

      {alternatives.length > 0 && (
        <section className="alternatives" aria-labelledby="alternatives-title">
          <div className="divider" />
          <h2 className="compare-title" id="alternatives-title">{detail.libelle_alternatives}</h2>
          <ul className="cards">
            {alternatives.map(({ aliment: alt, score: altScore }) => (
              <li key={alt.id_aliment ?? alt.nom} className="food-card">
                <Link to={`/aliment/${alt.id_aliment}`} className="food-card-link">
                  <FoodImage food={alt} className="food-card-img" />
                  <div className="body">
                    <span className="name">{alt.nom}</span>
                    {altScore.disponible && (
                      <>
                        <ScoreBar level={altScore.niveau} label={altScore.libelle} mini />
                        <span className="food-card-level">{altScore.libelle}</span>
                      </>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
          <p className="alternatives-chat">
            Une question sur ces aliments ? <Link to="/chatbot">Poser une question</Link>
          </p>
        </section>
      )}
    </article>
  );
}
