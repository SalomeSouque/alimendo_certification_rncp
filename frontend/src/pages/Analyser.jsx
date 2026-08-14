import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import './Analyser.css';

// Données de démo — les deux modes d'analyse
const modes = [
  {
    to: '/produit-emballe',
    icone: '/assets/code_bar.svg',
    titre: 'Produit emballé',
    desc: 'Scanner le code-barre',
  },
  {
    to: '/aliment-frais', 
    icone: '/assets/feuille_logo.svg',
    titre: 'Aliment frais',
    desc: 'Fruit, légume, viande, poisson…',
  },
];

export default function Analyser() {
  return (
    <Layout>
      <main className="analyse-main">
        <h1 className="analyse-title">Votre aliment a-t-il un code-barre ?</h1>

        <div className="choice-cards">
          {modes.map((mode, i) => (
            <Link className="choice-card" to={mode.to} key={i}>
              <div className="choice-icon"><img src={mode.icone} alt="" /></div>
              <h2>{mode.titre}</h2>
              <p>{mode.desc}</p>
            </Link>
          ))}
        </div>

        <form className="search-bar" onSubmit={(e) => e.preventDefault()}>
          <img className="loupe" src="/assets/loupe.svg" alt="" />
          <input
            type="text"
            placeholder="ou rechercher directement par nom"
            aria-label="Rechercher un aliment par nom"
          />
          <Link className="search-go" to="/aliment" aria-label="Rechercher">
            <img src="/assets/fleche_recherche_ou_retour.svg" alt="" />
          </Link>
        </form>

        <p className="analyse-note">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
      </main>
    </Layout>
  );
}