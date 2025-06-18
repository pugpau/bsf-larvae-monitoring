import React from 'react';
import ReactDOM from 'react-dom/client';
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import 'bootstrap/dist/css/bootstrap.min.css';
import App from './App.js';
import './index.css';
import './styles/responsive-utilities.css';
import './styles/responsive-16-10.css';

const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3', // Material Blue
    },
    secondary: {
      main: '#f50057', // Material Pink
    },
  },
  typography: {
    fontFamily: 'Roboto, Arial, sans-serif',
  },
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 960,
      lg: 1280,
      xl: 1920,
    },
  },
  spacing: 8,
  components: {
    MuiContainer: {
      styleOverrides: {
        root: {
          '@media (min-aspect-ratio: 16/10)': {
            paddingLeft: 24,
            paddingRight: 24,
          },
        },
        maxWidthMd: {
          '@media (min-aspect-ratio: 16/10) and (min-width: 1400px)': {
            maxWidth: '100%',
          },
        },
        maxWidthLg: {
          '@media (min-aspect-ratio: 16/10)': {
            maxWidth: 1400,
          },
        },
        maxWidthXl: {
          '@media (min-aspect-ratio: 16/10)': {
            maxWidth: 1920,
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          '@media (min-aspect-ratio: 16/10)': {
            marginBottom: 24,
          },
        },
      },
    },
    MuiCardContent: {
      styleOverrides: {
        root: {
          '@media (min-aspect-ratio: 16/10)': {
            padding: 24,
            '&:last-child': {
              paddingBottom: 24,
            },
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          '@media (min-aspect-ratio: 16/10)': {
            padding: '16px 24px',
            whiteSpace: 'normal',
            wordBreak: 'break-word',
          },
        },
      },
    },
  },
});

const root = ReactDOM.createRoot(
  document.getElementById('root')
);

root.render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>
);