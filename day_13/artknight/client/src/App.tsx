// SECTION: IMPORTS
// Description: Imports React hooks, icon assets, and all mode-specific subcomponents.

import { useState } from 'react';
import { Info, Sparkles, ScanSearch, Bot } from 'lucide-react';
import { Header } from './components/Header';
import { Dashboard } from './components/Dashboard';
import { UploadSection } from './components/UploadSection';
import { DamageDetection } from './components/DamageDetection';
import { RagBot } from './components/RagBot';
import { cn } from './lib/utils';


// SECTION: TYPES AND INTERFACES
// Description: Defines structural contracts for JSON payloads and app mode identifiers.

type AppMode = 'restoration' | 'damage' | 'rag';

interface Feature {
  name: string;
  value: number;
}

interface AnalysisData {
  prediction: string;
  features: Feature[];
}


// SECTION: TAB CONFIG
// Description: Declares the three dashboard modes with labels, icons, and accent colours.

const TABS: { id: AppMode; label: string; icon: React.ElementType; color: string; activeColor: string; activeBg: string }[] = [
  {
    id: 'restoration',
    label: 'Restoration Prediction',
    icon: Sparkles,
    color: 'text-indigo-500',
    activeColor: 'text-indigo-600 dark:text-indigo-400',
    activeBg: 'bg-indigo-500/10 border-indigo-500/30',
  },
  {
    id: 'damage',
    label: 'Damage Detection',
    icon: ScanSearch,
    color: 'text-rose-500',
    activeColor: 'text-rose-600 dark:text-rose-400',
    activeBg: 'bg-rose-500/10 border-rose-500/30',
  },
  {
    id: 'rag',
    label: 'RAG Bot',
    icon: Bot,
    color: 'text-violet-500',
    activeColor: 'text-violet-600 dark:text-violet-400',
    activeBg: 'bg-violet-500/10 border-violet-500/30',
  },
];


// SECTION: MAIN APP COMPONENT
// Description: Assembles the app shell, tab switcher, and renders the active mode panel.

export default function App() {
  const [mode, setMode] = useState<AppMode>('restoration');
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);

  const handleResult = (res: AnalysisData | null) => {
    console.log("Setting analysis data:", res);
    setAnalysisData(res);
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 transition-colors duration-300">

      <Header />

      <main className="container mx-auto px-4 py-8 max-w-6xl">

        {/* Page header */}
        <header className="mb-8">
          <h1 className="text-3xl font-bold dark:text-white text-zinc-900 tracking-tight">Artwork Analysis</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">
            Analyze artwork complexity, detect damage, and query the conservation knowledge base.
          </p>

          <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl flex items-start gap-3">
            <Info className="w-5 h-5 text-amber-600 dark:text-amber-500 shrink-0 mt-0.5" />
            <p className="text-xs leading-relaxed text-amber-800 dark:text-amber-400">
              <span className="font-bold uppercase">Disclaimer:</span> This system uses machine learning models trained on numerical image features and conservation documents. Results are based on statistical extraction and may not be fully accurate for all artwork types.
            </p>
          </div>
        </header>

        {/* Tab switcher */}
        <div className="flex flex-col sm:flex-row gap-3 mb-8">
          {TABS.map(tab => {
            const Icon = tab.icon;
            const isActive = mode === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setMode(tab.id)}
                className={cn(
                  "flex items-center gap-3 px-5 py-3.5 rounded-2xl border-2 font-bold text-sm transition-all duration-200 flex-1 justify-center sm:justify-start",
                  isActive
                    ? `${tab.activeBg} ${tab.activeColor} shadow-sm`
                    : "border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700"
                )}
              >
                <Icon className={cn("w-5 h-5 shrink-0", isActive ? tab.activeColor : tab.color)} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Active mode panel */}
        <div className="space-y-12">
          {mode === 'restoration' && (
            <>
              <UploadSection onResult={handleResult} />
              <Dashboard data={analysisData} />
            </>
          )}

          {mode === 'damage' && <DamageDetection />}

          {mode === 'rag' && <RagBot />}
        </div>

        <footer className="mt-16 pt-8 border-t dark:border-zinc-800 border-zinc-200 text-center">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            &copy; {new Date().getFullYear()} MLOps Lab. Built with Flask, OpenCV, YOLO, and React.
          </p>
        </footer>
      </main>
    </div>
  );
}
