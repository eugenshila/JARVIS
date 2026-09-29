import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import ConfirmGate from './components/ConfirmGate'
import './index.css'

// ConfirmGate sits outside <App> on purpose: an irreversible action waiting on
// a human must be reachable from every view (dashboard, HUD, classic chat),
// not only the one that happened to start it.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfirmGate />
    <App />
  </React.StrictMode>
)
