/**
 * Dreaming — Dashboard Plugin v2.0
 *
 * Displays Eliana's dream journal entries, dreaming state, vector store stats,
 * and provides a re-index button. Calls the plugin backend at /api/plugins/hermes-dreaming/.
 *
 * Plain IIFE, no build step. Uses window.__HERMES_PLUGIN_SDK__.
 */
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !window.__HERMES_PLUGINS__) return;

  const React = SDK.React;
  const h = React.createElement;
  const { useState, useEffect, useCallback } = SDK.hooks;
  const { Card, CardContent, CardHeader, CardTitle, Badge, Button } = SDK.components;
  const { cn, timeAgo } = SDK.utils;

  const API_BASE = "/api/plugins/hermes-dreaming";

  async function api(path, opts) {
    const token = window.__HERMES_SESSION_TOKEN__ || "";
    const headers = { "Content-Type": "application/json" };
    if (token) headers["X-Hermes-Session-Token"] = token;
    const res = await fetch(API_BASE + path, { headers, ...opts });
    if (!res.ok) {
      const text = await res.text().catch(function () { return res.statusText; });
      throw new Error(res.status + ": " + text);
    }
    return res.json();
  }

  // --- Icons ---
  function MoonIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, props || {}),
      h("path", { d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" }));
  }
  function BrainIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, props || {}),
      h("path", { d: "M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" }),
      h("path", { d: "M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" }),
      h("path", { d: "M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" }),
      h("path", { d: "M17.599 6.5a3 3 0 0 0 .399-1.375" }),
      h("path", { d: "M6.003 5.125A3 3 0 0 0 6.401 6.5" }),
      h("path", { d: "M3.477 10.896a4 4 0 0 1 .585-.396" }),
      h("path", { d: "M19.938 10.5a4 4 0 0 1 .585.396" }),
      h("path", { d: "M6 18a4 4 0 0 1-1.967-.516" }),
      h("path", { d: "M19.967 17.484A4 4 0 0 1 18 18" }));
  }
  function ClockIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, props || {}),
      h("circle", { cx: "12", cy: "12", r: "10" }),
      h("polyline", { points: "12 6 12 12 16 14" }));
  }
  function ZapIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, props || {}),
      h("polygon", { points: "13 2 3 14 12 14 11 22 21 10 12 10 13 2" }));
  }
  function LinkIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, props || {}),
      h("path", { d: "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" }),
      h("path", { d: "M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" }));
  }
  function DatabaseIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, props || {}),
      h("ellipse", { cx: "12", cy: "5", rx: "9", ry: "3" }),
      h("path", { d: "M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" }),
      h("path", { d: "M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" }));
  }
  function RefreshIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, props || {}),
      h("path", { d: "M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" }),
      h("path", { d: "M21 3v5h-5" }),
      h("path", { d: "M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" }),
      h("path", { d: "M8 16H3v5" }));
  }

  // --- Dream Card ---
  function DreamCard({ dream, onSelect }) {
    const hasInsights = dream.insights && dream.insights.length > 0;
    const hasConnections = dream.connections && dream.connections.length > 0;
    const wasNotified = dream.notified_user;

    return h(Card, {
        className: cn("cursor-pointer transition-all hover:shadow-md", wasNotified && "border-l-4 border-l-amber-500"),
        onClick: function () { onSelect(dream); },
      },
      h(CardContent, { className: "pt-4" },
        h("div", { className: "flex items-start justify-between gap-3" },
          h("div", { className: "flex-1 min-w-0" },
            h("div", { className: "flex items-center gap-2 mb-1" },
              h(MoonIcon, { className: "w-4 h-4 text-indigo-400 shrink-0" }),
              h("span", { className: "font-medium text-sm truncate" }, dream.title || dream.id),
              wasNotified && h(Badge, { variant: "outline", className: "text-xs text-amber-400 border-amber-500/30" }, "shared")
            ),
            h("div", { className: "flex items-center gap-3 text-xs text-muted-foreground" },
              h("span", { className: "flex items-center gap-1" }, h(ClockIcon, { className: "w-3 h-3" }), dream.timestamp),
              dream.duration && dream.duration !== "unknown" && h("span", null, "⏱ " + dream.duration)
            )
          )
        ),
        (hasInsights || hasConnections) && h("div", { className: "mt-3 space-y-1" },
          hasInsights && h("div", { className: "flex items-start gap-1.5 text-xs" },
            h(ZapIcon, { className: "w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" }),
            h("span", { className: "text-amber-200/80 line-clamp-2" }, dream.insights[0])
          ),
          hasConnections && h("div", { className: "flex items-start gap-1.5 text-xs" },
            h(LinkIcon, { className: "w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" }),
            h("span", { className: "text-blue-200/80 line-clamp-2" }, dream.connections[0])
          )
        )
      )
    );
  }

  // --- Dream Detail Modal ---
  function DreamDetail({ dream, onClose }) {
    if (!dream) return null;
    return h("div", { className: "fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4", onClick: function (e) { if (e.target === e.currentTarget) onClose(); } },
      h(Card, { className: "max-w-2xl w-full max-h-[80vh] overflow-y-auto bg-background border-border shadow-2xl" },
        h(CardHeader, null,
          h("div", { className: "flex items-center justify-between" },
            h("div", { className: "flex items-center gap-2" },
              h(MoonIcon, { className: "w-5 h-5 text-indigo-400" }),
              h(CardTitle, null, dream.title || dream.id)
            ),
            h(Button, { variant: "ghost", size: "sm", onClick: onClose }, "✕")
          ),
          h("div", { className: "flex items-center gap-3 text-xs text-muted-foreground mt-1" },
            h("span", null, "🕐 " + dream.timestamp),
            dream.duration && dream.duration !== "unknown" && h("span", null, "⏱ " + dream.duration),
            dream.notified_user && h(Badge, { variant: "outline", className: "text-xs text-amber-400" }, "Shared with user")
          )
        ),
        h(CardContent, { className: "space-y-4" },
          dream.content && h("div", null,
            h("h4", { className: "text-sm font-semibold mb-2 text-muted-foreground" }, "Dream Journal"),
            h("pre", { className: "text-xs bg-muted/30 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed" }, dream.content)
          )
        )
      )
    );
  }

  // --- Vector Store Stats Card ---
  function VectorStatsCard({ stats, onReindex, reindexing }) {
    return h(Card, null,
      h(CardHeader, null,
        h("div", { className: "flex items-center justify-between" },
          h("div", { className: "flex items-center gap-2" },
            h(DatabaseIcon, { className: "w-5 h-5 text-emerald-400" }),
            h(CardTitle, { className: "text-base" }, "Vector Store")
          ),
          h(Button, { variant: "outline", size: "sm", onClick: onReindex, disabled: reindexing },
            h(RefreshIcon, { className: cn("w-3.5 h-3.5 mr-1.5", reindexing && "animate-spin") }),
            reindexing ? "Indexing..." : "Re-index"
          )
        )
      ),
      h(CardContent, null,
        !stats.installed
          ? h("div", { className: "text-xs text-amber-400" }, "⚠ ChromaDB not installed. Run: pip install chromadb")
          : h("div", { className: "grid grid-cols-3 gap-4" },
              h("div", null,
                h("div", { className: "text-lg font-bold" }, stats.facts || "—"),
                h("div", { className: "text-xs text-muted-foreground" }, "Holographic Facts")
              ),
              h("div", null,
                h("div", { className: "text-lg font-bold" }, stats.indexed || "—"),
                h("div", { className: "text-xs text-muted-foreground" }, "Vector Indexed")
              ),
              h("div", null,
                h("div", { className: "text-lg font-bold" }, stats.size || "—"),
                h("div", { className: "text-xs text-muted-foreground" }, "Storage")
              )
            )
      )
    );
  }

  // --- Main Page ---
  function DreamsPage() {
    const [state, setState] = useState(null);
    const [dreams, setDreams] = useState([]);
    const [vectorStats, setVectorStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedDream, setSelectedDream] = useState(null);
    const [reindexing, setReindexing] = useState(false);

    const loadData = useCallback(function () {
      setLoading(true);
      setError(null);
      Promise.all([
        api("/state").catch(function () { return null; }),
        api("/dreams?limit=50").catch(function () { return null; }),
        api("/vector-stats").catch(function () { return null; }),
      ])
        .then(function (results) {
          var stateResult = results[0], dreamsResult = results[1], vectorResult = results[2];
          if (stateResult) setState(stateResult);
          if (dreamsResult) setDreams(dreamsResult.dreams || []);
          if (vectorResult) setVectorStats(vectorResult);
          if (!stateResult && !dreamsResult) setError("Failed to load dreaming data");
        })
        .catch(function (err) { setError(err.message); })
        .finally(function () { setLoading(false); });
    }, []);

    useEffect(function () { loadData(); }, [loadData]);

    const handleReindex = useCallback(function () {
      setReindexing(true);
      api("/reindex", { method: "POST" })
        .then(function () { loadData(); })
        .catch(function (err) { setError("Reindex failed: " + err.message); })
        .finally(function () { setReindexing(false); });
    }, [loadData]);

    if (loading) {
      return h("div", { className: "flex items-center justify-center py-12" },
        h("div", { className: "text-muted-foreground flex items-center gap-2" },
          h(MoonIcon, { className: "w-5 h-5 animate-pulse" }), "Loading dreams..."
        )
      );
    }

    if (error) {
      return h("div", { className: "flex flex-col items-center justify-center py-12 gap-3" },
        h("div", { className: "text-red-400 text-sm" }, "⚠ " + error),
        h(Button, { variant: "outline", size: "sm", onClick: loadData }, "Retry")
      );
    }

    return h("div", { className: "space-y-6" },
      // Header
      h("div", { className: "flex items-center justify-between" },
        h("div", { className: "flex items-center gap-3" },
          h("div", { className: "p-2 rounded-lg bg-indigo-500/10" },
            h(BrainIcon, { className: "w-6 h-6 text-indigo-400" })
          ),
          h("div", null,
            h("h2", { className: "text-lg font-semibold" }, "Dream Journal"),
            h("p", { className: "text-xs text-muted-foreground" },
              "Idle-time memory consolidation • 30min threshold • Two-tier memory"
            )
          )
        ),
        h(Button, { variant: "ghost", size: "sm", onClick: loadData }, "↻ Refresh")
      ),

      // Stats row
      h("div", { className: "grid grid-cols-2 md:grid-cols-4 gap-3" },
        h(Card, null, h(CardContent, { className: "pt-4 pb-4" },
          h("div", { className: "text-2xl font-bold" }, state && state.total_dreams != null ? state.total_dreams : "—"),
          h("div", { className: "text-xs text-muted-foreground" }, "Total Dreams")
        )),
        h(Card, null, h(CardContent, { className: "pt-4 pb-4" },
          h("div", { className: "text-2xl font-bold" }, state && state.dreams_today != null ? state.dreams_today : "—"),
          h("div", { className: "text-xs text-muted-foreground" }, "Dreams Today")
        )),
        h(Card, null, h(CardContent, { className: "pt-4 pb-4" },
          h("div", { className: "text-2xl font-bold" }, dreams.length),
          h("div", { className: "text-xs text-muted-foreground" }, "Journal Entries")
        )),
        h(Card, null, h(CardContent, { className: "pt-4 pb-4" },
          h("div", { className: "text-2xl font-bold" },
            state && state.last_dream_at ? timeAgo(state.last_dream_at) : "—"
          ),
          h("div", { className: "text-xs text-muted-foreground" }, "Last Dream")
        ))
      ),

      // Vector Store Stats
      vectorStats && h(VectorStatsCard, { stats: vectorStats, onReindex: handleReindex, reindexing: reindexing }),

      // Dream entries
      h("div", null,
        h("h3", { className: "text-sm font-semibold mb-3 text-muted-foreground" }, "Recent Dreams"),
        dreams.length === 0
          ? h("div", { className: "text-center py-12 text-muted-foreground" },
              h(MoonIcon, { className: "w-8 h-8 mx-auto mb-3 opacity-30" }),
              h("p", { className: "text-sm" }, "No dreams yet."),
              h("p", { className: "text-xs mt-1" }, "Dreams appear here after 30min idle-time consolidation cycles.")
            )
          : h("div", { className: "space-y-3" },
              dreams.map(function (dream) {
                return h(DreamCard, { key: dream.id, dream: dream, onSelect: setSelectedDream });
              })
            )
      ),

      // Detail modal
      selectedDream && h(DreamDetail, { dream: selectedDream, onClose: function () { setSelectedDream(null); } })
    );
  }

  // --- Register plugin ---
  if (window.__HERMES_PLUGINS__) {
    window.__HERMES_PLUGINS__.register("hermes-dreaming", DreamsPage);
  }
})();
