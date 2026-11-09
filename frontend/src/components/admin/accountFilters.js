// src/components/admin/accountFilters.js
// Pure helpers of the admin list: filter definitions, counts and search.
// Kept out of the components so they can be unit tested on their own.

/** Filters of the segmented control, in display order. */
export const ACCOUNT_FILTERS = [
  { key: 'pending', label: 'À valider', match: (account) => !account.acces_ia },
  { key: 'open', label: 'Accès ouvert', match: (account) => account.acces_ia },
  { key: 'all', label: 'Tous', match: () => true },
];

/**
 * @param {import('../../services/admin').AdminAccount[]} accounts
 * @returns {Record<string, number>} number of accounts per filter key.
 */
export function countByFilter(accounts) {
  return Object.fromEntries(
    ACCOUNT_FILTERS.map((f) => [f.key, accounts.filter(f.match).length]),
  );
}

/**
 * Keeps the accounts matching the filter and whose email contains the search term
 * (case-insensitive). The backend order (most recent first) is preserved.
 * @param {import('../../services/admin').AdminAccount[]} accounts
 * @param {string} filterKey - one of ACCOUNT_FILTERS keys.
 * @param {string} term - free text, may be empty.
 */
export function filterAccounts(accounts, filterKey, term) {
  const filter = ACCOUNT_FILTERS.find((f) => f.key === filterKey) ?? ACCOUNT_FILTERS[2];
  const needle = term.trim().toLowerCase();
  return accounts.filter(
    (account) => filter.match(account) && account.email.toLowerCase().includes(needle),
  );
}
