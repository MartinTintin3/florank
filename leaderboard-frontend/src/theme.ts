import { createTheme } from '@mantine/core';

const theme = createTheme({
  fontFamily: 'Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  headings: {
    fontWeight: '600',
    fontFamily: 'Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  },
  defaultRadius: 'md',
  primaryColor: 'blue',
  colors: {
    blue: [
      '#e6f0ff',
      '#c5d6ff',
      '#9fbbff',
      '#789fff',
      '#5284ff',
      '#386ae6',
      '#2b53b4',
      '#1d3c82',
      '#0f2551',
      '#030f23',
    ],
  },
});

export default theme;
