import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import './Home.css';

// Données de démo de l'étape 1 (les deux méthodes d'entrée)
const methodes = [
  { icone: '/assets/code_bar.svg', titre: 'Code-barre', sousTitre: 'Produit emballé' },
  { icone: '/assets/camera.svg', titre: 'Photo', sousTitre: 'Aliment frais' },
];

export default function Home() {
  const wave = (
    <img
      className="wave wave-home"
      src="/assets/yellow_line_home_page.svg"
      alt=""
      aria-hidden="true"
    />
  );

  return (
    <Layout wave={wave}>
      {/* Hero */}
      <section className="hero">
        <p className="hero-tag">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
        <h1 className="hero-title">Vivre avec<br />l'endométriose,<br />comprendre son assiette</h1>
        <p className="hero-description">
          Estimez le potentiel inflammatoire d'un aliment à partir d'une photo, d'un
          code-barre ou de son nom. Obtenez une information sourcée sur un aliment, cet
          outil ne remplace pas un suivi médical.<br />
          Consultez un professionnel de santé pour toute décision relative à votre pathologie.
        </p>
        <div className="hero-buttons">
          <Link to="/analyser" className="btn-primary">
            Commencer l'analyse <span className="arrow">&rarr;</span>
          </Link>
          <Link to="/chatbot" className="btn-secondary">Poser une question</Link>
        </div>
      </section>

      <div className="hero-image">
        <img src="/assets/img_hero_section.png" alt="Personne allongée sur un canapé" />
      </div>

      {/* Étape 1 */}
      <section className="section-step1">
        <span className="step-label">Étape 1</span>
        <h2 className="section-title">Scannez, photographiez, ou<br />cherchez</h2>
        <p className="section-body">
          Un produit emballé se reconnaît à son code-barre.<br />
          Un aliment frais, à une photo ou simplement à son nom.<br />
          Deux chemins selon ce que vous avez sous la main.
        </p>
        <div className="method-cards">
          {methodes.map((m, i) => (
            <div className="method-card" key={i}>
              <div className="method-icon"><img src={m.icone} alt="" /></div>
              <div>
                <div className="method-card-title">{m.titre}</div>
                <div className="method-card-subtitle">{m.sousTitre}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Étape 2 */}
      <section className="section-step2">
        <div className="step2-text">
          <span className="step-label">Étape 2</span>
          <h2 className="section-title">Et vous obtenez son profil</h2>
          <p className="section-body">
            Le score situe l'aliment sur une échelle, du plus anti-inflammatoire au plus
            pro-inflammatoire. En dessous, retrouvez le détail des nutriments et micro-nutriments
            qui allègent ou alourdissent le score.
          </p>
        </div>

        <div className="step2-visual">
          <div className="card card-aliment">
            <div className="lbl">Aliment</div>
            <div className="val">Orange</div>
            <div className="sub">Fruit entier, mûr</div>
          </div>

          <div className="card card-micro">
            <div className="ic"><img src="/assets/couvert.svg" alt="" /></div>
            <div>
              <div className="t">Micro-nutriment</div>
              <div className="s">Source de vitamine C</div>
            </div>
          </div>

          <div className="orange-img"><img src="/assets/orange.svg" alt="Orange coupée en deux" /></div>

          <div className="card card-score">
            <div className="lbl">Potentiel inflammatoire</div>
            <div className="score-bar"><span className="score-knob"></span></div>
            <div className="caption">Profil plutôt anti-inflammatoire</div>
          </div>
        </div>
      </section>

      {/* Pourquoi */}
      <section className="section-pourquoi">
        <div className="pourquoi-card">
          <div className="pourquoi-label">Pourquoi Alimendo</div>
          <h2 className="pourquoi-title">Pourquoi l'alimentation ?</h2>
          <p className="pourquoi-body">
            L'endométriose est une maladie inflammatoire chronique.
            Des travaux de recherche s'intéressent au lien entre alimentation et inflammation,
            mais à ce jour, aucune institution médicale n'a émis de recommandation nutritionnelle
            spécifique à l'endométriose.<br /><br />
            Alimendo vous donne de quoi lire ces travaux, et obtenir l'information rapidement et facilement.
          </p>
          <div className="pourquoi-buttons">
            <Link to="/en-savoir-plus" className="btn-primary">Comprendre le score et ses limites</Link>
            <Link to="/en-savoir-plus" className="btn-secondary">Les associations qui accompagnent</Link>
          </div>
        </div>
      </section>

      {/* Chatbot */}
      <section className="section-chatbot">
        <div className="chatbot-label">Une aide accessible</div>
        <h2 className="chatbot-title">Une question ? Elle a sa place ici.</h2>
        <p className="chatbot-body">
          Le chatbot d'Alimendo répond à partir de sources scientifiques et associatives
          identifiées à vos questions liées à l'endométriose et/ou l'impact de l'alimentation
          sur la maladie. Il est accessible en bas de chaque page.
        </p>
        <div className="chatbot-cta">
          <Link to="/chatbot" className="btn-secondary">Poser une question</Link>
        </div>
      </section>
    </Layout>
  );
}