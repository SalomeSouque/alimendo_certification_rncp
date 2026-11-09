import { adminAccounts } from '../../test/fixtures';
import { countByFilter, filterAccounts } from './accountFilters';

describe('accountFilters', () => {
  it('counts the accounts per filter', () => {
    expect(countByFilter(adminAccounts())).toEqual({ pending: 2, open: 2, all: 4 });
  });

  it('keeps the backend order and filters on the AI access', () => {
    const emails = (list) => list.map((a) => a.email);
    expect(emails(filterAccounts(adminAccounts(), 'pending', ''))).toEqual([
      'camille.martin@exemple.fr',
      'jury.simplon@exemple.fr',
    ]);
    expect(emails(filterAccounts(adminAccounts(), 'open', ''))).toEqual([
      'sophie.l@exemple.fr',
      'admin@alimendo.fr',
    ]);
  });

  it('searches the email, case-insensitive and trimmed', () => {
    const result = filterAccounts(adminAccounts(), 'all', '  JURY ');
    expect(result.map((a) => a.id)).toEqual([11]);
  });

  it('unknown filter key: falls back to all accounts', () => {
    expect(filterAccounts(adminAccounts(), 'unknown', '')).toHaveLength(4);
  });
});
