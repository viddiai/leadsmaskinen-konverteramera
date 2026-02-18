/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Leadsmaskinen brand colors
        primary: {
          50: '#fff4f0',
          100: '#ffe8df',
          200: '#ffd0bf',
          300: '#ffb89f',
          400: '#ff916e',
          500: '#FF6A3D',  // Leadsmaskinen Orange
          600: '#e55a2f',
          700: '#cc4a21',
          800: '#b33a13',
          900: '#992a05',
        },
        graphite: '#2B2F33',    // Deep Graphite - headings
        steel: '#6E7378',       // Steel Grey - body text
        softwhite: '#FAFAFA',   // Soft White - background
        lightgrey: '#E7E7E7',   // Light Grey - sections, borders
        success: '#2ECC71',     // Success Green
        warning: '#F4D03F',     // Warning Yellow
        info: '#3498DB',        // Info Blue
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        display: ['Poppins', 'system-ui', '-apple-system', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'fade-slide-in': 'fadeSlideIn 0.8s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeSlideIn: {
          '0%': { opacity: '0', transform: 'translateY(20px)', filter: 'blur(5px)' },
          '100%': { opacity: '1', transform: 'translateY(0)', filter: 'blur(0)' },
        },
      },
    },
  },
  plugins: [],
}
