// src/components/icons.jsx
// Small line icons of the mobile maquettes (24 px grid, colour = currentColor).
// Always decorative: the button or link around them carries the accessible name.

function Icon({ children, size = 24 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export const MenuIcon = (props) => (
  <Icon {...props}><path d="M4 7h16M4 12h16M4 17h16" /></Icon>
);

export const CloseIcon = (props) => (
  <Icon {...props}><path d="M6 6l12 12M18 6L6 18" /></Icon>
);

export const UserIcon = (props) => (
  <Icon {...props}>
    <circle cx="12" cy="8" r="4" fill="currentColor" stroke="none" />
    <path d="M4.5 20c.8-3.6 3.8-5.5 7.5-5.5s6.7 1.9 7.5 5.5z" fill="currentColor" stroke="none" />
  </Icon>
);

export const ImageIcon = (props) => (
  <Icon {...props}>
    <rect x="3.5" y="3.5" width="17" height="17" rx="3" />
    <circle cx="9" cy="9" r="1.6" />
    <path d="M20.5 15.5l-4.5-4.5-9 9" />
  </Icon>
);

export const FlashIcon = (props) => (
  <Icon {...props}><path d="M13 2.5L5 13.5h6l-1 8 8-11h-6z" /></Icon>
);

export const QuestionIcon = (props) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.6 9.3a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.2-2.4 3.6" />
    <circle cx="12" cy="17" r=".6" fill="currentColor" />
  </Icon>
);
