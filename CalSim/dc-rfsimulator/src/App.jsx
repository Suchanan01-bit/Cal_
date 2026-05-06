/**
 * Main Application Component
 */

import { useState } from 'react';
import { SimulatorProvider } from './context/SimulatorContext';
import { TaskProvider } from './context/TaskContext';
import LandingPage from './pages/LandingPage';
import SimulatorPage from './pages/SimulatorPage';
import TestsPage from './pages/TestsPage';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('landing');

  return (
    <SimulatorProvider>
      <TaskProvider>
        {currentPage === 'landing' && (
        <LandingPage
          onNavigate={() => setCurrentPage('simulator')}
          onNavigateTests={() => setCurrentPage('tests')}
        />
      )}
      {currentPage === 'simulator' && (
        <SimulatorPage onNavigate={() => setCurrentPage('landing')} />
      )}
      {currentPage === 'tests' && (
        <TestsPage onNavigate={() => setCurrentPage('landing')} />
      )}
      </TaskProvider>
    </SimulatorProvider>
  );
}

export default App;
