/**
 * Dream Engine — Dashboard Plugin v1.2
 *
 * Blog-style dream journal with modal detail view, rich LLM output display,
 * and manual controls. Calls the plugin backend at
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
  var Card = SDK.components.Card;
  var CardContent = SDK.components.CardContent;
  var CardHeader = SDK.components.CardHeader;
  var CardTitle = SDK.components.CardTitle;
  var Badge = SDK.components.Badge;
  var Button = SDK.components.Button;
  var Input = SDK.components.Input;
  var Label = SDK.components.Label;
  var cn = SDK.utils.cn;

  var API_BASE = "/api/plugins/hermes-dream-engine";

  var ALGO_DEFAULTS = {
    idle_threshold_seconds: 300,
    dormant_threshold_seconds: 1800,
    soak_threshold_seconds: 3000,
    hypnagogic_duration_seconds: 120,
    max_dreams_per_day: 2,
    consolidation_memory_count: 150,
    invention_sample_size: 10
  };

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
  function MoonIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" }));
  }
  function ZapIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("polygon", { points: "13 2 3 14 12 14 11 22 21 10 12 10 13 2" }));
  }
  function RefreshIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" }),
      h("path", { d: "M21 3v5h-5" }),
      h("path", { d: "M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" }),
      h("path", { d: "M8 16H3v5" }));
  }
  function BrainIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" }),
      h("path", { d: "M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" }));
  }
  function BookIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" }));
  }
  function XIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "M18 6 6 18" }), h("path", { d: "m6 6 12 12" }));
  }
  function TrashIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "M3 6h18" }), h("path", { d: "M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" }), h("path", { d: "M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" }));
  }
  function ChevronIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "m6 9 6 6 6-6" }));
  }
  function LightbulbIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5" }),
      h("path", { d: "M9 18h6" }), h("path", { d: "M10 22h4" }));
  }
  function ShieldIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" }));
  }
  function SparkleIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" }));
  }
  function AlertIcon(p) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, p||{}),
      h("path", { d: "m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" }),
      h("path", { d: "M12 9v4" }), h("path", { d: "M12 17h.01" }));
  }

  var STATE_COLORS = {
    active: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
    idle: "text-amber-400 border-amber-500/30 bg-amber-500/10",
    dormant: "text-blue-400 border-blue-500/30 bg-blue-500/10",
    hypnagogic: "text-purple-400 border-purple-500/30 bg-purple-500/10",
    dreaming: "text-pink-400 border-pink-500/30 bg-pink-500/10"
  };
  var STATE_LABELS = {
    active: "Active", idle: "Idle", dormant: "Dormant",
    hypnagogic: "Hypnagogic", dreaming: "Dreaming"
  };
  var PHASE_LABELS = {
    consolidation: "Memory Consolidation",
    problem_reevaluation: "Problem Re-evaluation",
    invention: "Free Association & Invention",
    dream_log: "Dream Log & Integration"
  };
  var PHASE_ICONS = {
    consolidation: ShieldIcon,
    problem_reevaluation: AlertIcon,
    invention: SparkleIcon,
    dream_log: LightbulbIcon
  };

  function fmtDuration(seconds) {
    if (seconds == null || isNaN(seconds)) return "\u2014";
    if (seconds < 60) return Math.round(seconds) + "s";
    if (seconds < 3600) return Math.round(seconds / 60) + "m " + Math.round(seconds % 60) + "s";
    return Math.round(seconds / 3600) + "h " + Math.round((seconds % 3600) / 60) + "m";
  }

  // Generate a human-readable topic title from phase outputs
  function generateEntryTitle(entry) {
    var outputs = entry.phase_outputs || {};
    var dreamLog = outputs.dream_log || {};

    // Best: use synthesis — it's a paragraph about the dream's meaning
    if (dreamLog.synthesis && dreamLog.synthesis.length > 15) {
      return topicFromText(dreamLog.synthesis);
    }
    // Next: key_insight — should be a single clear statement
    if (dreamLog.key_insight && dreamLog.key_insight.length > 15) {
      return topicFromText(dreamLog.key_insight);
    }

    // Fallback to invention phase — use the highest-significance idea
    var inv = outputs.invention || {};
    var ideas = inv.novel_ideas || [];
    // Sort by significance if available, pick the best
    var bestIdea = null;
    var bestSig = 0;
    for (var i = 0; i < ideas.length; i++) {
      var idea = ideas[i];
      var text = typeof idea === "string" ? idea : (idea.idea || "");
      var sig = (idea && typeof idea === "object" && idea.significance) ? idea.significance : 0;
      if (text && sig >= bestSig) {
        bestSig = sig;
        bestIdea = text;
      }
    }
    if (bestIdea) {
      return topicFromText(bestIdea);
    }

    // Fallback to dream_log action plan — escalate items are most interesting
    var actionPlan = dreamLog.action_plan || {};
    var escalate = actionPlan.escalate || [];
    if (escalate.length > 0) {
      var firstEsc = escalate[0];
      var escText = typeof firstEsc === "string" ? firstEsc : (firstEsc.item || "");
      if (escText && escText.length > 10) {
        return "Escalation: " + topicFromText(escText);
      }
    }

    // Fallback to consolidation — use a key connection insight
    var cons = outputs.consolidation || {};
    var connections = cons.connections || [];
    if (connections.length > 0) {
      var firstConn = connections[0];
      var insight = (firstConn && typeof firstConn === "object") ? firstConn.insight : "";
      if (insight && insight.length > 10) {
        return topicFromText(insight);
      }
    }

    // Last resort
    return "Dream Session";
  }

  // Extract a short topic title from a paragraph of text
  function topicFromText(text) {
    if (!text) return "Dream Session";
    // Clean up markdown artifacts and brackets
    text = text.replace(/[\[\]{}()]/g, "").trim();

    // Skip common LLM filler openings to get to the meaningful content
    var fillerPatterns = [
      /^this dream session\s*/i,
      /^in this dream\s*/i,
      /^the (key )?insight from this\s*/i,
      /^the most important (thing|insight|takeaway)\s*/i,
      /^during this dream\s*/i,
      /^after (reviewing|consolidating|examining)\s*/i,
      /^across all phases\s*/i,
      /^the (main|central|primary|core) (theme|idea|takeaway|insight)\s*/i,
      /^dreaming about\s*/i,
      /^consolidated\s*/i,
      /^brief summary\s*:?\s*/i,
    ];
    for (var f = 0; f < fillerPatterns.length; f++) {
      text = text.replace(fillerPatterns[f], "");
    }
    text = text.trim();

    // Take first sentence (end of first real clause)
    var firstSentence = text.split(/[.!?]/)[0].trim();
    // Also try to stop at semicolons and em-dashes for cleaner breaks
    firstSentence = firstSentence.split(/[;—–]/)[0].trim();

    var words = firstSentence.split(/\s+/);
    // Skip leading connector words
    var connectors = {"and":1,"but":1,"so":1,"yet":1,"or":1,"nor":1,"for":1,"also":1,"then":1,"thus":1,"hence":1,"since":1,"because":1,"although":1,"however":1,"moreover":1,"furthermore":1,"meanwhile":1,"still":1,"already":1,"just":1,"even":1,"now":1,"here":1,"there":1,"this":1,"that":1,"these":1,"those":1,"with":1,"from":1,"into":1,"through":1,"between":1,"after":1,"before":1,"during":1,"about":1,"against":1,"among":1,"within":1,"without":1,"across":1,"along":1,"around":1,"under":1,"over":1};
    var startIdx = 0;
    while (startIdx < words.length && connectors[words[startIdx].toLowerCase()]) {
      startIdx++;
    }
    if (startIdx > 0 && startIdx < words.length) {
      words = words.slice(startIdx);
    }

    // Take 4-7 words for a punchy title (was 8, which was too long)
    var title = words.slice(0, Math.min(7, words.length)).join(" ");

    // If the title is too short (< 3 words), the source text was probably garbage
    if (words.length < 3) {
      // Try the full first sentence instead
      title = firstSentence;
    }

    if (title.length > 65) title = title.substring(0, 62) + "...";
    if (title.length < 2) return "Dream Session";

    // Capitalize first letter
    title = title.charAt(0).toUpperCase() + title.slice(1);
    return title;
  }

  // Generate a brief summary from phase outputs
  function generateEntrySummary(entry) {
    var outputs = entry.phase_outputs || {};
    var parts = [];
    if (outputs.consolidation && outputs.consolidation.summary) {
      parts.push(outputs.consolidation.summary);
    }
    if (outputs.problem_reevaluation && outputs.problem_reevaluation.summary) {
      parts.push(outputs.problem_reevaluation.summary);
    }
    if (parts.length > 0) return parts.join(" | ");
    return entry.summary || "No summary available.";
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

  // --- Phase Detail Section (for modal) ---
  function PhaseSection(props) {
    var phase = props.phase;
    var output = props.output;
    var Icon = PHASE_ICONS[phase] || LightbulbIcon;
    var label = PHASE_LABELS[phase] || phase;
    var expandedState = useState(false);
    var isExpanded = expandedState[0];
    var setExpanded = expandedState[1];

    // Collect all meaningful content from this phase
    var sections = [];

    if (output.summary) sections.push({ title: "Summary", content: output.summary, type: "text" });
    if (output.key_insight) sections.push({ title: "Key Insight", content: output.key_insight, type: "text" });
    if (output.synthesis) sections.push({ title: "Synthesis", content: output.synthesis, type: "text" });
    // Handle LLM typo: "synmthesis" instead of "synthesis"
    if (!output.synthesis && output.synmthesis) sections.push({ title: "Synthesis", content: output.synmthesis, type: "text" });

    if (output.contradictions && output.contradictions.length > 0) {
      sections.push({
        title: "Contradictions Found (" + output.contradictions.length + ")",
        items: output.contradictions.map(function (c) {
          return (c.fact_a || "").substring(0, 150) + "\n\u2192 vs \u2192\n" + (c.fact_b || "").substring(0, 150) + "\n\u21D2 Resolution: " + (c.resolution || "none");
        }),
        type: "items"
      });
    }

    if (output.connections && output.connections.length > 0) {
      sections.push({
        title: "Connections (" + output.connections.length + ")",
        items: output.connections.map(function (c) { return c.insight || JSON.stringify(c); }),
        type: "items"
      });
    }

    if (output.reconsidered && output.reconsidered.length > 0) {
      sections.push({
        title: "Reconsidered Problems (" + output.reconsidered.length + ")",
        items: output.reconsidered.map(function (r) {
          return (r.problem || "?") + "\n\u2192 " + (r.new_perspective || "") + "\n\u21D2 " + (r.resolution || "");
        }),
        type: "items"
      });
    }

    if (output.creative_solutions && output.creative_solutions.length > 0) {
      sections.push({
        title: "Creative Solutions",
        items: output.creative_solutions.map(function (s) {
          return typeof s === "string" ? s : (s.item || s.idea || JSON.stringify(s));
        }),
        type: "items"
      });
    }

    if (output.connections_made && output.connections_made.length > 0) {
      sections.push({
        title: "Unexpected Connections (" + output.connections_made.length + ")",
        items: output.connections_made.map(function (c) {
          return (c.item_a || "").substring(0, 120) + "\n\u2261 " + (c.unexpected_link || "") + "\n" + ((c.item_b || "").substring(0, 120));
        }),
        type: "items"
      });
    }

    if (output.novel_ideas && output.novel_ideas.length > 0) {
      sections.push({
        title: "Novel Ideas (" + output.novel_ideas.length + ")",
        items: output.novel_ideas.map(function (idea) {
          var s = typeof idea === "string" ? idea : (idea.idea || "");
          if (idea && typeof idea === "object") {
            if (idea.potential) s += "\n[Potential: " + idea.potential + "]";
            if (idea.notes) s += "\n" + idea.notes;
          }
          return s;
        }),
        type: "items"
      });
    }

    if (output.problems_reviewed && output.problems_reviewed.length > 0) {
      sections.push({
        title: "Problems Reviewed",
        items: output.problems_reviewed,
        type: "items"
      });
    }

    if (output.let_go && output.let_go.length > 0) {
      sections.push({
        title: "Decided to Let Go",
        items: output.let_go,
        type: "items"
      });
    }

    // Action plan (dream_log phase) — priority-coded sections
    var actionPlan = output.action_plan || {};
    var solveItems = actionPlan.solve_it || [];
    var escalateItems = actionPlan.escalate || [];
    var deferItems = actionPlan.defer || [];
    if (solveItems.length > 0) {
      sections.push({
        title: "Solve It (autonomous) " + solveItems.length,
        items: solveItems.map(function (item) {
          return typeof item === "string" ? item : (item.item || JSON.stringify(item));
        }),
        type: "items",
        accent: "green"
      });
    }
    if (escalateItems.length > 0) {
      sections.push({
        title: "Escalate (your attention needed) " + escalateItems.length,
        items: escalateItems.map(function (item) {
          return typeof item === "string" ? item : (item.item || JSON.stringify(item));
        }),
        type: "items",
        accent: "red"
      });
    }
    if (deferItems.length > 0) {
      sections.push({
        title: "Defer (future dreams) " + deferItems.length,
        items: deferItems.map(function (item) {
          return typeof item === "string" ? item : (item.item || JSON.stringify(item));
        }),
        type: "items",
        accent: "gray"
      });
    }

    // Final thoughts (dream_log phase)
    if (output.final_thoughts) {
      sections.push({ title: "Final Thoughts", content: output.final_thoughts, type: "text" });
    }

    if (sections.length === 0) return null;

    return h("div", { className: "mb-4" },
      h("button", {
        onClick: function () { setExpanded(!isExpanded); },
        className: "flex items-center gap-2 w-full text-left py-2 px-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
      },
        h(Icon, { className: "w-4 h-4 text-purple-400 shrink-0" }),
        h("span", { className: "text-sm font-medium flex-1" }, label),
        h(ChevronIcon, { className: cn("w-4 h-4 transition-transform", isExpanded && "rotate-180") })
      ),
      isExpanded && h("div", { className: "mt-2 pl-4 space-y-3" },
        sections.map(function (section, idx) {
          var accentClass = "";
          var accentBorder = "";
          if (section.accent === "green") { accentClass = "text-emerald-400"; accentBorder = "border-emerald-500/30"; }
          if (section.accent === "red") { accentClass = "text-amber-400"; accentBorder = "border-amber-500/30 bg-amber-500/5"; }
          if (section.accent === "gray") { accentClass = "text-gray-400"; accentBorder = "border-gray-500/30"; }
          var itemBgClass = "";
          if (section.accent === "green") itemBgClass = "dream-phase-solve";
          if (section.accent === "red") itemBgClass = "dream-phase-escalate";
          if (section.accent === "gray") itemBgClass = "dream-phase-defer";
          return h("div", { key: idx },
            h("div", { className: cn("text-[10px] uppercase tracking-wider font-medium mb-1", accentClass || "text-muted-foreground") }, section.title),
            section.type === "text"
              ? h("p", { className: "text-xs leading-relaxed whitespace-pre-wrap text-gray-200" }, section.content)
              : h("div", { className: "space-y-2" },
                  section.items.map(function (item, i) {
                    return h("div", { key: i, className: cn("text-xs rounded-md p-2.5 whitespace-pre-wrap leading-relaxed border", section.accent ? itemBgClass : "bg-white/[0.04] text-gray-300 border-white/[0.06]", section.accent ? "" : "") }, item);
                  })
                )
          );
        })
      )
    );
  }

  // --- Dream Detail Modal ---
  function DreamDetailModal(props) {
    var entry = props.entry;
    var onClose = props.onClose;
    if (!entry) return null;

    var phaseOutputs = entry.phase_outputs || {};
    var phases = entry.phases_run || [];
    var allSections = [];
    phases.forEach(function (phase) {
      if (phaseOutputs[phase]) {
        allSections.push({ phase: phase, output: phaseOutputs[phase] });
      }
    });

    var hasErrors = entry.errors && entry.errors.length > 0;
    var completed = entry.state_on_exit === "completed";

    // Close on Escape key
    useEffect(function () {
      var handler = function (e) { if (e.key === "Escape") onClose(); };
      document.addEventListener("keydown", handler);
      return function () { document.removeEventListener("keydown", handler); };
    }, [onClose]);

    return h("div", null,
      // Opaque backdrop — separate layer
      h("div", { className: "dream-modal-backdrop", onClick: onClose }),
      // Modal panel — separate layer, centered
      h("div", { className: "dream-modal-panel" },
        h("div", {
          className: "dream-modal-inner",
          onClick: function (e) { e.stopPropagation(); }
        },
          // Header
          h("div", { className: "dream-modal-header" },
            h("div", { className: "flex items-center gap-3" },
              h("div", { className: "p-2 rounded-lg bg-purple-500/10" },
                h(MoonIcon, { className: "w-5 h-5 text-purple-400" })),
              h("div", null,
                h("h2", { className: "text-base font-semibold text-gray-100" }, entry.hrr_title || generateEntryTitle(entry)),
                h("p", { className: "text-xs text-muted-foreground mt-0.5" },
                  entry.started_at || "\u2014",
                  " \u00b7 ", entry.memories_reviewed || 0, " memories reviewed",
                  " \u00b7 ", (entry.phases_run || []).length, " phases"
                )
              )
            ),
            h("button", {
              onClick: onClose,
              className: "p-2 rounded-lg hover:bg-white/10 transition-colors text-muted-foreground hover:text-white"
            }, h(XIcon, { className: "w-5 h-5" }))
          ),

          // Scrollable body — uses CSS class with min-height: 0 fix
          h("div", { className: "dream-modal-body" },
            // Status badge
            h("div", { className: "flex items-center gap-2 mb-4" },
              h(Badge, {
                variant: "outline",
                className: cn("text-xs",
                  completed && !hasErrors ? "text-emerald-400 border-emerald-500/30" :
                  hasErrors ? "text-amber-400 border-amber-500/30" :
                  "text-red-400 border-red-500/30"
                )
              }, entry.state_on_exit),
              entry.contradictions_found > 0 && h(Badge, { variant: "outline", className: "text-xs text-orange-400 border-orange-500/30" },
                entry.contradictions_found + " contradictions resolved")
            ),

            // Phase sections
            allSections.length > 0
              ? allSections.map(function (section) {
                  return h(PhaseSection, {
                    key: section.phase,
                    phase: section.phase,
                    output: section.output
                  });
                })
              : h("p", { className: "text-sm text-muted-foreground text-center py-8" }, "No phase output recorded."),

            // Errors
            hasErrors && h("div", { className: "mt-4 text-xs text-red-400 bg-red-500/10 rounded-lg p-3" },
              h("div", { className: "font-medium mb-1" }, "Errors:"),
              entry.errors.map(function (e, i) { return h("div", { key: i }, "  \u2022 " + e); })
            ),

            // Raw output for debugging
            h("details", { className: "mt-4" },
              h("summary", { className: "text-[10px] text-muted-foreground cursor-pointer" }, "Raw JSON Output"),
              h("pre", { className: "text-[10px] text-muted-foreground overflow-x-auto mt-1 bg-black/20 rounded p-2 max-h-40" },
                JSON.stringify(phaseOutputs, null, 2))
            )
          ),

          // Footer
          h("div", { className: "dream-modal-footer" },
            h("span", { className: "text-[10px] text-muted-foreground" }, "Session: " + (entry.session_id || "?")),
            h(Button, { variant: "outline", size: "sm", onClick: onClose }, "Close")
          )
        )
      )
    );
  }
// --- Dream Journal Entry (blog post card) ---
  function DreamJournalEntry(props) {
    var entry = props.entry;
    var onOpen = props.onOpen;
    var deletingState = useState(false);
    var isDeleting = deletingState[0];
    var setIsDeleting = deletingState[1];

    var handleDelete = function (e) {
      e.stopPropagation();
      if (!confirm("Delete dream session " + entry.session_id + "?")) return;
      setIsDeleting(true);
      api("/journal/" + entry.session_id, { method: "DELETE" })
        .then(function () { if (props.onDelete) props.onDelete(); })
        .catch(function () { setIsDeleting(false); });
    };

    var title = entry.hrr_title || generateEntryTitle(entry);
    var summary = generateEntrySummary(entry);
    var phaseOutputs = entry.phase_outputs || {};
    var insights = entry.insights || [];
    var ideas = entry.ideas || [];
    var phases = entry.phases_run || [];
    var completed = entry.state_on_exit === "completed";
    var hasErrors = entry.errors && entry.errors.length > 0;

    return h(Card, null,
      h(CardContent, { className: "pt-4" },
        // Clickable card — opens modal
        h("div", {
          onClick: function () { onOpen(entry); },
          className: "cursor-pointer group"
        },
          h("div", { className: "flex items-start justify-between gap-3" },
            h("div", { className: "flex-1 min-w-0" },
              // Date & meta line
              h("div", { className: "flex items-center gap-2 mb-1.5 text-[10px] text-muted-foreground" },
                h(MoonIcon, { className: "w-3 h-3" }),
                h("span", null, entry.started_at || "\u2014"),
                entry.ended_at && h("span", null, "\u2026" + entry.ended_at),
                h("span", { className: "text-muted-foreground/50" }, "|"),
                h("span", null, entry.memories_reviewed + " memories reviewed"),
                entry.contradictions_found > 0 && h("span", null, " | " + entry.contradictions_found + " contradictions"),
                h(Badge, {
                  variant: "outline",
                  className: cn("text-[10px] ml-1",
                    completed && !hasErrors ? "text-emerald-400 border-emerald-500/30" :
                    hasErrors ? "text-amber-400 border-amber-500/30" :
                    "text-red-400 border-red-500/30"
                  )
                }, entry.state_on_exit)
              ),
              // Title — human-readable topic
              h("h3", { className: "text-sm font-semibold text-gray-200 group-hover:text-purple-300 transition-colors" }, title),
              // Summary
              h("p", { className: "text-xs text-muted-foreground mt-1 line-clamp-2" }, summary),
              // Stats badges
              h("div", { className: "flex items-center gap-1.5 mt-2 flex-wrap" },
                insights.length > 0 && h(Badge, { variant: "outline", className: "text-[10px] text-blue-400" },
                  h(LightbulbIcon, { className: "w-3 h-3 mr-0.5" }), insights.length + " insights"),
                ideas.length > 0 && h(Badge, { variant: "outline", className: "text-[10px] text-purple-400" },
                  h(SparkleIcon, { className: "w-3 h-3 mr-0.5" }), ideas.length + " ideas"),
                phases.map(function (p) {
                  return h(Badge, { key: p, variant: "outline", className: "text-[10px]" }, PHASE_LABELS[p] || p);
                })
              )
            ),
            // Delete button
            h("div", { className: "flex items-center gap-1 shrink-0" },
              h(Button, { variant: "ghost", size: "sm", onClick: handleDelete, disabled: isDeleting, title: "Delete" },
                h(TrashIcon, { className: "w-3.5 h-3.5" }))
            )
          )
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
    var merged = Object.assign({}, ALGO_DEFAULTS, props.config || {});
    var localState = useState(merged);
    var local = localState[0];
    var setLocal = localState[1];
    var savingState = useState(false);
    var saving = savingState[0];
    var setSaving = savingState[1];

    var fields = [
      { key: "max_dreams_per_day", label: "Max dreams / day", hint: "Dream sessions per day. Default: 2", min: 1, max: 10 },
      { key: "idle_threshold_seconds", label: "T1 \u2014 Idle threshold (s)", hint: "Active \u2192 Idle. Default: 300 (5 min)", min: 60, max: 3600 },
      { key: "dormant_threshold_seconds", label: "T2 \u2014 Dormant threshold (s)", hint: "Idle \u2192 Dormant (cumulative). Default: 1800 (30 min)", min: 300, max: 7200 },
      { key: "soak_threshold_seconds", label: "T3 \u2014 Soak period (s)", hint: "Dormant soak before dream gate. Default: 3000 (5 min)", min: 600, max: 14400 },
      { key: "hypnagogic_duration_seconds", label: "T4 \u2014 Hypnagogic duration (s)", hint: "Pre-dream prep window. Default: 120 (2 min)", min: 30, max: 600 },
      { key: "consolidation_memory_count", label: "Memories to consolidate (N)", hint: "Phase 1: recent memories reviewed. Default: 150", min: 10, max: 500 },
      { key: "invention_sample_size", label: "Invention sample size (K)", hint: "Phase 3: random memories sampled. Default: 10", min: 3, max: 30 }
    ];

    var updateField = useCallback(function (key, value) {
      var next = Object.assign({}, local);
      next[key] = value;
      setLocal(next);
    }, [local]);

    return h("div", { className: "space-y-3" },
      fields.map(function (f) {
        return h("div", { key: f.key },
          h(Label, { className: "text-xs" }, f.label),
          h(Input, {
            type: "number",
            min: f.min,
            max: f.max,
            value: local[f.key],
            onChange: function (e) { updateField(f.key, parseInt(e.target.value) || ALGO_DEFAULTS[f.key]); },
            className: "h-8 text-xs"
          }),
          h("p", { className: "text-[10px] text-muted-foreground mt-0.5" }, f.hint)
        );
      }),
      h("div", { className: "flex items-center gap-2 pt-2" },
        h(Button, { size: "sm", onClick: function () {
          setSaving(true);
          api("/config", { method: "PUT", body: JSON.stringify(local) })
            .then(function () { setSaving(false); if (props.onSave) props.onSave(); })
            .catch(function () { setSaving(false); });
        }, disabled: saving }, saving ? "Saving..." : "Save Config"),
        h(Button, { variant: "outline", size: "sm", onClick: function () {
          setLocal(Object.assign({}, ALGO_DEFAULTS));
        } }, "Reset to Defaults")
      )
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
    var initialLoadState = useState(true);
    var initialLoad = initialLoadState[0];
    var setInitialLoad = initialLoadState[1];
    var errorState = useState(null);
    var error = errorState[0];
    var setError = errorState[1];
    var tabState = useState("status");
    var activeTab = tabState[0];
    var setActiveTab = tabState[1];
    var forcingState = useState(false);
    var forcing = forcingState[0];
    var setForcing = forcingState[1];
    // Modal state
    var modalEntryState = useState(null);
    var modalEntry = modalEntryState[0];
    var setModalEntry = modalEntryState[1];

    var loadData = useCallback(function () {
      setError(null);
      Promise.all([
        api("/status").catch(function () { return null; }),
        api("/journal?limit=50").catch(function () { return null; })
      ]).then(function (results) {
        if (results[0]) setStatus(results[0]);
        if (results[1]) setJournal(results[1].entries || []);
        if (!results[0] && !results[1]) setError("Failed to load data");
        if (results[0]) setInitialLoad(false);
      }).catch(function (err) {
        setError(err.message);
        setInitialLoad(false);
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

    if (initialLoad && !status) {
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
            h(MoonIcon, { className: "w-6 h-6 text-purple-400" })),
          h("div", null,
            h("h2", { className: "text-lg font-semibold" }, "Dream Engine"),
            h("p", { className: "text-xs text-muted-foreground" },
              "Event-driven sleep detection & memory consolidation")
          )
        ),
        h("div", { className: "flex items-center gap-2" },
          h(Button, { variant: "ghost", size: "sm", onClick: loadData, title: "Refresh" },
            h(RefreshIcon, { className: "w-3.5 h-3.5" })),
          h(Button, { variant: "outline", size: "sm", onClick: handleHeartbeat, title: "Send heartbeat \u2014 resets idle timers" },
            h(ZapIcon, { className: "w-3.5 h-3.5 mr-1" }), "Ping"),
          h(Button, { size: "sm", onClick: handleForceDream, disabled: forcing, title: "Force a dream session" },
            forcing ? "Dreaming..." : h(BrainIcon, { className: "w-3.5 h-3.5 mr-1" }),
            forcing ? "Dreaming..." : "Force Dream")
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
          "Journal (" + journal.length + ")"),
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

      // Journal tab (blog-style entries — click opens modal)
      activeTab === "journal" && (journal.length === 0
        ? h("div", { className: "text-center py-12 text-muted-foreground" },
            h(MoonIcon, { className: "w-8 h-8 mx-auto mb-3 opacity-30" }),
            h("p", { className: "text-sm" }, "No dream sessions yet."),
            h("p", { className: "text-xs mt-1" }, "Dreams appear here after sustained dormancy.")
          )
        : h("div", { className: "space-y-4" },
            journal.map(function (entry) {
              return h(DreamJournalEntry, {
                key: (entry.session_id || "") + (entry.started_at || ""),
                entry: entry,
                onOpen: setModalEntry,
                onDelete: loadData
              });
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

      // Modal
      modalEntry && h(DreamDetailModal, {
        entry: modalEntry,
        onClose: function () { setModalEntry(null); }
      })
    );
  }

  // --- Register plugin ---
  if (window.__HERMES_PLUGINS__) {
    window.__HERMES_PLUGINS__.register("hermes-dream-engine", DreamEnginePage);
  }
})();
