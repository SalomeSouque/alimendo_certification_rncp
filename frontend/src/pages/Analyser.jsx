import { Link, Navigate } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import FoodSearchForm from '../components/FoodSearchForm.jsx';
import { MOBILE_QUERY } from '../config/breakpoints';
import { useMediaQuery } from '../components/useMediaQuery';
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
  // Phones: no choice cards, the full-screen analysis opens on the "Code-barre" tab
  // and the other modes are one tap away at the bottom (maquettes M3).
  const isMobile = useMediaQuery(MOBILE_QUERY);
  if (isMobile) return <Navigate to="/produit-emballe" replace />;

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