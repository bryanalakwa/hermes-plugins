/**
 * Dream Engine — Dashboard Plugin v1.0
 *
 * Visualizes the 5-state dreaming state machine, dream journal,
 * and provides manual controls. Calls the plugin backend at
 * /api/plugins/hermes-dream-engine/.
 *
 * Plain IIFE, no build step. Uses window.__HERMES_PLUGIN_SDK__.
 */
(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !window.__HERMES_PLUGINS__) return;

  var React = SDK.React;
  var h = React.createElement;
  var useState = SDK.hooks.useState;
  var useEffect = SDK.hooks.useEffect;
  var useCallback = SDK.hooks.useCallback;
  var useRef = SDK.hooks.useRef;
  var Card = SDK.components.Card;
  var CardContent = SDK.components.CardContent;
  var CardHeader = SDK.components.CardHeader;
  var CardTitle = SDK.components.CardTitle;
  var Badge = SDK.components.Badge;
  var Button = SDK.components.Button;
  var Input = SDK.components.Input;
  var Label = SDK.components.Label;
  var cn = SDK.utils.cn;
  var timeAgo = SDK.utils.timeAgo;

  var API_BASE = "/api/plugins/hermes-dream-engine";

  function api(path, opts) {
    var token = window.__HERMES_SESSION_TOKEN__ || "";
    var headers = { "Content-Type": "application/json" };
    if (token) headers["X-Hermes-Session-Token"] = token;
    return fetch(API_BASE + path, Object.assign({ headers: headers }, opts)).then(function (res) {
      if (!res.ok) {
        return res.text().catch(function () { return res.statusText; }).then(function (text) {
          throw new Error(res.status + ": " + text);
        });
      }
      return res.json();
    });
  }

  // --- Icons ---
  function MoonIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, props || {}),
      h("path", { d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" }));
  }
  function ZapIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("polygon", { points: "13 2 3 14 12 14 11 22 21 10 12 10 13 2" }));
  }
  function RefreshIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("path", { d: "M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" }),
      h("path", { d: "M21 3v5h-5" }),
      h("path", { d: "M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" }),
      h("path", { d: "M8 16H3v5" }));
  }
  function CheckIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("polyline", { points: "20 6 9 17 4 12" }));
  }
  function BrainIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("path", { d: "M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" }),
      h("path", { d: "M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" }));
  }
  function BookIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("path", { d: "M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" }));
  }

  // --- State colors ---
  var STATE_COLORS = {
    active: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
    idle: "text-amber-400 border-amber-500/30 bg-amber-500/10",
    dormant: "text-blue-400 border-blue-500/30 bg-blue-500/10",
    hypnagogic: "text-purple-400 border-purple-500/30 bg-purple-500/10",
    dreaming: "text-pink-400 border-pink-500/30 bg-pink-500/10"
  };
  var STATE_LABELS = {
    active: "Active",
    idle: "Idle",
    dormant: "Dormant",
    hypnagogic: "Hypnagogic",
    dreaming: "Dreaming"
  };

  function fmtDuration(seconds) {
    if (seconds == null || isNaN(seconds)) return "\u2014";
    if (seconds < 60) return Math.round(seconds) + "s";
    if (seconds < 3600) return Math.round(seconds / 60) + "m " + Math.round(seconds % 60) + "s";
    return Math.round(seconds / 3600) + "h " + Math.round((seconds % 3600) / 60) + "m";
  }

  // --- State Machine Viz ---
  function StateMachineViz(props) {
    var states = ["active", "idle", "dormant", "hypnagogic", "dreaming"];
    var labels = ["Active", "Idle", "Dormant", "Hypnagogic", "Dreaming"];
    return h("div", { className: "flex items-center gap-1 overflow-x-auto pb-2" },
      states.map(function (s, i) {
        return h("div", { key: s, className: "flex items-center" },
          h("div", {
            className: cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium border transition-all",
              props.state === s
                ? STATE_COLORS[s] + " ring-1 ring-current scale-105"
                : "text-muted-foreground border-border/20 bg-white/5"
            )
          }, labels[i]),
          i < states.length - 1 && h("div", { className: "w-4 h-px bg-border/30 mx-0.5" })
        );
      })
    );
  }

  // --- Timer Bar ---
  function TimerBar(props) {
    var pct = props.total > 0 ? Math.min(100, (props.elapsed / props.total) * 100) : 0;
    return h("div", { className: "space-y-1" },
      h("div", { className: "flex items-center justify-between text-xs" },
        h("span", { className: "text-muted-foreground" }, props.label),
        h("span", { className: "font-mono" }, fmtDuration(props.elapsed), " / ", fmtDuration(props.total))
      ),
      h("div", { className: "h-1.5 bg-white/5 rounded-full overflow-hidden" },
        h("div", { className: cn("h-full rounded-full transition-all duration-1000", props.color), style: { width: pct + "%" } })
      )
    );
  }

  // --- Dream Session Card ---
  function DreamSessionCard(props) {
    var entry = props.entry;
    var completed = entry.state_on_exit === "completed";
    var interrupted = entry.state_on_exit === "interrupted";
    return h(Card, null,
      h(CardContent, { className: "pt-4" },
        h("div", { className: "flex items-start justify-between gap-3" },
          h("div", { className: "flex-1 min-w-0" },
            h("div", { className: "flex items-center gap-2 mb-1" },
              h("span", { className: "font-mono text-xs text-muted-foreground" }, "#", entry.session_id),
              h(Badge, {
                variant: "outline",
                className: cn("text-xs",
                  completed ? "text-emerald-400 border-emerald-500/30" :
                  interrupted ? "text-amber-400 border-amber-500/30" :
                  "text-red-400 border-red-500/30"
                )
              }, entry.state_on_exit),
              entry.dreams_today != null && h("span", { className: "text-xs text-muted-foreground" }, "(dream " + entry.dreams_today + ")")
            ),
            h("div", { className: "flex items-center gap-3 text-xs text-muted-foreground" },
              h("span", null, entry.started_at || "\u2014"),
              entry.ended_at && h("span", null, "\u2192 " + entry.ended_at)
            ),
            entry.summary && h("p", { className: "text-xs mt-2 text-gray-300" }, entry.summary)
          ),
          h("div", { className: "flex items-center gap-2 shrink-0 text-xs" },
            entry.memories_consolidated > 0 && h(Badge, { variant: "outline", className: "text-xs" }, entry.memories_consolidated + " mem"),
            entry.insights_generated > 0 && h(Badge, { variant: "outline", className: "text-xs text-blue-400" }, entry.insights_generated + " insights"),
            entry.ideas_invented > 0 && h(Badge, { variant: "outline", className: "text-xs text-purple-400" }, entry.ideas_invented + " ideas")
          )
        ),
        entry.phases_run && entry.phases_run.length > 0 && h("div", { className: "flex gap-1 mt-2 flex-wrap" },
          entry.phases_run.map(function (phase) {
            return h(Badge, { key: phase, variant: "outline", className: "text-[10px] py-0" }, phase);
          })
        ),
        entry.errors && entry.errors.length > 0 && h("div", { className: "mt-2 text-xs text-red-400" },
          "Errors: " + entry.errors.join("; ")
        )
      )
    );
  }

  // --- Transition Log ---
  function TransitionLog(props) {
    if (!props.transitions || props.transitions.length === 0) {
      return h("div", { className: "text-center py-6 text-muted-foreground text-sm" }, "No state transitions yet.");
    }
    return h("div", { className: "space-y-1 max-h-60 overflow-y-auto" },
      props.transitions.map(function (t, i) {
        return h("div", { key: i, className: "flex items-center gap-2 text-xs py-1 border-b border-border/10" },
          h("span", { className: "font-mono text-muted-foreground w-20" }, t.timestamp),
          h(Badge, { variant: "outline", className: "text-[10px]" }, t.from),
          h("span", { className: "text-muted-foreground" }, "\u2192"),
          h(Badge, { variant: "outline", className: "text-[10px] " + (STATE_COLORS[t.to] || "") }, t.to),
          h("span", { className: "text-muted-foreground flex-1 truncate" }, t.reason)
        );
      })
    );
  }

  // --- Config Editor ---
  function ConfigEditor(props) {
    var configState = props.config || {};
    var localRef = useRef(configState);
    var local = localRef.current;
    var setLocal = useState(local)[1];
    var savingState = useState(false);
    var saving = savingState[0];
    var setSaving = savingState[1];

    var fields = [
      { key: "idle_threshold_seconds", label: "T1 \u2014 Idle threshold (s)", min: 60, max: 3600 },
      { key: "dormant_threshold_seconds", label: "T2 \u2014 Dormant threshold (s)", min: 300, max: 7200 },
      { key: "soak_threshold_seconds", label: "T3 \u2014 Soak period (s)", min: 600, max: 14400 },
      { key: "hypnagogic_duration_seconds", label: "T4 \u2014 Hypnagogic duration (s)", min: 30, max: 600 },
      { key: "max_dreams_per_day", label: "Max dreams/day", min: 1, max: 10 },
      { key: "consolidation_memory_count", label: "Memories to consolidate", min: 10, max: 500 },
      { key: "invention_sample_size", label: "Invention sample size (K)", min: 3, max: 30 }
    ];

    var updateField = useCallback(function (key, value) {
      var next = Object.assign({}, localRef.current);
      next[key] = value;
      localRef.current = next;
      setLocal(next);
    }, []);

    return h("div", { className: "space-y-3" },
      fields.map(function (f) {
        return h("div", { key: f.key },
          h(Label, { className: "text-xs" }, f.label),
          h(Input, {
            type: "number",
            min: f.min,
            max: f.max,
            value: local[f.key] || "",
            onChange: function (e) { updateField(f.key, parseInt(e.target.value) || 0); },
            className: "h-8 text-xs"
          })
        );
      }),
      h(Button, { size: "sm", onClick: function () {
        setSaving(true);
        api("/config", { method: "PUT", body: JSON.stringify(localRef.current) })
          .then(function () { setSaving(false); props.onSave(); })
          .catch(function () { setSaving(false); });
      }, disabled: saving }, saving ? "Saving..." : "Save Config")
    );
  }

  // --- Main Page ---
  function DreamEnginePage() {
    var statusState = useState(null);
    var status = statusState[0];
    var setStatus = statusState[1];
    var journalState = useState([]);
    var journal = journalState[0];
    var setJournal = journalState[1];
    var loadingState = useState(true);
    var loading = loadingState[0];
    var setLoading = loadingState[1];
    var errorState = useState(null);
    var error = errorState[0];
    var setError = errorState[1];
    var tabState = useState("status");
    var activeTab = tabState[0];
    var setActiveTab = tabState[1];
    var forcingState = useState(false);
    var forcing = forcingState[0];
    var setForcing = forcingState[1];
    var bottomRef = useRef(null);

    var loadData = useCallback(function () {
      setLoading(true);
      setError(null);
      Promise.all([
        api("/status").catch(function () { return null; }),
        api("/journal?limit=50").catch(function () { return null; })
      ]).then(function (results) {
        if (results[0]) setStatus(results[0]);
        if (results[1]) setJournal(results[1].entries || []);
        if (!results[0] && !results[1]) setError("Failed to load data");
      }).catch(function (err) {
        setError(err.message);
      }).finally(function () {
        setLoading(false);
      });
    }, []);

    useEffect(function () { loadData(); }, [loadData]);

    useEffect(function () {
      var interval = setInterval(loadData, 15000);
      return function () { clearInterval(interval); };
    }, [loadData]);

    var handleForceDream = useCallback(function () {
      setForcing(true);
      api("/dream/force", { method: "POST" })
        .then(function () { loadData(); })
        .catch(function (err) { setError(err.message); })
        .finally(function () { setForcing(false); });
    }, [loadData]);

    var handleReset = useCallback(function () {
      if (!confirm("Reset all dream engine state?")) return;
      api("/state/reset", { method: "POST" })
        .then(function () { loadData(); })
        .catch(function () {});
    }, [loadData]);

    var handleHeartbeat = useCallback(function () {
      api("/heartbeat", { method: "POST" })
        .then(function () { loadData(); })
        .catch(function () {});
    }, [loadData]);

    if (loading && !status) {
      return h("div", { className: "flex items-center justify-center py-12" },
        h("div", { className: "text-muted-foreground flex items-center gap-2" },
          h(MoonIcon, { className: "w-5 h-5 animate-pulse" }),
          "Loading dream engine..."
        )
      );
    }

    var monitor = (status && status.monitor) ? status.monitor : {};
    var thresholds = monitor.thresholds || {};
    var config = (status && status.config) ? status.config : {};

    return h("div", { className: "space-y-4" },
      // Header
      h("div", { className: "flex items-center justify-between" },
        h("div", { className: "flex items-center gap-3" },
          h("div", { className: "p-2 rounded-lg bg-purple-500/10" },
            h(MoonIcon, { className: "w-6 h-6 text-purple-400" })
          ),
          h("div", null,
            h("h2", { className: "text-lg font-semibold" }, "Dream Engine"),
            h("p", { className: "text-xs text-muted-foreground" },
              "Event-driven sleep detection & memory consolidation")
          )
        ),
        h("div", { className: "flex items-center gap-2" },
          h(Button, { variant: "ghost", size: "sm", onClick: loadData, title: "Refresh" },
            h(RefreshIcon, { className: "w-3.5 h-3.5" })
          ),
          h(Button, { variant: "outline", size: "sm", onClick: handleHeartbeat, title: "Send heartbeat" },
            h(ZapIcon, { className: "w-3.5 h-3.5 mr-1" }), "Ping"
          ),
          h(Button, { size: "sm", onClick: handleForceDream, disabled: forcing, title: "Force a dream session" },
            forcing ? "Dreaming..." : h(BrainIcon, { className: "w-3.5 h-3.5 mr-1" }),
            forcing ? "Dreaming..." : "Force Dream"
          )
        )
      ),

      error && h("div", { className: "text-xs text-red-400 bg-red-500/10 rounded p-2" }, "\u26a0 " + error),

      // State machine viz
      status && h(Card, null,
        h(CardHeader, { className: "pb-2" },
          h(CardTitle, { className: "text-sm" }, "State Machine")
        ),
        h(CardContent, null,
          h(StateMachineViz, { state: status.state }),
          h("div", { className: "mt-3" },
            h(Badge, {
              variant: "outline",
              className: cn("text-sm", STATE_COLORS[status.state] || "")
            }, STATE_LABELS[status.state] || status.state)
          )
        )
      ),

      // Timer bars
      status && h(Card, null,
        h(CardHeader, { className: "pb-2" },
          h(CardTitle, { className: "text-sm" }, "Timers")
        ),
        h(CardContent, { className: "space-y-3" },
          h(TimerBar, { label: "Idle (T1)", elapsed: monitor.last_ago_seconds || 0, total: thresholds.T1_idle || 300, color: "bg-amber-500" }),
          h(TimerBar, { label: "Soak (T3)", elapsed: monitor.soak_elapsed || 0, total: thresholds.T3_soak || 3000, color: "bg-blue-500" }),
          h(TimerBar, { label: "Hypnagogic (T4)", elapsed: monitor.hypnagogic_elapsed || 0, total: thresholds.T4_hypnagogic || 120, color: "bg-purple-500" }),
          h("div", { className: "flex items-center justify-between text-xs pt-2 border-t border-border/20" },
            h("span", { className: "text-muted-foreground" }, "Dreams today"),
            h("span", { className: "font-mono" }, (status.dreams_today || 0) + " / " + (status.max_dreams || 2))
          )
        )
      ),

      // Tabs
      h("div", { className: "flex gap-1 border-b border-border/30 pb-2" },
        h(Button, { variant: activeTab === "status" ? "default" : "ghost", size: "sm",
          onClick: function () { setActiveTab("status"); } }, "Status"),
        h(Button, { variant: activeTab === "journal" ? "default" : "ghost", size: "sm",
          onClick: function () { setActiveTab("journal"); } },
          h(BookIcon, { className: "w-3.5 h-3.5 mr-1.5" }),
          "Journal (" + journal.length + ")"
        ),
        h(Button, { variant: activeTab === "config" ? "default" : "ghost", size: "sm",
          onClick: function () { setActiveTab("config"); } }, "Config")
      ),

      // Status tab
      activeTab === "status" && h("div", { className: "space-y-4" },
        h(Card, null,
          h(CardHeader, { className: "pb-2" },
            h(CardTitle, { className: "text-sm" }, "Recent Transitions")
          ),
          h(CardContent, null,
            h(TransitionLog, { transitions: status ? status.transitions : [] })
          )
        ),
        h(Card, null,
          h(CardHeader, { className: "pb-2" },
            h(CardTitle, { className: "text-sm" }, "Raw Status")
          ),
          h(CardContent, null,
            h("pre", { className: "text-xs text-muted-foreground overflow-x-auto max-h-40" },
              JSON.stringify(status, null, 2))
          )
        ),
        h("div", { className: "flex gap-2" },
          h(Button, { variant: "outline", size: "sm", onClick: handleReset }, "Reset State")
        )
      ),

      // Journal tab
      activeTab === "journal" && (journal.length === 0
        ? h("div", { className: "text-center py-12 text-muted-foreground" },
            h(MoonIcon, { className: "w-8 h-8 mx-auto mb-3 opacity-30" }),
            h("p", { className: "text-sm" }, "No dream sessions yet."),
            h("p", { className: "text-xs mt-1" }, "Dreams appear here after sustained dormancy.")
          )
        : h("div", { className: "space-y-3" },
            journal.map(function (entry) {
              return h(DreamSessionCard, { key: (entry.session_id || "") + (entry.started_at || ""), entry: entry });
            })
          )
      ),

      // Config tab
      activeTab === "config" && h(Card, null,
        h(CardHeader, { className: "pb-2" },
          h(CardTitle, { className: "text-sm" }, "Configuration")
        ),
        h(CardContent, null,
          h(ConfigEditor, { config: config, onSave: loadData })
        )
      ),

      h("div", { ref: bottomRef })
    );
  }

  // --- Register plugin ---
  if (window.__HERMES_PLUGINS__) {
    window.__HERMES_PLUGINS__.register("hermes-dream-engine", DreamEnginePage);
  }
})();
