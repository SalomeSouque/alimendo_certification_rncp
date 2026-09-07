# Alimendo — Fondation d'auth front + gating des features IA

Guide d'intégration des fichiers livrés. Objectif : brancher tout ça **sans réécrire tes pages**.
Tout marche **dès maintenant en mode mock** (aucun backend requis), et sera branchable sur FastAPI + JWT plus tard **sans retoucher les pages**.

---

## 1. Où poser les fichiers

Tous sous `frontend/` :

```
frontend/
├─ .env.example                        # -> copie en .env
└─ src/
   ├─ config/
   │  └─ features.js                   # LA liste des features protégées (le "mur")
   ├─ services/
   │  ├─ token.js                      # stockage du token (localStorage)
   │  ├─ api.js                        # wrapper fetch (attache le JWT)
   │  └─ auth.js                       # login / logout / fetchCurrentUser (mock-first)
   ├─ context/
   │  └─ AuthContext.jsx               # état d'auth global + hook useAuth
   └─ components/
      ├─ AuthGate.jsx                  # garde à mettre "par-dessus" une route
      └─ LoginRequired.jsx             # carte "connexion requise"
```

Puis :

```bash
cp frontend/.env.example frontend/.env   # VITE_AUTH_MOCK=true par défaut
```

---

## 2. Les 3 branchements à faire (les seules modifs dans ton code existant)

### 2.1 — Envelopper l'app dans `<AuthProvider>` (`main.jsx`)

Le provider doit englober toute l'app pour que `useAuth()` soit dispo partout.
Il se place **à l'intérieur** du `<BrowserRouter>` (les composants d'auth utilisent le routing).

```jsx
// src/main.jsx
import { AuthProvider } from './context/AuthContext';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
```

> Si ton `<BrowserRouter>` est déjà dans `App.jsx` et pas dans `main.jsx`, mets simplement
> `<AuthProvider>` juste à l'intérieur de `<BrowserRouter>`, où qu'il soit.

### 2.2 — Gater les 2 routes IA (`App.jsx`, là où sont tes `<Route>`)

On enveloppe l'élément de la route. **Rien à changer dans les composants de page.**

```jsx
import AuthGate from './components/AuthGate';

// Feature IA #1 — reconnaissance photo (VLM)
<Route
  path="/aliment-frais"
  element={
    <AuthGate feature="aliment-frais">
      <AlimentFrais />
    </AuthGate>
  }
/>

// Feature IA #2 — chatbot RAG
<Route
  path="/chatbot"
  element={
    <AuthGate feature="chatbot">
      <Chatbot />
    </AuthGate>
  }
/>
```

Les autres routes (`/produit-emballe`, recherche par nom, `/aliment`, `/`, `/en-savoir-plus`) **restent inchangées** : elles sont publiques.

> **Cas `Chatbot` (plein écran, hors `Layout`)** : le gating fonctionne pareil. Quand l'utilisateur
> n'est pas connecté, `AuthGate` rend la carte `LoginRequired` centrée à la place de la page.
> Elle s'affiche correctement dans les deux contextes (dans `Layout` pour `aliment-frais`, en plein
> écran pour `chatbot`).

### 2.3 — Brancher le bouton de la page `/connexion` (`Authentification`)

Ta carte est déjà maquettée (champs + toggle œil). Il ne reste qu'à câbler le submit sur `useAuth().login`.

```jsx
import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function Authentification() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(identifier, password);
      // Retour vers la page d'origine (posée par LoginRequired), sinon accueil.
      const from = location.state?.from ?? '/';
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  // À câbler sur ta maquette existante :
  //  <form onSubmit={handleSubmit}>
  //    <input value={identifier} onChange={(e) => setIdentifier(e.target.value)} ... />
  //    <input type={showPassword ? 'text' : 'password'}
  //           value={password} onChange={(e) => setPassword(e.target.value)} ... />
  //    {error && <p role="alert" style={{ color: 'crimson' }}>{error}</p>}
  //    <button type="submit" disabled={submitting}>
  //      {submitting ? 'Connexion…' : 'Se connecter'}
  //    </button>
  //  </form>
}
```

**En mode mock, n'importe quel couple identifiant + mot de passe non vide connecte.** C'est voulu : tu testes tout le parcours (login → accès aux features IA → logout) sans backend.

### (optionnel) Bouton de déconnexion dans le header

```jsx
import { useAuth } from '../context/AuthContext';

const { isAuthenticated, user, logout } = useAuth();

{isAuthenticated
  ? <button onClick={logout}>Se déconnecter ({user.email})</button>
  : <Link to="/connexion">Se connecter</Link>}
```

---

## 3. Passer du mock au vrai backend (plus tard, en 1 changement)

Quand FastAPI exposera l'auth :

1. Dans `.env` : `VITE_AUTH_MOCK=false`
2. Vérifie que le backend renvoie bien :
   - `POST /auth/login` → `{ "access_token": "...", "user": { "id", "email", "role" } }`
   - `GET /auth/me` (route protégée) → `{ "id", "email", "role" }`

**Aucune page à modifier.** Toute la bascule est encapsulée dans `auth.js`. C'est exactement pour ça qu'on est passé par un service : les composants ne connaissent que `useAuth()`, pas la façon dont l'auth est réellement faite.

---

## 4. Question infra — Docker Compose : backend minimal maintenant, ou full-front mocké ?

**Contexte** : ton `docker-compose` a des services vides ; le backend n'est pas encore démarrable ; tu veux savoir s'il faut monter un service backend minimal juste pour tester l'auth.

**Recommandation : reste full-front mocké pour l'instant.** Le mock couvre 100 % du parcours d'auth côté front (état connecté/déconnecté, gating, redirection, logout). Monter un FastAPI à moitié fait uniquement pour un `/auth/login` te ferait dépenser du temps (Dockerfile, PostgreSQL, migrations, hash bcrypt, JWT) sur une brique qui n'est pas encore ta priorité de semaine. En contexte solo / 7 semaines, le mock te débloque **aujourd'hui** et le vrai backend se branchera proprement le moment venu (section 3).

**Quand basculer** : le jour où tu attaques la vraie feature auth backend (création de la table `utilisateur`/`role`, hash bcrypt, endpoint JWT). À ce moment-là, tu ajouteras un service `api` au compose. Squelette pour plus tard (à ne PAS ajouter maintenant) :

```yaml
# docker-compose.yml — à ajouter QUAND le backend existera
services:
  api:
    build: ./backend
    env_file: ./backend/.env
    ports:
      - "8000:8000"
    depends_on:
      - db
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: alimendo
      POSTGRES_USER: alimendo
      POSTGRES_PASSWORD: change_me   # -> via .env, jamais en dur
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

> Le reverse proxy reste géré par ton proche spécialiste — on n'y touche pas.

---

## 5. Note de cours (pour toi)

**React Context — pourquoi ?** "Est-ce que l'utilisateur est connecté ?" est une info dont ont besoin plein d'endroits sans lien de parent à enfant direct (le header, les pages IA, la page connexion). Sans contexte, tu devrais passer cette info de composant en composant (`props drilling`) ou la dupliquer par page → risque d'incohérence. Le Context crée **une seule source de vérité** lue via `useAuth()`. À retenir : Context = état partagé transverse, mis à jour à un seul endroit (le `AuthProvider`).

**Pourquoi un service `auth.js` séparé du contexte ?** Le contexte gère l'état *React* (re-render quand on se connecte). Le service gère le *comment* (mock ou fetch). En les séparant, tu peux changer le "comment" (mock → FastAPI) sans toucher au "quand re-render". C'est le principe d'**inversion de dépendance** : les pages dépendent d'une abstraction stable (`useAuth`), pas des détails (fetch, localStorage).

**Gating par route vs par bouton.** Ici on gate **la route entière** (`AuthGate` autour de l'élément) : simple, zéro modif dans les pages, cohérent avec la maquette "cette fonctionnalité demande un compte". L'alternative serait de gater *au clic* sur le bouton d'analyse (laisser voir la page, bloquer l'action). C'est possible plus tard avec le même `useAuth()` — mais plus intrusif dans les pages. Pour 7 semaines, le route-level est le bon compromis.

**Le token dans localStorage — le sais-tu ?** C'est simple et ça marche pour un POC, mais c'est lisible par du JavaScript → **vulnérable au XSS**. L'alternative plus sûre (cookie `httpOnly` posé par le backend) est plus lourde à mettre en place. Choix conscient pour un projet étudiant, à **noter comme dette technique** et à mentionner à l'oral (montrer qu'on connaît le trade-off = point positif).

---

## 6. Points à aligner (repérés au passage, non bloquants)

- **`identifiant` vs `email`** : ta maquette `/connexion` parle d'"identifiant", mais le MPD authentifie sur `email` (`utilisateur.email`). Le code envoie l'identifiant saisi comme `email`. Décide : soit le label devient "Email", soit tu autorises un pseudo en plus de l'email côté backend. Le plus simple = label "Email".
- **Registre de la copie (`tu` vs `vous`, écriture inclusive `·e`)** : la carte `LoginRequired` utilise "tu / connecté·e". Aligne-le sur le reste du site (choisis un registre et tiens-le partout).
- **Rôle non utilisé** : le MPD a une table `role`, mais rien ne s'appuie encore dessus pour autoriser/interdire (tout est binaire connecté/déconnecté). C'est ok pour maintenant ; à garder en tête si tu ajoutes un back-office.
- **Pas d'expiration / refresh token** géré côté front pour l'instant. En mode réel, un token expiré est nettoyé au prochain `GET /auth/me` qui échoue (l'utilisateur est redéconnecté). Suffisant pour un POC.

---

## 7. Textes de la carte (FR / EN) — pour référence

**FR** (dans le composant) :
> **Connexion requise** — Pour utiliser {la feature}, il faut être connecté·e à un compte. C'est rapide, et ça permet de retrouver ses analyses. · *Se connecter* · *Retour à l'accueil*

**EN** (si i18n plus tard) :
> **Sign-in required** — To use {the feature}, you need to be signed in. It's quick, and it lets you keep track of your analyses. · *Sign in* · *Back to home*

---

## 8. À reporter dans `progress.md`

```
## Session 2026-08-21 — Fondation auth front + gating features IA
- Ce qui a été fait :
  - Fondation d'auth côté front, mockée et branchable FastAPI+JWT sans réécrire les pages.
  - services/token.js, services/api.js, services/auth.js (mock-first).
  - context/AuthContext.jsx (état global + hook useAuth).
  - Gating "par-dessus" : config/features.js + AuthGate.jsx + LoginRequired.jsx.
  - .env.example (VITE_AUTH_MOCK, VITE_API_URL).
- Décisions prises :
  - Mur de connexion sur les 2 features IA uniquement : aliment-frais (VLM) + chatbot (RAG).
    Scan code-barre et recherche par nom restent publics.
  - Gating au niveau ROUTE (pas au clic) : plus simple, zéro modif dans les pages.
  - Rester full-front MOCKÉ pour l'auth ; pas de service backend dans docker-compose pour l'instant.
  - Token en localStorage (choix POC assumé).
- Prochaine étape :
  - Câbler main.jsx (AuthProvider), les 2 routes IA (AuthGate), et le submit de /connexion.
  - Aligner label "identifiant" -> "Email" sur la maquette.
- Points bloquants : aucun (mock autonome).
- Dette technique identifiée :
  - Token localStorage = surface XSS (alternative : cookie httpOnly). À revoir si le temps le permet.
  - Pas d'expiration / refresh token côté front.
  - Table role non exploitée pour l'autorisation (auth binaire pour l'instant).
  - identifiant vs email à trancher côté maquette + backend.
```
