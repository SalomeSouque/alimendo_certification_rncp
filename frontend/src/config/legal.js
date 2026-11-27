// Values shown on the "Mentions légales" and "Confidentialité" pages.
// TO COMPLETE before opening the site: fields marked TODO_COMPLETE are displayed
// as "à compléter" on the pages until they are filled in.

export const TODO_COMPLETE = null;

export const LEGAL = {
  editorName: 'Salomé Souque',
  /** Dedicated contact address of the project (not a personal address). */
  contactEmail: TODO_COMPLETE,
  /** Company renting the server (name, postal address, phone): required by the LCEN. */
  host: {
    name: TODO_COMPLETE,
    address: TODO_COMPLETE,
    phone: TODO_COMPLETE,
  },
  /** Retention of the database backups (deploy/backup_db.sh, KEEP_DAYS). */
  backupDays: 7,
  /** Retention of the server logs (IP addresses): to confirm with the server administrator. */
  serverLogsRetention: TODO_COMPLETE,
  updatedOn: '27 novembre 2026',
};
