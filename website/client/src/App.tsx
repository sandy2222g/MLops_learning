import { useState } from 'react';
import { Info } from 'lucide-react';
import { Header } from './components/Header';
import { Dashboard } from './components/Dashboard';
import { UploadSection } from './components/UploadSection';

interface Feature {
  name: string;
  value: number;
}

interface AnalysisData {
  prediction: string;
  features: Feature[];
}

export default function App() {
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);

  const handleResult = (res: AnalysisData | null) => {
    console.log("Setting analysis data:", res);
    setAnalysisData(res);
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 transition-colors duration-300">
      <Header />
      
      <main className="container mx-auto px-4 py-8 max-w-6xl">
        <header className="mb-8">
          <h1 className="text-3xl font-bold dark:text-white text-zinc-900 tracking-tight">Artwork Analysis</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">
            Analyze artwork complexity by extracting visual features in real-time.
          </p>
          
          <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl flex items-start gap-3">
            <Info className="w-5 h-5 text-amber-600 dark:text-amber-500 shrink-0 mt-0.5" />
            <p className="text-xs leading-relaxed text-amber-800 dark:text-amber-400">
              <span className="font-bold uppercase">Disclaimer:</span> This system uses a text-based machine learning model trained on numerical image features. Results are based on statistical extraction and may not be fully accurate or expected for all artwork types.
            </p>
          </div>
        </header>

        <div className="space-y-12">
          <UploadSection onResult={handleResult} />
          <Dashboard data={analysisData} />
        </div>

        <footer className="mt-16 pt-8 border-t dark:border-zinc-800 border-zinc-200 text-center">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            &copy; {new Date().getFullYear()} MLOps Lab. Built with Flask, OpenCV, and React.
          </p>
        </footer>
      </main>
    </div>
  );
}
