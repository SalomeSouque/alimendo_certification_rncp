import Layout from '../components/Layout.jsx';
import './EnSavoirPlus.css';

// Données de démo — remplaceront un futur appel API / contenu éditorial validé
const sections = [
  {
    titre: 'Comprendre le score',
    corps: [
      "Chaque aliment du site reçoit une note entre -2 et +2.",
      <dl>
        <dd>-2 très anti-inflammatoire</dd>
        <dd>-1 plutôt anti-inflammatoire</dd>
        <dd> 0 neutre, ou données trop faibles pour se prononcer</dd>
        <dd>+1 plutôt pro-inflammatoire</dd>
        <dd>+2 très pro-inflammatoire</dd>
      </dl>,
      "Ce score résume ce que la recherche dit du lien entre un aliment et l'inflammation en général. Il ne dit pas ce que cet aliment fera à votre endométriose. Personne ne peut le dire aujourd'hui (voir les limites de cet outils).",
      "Un aliment noté +2 n'est pas un aliment interdit. Il n'y a pas d'aliment interdit sur ce site le score est un repère.",
    ],
    ouvert: true,
  },
  {
    titre: "Qu'est-ce que l'endométriose ?",
    corps: [
      "L'endométriose est une systémique inflammatoire chronique et incurable. Elle se caractérise par la présence de tissu semblable à celui qui tapisse l'intérieur de l'utérus, mais situé ailleurs dans le corps. Sur les ovaires, sur le péritoine, parfois sur la vessie ou l'intestin.", 
      "Ce tissu réagit aux hormones du cycle. Il s'épaissit, saigne, sans pouvoir être évacué. Cela entretient une inflammation et, chez beaucoup de femmes, des douleurs.",
      "Environ une personne menstruée sur dix est concernée. À l'échelle mondiale, cela représente près de 190 millions de femmes.",
      "Les symptômes varient énormément d'une personne à l'autre. Douleurs de règles intenses, douleurs pendant les rapports, troubles digestifs, fatigue profonde, difficultés à concevoir. Certaines personnes ont des lésions étendues et peu de douleurs. D'autres ont peu de lésions et souffrent beaucoup. L'étendue de la maladie ne prédit pas ce que l'on ressent.",
      "Le diagnostic prend souvent des années. Les douleurs de règles ont longtemps été considérées comme normales, y compris par des soignants. Beaucoup de personnes ont entendu que c'était dans leur tête avant d'obtenir une réponse. Si c'est votre cas, ce n'était pas dans votre tête.",
      "L'origine de la maladie reste mal comprise. Plusieurs pistes sont étudiées, notamment génétiques, immunitaires, et plus récemment du côté du microbiote intestinal. La recherche avance, mais nous n'en sommes pas encore à une explication complète."
    ],
  },
  {
  titre: 'Les limites de cet outil',
  corps: [
    <div>
      <p>L'endométriose est une maladie encore mal comprise, et la recherche sur son lien avec l'alimentation en est à ses débuts. Cet outil hérite de ces incertitudes et ses limites sont fortes :</p>
      <br/>
      <ul style={{ listStyleType: 'none' }}>
        {/* Point 1 */}
        <li>
          <b>Ce site ne remplace pas un professionnel de santé.</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>Il ne pose aucun diagnostic et ne donne aucun conseil personnalisé. Si vos douleurs vous inquiètent, changent, ou deviennent difficiles à supporter, parlez-en à un médecin.</li>
          </ul>
        </li>
        <br/>
        {/* Point 2 */}
        <li>
          <b>C'est un projet étudiant.</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>Le site a été conçu dans le cadre d'un projet de fin d'études, à partir d'un petit nombre de sources sélectionnées. Aucun professionnel de santé n'en a validé le contenu.</li>
          </ul>
        </li>
        <br/>
        {/* Point 3 */}
        <li>
          <b>Aucun régime n'a été prouvé efficace contre l'endométriose.</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>C'est la position des recommandations internationales de référence. À ce jour, les données ne permettent de conseiller aucune alimentation particulière pour réduire les douleurs ou améliorer la qualité de vie. Ce site ne prétend pas le contraire.</li>
          </ul>
        </li>
        <br/>
        {/* Point 4 */}
        <li>
          <b>Attention aux régimes restrictifs.</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>Supprimer beaucoup d'aliments sans accompagnement expose à des carences et peut abîmer durablement le rapport à la nourriture. Ce site n'est pas fait pour vous aider à éliminer. Si vous voulez faire évoluer votre alimentation, un médecin ou un diététicien pourra vous accompagner en tenant compte de votre situation.</li>
          </ul>
        </li>
        <br/>
        {/* Point 5 */}
        <li>
          <b>Ce que vous ressentez compte, même si la science ne l'explique pas encore.</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>De nombreuses personnes constatent que certains aliments influencent leur confort digestif ou leurs douleurs. Ce vécu est réel. Il n'est simplement pas encore démontré à l'échelle d'une population.</li>
          </ul>
        </li>
        <br/>
        {/* Point 6 */}
        <li>
          <b>Le score parle d'inflammation, pas de vos symptômes.</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>La plupart des études disponibles portent sur l'inflammation en général, ou sur le risque de développer une endométriose. Très peu portent sur le soulagement des symptômes chez des personnes déjà malades. Ce sont deux questions différentes, et nous ne les mélangeons pas.</li>
          </ul>
        </li>
        <br/>
        {/* Point 7 */}
        <li>
          <b>Une association n'est pas une cause.</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>Quand une étude observe que les personnes qui mangent différemment ont des symptômes différents, cela ne prouve pas que l'alimentation en soit la cause. Beaucoup d'autres facteurs entrent en jeu.</li>
          </ul>
        </li>

      </ul>
      
    </div>
  ],
},
  {
    titre: 'Qui est derrière ce projet ?',
    corps: [
      "Je m'appelle Salomé, je suis étudiante en développement et en intelligence artificielle, et ce site est mon projet de fin d'études.",
      "Je souhaite m'orienter vers des métiers alliant médecine et IA, c'est pour cela que j'ai choisi un sujet médical. L'endométriose est une maladie encore trop méconnue, bien que découverte il y a envrion 160 ans et touchant personne menstruée sur dix. Je trouve donc pertinent de mettre la lumière sur ce sujet.",
      "Je ne suis pas médecin. Je n'ai pas de formation en nutrition ni en gynécologie. Je n'ai mené aucune recherche scientifique. Ce que j'ai fait, c'est lire ce que la recherche dit déjà, essayer de le comprendre, et le présenter le plus honnêtement possible.",
      "C'est aussi pour cette raison que vous trouverez autant de nuances et de limites sur ce site.",
    ],
  },
  {
    titre: 'Ressources et associations',
    corps: [
    <div>
      <p>Les organisations ci-dessous sont des structures réelles, avec des personnes, des comités scientifiques et des années d'expérience. Pour tout ce qui touche à votre santé, elles sont infiniment plus fiables que ce site.</p>
      <br/>
      <p style={{fontSize:"19px"}}><b>Associations de patientes :</b></p>
      <ul style={{ listStyleType: 'none' }}>
        {/* Association 1 */}
        <li  style={{ paddingLeft: '10px'}}>
          <b>- EndoFrance</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>La plus ancienne association française, créée en 2001, agréée par le ministère de la Santé depuis 2018. Elle s'appuie sur un conseil scientifique pluridisciplinaire et accompagne les personnes concernées ainsi que leur entourage.</li>
            <li><a href=" https://www.endofrance.org/" className='link-ressource'>endofrance.org</a></li>
          </ul>
        </li>
        <br/>
        {/* Association 2 */}
        <li  style={{ paddingLeft: '10px'}}>
          <b>- ENDOmind</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>Créée en 2014, également agréée par le ministère de la Santé. Très engagée sur la sensibilisation et le soutien à la recherche. Elle est à l'origine de la Fondation pour la Recherche sur l'Endométriose.</li>
            <li><a href="https://www.endomind.org/" className='link-ressource'>endomind.org</a></li>
          </ul>
        </li>
        <br/>
        {/* Association 3 */}
        <li  style={{ paddingLeft: '10px'}}>
          <b>- Info-Endométriose</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>Association d'information et de sensibilisation, à l'origine de campagnes nationales sur la maladie.</li>
            <li><a href="https://www.info-endometriose.fr/" className='link-ressource'>info-endometriose.fr</a></li>
          </ul>
        </li>
        <br/>
      </ul>
      <ul style={{ listStyleType: 'none' }}>
        <p style={{fontSize:"19px"}}><b>Pour aller plus loin :</b></p>
        {/* Source 1 */}
        <li  style={{ paddingLeft: '10px'}}>
          <b>- Dossier Inserm sur l'endométriose</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>Le point de référence en français sur la maladie et l'état de la recherche, rédigé avec des chercheurs.</li>
            <li><a href="https://www.inserm.fr/dossier/endometriose/" className='link-ressource'>inserm.fr/dossier/endometriose</a></li>
          </ul>
        </li>
        <br/>
        {/* Source 2 */}
        <li  style={{ paddingLeft: '10px'}}>
          <b>- Fondation pour la Recherche sur l'Endométriose</b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>La seule fondation européenne dédiée à cette maladie.</li>
            <li><a href="https://www.fondation-endometriose.org/" className='link-ressource'>fondation-endometriose.org</a></li>
          </ul>
        </li>
        <br/>
        {/* Source 3 */}
        <li  style={{ paddingLeft: '10px'}}>
          <b>- Organisation mondiale de la Santé (OMS) </b>
          <ul style={{ paddingLeft: '20px', listStyleType: 'none' }}>
            <li>La fiche d'information internationale sur l'endométriose.</li>
            <li><a href="https://www.who.int/news-room/fact-sheets/detail/endometriosis" className='link-ressource'>who.int</a></li>
          </ul>
        </li>
        <br/>
      </ul>
      <p style={{fontSize:"19px"}}><b>Si vous cherchez un professionnel :</b></p>
      <p>Des filières de soins et des centres experts dédiés à l'endométriose existent dans plusieurs régions françaises. Votre médecin traitant ou votre gynécologue peut vous orienter. Les associations ci-dessus tiennent également des annuaires et des groupes de parole.</p>
      <br/>
      <p><i>Si vos douleurs sont soudaines, très intenses ou inhabituelles, ne cherchez pas d'information en ligne : contactez un médecin, ou le 15.</i></p>
      
    </div>],
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
                <div className="acc-body">{section.corps.map((p, i) => (
                <p key={i} Style="margin-top: 10px">{p}</p>
              ))}</div>
              </details>
            ))}
          </div>
        </div>
      </main>
    </Layout>
  );
}