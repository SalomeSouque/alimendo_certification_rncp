// src/components/ErrorBoundary.jsx
// Catches rendering errors so a bug shows a message instead of a blank page.
// React only supports this with a class component (no hook equivalent).

import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // Visible in the browser console for diagnosis (C21). No personal data here.
    console.error('Rendering error caught by ErrorBoundary:', error, info?.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <main className="error-boundary" role="alert">
        <h1>Une erreur est survenue</h1>
        <p>Cette page n’a pas pu s’afficher. Rechargez-la, ou revenez à l’accueil.</p>
        <div className="error-boundary-actions">
          <button type="button" className="btn-primary" onClick={() => window.location.reload()}>
            Recharger la page
          </button>
          {/* Plain link: the router may be the part that failed. */}
          <a href="/" className="btn-secondary">Retour à l’accueil</a>
        </div>
      </main>
    );
  }
}
