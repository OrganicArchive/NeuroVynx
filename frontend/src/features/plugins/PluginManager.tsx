import { useState, useEffect } from 'react';
import { Settings, Puzzle, CheckCircle2, AlertTriangle, XCircle, Info, ShieldCheck, User, HardDrive } from 'lucide-react';

interface PluginManifest {
  plugin_id: string;
  name: string;
  version: string;
  author: string;
  category: string;
  trust_tier: string;
  permissions: string[];
  entrypoint: string;
  plugin_api_version: string;
  description?: string;
}

interface PluginInfo {
  manifest: PluginManifest;
  status: string;
  enabled: boolean;
  path: string;
  error_state?: string;
  last_error?: string;
}

const API_BASE = 'http://localhost:8000/api/v1/plugins';

const TrustTierBadge = ({ tier }: { tier: string }) => {
  const tiers: Record<string, { label: string; color: string; icon: any }> = {
    core_certified: { label: 'Core Certified', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: ShieldCheck },
    official_experimental: { label: 'Official Experimental', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30', icon: Settings },
    community_reviewed: { label: 'Community Reviewed', color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: User },
    unverified_local: { label: 'Unverified Local', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30', icon: HardDrive },
  };

  const config = tiers[tier] || tiers.unverified_local;
  const Icon = config.icon;

  return (
    <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${config.color}`}>
      <Icon size={12} />
      {config.label}
    </span>
  );
};

const StatusBadge = ({ status, lastError }: { status: string; lastError?: string }) => {
  const statuses: Record<string, { label: string; color: string; icon: any }> = {
    enabled: { label: 'Running', color: 'text-green-400', icon: CheckCircle2 },
    disabled: { label: 'Disabled', color: 'text-muted-foreground', icon: Info },
    failed: { label: 'Failed', color: 'text-red-400', icon: XCircle },
    incompatible: { label: 'Incompatible', color: 'text-yellow-400', icon: AlertTriangle },
    loaded: { label: 'Ready', color: 'text-blue-400', icon: Info },
  };

  const config = statuses[status] || statuses.disabled;
  const Icon = config.icon;

  return (
    <div className="flex flex-col gap-1">
      <span className={`flex items-center gap-1.5 text-xs font-medium ${config.color}`}>
        <Icon size={14} />
        {config.label}
      </span>
      {lastError && (
        <span className="text-[10px] text-red-400/80 max-w-[200px] truncate" title={lastError}>
          {lastError}
        </span>
      )}
    </div>
  );
};

export default function PluginManager({ onBack }: { onBack: () => void }) {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlugins = async () => {
    try {
      const response = await fetch(API_BASE);
      if (!response.ok) throw new Error('Failed to fetch plugins');
      const data = await response.json();
      setPlugins(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlugins();
  }, []);

  const togglePlugin = async (id: string, currentEnabled: boolean) => {
    try {
      const response = await fetch(`${API_BASE}/${id}/toggle?enabled=${!currentEnabled}`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Toggle failed');
      fetchPlugins();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="flex flex-col h-full bg-background">
      <header className="flex items-center justify-between px-8 py-6 border-b border-border bg-card/30 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <button 
            onClick={onBack}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
          >
            ← Back to App
          </button>
          <div className="w-px h-6 bg-border mx-2" />
          <div className="flex items-center gap-3">
            <Puzzle className="text-primary w-6 h-6" />
            <h1 className="text-xl font-bold">Plugin Ecosystem</h1>
          </div>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-secondary border border-border text-xs text-muted-foreground">
          <Info size={14} />
          API Version: 1.0 (Stable)
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-8 py-8 max-w-6xl w-full mx-auto">
        {error && (
          <div className="mb-8 p-4 bg-destructive/10 border border-destructive/20 text-destructive rounded-lg flex items-center gap-3">
            <AlertTriangle size={18} />
            <span className="text-sm font-medium">{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              <p className="text-sm">Scanning plugin directories...</p>
            </div>
          ) : plugins.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-4 border-2 border-dashed border-border rounded-xl">
              <Puzzle size={48} className="opacity-20" />
              <div className="text-center">
                <p className="text-lg font-medium">No plugins discovered</p>
                <p className="text-sm opacity-60">Plugins should be located in <code>/plugins/official</code> or <code>/plugins/local</code></p>
              </div>
            </div>
          ) : (
            plugins.map((plugin) => (
              <div 
                key={plugin.manifest.plugin_id}
                className={`group relative flex flex-col p-6 rounded-xl border transition-all duration-200 ${
                  plugin.enabled 
                    ? 'bg-card border-border/60 shadow-sm' 
                    : 'bg-card/40 border-border/20 opacity-80'
                }`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-lg flex items-center justify-center ${
                      plugin.enabled ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                    }`}>
                      <Puzzle size={24} />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold flex items-center gap-3">
                        {plugin.manifest.name}
                        <span className="text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground uppercase opacity-60">
                          {plugin.manifest.category}
                        </span>
                      </h3>
                      <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1 capitalize">
                          <User size={12} />
                          {plugin.manifest.author}
                        </span>
                        <div className="w-1 h-1 rounded-full bg-border" />
                        <span>v{plugin.manifest.version}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-3">
                    <StatusBadge status={plugin.status} lastError={plugin.last_error} />
                    <button
                      onClick={() => togglePlugin(plugin.manifest.plugin_id, plugin.enabled)}
                      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
                        plugin.enabled ? 'bg-primary' : 'bg-muted'
                      }`}
                    >
                      <span className="sr-only">Toggle plugin</span>
                      <span
                        aria-hidden="true"
                        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                          plugin.enabled ? 'translate-x-5' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 mb-6">
                  <TrustTierBadge tier={plugin.manifest.trust_tier} />
                  {plugin.manifest.permissions.map(perm => (
                    <span key={perm} className="text-[10px] font-mono px-2 py-0.5 rounded bg-muted/50 border border-border/30 text-muted-foreground">
                      {perm}
                    </span>
                  ))}
                </div>

                <p className="text-sm text-muted-foreground leading-relaxed mb-6 line-clamp-2 italic">
                  {plugin.manifest.description || "No description provided for this extension."}
                </p>

                <div className="mt-auto pt-4 border-t border-border/20 flex items-center justify-between text-[11px] text-muted-foreground/60 font-mono">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 size={12} className={plugin.status !== 'incompatible' ? 'text-green-500' : 'text-muted-foreground'} />
                    API Version: {plugin.manifest.plugin_api_version}
                  </span>
                  <span className="truncate max-w-[400px]" title={plugin.path}>
                    Location: {plugin.path}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </main>

      <footer className="p-8 border-t border-border bg-card/20 text-center text-[10px] text-muted-foreground uppercase tracking-widest">
        NeuroVynx Plugin Registry Architecture &copy; 2026 Phase 19 Release
      </footer>
    </div>
  );
}
