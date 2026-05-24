import { Database, ShieldCheck, Sparkles, AlertTriangle, Zap, Info, ListTree } from 'lucide-react';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';

interface Feature {
  name: string;
  value: number;
}

interface DashboardProps {
  data: {
    prediction: string;
    features: Feature[];
  } | null;
}

export function Dashboard({ data }: DashboardProps) {
  const prediction = data?.prediction || null;
  const features = data?.features || [];

  const stats = [
    { label: 'Model Accuracy', value: '99.6%', icon: ShieldCheck, color: 'text-emerald-500' },
    { label: 'Backend Engine', value: 'Flask/OpenCV', icon: Database, color: 'text-blue-500' },
    { label: 'Inference Time', value: '0.42s', icon: Zap, color: 'text-yellow-500' },
  ];

  const getPredictionStyles = (pred: string) => {
    switch (pred.toLowerCase()) {
      case 'easy': return { color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', icon: ShieldCheck };
      case 'moderate': return { color: 'text-blue-500', bg: 'bg-blue-500/10', border: 'border-blue-500/20', icon: Info };
      case 'difficult': return { color: 'text-orange-500', bg: 'bg-orange-500/10', border: 'border-orange-500/20', icon: AlertTriangle };
      case 'impossible': return { color: 'text-red-500', bg: 'bg-red-500/10', border: 'border-red-500/20', icon: Sparkles };
      default: return { color: 'text-zinc-500', bg: 'bg-zinc-500/10', border: 'border-zinc-500/20', icon: Info };
    }
  };

  const predStyle = prediction ? getPredictionStyles(prediction) : null;
  const PredIcon = predStyle?.icon;

  return (
    <div className="space-y-8">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((stat, i) => (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            key={stat.label}
            className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">{stat.label}</span>
              <stat.icon className={`w-5 h-5 ${stat.color}`} />
            </div>
            <div className="text-2xl font-bold dark:text-white text-zinc-900">{stat.value}</div>
          </motion.div>
        ))}
      </div>

      {/* Main Results Container */}
      <div className="grid grid-cols-1 gap-8">
        
        {/* Prediction Card */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className={cn(
            "p-8 rounded-3xl border-2 flex flex-col items-center justify-center text-center transition-all duration-500",
            prediction 
              ? `${predStyle?.bg} ${predStyle?.border}` 
              : "bg-zinc-100/50 dark:bg-zinc-900/50 border-zinc-200 dark:border-zinc-800 border-dashed"
          )}
        >
          {!prediction ? (
            <div className="flex flex-col items-center gap-4 py-12 text-zinc-400">
              <Sparkles className="w-12 h-12 opacity-20" />
              <p className="font-medium">Upload an image to start analysis</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-6 py-4">
              <div className={cn("w-16 h-16 rounded-2xl flex items-center justify-center shadow-xl", predStyle?.bg)}>
                {PredIcon && <PredIcon className={cn("w-8 h-8", predStyle?.color)} />}
              </div>
              <div>
                <span className="text-xs font-bold uppercase tracking-widest text-zinc-500 block mb-1">Restoration Result</span>
                <h3 className={cn("text-4xl font-black tracking-tight", predStyle?.color)}>
                  {prediction.toUpperCase()}
                </h3>
              </div>
            </div>
          )}
        </motion.div>

        {/* Feature Extraction View (METRICS) */}
        {features.length > 0 && (
          <motion.div 
            id="features-section"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="scroll-mt-24 space-y-4"
          >
            <div className="flex items-center gap-3 border-b dark:border-zinc-800 border-zinc-200 pb-2">
              <h2 className="text-xl font-bold dark:text-white text-zinc-900 flex items-center gap-2">
                <ListTree className="w-5 h-5 text-indigo-500" />
                Extracted Metrics
              </h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {features.map((feature, i) => (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  key={feature.name}
                  className="bg-white dark:bg-zinc-900 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 flex justify-between items-center"
                >
                  <span className="text-xs font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-tighter">{feature.name}</span>
                  <span className="text-sm font-mono font-bold text-indigo-600 dark:text-indigo-400">{feature.value}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
