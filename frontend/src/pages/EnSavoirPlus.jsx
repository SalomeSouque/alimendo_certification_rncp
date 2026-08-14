import Layout from '../components/Layout.jsx';
import './EnSavoirPlus.css';

// Données de démo — remplaceront un futur appel API / contenu éditorial validé
const sections = [
  {
    titre: 'Comprendre le score',
    corps: `Le score situe l'aliment sur un axe continu de −2 à +2, du profil plutôt anti-inflammatoire au profil plutôt pro-inflammatoire. Il reflète le profil nutritionnel de l'aliment et son potentiel inflammatoire estimé selon la littérature scientifique (approche inspirée du Dietary Inflammatory Index, Shivappa et al., 2014). Il qualifie un profil, jamais l'aliment comme « bon » ou « mauvais ».`,
    ouvert: true,
  },
  {
    titre: "Qu'est-ce que l'endométriose ?",
    corps: `L'endométriose est une maladie inflammatoire chronique dans laquelle un tissu semblable à la muqueuse utérine se développe hors de l'utérus. Elle peut provoquer des douleurs et concerne environ une personne menstruée sur dix.`,
  },
  {
    titre: 'Les limites de cet outil',
    corps: `Aucune institution médicale n'a émis de recommandation nutritionnelle spécifique à l'endométriose. Cet outil propose une lecture informative et sourcée, il ne pose pas de diagnostic et ne remplace pas l'avis d'un professionnel de santé.`,
  },
  {
    titre: 'Qui est derrière ce projet ?',
    corps: `Alimendo est un projet étudiant réalisé dans le cadre d'une formation en développement, à but pédagogique et non commercial.`,
  },
  {
    titre: 'Ressources et associations',
    corps: `Plusieurs associations accompagnent les personnes concernées par l'endométriose et diffusent une information fiable. Retrouvez-les dans la section Ressources.`,
  },
];

export default function EnSavoirPlus() {
  const wave = (
    <img
      className="wave wave-savoir"
      src="/assets/yellow_line_en_savoir_plus_page.svg"
      alt=""
      aria-hidden="true"
    />
  );

  return (
    <Layout wave={wave}>
      <main className="savoir-main">
        <div className="savoir-col">
          <h1 className="savoir-title">En savoir plus</h1>
          <p className="savoir-subtitle">
            Le fonctionnement du score, le contexte, et ce que cet outil ne fait pas.
          </p>

          <div className="accordion">
            {sections.map((section, i) => (
              <details className="acc-item" key={i} open={section.ouvert}>
                <summary>
                  {section.titre}
                  <img className="chev" src="/assets/felche_en_savoir_plus.svg" alt="" />
                </summary>
                <div className="acc-body">{section.corps}</div>
              </details>
            ))}
          </div>
        </div>
      </main>
    </Layout>
  );
}