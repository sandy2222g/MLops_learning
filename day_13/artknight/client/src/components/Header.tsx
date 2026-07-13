// SECTION: IMPORTS
// Description: Imports lucide icons and core hooks for viewport scroll management and theme controls.

import { Sun, Moon, Menu, X, Cpu } from 'lucide-react';
import { useState, useEffect } from 'react';


// SECTION: HEADER COMPONENT
// Description: Implements top navigation bar, manages state transitions for dark mode toggle and mobile responsive slide menu.

export function Header() {
  const [isDark, setIsDark] = useState(true);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  const scrollTo = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
    setIsMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white/80 backdrop-blur dark:bg-zinc-950/80 dark:border-zinc-800 border-zinc-200">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          <div className="bg-indigo-600 p-2 rounded-lg">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-xl tracking-tight dark:text-white text-zinc-900">
            MLOps<span className="text-indigo-600 font-mono">Lab</span>
          </span>
        </div>

        <nav className="hidden md:flex items-center gap-6">
          <button onClick={() => scrollTo('analyze-section')} className="text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Overview</button>
          <button onClick={() => scrollTo('analyze-section')} className="text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Analyze</button>
          <button onClick={() => scrollTo('features-section')} className="text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Extracted Metrics</button>
        </nav>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsDark(!isDark)}
            className="p-2 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun className="w-5 h-5 text-yellow-400" /> : <Moon className="w-5 h-5 text-zinc-600" />}
          </button>
          
          <button
            className="md:hidden p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            {isMenuOpen ? <X className="w-6 h-6 dark:text-white text-zinc-900" /> : <Menu className="w-6 h-6 dark:text-white text-zinc-900" />}
          </button>
        </div>
      </div>

      {isMenuOpen && (
        <div className="md:hidden bg-white dark:bg-zinc-950 border-b dark:border-zinc-800 border-zinc-200 p-4 space-y-4 animate-in slide-in-from-top duration-200">
          <button onClick={() => scrollTo('analyze-section')} className="block w-full text-left text-base font-medium text-zinc-600 dark:text-zinc-400 py-2">Overview</button>
          <button onClick={() => scrollTo('analyze-section')} className="block w-full text-left text-base font-medium text-zinc-600 dark:text-zinc-400 py-2">Analyze</button>
          <button onClick={() => scrollTo('features-section')} className="block w-full text-left text-base font-medium text-zinc-600 dark:text-zinc-400 py-2">Extracted Metrics</button>
        </div>
      )}
    </header>
  );
}
