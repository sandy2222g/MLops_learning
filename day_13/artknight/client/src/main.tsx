// SECTION: IMPORTS
// Description: Imports core React engine, mounting utilities, root stylesheet, and target layout component.

import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';


// SECTION: ROOT MOUNTING INTERACTION
// Description: Targets the HTML anchor container with ID 'root' and mounts the React virtual DOM tree inside it.

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
