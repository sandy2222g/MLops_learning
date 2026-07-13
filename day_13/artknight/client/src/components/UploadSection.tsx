// SECTION: IMPORTS
// Description: Imports file-handling icons, React hooks, and layout styling wrappers.

import { UploadCloud, CheckCircle2, FileImage, Loader2, AlertCircle } from 'lucide-react';
import { useState, useRef } from 'react';
import { cn } from '../lib/utils';


// SECTION: TYPES AND PROPS
// Description: Formulates expected parameter types representing analysis values returned from server interactions.

interface Feature {
  name: string;
  value: number;
}

interface PredictionResult {
  prediction: string;
  features: Feature[];
  status: string;
}

interface UploadSectionProps {
  onResult: (res: { prediction: string; features: Feature[] } | null) => void;
}


// SECTION: UPLOAD MANAGEMENT COMPONENT
// Description: Orchestrates drag-drop listeners, builds preview URLs, uploads file to backend Flask API and captures response.

export function UploadSection({ onResult }: UploadSectionProps) {
  const [dragActive, setDragActive] = useState(false);
  const [status, setStatus] = useState<'idle' | 'processing' | 'analyzed' | 'error'>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileDetails, setFileDetails] = useState<{ name: string; size: string; type: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setFileDetails({
        name: file.name,
        size: (file.size / (1024 * 1024)).toFixed(2) + " MB",
        type: file.type.split('/')[1].toUpperCase()
      });
      setStatus('idle');
      onResult(null);
    }
  };

  const analyzeImage = async () => {
    if (!selectedFile) return;

    setStatus('processing');
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      console.log("Sending analysis request...");
      const response = await fetch('/api/predict_restoration', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Backend error');

      const data: PredictionResult = await response.json();
      console.log("Analysis response data:", data);
      setStatus('analyzed');
      
      if (data.prediction && data.features) {
        console.log("Calling onResult with valid data");
        onResult({ prediction: data.prediction, features: data.features });
      } else {
        console.error("Incomplete data from backend:", data);
        setStatus('error');
      }
    } catch (error) {
      console.error("Analysis failed:", error);
      setStatus('error');
    }
  };

  return (
    <section id="analyze-section" className="mb-10 flex flex-col gap-4 scroll-mt-24">
      <div className="flex items-center gap-3 border-b dark:border-zinc-800 border-zinc-200 pb-2">
        <h2 className="text-xl font-bold dark:text-white text-zinc-900 flex items-center gap-2">
          <FileImage className="w-5 h-5 text-indigo-500" />
          Artwork Input
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <div 
          className={cn(
            "lg:col-span-2 relative h-80 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center transition-all duration-300 overflow-hidden group cursor-pointer",
            dragActive ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-500/5" : "dark:border-zinc-800 border-zinc-200 bg-white dark:bg-zinc-900 hover:border-indigo-500/50",
          )}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => { e.preventDefault(); setDragActive(false); e.dataTransfer.files && handleFile(e.dataTransfer.files[0]); }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input 
            type="file" 
            className="hidden" 
            ref={fileInputRef} 
            onChange={(e) => e.target.files && handleFile(e.target.files[0])}
            accept="image/*"
          />

          {!previewUrl ? (
            <>
              <div className="w-16 h-16 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <UploadCloud className="w-8 h-8 text-zinc-400 group-hover:text-indigo-500 transition-colors" />
              </div>
              <p className="text-zinc-600 dark:text-zinc-300 font-medium">Click to upload artwork image</p>
            </>
          ) : (
            <div className="absolute inset-0 w-full h-full">
              <img src={previewUrl} alt="Preview" className="w-full h-full object-contain" />
              {status === 'processing' && (
                <div className="absolute inset-0 bg-white/50 dark:bg-black/50 backdrop-blur-sm flex items-center justify-center">
                  <div className="flex flex-col items-center gap-3">
                    <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
                    <span className="font-bold text-indigo-600">Running Computer Vision...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 flex flex-col">
          <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-wider mb-6">File Info</h3>
          <div className="space-y-4 flex-1">
            <DetailItem label="FILENAME" value={fileDetails?.name || "---"} />
            <DetailItem label="SIZE" value={fileDetails?.size || "---"} />
            <DetailItem label="STATUS" value={status.toUpperCase()} />
          </div>
          
          <button 
            disabled={!selectedFile || status === 'processing'}
            onClick={(e) => { e.stopPropagation(); analyzeImage(); }}
            className={cn(
              "w-full py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2 mt-6 shadow-lg shadow-indigo-500/20",
              selectedFile && status !== 'processing' ? "bg-indigo-600 text-white hover:bg-indigo-700" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-400 cursor-not-allowed"
            )}
          >
            {status === 'processing' ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Analyze
          </button>
          
          {status === 'error' && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-500/10 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400 text-xs font-medium">
              <AlertCircle className="w-4 h-4" />
              Check backend connection.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}


// SECTION: SUBCOMPONENTS - DETAILS METADATA ROW
// Description: Renders simple, aligned key/value blocks on the sidebar panel.

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] text-zinc-500 font-bold tracking-widest">{label}</span>
      <span className="text-sm font-medium dark:text-white text-zinc-900 truncate">{value}</span>
    </div>
  );
}
