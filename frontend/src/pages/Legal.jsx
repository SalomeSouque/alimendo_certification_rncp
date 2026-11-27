import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import { LEGAL } from '../config/legal.js';
import './Legal.css';

/** A value of src/config/legal.js, or a visible "à compléter" while it is empty. */
function Value({ children }) {
  return children ? children : <span className="legal-todo">à compléter</span>;
}

function ContactEmail() {
  return LEGAL.contactEmail
    ? <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>
    : <Value />;
}

function LegalPage({ title, children }) {
  return (
    <Layout>
      <main className="legal-main">
        <div className="legal-col">
          <h1 className="legal-title">{title}</h1>
          <p className="legal-updated">Dernière mise à jour : {LEGAL.updatedOn}</p>
          {children}
        </div>
      </main>
    </Layout>
  );
}

/** Legal notice (French LCEN, art. 6-III). */
export function MentionsLegales() {
  return (
    <LegalPage title="Mentions légales">
      <h2>Éditrice du site</h2>
      <p>
        Alimendo est un projet étudiant non commercial, réalisé par <strong>{LEGAL.editorName}</strong>,
        personne physique, dans le cadre de la certification « Développeur en intelligence
        artificielle » (RNCP37827). Elle est aussi directrice de la publication.
      </p>
      <p>Contact : <ContactEmail /></p>

      <h2>Hébergement</h2>
      <p>
        <Value>{LEGAL.host.name}</Value><br />
        <Value>{LEGAL.host.address}</Value><br />
        Téléphone : <Value>{LEGAL.host.phone}</Value>
      </p>

      <h2>Nature du service</h2>
      <p>
        Alimendo donne des informations générales sur le profil nutritionnel des aliments, à partir
        de données publiques. Ce n’est pas un dispositif médical. Cet outil ne remplace pas un suivi
        médical. Consultez un professionnel de santé pour toute décision relative à votre pathologie.
      </p>

      <h2>Sources des données</h2>
      <ul>
        <li>Table de composition nutritionnelle Ciqual, ANSES (Licence Ouverte).</li>
        <li>Open Food Facts : données produits sous licence ODbL, images sous licence CC BY-SA.</li>
        <li>Les sources des réponses du chatbot sont citées sous chaque réponse.</li>
      </ul>

      <h2>Données personnelles</h2>
      <p>
        Voir la page <Link to="/confidentialite">Confidentialité</Link>.
      </p>
    </LegalPage>
  );
}

/** Privacy notice (GDPR art. 13). Must stay consistent with docs/rgpd/. */
export function Confidentialite() {
  return (
    <LegalPage title="Confidentialité">
      <h2>Responsable du traitement</h2>
      <p>
        {LEGAL.editorName}, éditrice d’Alimendo (projet étudiant). Contact : <ContactEmail />
      </p>

      <h2>Données enregistrées</h2>
      <p>
        Seule la création d’un compte enregistre des données personnelles : votre email, votre mot
        de passe (chiffré de façon irréversible, jamais stocké en clair), la date de création du
        compte, la date de votre dernière connexion et l’ouverture ou non de votre accès aux outils
        d’intelligence artificielle. Aucune autre donnée n’est demandée.
      </p>
      <p>
        Le score d’un aliment, la recherche et les pages d’information sont accessibles sans compte.
      </p>

      <h2>Pourquoi et sur quelle base</h2>
      <p>
        Ces données servent uniquement à gérer votre compte et votre accès au chatbot et à l’analyse
        par photo. Base légale : l’exécution du service que vous demandez (article 6.1.b du RGPD).
        Avoir un compte sur un site consacré à l’endométriose peut révéler une information sur votre
        santé : c’est pourquoi l’inscription demande aussi votre consentement explicite
        (article 9.2.a du RGPD).
      </p>

      <h2>Ce qui n’est pas enregistré</h2>
      <ul>
        <li>
          Les questions posées au chatbot ne sont pas enregistrées. Elles peuvent être transmises à
          un service d’IA externe (Mistral AI) pour générer la réponse : n’indiquez pas
          d’informations personnelles ou de santé.
        </li>
        <li>
          Les photos d’aliments sont analysées sur notre serveur, en mémoire, puis oubliées.
        </li>
        <li>
          Le code-barre est lu dans votre navigateur : seuls ses chiffres sont envoyés au serveur.
        </li>
        <li>Pas de cookie, pas de publicité, pas de mesure d’audience.</li>
      </ul>

      <h2>Durées de conservation</h2>
      <ul>
        <li>Votre compte est supprimé après 3 ans sans connexion, ou plus tôt à votre demande.</li>
        <li>
          Les sauvegardes de la base sont conservées {LEGAL.backupDays} jours : un compte supprimé
          en disparaît au plus tard après ce délai.
        </li>
        <li>
          Les journaux techniques du serveur (adresse IP, page demandée), utiles à la sécurité,
          sont conservés <Value>{LEGAL.serverLogsRetention}</Value>.
        </li>
      </ul>

      <h2>Qui y a accès</h2>
      <p>
        Uniquement l’administratrice du site. Les données sont stockées chez l’hébergeur du site
        (voir les <Link to="/mentions-legales">mentions légales</Link>). Elles ne sont ni vendues ni
        partagées.
      </p>

      <h2>Dans votre navigateur</h2>
      <p>
        Une fois connectée, un jeton de connexion est gardé dans votre navigateur (stockage local)
        pour vous éviter de vous reconnecter à chaque page. Il est effacé à la déconnexion. Les
        polices d’écriture sont chargées depuis Google Fonts, ce qui transmet votre adresse IP à
        Google.
      </p>

      <h2>Vos droits</h2>
      <p>
        Vous pouvez demander l’accès à vos données, leur correction, leur suppression, la limitation
        de leur utilisation, leur portabilité, vous y opposer et retirer votre consentement à tout
        moment, en écrivant à <ContactEmail /> depuis l’adresse de votre compte. Réponse sous un
        mois. Vous pouvez aussi adresser une réclamation à la CNIL
        (<a href="https://www.cnil.fr" target="_blank" rel="noreferrer">cnil.fr</a>).
      </p>
    </LegalPage>
  );
}
