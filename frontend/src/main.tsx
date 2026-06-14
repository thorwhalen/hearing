// Entry point: mount the React app. (For a frontend novice: this is the one
// place that connects React to the page's <div id="root">.)
import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
