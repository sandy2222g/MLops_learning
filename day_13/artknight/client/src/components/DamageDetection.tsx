// SECTION: IMPORTS
// Description: Imports icons, React hooks, and styling utilities for the damage detection panel.

import { ScanSearch, FileImage, Loader2, CheckCircle2, AlertCircle, ShieldAlert, Percent, Hash, Activity } from 'lucide-react';
import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from '../lib/utils';


// SECTION: TYPES
// Description: Defines the shape of the YOLO detection response from the backend.

interface DetectionResult {
  crack_count: number;
  avg_confidence: number;
  coverage_pct: number;
  annotated_image: string;
  status: string;
}


// SECTION: DAMAGE DETECTION COMPONENT
// Description: Handles image upload, sends it to /detect_damage, and displays the annotated result with crack stats.

export function DamageDetection() {
  const [dragActive, setDragActive] = useState(false);
  const [status, setStatus] = useState<'idle' | 'processing' | 'done' | 'error'>('idle');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setStatus('idle');
      setErrorMsg('');
    }
  };

  const runDetection = async () => {
    if (!selectedFile) return;
    setStatus('processing');
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('/api/detect_damage', { method: 'POST', body: formData });
      if (!response.ok) throw new Error('Backend error');
      const data: DetectionResult = await response.json();
      setResult(data);
      setStatus('done');
    } catch (e) {
      console.error(e);
      setErrorMsg('Detection failed. Check backend connection.');
      setStatus('error');
    }
  };

  const hasDamage = result && result.crack_count > 0;

  return (
    <div className="space-y-6">

      {/* SECTION: HEADER */}
      <div className="flex items-center gap-3 border-b dark:border-zinc-800 border-zinc-200 pb-2">
        <h2 className="text-xl font-bold dark:text-white text-zinc-900 flex items-center gap-2">
          <ScanSearch className="w-5 h-5 text-rose-500" />
          Damage Detection
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* SECTION: DROP ZONE */}
        <div
          className={cn(
            "lg:col-span-2 relative h-80 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center transition-all duration-300 overflow-hidden group cursor-pointer",
            dragActive
              ? "border-rose-500 bg-rose-50 dark:bg-rose-500/5"
              : "dark:border-zinc-800 border-zinc-200 bg-white dark:bg-zinc-900 hover:border-rose-500/50"
          )}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => { e.preventDefault(); setDragActive(false); e.dataTransfer.files && handleFile(e.dataTransfer.files[0]); }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input type="file" className="hidden" ref={fileInputRef} accept="image/*"
            onChange={(e) => e.target.files && handleFile(e.target.files[0])} />

          {!previewUrl ? (
            <>
              <div className="w-16 h-16 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <FileImage className="w-8 h-8 text-zinc-400 group-hover:text-rose-500 transition-colors" />
              </div>
              <p className="text-zinc-600 dark:text-zinc-300 font-medium">Click to upload artwork image</p>
              <p className="text-xs text-zinc-400 mt-1">Detects surface cracks using YOLO segmentation</p>
            </>
          ) : (
            <div className="absolute inset-0 w-full h-full">
              <img src={previewUrl} alt="Preview" className="w-full h-full object-contain" />
              {status === 'processing' && (
                <div className="absolute inset-0 bg-white/60 dark:bg-black/60 backdrop-blur-sm flex items-center justify-center">
                  <div className="flex flex-col items-center gap-3">
                    <Loader2 className="w-10 h-10 text-rose-500 animate-spin" />
                    <span className="font-bold text-rose-600 dark:text-rose-400">Running YOLO Detection...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* SECTION: SIDEBAR CONTROLS */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 flex flex-col gap-4">
          <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-wider">Detection Info</h3>

          <div className="space-y-3 flex-1">
            <InfoRow label="FILE" value={selectedFile?.name || '---'} />
            <InfoRow label="MODEL" value="YOLOv8 Seg" />
            <InfoRow label="CLASS" value="Crack" />
            <InfoRow label="STATUS" value={status.toUpperCase()} />
          </div>

          <button
            disabled={!selectedFile || status === 'processing'}
            onClick={(e) => { e.stopPropagation(); runDetection(); }}
            className={cn(
              "w-full py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2 shadow-lg shadow-rose-500/20",
              selectedFile && status !== 'processing'
                ? "bg-rose-500 text-white hover:bg-rose-600"
                : "bg-zinc-100 dark:bg-zinc-800 text-zinc-400 cursor-not-allowed"
            )}
          >
            {status === 'processing' ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Detect Damage
          </button>

          {status === 'error' && (
            <div className="p-3 bg-red-50 dark:bg-red-500/10 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400 text-xs font-medium">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {errorMsg}
            </div>
          )}
        </div>
      </div>

      {/* SECTION: RESULTS */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            className="space-y-6"
          >
            {/* Stats row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard
                icon={Hash}
                label="Cracks Detected"
                value={result.crack_count.toString()}
                color={hasDamage ? 'text-rose-500' : 'text-emerald-500'}
                bg={hasDamage ? 'bg-rose-500/10' : 'bg-emerald-500/10'}
              />
              <StatCard
                icon={Activity}
                label="Avg Confidence"
                value={`${result.avg_confidence.toFixed(1)}%`}
                color="text-orange-500"
                bg="bg-orange-500/10"
              />
              <StatCard
                icon={Percent}
                label="Damage Coverage"
                value={`${result.coverage_pct.toFixed(2)}%`}
                color="text-amber-500"
                bg="bg-amber-500/10"
              />
            </div>

            {/* Severity badge */}
            <div className={cn(
              "p-4 rounded-2xl border-2 flex items-center gap-3",
              hasDamage
                ? "bg-rose-500/10 border-rose-500/20"
                : "bg-emerald-500/10 border-emerald-500/20"
            )}>
              <ShieldAlert className={cn("w-6 h-6 shrink-0", hasDamage ? "text-rose-500" : "text-emerald-500")} />
              <div>
                <p className={cn("font-bold text-sm", hasDamage ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400")}>
                  {hasDamage ? `Damage Detected — ${result.crack_count} crack region${result.crack_count !== 1 ? 's' : ''} found` : 'No Damage Detected'}
                </p>
                <p className="text-xs text-zinc-500 mt-0.5">
                  {hasDamage
                    ? `Surface coverage: ${result.coverage_pct.toFixed(2)}% · Average detection confidence: ${result.avg_confidence.toFixed(1)}%`
                    : 'The YOLO model found no crack regions in the uploaded image.'}
                </p>
              </div>
            </div>

            {/* Annotated image */}
            <div className="rounded-2xl overflow-hidden border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
              <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
                <p className="text-sm font-bold text-zinc-500 uppercase tracking-wider">Annotated Output</p>
              </div>
              <img
                src={`data:image/jpeg;base64,${result.annotated_image}`}
                alt="YOLO annotated result"
                className="w-full object-contain max-h-[500px]"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}


// SECTION: SUBCOMPONENTS
// Description: Small reusable display primitives used within the detection panel.

function StatCard({ icon: Icon, label, value, color, bg }: {
  icon: React.ElementType;
  label: string;
  value: string;
  color: string;
  bg: string;
}) {
  return (
    <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm flex items-center gap-4">
      <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center", bg)}>
        <Icon className={cn("w-5 h-5", color)} />
      </div>
      <div>
        <p className="text-xs text-zinc-500 font-bold uppercase tracking-wider">{label}</p>
        <p className={cn("text-xl font-black", color)}>{value}</p>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] text-zinc-500 font-bold tracking-widest">{label}</span>
      <span className="text-sm font-medium dark:text-white text-zinc-900 truncate">{value}</span>
    </div>
  );
}
