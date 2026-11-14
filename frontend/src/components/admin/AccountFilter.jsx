// src/components/admin/AccountFilter.jsx
// Segmented control: "À valider", "Accès ouvert", "Tous", each with its count.
// Toggle buttons (aria-pressed) grouped under one accessible name.

import { ACCOUNT_FILTERS } from './accountFilters';

export default function AccountFilter({ value, counts, onChange }) {
  return (
    <div className="account-filter" role="group" aria-label="Filtrer les comptes">
      {ACCOUNT_FILTERS.map((filter) => (
        <button
          key={filter.key}
          type="button"
          className="account-filter-btn"
          aria-pressed={value === filter.key}
          onClick={() => onChange(filter.key)}
        >
          {filter.label}
          <span className="account-filter-count">{counts[filter.key] ?? 0}</span>
        </button>
      ))}
    </div>
  );
}
