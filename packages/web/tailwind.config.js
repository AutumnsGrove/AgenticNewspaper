/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			fontFamily: {
				sans: ['var(--font-body)', 'system-ui', 'sans-serif'],
				serif: ['var(--font-heading)', 'Georgia', 'serif'],
				mono: ['JetBrains Mono', 'Fira Code', 'monospace']
			},
			colors: {
				// Newspaper-inspired color palette
				paper: {
					50: '#faf9f7',
					100: '#f5f3ef',
					200: '#e8e4dc',
					300: '#d4cec2',
					400: '#b5ab9a',
					500: '#9a8e7a',
					600: '#7d7264',
					700: '#655c51',
					800: '#544d44',
					900: '#48423b'
				},
				ink: {
					50: '#f6f6f6',
					100: '#e7e7e7',
					200: '#d1d1d1',
					300: '#b0b0b0',
					400: '#888888',
					500: '#6d6d6d',
					600: '#5d5d5d',
					700: '#4f4f4f',
					800: '#454545',
					900: '#3d3d3d',
					950: '#1a1a1a'
				}
			},
			typography: {
				DEFAULT: {
					css: {
						maxWidth: 'none',
						color: 'inherit',
						a: {
							color: '#2563eb',
							textDecoration: 'underline',
							'&:hover': {
								color: '#1d4ed8'
							}
						},
						'h1, h2, h3, h4': {
							fontFamily: 'Georgia, serif'
						},
						blockquote: {
							borderLeftColor: '#d4cec2',
							fontStyle: 'italic'
						}
					}
				}
			}
		}
	},
	plugins: [require('@tailwindcss/typography')]
};
