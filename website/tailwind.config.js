export default {
  content: ["./index.html","./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          ink:   "#0B132B",  // deep navy
          stone: "#2F3A4A",  // charcoal/blue-gray
          sand:  "#F7F4EE",  // warm off-white
          gold:  "#C5A572",  // soft gold (accessible)
          sky:   "#E8F1F8",  // pale sky for sections/cards
          line:  "#E6E1D9",  // hairline divider
        },
      },
      fontFamily: {
        sans: ["Manrope", "Noto Sans Ethiopic", "Noto Sans", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 8px 24px rgba(11,19,43,0.06)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
    },
  },
  plugins: [],
}
