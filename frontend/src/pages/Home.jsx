import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import { COMPACT_HEADER_QUERY, MOBILE_QUERY } from '../config/breakpoints';
import { useMediaQuery } from '../components/useMediaQuery';
import { useViewportWidth } from '../components/useViewportWidth';
import './Home.css';

// Width of the desktop maquette: the stage is drawn at this size, then zoomed to the screen.
const DESIGN_WIDTH = 1728;

// Données de démo de l'étape 1 (les deux méthodes d'entrée)
const methodes = [
  { icone: '/assets/code_bar.svg', titre: 'Code-barre', sousTitre: 'Produit emballé' },
  { icone: '/assets/camera.svg', titre: 'Photo', sousTitre: 'Aliment frais' },
];

/** One piece of the phone yellow line (decorative), positioned in Home.css. */
function LinePiece({ name, lazy = true }) {
  return (
    <img
      className={`home-line home-line--${name}`}
      src={`/assets/home_line_m_${name}.svg`}
      alt=""
      aria-hidden="true"
      data-bleed
      loading={lazy ? 'lazy' : 'eager'}
    />
  );
}

export default function Home() {
  // Phones, tablets and small laptops share the one-column home (no tablet maquette;
  // below 1280 px the desktop composition no longer fits).
  const isMobile = useMediaQuery(COMPACT_HEADER_QUERY);
  // The line pieces are cut where the line leaves a phone screen: on a tablet the cuts
  // would show, so tablets get no line (and do not download the pieces).
  const isPhone = useMediaQuery(MOBILE_QUERY);
  // Desktop: one line behind the whole stage. Phones: the line of the maquette is cut
  // into pieces where it leaves the screen, and each piece is attached to its section,
  // so it follows the content whatever the text height.
  const wave = isMobile ? null : (
    <img className="wave wave-home" src="/assets/yellow_line_home_page.svg" alt="" aria-hidden="true" />
  );
  // Desktop: the stage keeps the 1728 px maquette and is zoomed to the screen width,
  // so the line, the picture, the cards and the texts keep their proportions
  // (--z is used in Home.css for the minimum text sizes).
  const width = useViewportWidth();
  const zoom = width / DESIGN_WIDTH;
  const stageStyle = isMobile || !width ? undefined : { zoom, '--z': zoom };
  const heroImage = (
    // data-bleed: on phones the picture is cut by the screen edge on purpose (maquette).
    <div className="hero-image" data-bleed>
      {isPhone && <LinePiece name="hero" lazy={false} />}
      <img src="/assets/img_hero_section.png" alt="Personne allongée sur un canapé" />
    </div>
  );

  return (
    <Layout>
      {/* <main>: the main landmark of the page (WCAG 1.3.1, skip to the content). */}
      <main className="home-stage" style={stageStyle}>
        {wave}
        {/* Hero */}
        <section className="hero">
          <p className="hero-tag">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
          {/* .br-m: a space that becomes a line break on phones only (maquette). */}
          <h1 className="hero-title">
            Vivre avec<br />l'endométriose,<br />comprendre<span className="br-m"> </span>son<span className="br-m"> </span>assiette
          </h1>
          {/* Phones: the picture sits between the title and the text (maquette accueil mobile). */}
          {isMobile && heroImage}
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

        {!isMobile && heroImage}

        {/* Étape 1 */}
        <section className="section-step1">
          {isPhone && <LinePiece name="step1" />}
          <span className="step-label">Étape 1</span>
          <h2 className="section-title">Scannez, photographiez, ou <br />cherchez</h2>
          <p className="section-body">
            Un produit emballé se reconnaît à son code-barre. <br />
            Un aliment frais, à une photo ou simplement à son nom. <br />
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
          {isPhone && <LinePiece name="step2" />}
          <div className="step2-text">
            <span className="step-label">Étape 2</span>
            <h2 className="section-title">Et vous obtenez son profil</h2>
            <p className="section-body">
              Le score situe l'aliment sur une échelle, du plus anti-inflammatoire au plus
              pro-inflammatoire.<br className="br-d" /> En dessous, retrouvez le détail des
              nutriments et micro-nutriments qui allègent ou alourdissent le score.
            </p>
          </div>

          <div className="step2-visual">
            {isPhone && <LinePiece name="orange" />}
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
            <h2 className="pourquoi-title">Pourquoi<span className="br-m"> </span>l'alimentation&nbsp;?</h2>
            <p className="pourquoi-body">
              L'endométriose est une maladie inflammatoire chronique. <br className="br-d" />
              Des travaux de recherche s'intéressent au lien entre alimentation et inflammation,
              mais à ce jour, aucune institution médicale n'a émis de recommandation nutritionnelle
              spécifique à l'endométriose.<br /><br className="br-mo" />
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
          {isPhone && <LinePiece name="chatbot" />}
          <div className="chatbot-label">Une aide accessible</div>
          <h2 className="chatbot-title">Une question ? Elle a sa place ici.</h2>
          <p className="chatbot-body">
            Le chatbot d'Alimendo répond à partir de sources scientifiques<br className="br-d" /> et
            associatives identifiées à vos questions liées à l'endométriose<br className="br-d" /> et/ou
            l'impact de l'alimentation sur la maladie.<br className="br-d" /> Il est accessible en bas
            de chaque page.
          </p>
          <div className="chatbot-cta">
            <Link to="/chatbot" className="btn-secondary">Poser une question</Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}