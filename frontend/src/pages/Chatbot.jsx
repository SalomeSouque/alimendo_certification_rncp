import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header.jsx';
import './Chatbot.css';

// Conversation de démo au chargement (remplacée par un état vide quand le RAG sera branché)
const messagesInitiaux = [
  {
    role: 'bot',
    paragraphes: [
      "Bonjour,",
      "Je suis un assistant documentaire : je réponds à des questions générales sur l'endométriose et sur ce que la recherche dit de l'alimentation, en citant mes sources.",
      "En revanche, je ne pose aucun diagnostic et je ne remplace pas un professionnel de santé.",
      "Pour le score d'un aliment précis, utilisez le scan ou la recherche",
    ],
  },
];

export default function Chatbot() {
  const [messages, setMessages] = useState(messagesInitiaux);
  const [saisie, setSaisie] = useState('');
  const [enAttente, setEnAttente] = useState(false);
  const finDuFil = useRef(null);
  const { isAuthenticated, logout } = useAuth();

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
      <Header />

      <div className="chat-app">
        <div className="chat-thread">
          {messages.map((msg, i) =>
            msg.role === 'bot' ? (
              <div className="msg-bot" key={i}>{
                msg.paragraphes.map((p, i) => (
                <p key={i} Style="margin-top: 10px">{p}</p>
              ))}</div>
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
            Réponses informatives et sourcées, elles ne remplacent pas l'avis d'un professionnel de santé.<br />
            Projet étudiant
          </p>
        </div>
      </div>
    </div>
  );
}