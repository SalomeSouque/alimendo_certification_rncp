import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import './Aliment.css';

export default function Aliment() {
  return (
    <Layout>
      <main className="aliment-wrap">

        <div className="top-row">
          <div className="col-left">
            <img className="food-img" src="/assets/saumon.png" alt="Saumon atlantique" />
            <div className="disclaimer-card">
              <p>
                Score basé sur le profil nutritionnel de l'aliment et son potentiel inflammatoire
                estimé selon la littérature scientifique (approche inspirée du Dietary Inflammatory
                Index, Shivappa et al., 2014). <b>Cet outil ne remplace pas un professionnel de santé.</b>
              </p>
              <Link to="/en-savoir-plus" className="btn-primary">En savoir plus</Link>
            </div>
          </div>

          <div className="col-right">
            <div className="food-kicker">Aliment frais · Poisson</div>
            <h1 className="food-title">Saumon atlantique</h1>

            <div className="score-card">
              <div className="kicker">Potentiel inflammatoire estimé</div>
              <div className="score-bar">
                <span className="score-knob" style={{ left: '22%' }}></span>
              </div>
              <div className="score-scale">
                <span>Anti-inflammatoire</span>
                <span>Neutre</span>
                <span>Pro-inflammatoire</span>
              </div>
              <div className="score-verdict">Profil plutôt anti-inflammatoire</div>
            </div>

            <p className="doc-line">
              Pour plus d'information sur la lecture du score{' '}
              <Link to="/en-savoir-plus">consulter la documentation.</Link>
            </p>

            <div className="factors up">
              <h3>Ce qui allège le score</h3>
              <div className="tags">
                <span className="tag pos">Oméga-3 (EPA/DHA)</span>
                <span className="tag pos">Vitamine D</span>
                <span className="tag pos">Sélénium</span>
                <span className="tag pos">Protéines</span>
              </div>
            </div>

            <div className="factors down">
              <h3>Ce qui alourdit le score</h3>
              <div className="tags">
                <span className="tag neg">Acides gras saturés</span>
              </div>
            </div>
          </div>
        </div>

        <div className="divider"></div>

        <h2 className="compare-title">Autres aliments au potentiel moins inflammatoire</h2>
        <p className="compare-sub">Même catégorie, score estimé plus bas. À vous de comparer.</p>

        <div className="compare-row">
          <div className="compare-left">
            <p>
              Comparaison établie sur le profil nutritionnel des aliments, à catégorie
              équivalente. Elle ne préjuge pas de l'effet d'un aliment sur une personne donnée.
            </p>
            <Link to="/chatbot" className="btn-secondary">Poser une question</Link>
          </div>

          <div className="carousel">
            <div className="cards">
              <div className="food-card">
                <img src="/assets/maquereau.png" alt="Maquereau" />
                <div className="body">
                  <div className="name">Maquereau</div>
                  <div className="mini-bar"><span className="mini-knob" style={{ left: '16%' }}></span></div>
                </div>
              </div>
              <div className="food-card">
                <img src="/assets/sardine.png" alt="Sardine" />
                <div className="body">
                  <div className="name">Sardine</div>
                  <div className="mini-bar"><span className="mini-knob" style={{ left: '19%' }}></span></div>
                </div>
              </div>
              <div className="food-card">
                <img src="/assets/truite.png" alt="Truite" />
                <div className="body">
                  <div className="name">Truite</div>
                  <div className="mini-bar"><span className="mini-knob" style={{ left: '14%' }}></span></div>
                </div>
              </div>
            </div>
            <button className="carousel-next" aria-label="Suivant">
              <img src="/assets/fleche_next.svg" alt="" />
            </button>
          </div>
        </div>

      </main>
    </Layout>
  );
}