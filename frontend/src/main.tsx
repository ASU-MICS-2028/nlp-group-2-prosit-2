import '@fontsource-variable/inter'
import '@fontsource/jetbrains-mono/400.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { Gallery } from './dev/Gallery'
import './styles/tokens.css'
import './styles/components.css'

// Find the <div id="root"> in index.html. Fail loudly if it is missing.
const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Could not find the #root element in index.html')
}

// The component gallery exists only while developing (it is left out of the production build).
const showGallery =
  import.meta.env.DEV && window.location.pathname === '/dev/gallery'

createRoot(rootElement).render(
  <StrictMode>{showGallery ? <Gallery /> : <App />}</StrictMode>,
)
