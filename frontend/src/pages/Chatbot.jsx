import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './Chatbot.css';

// Conversation de démo au chargement (remplacée par un état vide quand le RAG sera branché)
const messagesInitiaux = [
  {
    role: 'bot',
    texte: `Bonjour. Je réponds aux questions générales sur l'alimentation et l'endométriose, en m'appuyant sur des sources. Pour un aliment précis, l'analyse donnera un résultat plus fiable.`,
  },
];

export default function Chatbot() {
  const [messages, setMessages] = useState(messagesInitiaux);
  const [saisie, setSaisie] = useState('');
  const [enAttente, setEnAttente] = useState(false);
  const finDuFil = useRef(null);

  // Fait défiler le fil vers le bas à chaque nouveau message
  useEffect(() => {
    finDuFil.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function envoyer(e) {
    e.preventDefault();
    const question = saisie.trim();
    if (!question || enAttente) return;

    // 1. On ajoute le message de l'utilisatrice
    setMessages((prev) => [...prev, { role: 'user', texte: question }]);
    setSaisie('');
    setEnAttente(true);

    // 2. Placeholder du futur appel RAG — réponse simulée
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          texte: `Réponse à venir : le chatbot s'appuiera sur le corpus documentaire pour répondre, avec ses sources. (démonstration)`,
        },
      ]);
      setEnAttente(false);
    }, 1200);
  }

  return (
    <div className="chatbot-page">
      {/* Header repris du Layout mais sans le reste (page plein écran, pas de footer/FAB) */}
      <header className="header">
        <div className="header-logo"><img src="/assets/Logo.svg" alt="Logo Alimendo" /></div>
        <Link to="/" className="header-brand">ALIMENDO</Link>
        <span className="header-tagline">alimentation &amp; endométriose, en clair</span>
        <nav className="header-nav">
          <Link to="/">Accueil</Link>
          <Link to="/analyser">Analyser un aliment</Link>
          <Link to="/chatbot" className="active">Chatbot</Link>
          <Link to="/en-savoir-plus">En savoir plus</Link>
          <Link to="/connexion" className="btn-connect">Se connecter</Link>
        </nav>
      </header>

      <div className="chat-app">
        <div className="chat-thread">
          {messages.map((msg, i) =>
            msg.role === 'bot' ? (
              <div className="msg-bot" key={i}>{msg.texte}</div>
            ) : (
              <div className="msg-user" key={i}>{msg.texte}</div>
            )
          )}
          {enAttente && <div className="msg-bot msg-typing">…</div>}
          <div ref={finDuFil} />
        </div>

        <div className="chat-input-zone">
          <form className="chat-input" onSubmit={envoyer}>
            <input
              type="text"
              placeholder="Poser une question…"
              aria-label="Poser une question"
              value={saisie}
              onChange={(e) => setSaisie(e.target.value)}
            />
            <button className="chat-send" aria-label="Envoyer" type="submit">
              <img src="/assets/fleche_envoyer.svg" alt="" />
            </button>
          </form>
          <p className="chat-disclaimer">
            Réponses informatives et sourcées — elles ne remplacent pas l'avis d'un professionnel de santé.<br />
            · Projet étudiant ·
          </p>
        </div>
      </div>
    </div>
  );
}