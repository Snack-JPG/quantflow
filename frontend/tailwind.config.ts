import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0a',
        foreground: '#fafafa',
        card: '#141414',
        'card-foreground': '#fafafa',
        primary: '#22c55e',
        'primary-foreground': '#052e16',
        secondary: '#1f2937',
        'secondary-foreground': '#f3f4f6',
        muted: '#1f2937',
        'muted-foreground': '#9ca3af',
        accent: '#3b82f6',
        'accent-foreground': '#fafafa',
        destructive: '#ef4444',
        'destructive-foreground': '#fafafa',
        border: '#262626',
        input: '#262626',
        ring: '#3b82f6',
        buy: '#22c55e',
        sell: '#ef4444',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
export default config