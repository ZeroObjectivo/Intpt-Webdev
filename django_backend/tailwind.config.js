/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
      "./templates/**/*.html",
      "./apps/**/templates/**/*.html",
      "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        'umak-blue': '#001035',
        'umak-yellow': '#FFD700',
        'umak-light-blue': '#1E293B',
      }
    },
  },
  plugins: [],
}
