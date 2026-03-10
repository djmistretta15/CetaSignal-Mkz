/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Space Mono', 'monospace'],
        body: ['DM Sans', 'sans-serif'],
      },
      colors: {
        ocean: {
          950: '#00040D',
          900: '#000D1A',
          800: '#001A33',
          700: '#002647',
          600: '#003366',
          500: '#004D99',
          400: '#0066CC',
          300: '#0099FF',
          200: '#33B5FF',
          100: '#99DDFF',
        },
        signal: {
          contact:   '#00D4FF',
          dive:      '#0066CC',
          forage:    '#00CC88',
          navigate:  '#FF9900',
          broadcast: '#CC44FF',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'sonar': 'sonar 2s ease-out infinite',
        'wave': 'wave 8s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        sonar: {
          '0%': { transform: 'scale(1)', opacity: '0.8' },
          '100%': { transform: 'scale(3)', opacity: '0' }
        },
        wave: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' }
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px) rotate(-2deg)' },
          '50%': { transform: 'translateY(-10px) rotate(2deg)' }
        }
      }
    },
  },
  plugins: [],
}
