import { createTheme } from '@mui/material/styles';

// BSF-LoopTech Design System — MASTER.md
// Industrial Analytics Dashboard Theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      light: '#3B82F6',
      main: '#1E40AF',
      dark: '#1E3A8A',
      contrastText: '#FFFFFF',
    },
    secondary: {
      light: '#60A5FA',
      main: '#3B82F6',
      dark: '#2563EB',
      contrastText: '#FFFFFF',
    },
    error: {
      light: '#FEE2E2',
      main: '#DC2626',
      dark: '#B91C1C',
      contrastText: '#FFFFFF',
    },
    warning: {
      light: '#FEF3C7',
      main: '#D97706',
      dark: '#B45309',
      contrastText: '#000000',
    },
    info: {
      light: '#E0F2FE',
      main: '#0284C7',
      dark: '#0369A1',
      contrastText: '#FFFFFF',
    },
    success: {
      light: '#DCFCE7',
      main: '#16A34A',
      dark: '#15803D',
      contrastText: '#FFFFFF',
    },
    grey: {
      50: '#F8FAFC',
      100: '#F1F5F9',
      200: '#E2E8F0',
      300: '#CBD5E1',
      400: '#94A3B8',
      500: '#64748B',
      600: '#475569',
      700: '#334155',
      800: '#1E293B',
      900: '#0F172A',
    },
    background: {
      default: '#F8FAFC',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1E293B',
      secondary: '#64748B',
      disabled: '#94A3B8',
    },
    divider: '#E2E8F0',
  },
  typography: {
    fontFamily: "'Fira Sans', sans-serif",
    h1: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '1.5rem',
      fontWeight: 700,
      lineHeight: 1.2,
    },
    h2: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '1.125rem',
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h3: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '1rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h4: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '0.875rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h5: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '0.875rem',
      fontWeight: 500,
      lineHeight: 1.5,
    },
    h6: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '0.75rem',
      fontWeight: 500,
      lineHeight: 1.4,
    },
    subtitle1: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '0.875rem',
      fontWeight: 400,
      lineHeight: 1.5,
    },
    subtitle2: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '0.75rem',
      fontWeight: 500,
      lineHeight: 1.4,
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    },
    body1: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '0.875rem',
      fontWeight: 400,
      lineHeight: 1.5,
    },
    body2: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '0.75rem',
      fontWeight: 400,
      lineHeight: 1.4,
    },
    button: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '0.875rem',
      fontWeight: 600,
      textTransform: 'none',
    },
    caption: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '0.75rem',
      fontWeight: 500,
      lineHeight: 1.4,
    },
    overline: {
      fontFamily: "'Fira Sans', sans-serif",
      fontSize: '0.75rem',
      fontWeight: 500,
      lineHeight: 1.4,
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    },
  },
  shape: {
    borderRadius: 8,
  },
  shadows: [
    'none',
    '0 1px 2px rgba(0,0,0,0.05)',
    '0 2px 4px rgba(0,0,0,0.08)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
    '0 4px 12px rgba(0,0,0,0.1)',
  ],
  transitions: {
    easing: {
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeOut: 'cubic-bezier(0.0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
    },
    duration: {
      shortest: 150,
      shorter: 200,
      short: 200,
      standard: 200,
      complex: 300,
      enteringScreen: 200,
      leavingScreen: 150,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          textTransform: 'none',
          fontWeight: 600,
          fontSize: '0.875rem',
          padding: '8px 20px',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
        containedPrimary: {
          backgroundColor: '#1E40AF',
          '&:hover': {
            backgroundColor: '#1E3A8A',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          border: '1px solid #E2E8F0',
          boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
          '&:hover': {
            boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
        elevation1: {
          boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
        },
        elevation2: {
          boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
        },
        elevation3: {
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 4,
            fontFamily: "'Fira Sans', sans-serif",
            '&:hover fieldset': {
              borderColor: '#1E40AF',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#1E40AF',
              boxShadow: '0 0 0 2px rgba(30, 64, 175, 0.15)',
            },
          },
          '& input[type="number"]': {
            fontFamily: "'Fira Code', monospace",
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          fontFamily: "'Fira Sans', sans-serif",
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          fontFamily: "'Fira Sans', sans-serif",
          fontWeight: 500,
          fontSize: '0.875rem',
          textTransform: 'none',
          minWidth: 'auto',
          padding: '8px 16px',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          backgroundColor: '#F1F5F9',
          fontFamily: "'Fira Sans', sans-serif",
          fontWeight: 600,
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          color: '#64748B',
          borderBottom: '2px solid #E2E8F0',
          padding: '10px 12px',
        },
        body: {
          fontFamily: "'Fira Sans', sans-serif",
          fontSize: '0.875rem',
          padding: '10px 12px',
          borderBottom: '1px solid #E2E8F0',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: '#F8FAFC',
          },
        },
      },
    },
  },
});

export default theme;
