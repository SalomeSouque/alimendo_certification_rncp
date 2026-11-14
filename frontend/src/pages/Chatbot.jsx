import { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header.jsx';
import AccessPending from '../components/AccessPending.jsx';
import {
  askChatbot,
  ACTION_REDIRECT_SCAN,
  QUESTION_MAX_LENGTH,
  QUESTION_MIN_LENGTH,
} from '../services/chat';
import { CHATBOT_LONG_DISCLAIMER, CHATBOT_PRIVACY_NOTICE } from '../content/chatbotTexts';
import './Chatbot.css';

/** Splits an answer into paragraphs on blank lines. */
function toParagraphs(text) {
  return String(text ?? '')
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

let nextId = 0;
const newId = () => `m${nextId++}`;

/**
 * Chatbot page: questions go to POST /ai/chat. The API decides the answer,
 * its sources and its disclaimer; this page only displays them.
 */
export default function Chatbot() {
  // Message: { id, role: 'user'|'bot'|'error', text, sources?, disclaimer?, action?, question? }
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const [inputError, setInputError] = useState(null);
  const [accessPending, setAccessPending] = useState(false);
  const threadEnd = useRef(null);
  const inputRef = useRef(null);
  const noticeId = useId();
  const inputErrorId = useId();

  useEffect(() => {
    threadEnd.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' });
  }, [messages, pending]);

  async function ask(question) {
    setPending(true);
    try {
      const answer = await askChatbot(question);
      setMessages((prev) => [
        ...prev,
        {
          id: newId(),
          role: 'bot',
          text: answer.reponse,
          sources: answer.sources,
          disclaimer: answer.disclaimer,
          action: answer.action,
        },
      ]);
    } catch (err) {
      // 401 is handled by api.js / AuthProvider (redirect to /connexion).
      if (err?.status === 401) return;
      // 403: AI access not approved yet (or revoked) by an admin.
      if (err?.status === 403) {
        setAccessPending(true);
        return;
      }
      const text =
        err?.status === 422
          ? `Votre question doit contenir entre ${QUESTION_MIN_LENGTH} et ${QUESTION_MAX_LENGTH} caractères.`
          : err?.message ?? 'Une erreur est survenue. Réessayez.';
      setMessages((prev) => [...prev, { id: newId(), role: 'error', text, question }]);
    } finally {
      setPending(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (pending) return;
    const question = input.trim();
    if (question.length < QUESTION_MIN_LENGTH) {
      setInputError(`Votre question doit contenir au moins ${QUESTION_MIN_LENGTH} caractères.`);
      inputRef.current?.focus();
      return;
    }
    setInputError(null);
    setMessages((prev) => [...prev, { id: newId(), role: 'user', text: question }]);
    setInput('');
    ask(question);
  }

  function retry(message) {
    // Remove the error bubble, then ask the same question again.
    setMessages((prev) => prev.filter((m) => m.id !== message.id));
    ask(message.question);
  }

  if (accessPending) {
    return (
      <div className="chatbot-page">
        <Header />
        <main className="auth-main">
          <h1 className="sr-only">Chatbot documentaire</h1>
          <AccessPending />
        </main>
      </div>
    );
  }

  return (
    <div className="chatbot-page">
      <Header />

      <main className="chat-app">
        <h1 className="sr-only">Chatbot documentaire</h1>

        {/* §7.7: permanent banner, also shown on first opening. */}
        <section className="chat-banner" aria-label="À propos de cet assistant">
          <p className="chat-banner-title">{CHATBOT_LONG_DISCLAIMER.title}</p>
          {CHATBOT_LONG_DISCLAIMER.lines.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </section>

        <div className="chat-thread" role="log" aria-live="polite" aria-relevant="additions">
          {messages.map((msg) => {
            if (msg.role === 'user') {
              return (
                <div className="msg-user" key={msg.id}>
                  <span className="sr-only">Vous : </span>
                  {msg.text}
                </div>
              );
            }
            if (msg.role === 'error') {
              return (
                <div className="msg-error" key={msg.id} role="alert">
                  <p>{msg.text}</p>
                  <button type="button" className="btn-secondary msg-retry" onClick={() => retry(msg)}>
                    Réessayer
                  </button>
                </div>
              );
            }
            return (
              <article className="msg-bot" key={msg.id} aria-label="Réponse de l’assistant">
                {toParagraphs(msg.text).map((p, j) => (
                  <p key={j} className="msg-paragraph">{p}</p>
                ))}

                {msg.action === ACTION_REDIRECT_SCAN && (
                  <Link to="/analyser" className="btn-secondary msg-action">
                    Analyser un aliment
                  </Link>
                )}

                {msg.sources?.length > 0 && (
                  <div className="msg-sources">
                    <p className="msg-sources-title">Sources</p>
                    <ul>
                      {msg.sources.map((s) => (
                        <li key={s.id_source}>
                          {s.url ? (
                            <a href={s.url} target="_blank" rel="noopener noreferrer">
                              {s.titre}
                              <span className="sr-only"> (s’ouvre dans un nouvel onglet)</span>
                            </a>
                          ) : (
                            s.titre
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {msg.disclaimer && <p className="msg-disclaimer">{msg.disclaimer}</p>}
              </article>
            );
          })}

          {pending && (
            <div className="msg-bot msg-typing" role="status">
              <span className="typing-dots" aria-hidden="true">…</span>
              <span className="msg-typing-label">Recherche dans la documentation…</span>
            </div>
          )}
          <div ref={threadEnd} />
        </div>

        <div className="chat-input-zone">
          <form className="chat-input" onSubmit={handleSubmit} noValidate>
            <input
              ref={inputRef}
              type="text"
              placeholder="Poser une question…"
              aria-label="Poser une question"
              aria-describedby={[noticeId, inputError ? inputErrorId : null].filter(Boolean).join(' ')}
              aria-invalid={Boolean(inputError)}
              maxLength={QUESTION_MAX_LENGTH}
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button className="chat-send" aria-label="Envoyer" type="submit" disabled={pending}>
              <img src="/assets/fleche_envoyer.svg" alt="" aria-hidden="true" />
            </button>
          </form>
          {inputError && (
            <p id={inputErrorId} className="chat-input-error">{inputError}</p>
          )}
          <p id={noticeId} className="chat-privacy">{CHATBOT_PRIVACY_NOTICE}</p>
        </div>
      </main>
    </div>
  );
}