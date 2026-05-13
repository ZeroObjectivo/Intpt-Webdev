/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  safelist: [
    'fb-grid-1',
    'fb-grid-2',
    'fb-grid-3',
    'fb-grid-4',
    'fb-grid-5',
  ],
  theme: {
    extend: {
      colors: {
        'umak-blue': 'var(--umak-blue)',
        'umak-yellow': 'var(--umak-yellow)',
        'umak-light-blue': 'var(--umak-blue-light)',
        'umak-bright': 'var(--umak-blue-bright)',
      },
      fontFamily: {
        'sans': ['Metropolis', 'Inter', 'system-ui', 'sans-serif'],
        'heading': ['Marcellus SC', 'Georgia', 'serif'],
        'accent': ['Marcellus SC', 'Georgia', 'serif'],
      },
      borderRadius: {
        'xl': 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
      },
      boxShadow: {
        'soft': 'var(--shadow-soft)',
        'strong': 'var(--shadow-strong)',
      }
    },
  },
  plugins: [],
}
