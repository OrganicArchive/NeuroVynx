/**
 * NeuroVynx React Entry Point
 * ============================
 * 
 * Orchestrates the bootstrapping of the EEG Analysis Platform frontend.
 * 
 * Architecture:
 * - Managed State: Context/Redux for session metadata and file states.
 * - Reactive Viewers: Decoupled canvas-first rendering components.
 * - API Integration: Direct stream-based binding to the FastAPI DSP worker.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './app/App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
