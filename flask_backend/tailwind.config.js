/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
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
