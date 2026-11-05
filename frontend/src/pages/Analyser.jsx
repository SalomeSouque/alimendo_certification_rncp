import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import FoodSearchForm from '../components/FoodSearchForm.jsx';
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
              <div className="choice-icon"><img src={mode.icone} alt="" aria-hidden="true" /></div>
              <h2>{mode.titre}</h2>
              <p>{mode.desc}</p>
            </Link>
          ))}
        </div>

        <FoodSearchForm placeholder="ou rechercher directement par nom" />

        <p className="analyse-note">Projet étudiant · cet outil ne remplace pas un suivi médical.</p>
      </main>
    </Layout>
  );
}