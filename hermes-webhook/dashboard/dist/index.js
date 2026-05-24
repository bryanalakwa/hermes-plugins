/**
 * Inter-Agent Webhook — Dashboard Plugin v2.0
 *
 * Manage agent connections, send messages, view message history.
 * Calls the plugin backend at /api/plugins/webhook/.
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
  const { Card, CardContent, CardHeader, CardTitle, Badge, Button, Input, Label } = SDK.components;
  const { cn, timeAgo } = SDK.utils;

  const API_BASE = "/api/plugins/hermes-webhook";

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
  function SendIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, props || {}),
      h("path", { d: "m22 2-7 20-4-9-9-4Z" }), h("path", { d: "M22 2 11 13" }));
  }
  function PlusIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("path", { d: "M5 12h14" }), h("path", { d: "M12 5v14" }));
  }
  function TrashIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("path", { d: "M3 6h18" }), h("path", { d: "M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" }), h("path", { d: "M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" }));
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
  function XIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("path", { d: "M18 6 6 18" }), h("path", { d: "m6 6 12 12" }));
  }
  function ZapIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("polygon", { points: "13 2 3 14 12 14 11 22 21 10 12 10 13 2" }));
  }
  function BellIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("path", { d: "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" }),
      h("path", { d: "M10.3 21a1.94 1.94 0 0 0 3.4 0" }));
  }

  // --- Add Agent Modal ---
  function AddAgentModal({ onSave, onClose }) {
    const [nick, setNick] = useState("");
    const [url, setUrl] = useState("");
    const [secret, setSecret] = useState("");
    const [routePing, setRoutePing] = useState("agent-ping");
    const [routeNotify, setRouteNotify] = useState("agent-notify");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    const handleSave = useCallback(function () {
      if (!nick.trim() || !url.trim() || !secret.trim()) {
        setError("All fields are required");
        return;
      }
      setSaving(true);
      setError(null);
      api("/agents", {
        method: "POST",
        body: JSON.stringify({ nick: nick.trim(), url: url.trim(), secret: secret.trim(), route_ping: routePing, route_notify: routeNotify }),
      })
        .then(function () { onSave(); })
        .catch(function (err) { setError(err.message); })
        .finally(function () { setSaving(false); });
    }, [nick, url, secret, routePing, routeNotify, onSave]);

    return h("div", { className: "fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4", onClick: function (e) { if (e.target === e.currentTarget) onClose(); } },
      h(Card, { className: "max-w-lg w-full" },
        h(CardHeader, null,
          h("div", { className: "flex items-center justify-between" },
            h("div", { className: "flex items-center gap-2" },
              h(PlusIcon, { className: "w-5 h-5 text-emerald-400" }),
              h(CardTitle, null, "Add Agent")
            ),
            h(Button, { variant: "ghost", size: "sm", onClick: onClose }, "✕")
          )
        ),
        h(CardContent, { className: "space-y-4" },
          error && h("div", { className: "text-xs text-red-400 bg-red-500/10 rounded p-2" }, "⚠ " + error),

          h("div", null,
            h(Label, null, "Nickname"),
            h(Input, { placeholder: "e.g., remy, atlas", value: nick, onChange: function (e) { setNick(e.target.value); } })
          ),
          h("div", null,
            h(Label, null, "Tailscale Funnel URL"),
            h(Input, { placeholder: "https://agent.tailXXXXX.ts.net", value: url, onChange: function (e) { setUrl(e.target.value); } })
          ),
          h("div", null,
            h(Label, null, "Webhook Secret"),
            h(Input, { type: "password", placeholder: "64-char hex secret from the receiver", value: secret, onChange: function (e) { setSecret(e.target.value); } })
          ),
          h("div", { className: "grid grid-cols-2 gap-3" },
            h("div", null,
              h(Label, null, "Ping Route"),
              h(Input, { value: routePing, onChange: function (e) { setRoutePing(e.target.value); } })
            ),
            h("div", null,
              h(Label, null, "Notify Route"),
              h(Input, { value: routeNotify, onChange: function (e) { setRouteNotify(e.target.value); } })
            )
          ),

          h("div", { className: "flex justify-end gap-2 pt-2" },
            h(Button, { variant: "outline", onClick: onClose }, "Cancel"),
            h(Button, { onClick: handleSave, disabled: saving },
              saving ? "Saving..." : "Add Agent"
            )
          )
        )
      )
    );
  }

  // --- Send Message Modal ---
  function SendMessageModal({ agent, onSend, onClose }) {
    const [mode, setMode] = useState("ping");
    const [message, setMessage] = useState("");
    const [sending, setSending] = useState(false);
    const [result, setResult] = useState(null);

    const handleSend = useCallback(function () {
      if (!message.trim()) return;
      setSending(true);
      setResult(null);
      api("/send", {
        method: "POST",
        body: JSON.stringify({ nick: agent.nick, mode: mode, message: message.trim() }),
      })
        .then(function (r) { setResult({ ok: true, data: r }); setMessage(""); })
        .catch(function (err) { setResult({ ok: false, error: err.message }); })
        .finally(function () { setSending(false); });
    }, [agent.nick, mode, message]);

    return h("div", { className: "fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4", onClick: function (e) { if (e.target === e.currentTarget) onClose(); } },
      h(Card, { className: "max-w-lg w-full" },
        h(CardHeader, null,
          h("div", { className: "flex items-center justify-between" },
            h("div", { className: "flex items-center gap-2" },
              h(SendIcon, { className: "w-5 h-5 text-blue-400" }),
              h(CardTitle, null, "Send to " + agent.nick)
            ),
            h(Button, { variant: "ghost", size: "sm", onClick: onClose }, "✕")
          )
        ),
        h(CardContent, { className: "space-y-4" },
          // Mode toggle
          h("div", { className: "flex gap-2" },
            h(Button, { variant: mode === "ping" ? "default" : "outline", size: "sm", onClick: function () { setMode("ping"); } },
              h(ZapIcon, { className: "w-3.5 h-3.5 mr-1.5" }), "AI Ping"
            ),
            h(Button, { variant: mode === "notify" ? "default" : "outline", size: "sm", onClick: function () { setMode("notify"); } },
              h(BellIcon, { className: "w-3.5 h-3.5 mr-1.5" }), "Direct Notify"
            )
          ),
          h("div", { className: "text-xs text-muted-foreground" },
            mode === "ping"
              ? "Agent will read, reason, and compose a response (costs tokens)"
              : "Message forwarded verbatim to agent's Telegram (zero token cost)"
          ),

          h("div", null,
            h(Label, null, "Message"),
            h("textarea", {
              className: "w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-y min-h-[100px]",
              placeholder: "Type your message...",
              value: message,
              onChange: function (e) { setMessage(e.target.value); },
              rows: 4,
            })
          ),

          result && h("div", { className: cn("text-xs rounded p-2", result.ok ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400") },
            result.ok
              ? h("div", { className: "flex items-center gap-1.5" }, h(CheckIcon, null), "Delivered (HTTP " + (result.data && result.data.status || "?") + ")")
              : h("div", { className: "flex items-center gap-1.5" }, h(XIcon, null), "Failed: " + result.error)
          ),

          h("div", { className: "flex justify-end gap-2 pt-2" },
            h(Button, { variant: "outline", onClick: onClose }, "Close"),
            h(Button, { onClick: handleSend, disabled: sending || !message.trim() },
              sending ? "Sending..." : "Send"
            )
          )
        )
      )
    );
  }

  // --- Agent Card ---
  function AgentCard({ agent, onSend, onDelete, onTest }) {
    const [testing, setTesting] = useState(false);

    const handleTest = useCallback(function () {
      setTesting(true);
      api("/test/" + agent.nick, { method: "POST" })
        .catch(function () {})
        .finally(function () { setTesting(false); });
    }, [agent.nick]);

    return h(Card, null,
      h(CardContent, { className: "pt-4" },
        h("div", { className: "flex items-start justify-between gap-3" },
          h("div", { className: "flex-1 min-w-0" },
            h("div", { className: "flex items-center gap-2 mb-1" },
              h("span", { className: "font-semibold" }, agent.nick),
              agent.has_secret
                ? h(Badge, { variant: "outline", className: "text-xs text-emerald-400 border-emerald-500/30" }, "configured")
                : h(Badge, { variant: "outline", className: "text-xs text-amber-400 border-amber-500/30" }, "no secret")
            ),
            h("div", { className: "text-xs text-muted-foreground truncate" }, agent.url),
            h("div", { className: "flex gap-2 mt-1 text-xs text-muted-foreground" },
              h("span", null, "ping: " + agent.route_ping),
              h("span", null, "notify: " + agent.route_notify)
            )
          ),
          h("div", { className: "flex items-center gap-1.5 shrink-0" },
            h(Button, { variant: "ghost", size: "sm", onClick: handleTest, disabled: testing, title: "Test connection" },
              h(RefreshIcon, { className: cn("w-3.5 h-3.5", testing && "animate-spin") })
            ),
            h(Button, { variant: "ghost", size: "sm", onClick: function () { onSend(agent); }, title: "Send message" },
              h(SendIcon, { className: "w-3.5 h-3.5" })
            ),
            h(Button, { variant: "ghost", size: "sm", onClick: function () { onDelete(agent.nick); }, title: "Delete" },
              h(TrashIcon, { className: "w-3.5 h-3.5 text-red-400" })
            )
          )
        )
      )
    );
  }

  // --- Message History Item ---
  function HistoryItem({ msg }) {
    const isOut = msg.direction === "out";
    const isSuccess = msg.status === "delivered";

    return h("div", { className: "flex items-start gap-3 py-2 border-b border-border/30 last:border-0" },
      h("div", { className: cn("w-2 h-2 rounded-full mt-1.5 shrink-0", isSuccess ? "bg-emerald-400" : "bg-red-400") }),
      h("div", { className: "flex-1 min-w-0" },
        h("div", { className: "flex items-center gap-2 text-xs" },
          h("span", { className: "font-medium" }, isOut ? "→ " + msg.nick : msg.nick + " →"),
          h("span", { className: "text-muted-foreground" }, msg.timestamp),
          h(Badge, { variant: "outline", className: "text-xs" }, msg.mode),
          msg.is_test && h(Badge, { variant: "outline", className: "text-xs text-amber-400" }, "test")
        ),
        h("div", { className: "text-sm mt-0.5 truncate" }, msg.message),
        !isSuccess && h("div", { className: "text-xs text-red-400 mt-0.5" }, "Failed (HTTP " + (msg.http_status || "?") + ")")
      )
    );
  }

  // --- Main Page ---
  function AgentsPage() {
    const [agents, setAgents] = useState([]);
    const [history, setHistory] = useState([]);
    const [identity, setIdentity] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showAdd, setShowAdd] = useState(false);
    const [sendingTo, setSendingTo] = useState(null);
    const [activeTab, setActiveTab] = useState("agents"); // "agents" | "history"

    const loadData = useCallback(function () {
      setLoading(true);
      setError(null);
      Promise.all([
        api("/agents").catch(function () { return null; }),
        api("/history?limit=50").catch(function () { return null; }),
        api("/identity").catch(function () { return null; }),
      ])
        .then(function (results) {
          if (results[0]) setAgents(results[0].agents || []);
          if (results[1]) setHistory(results[1].messages || []);
          if (results[2]) setIdentity(results[2]);
          if (!results[0] && !results[1]) setError("Failed to load data");
        })
        .catch(function (err) { setError(err.message); })
        .finally(function () { setLoading(false); });
    }, []);

    useEffect(function () { loadData(); }, [loadData]);

    const handleDelete = useCallback(function (nick) {
      if (!confirm("Delete agent '" + nick + "'?")) return;
      api("/agents/" + nick, { method: "DELETE" })
        .then(function () { loadData(); })
        .catch(function (err) { setError(err.message); });
    }, [loadData]);

    if (loading) {
      return h("div", { className: "flex items-center justify-center py-12" },
        h("div", { className: "text-muted-foreground flex items-center gap-2" },
          h(SendIcon, { className: "w-5 h-5 animate-pulse" }), "Loading agents..."
        )
      );
    }

    return h("div", { className: "space-y-6" },
      // Header
      h("div", { className: "flex items-center justify-between" },
        h("div", { className: "flex items-center gap-3" },
          h("div", { className: "p-2 rounded-lg bg-blue-500/10" },
            h(SendIcon, { className: "w-6 h-6 text-blue-400" })
          ),
          h("div", null,
            h("h2", { className: "text-lg font-semibold" }, "Agent Network"),
            h("p", { className: "text-xs text-muted-foreground" },
              identity ? (identity.my_name + " • " + agents.length + " agent" + (agents.length !== 1 ? "s" : "")) : "Inter-agent webhook communication"
            )
          )
        ),
        h("div", { className: "flex items-center gap-2" },
          h(Button, { variant: "ghost", size: "sm", onClick: loadData }, h(RefreshIcon, { className: "w-3.5 h-3.5" })),
          h(Button, { size: "sm", onClick: function () { setShowAdd(true); } },
            h(PlusIcon, { className: "w-3.5 h-3.5 mr-1.5" }), "Add Agent"
          )
        )
      ),

      // Identity / status bar
      identity && h("div", { className: "flex items-center gap-3 text-xs" },
        h(Badge, { variant: identity.webhook_enabled ? "default" : "outline", className: identity.webhook_enabled ? "text-emerald-400" : "text-amber-400" },
          identity.webhook_enabled ? "● Webhook listening on port " + identity.webhook_port : "○ Webhook not enabled"
        ),
        identity.routes.length > 0 && h("span", { className: "text-muted-foreground" },
          "Routes: " + identity.routes.join(", ")
        )
      ),

      // Tabs
      h("div", { className: "flex gap-1 border-b border-border/30 pb-2" },
        h(Button, { variant: activeTab === "agents" ? "default" : "ghost", size: "sm", onClick: function () { setActiveTab("agents"); } },
          "Agents (" + agents.length + ")"
        ),
        h(Button, { variant: activeTab === "history" ? "default" : "ghost", size: "sm", onClick: function () { setActiveTab("history"); } },
          "History (" + history.length + ")"
        )
      ),

      error && h("div", { className: "text-xs text-red-400 bg-red-500/10 rounded p-2" }, "⚠ " + error),

      // Agents tab
      activeTab === "agents" && (
        agents.length === 0
          ? h("div", { className: "text-center py-12 text-muted-foreground" },
              h(SendIcon, { className: "w-8 h-8 mx-auto mb-3 opacity-30" }),
              h("p", { className: "text-sm" }, "No agents configured."),
              h("p", { className: "text-xs mt-1" }, "Add an agent to start sending inter-agent messages.")
            )
          : h("div", { className: "space-y-3" },
              agents.map(function (agent) {
                return h(AgentCard, {
                  key: agent.nick,
                  agent: agent,
                  onSend: setSendingTo,
                  onDelete: handleDelete,
                  onTest: function () { api("/test/" + agent.nick, { method: "POST" }).then(function () { loadData(); }); },
                });
              })
            )
      ),

      // History tab
      activeTab === "history" && h("div", null,
        history.length === 0
          ? h("div", { className: "text-center py-12 text-muted-foreground" },
              h("p", { className: "text-sm" }, "No messages yet.")
            )
          : h("div", null,
              h("div", { className: "flex justify-end mb-2" },
                h(Button, { variant: "ghost", size: "sm", onClick: function () {
                  api("/history", { method: "DELETE" }).then(function () { loadData(); });
                }}, "Clear history")
              ),
              history.map(function (msg) {
                return h(HistoryItem, { key: msg.id, msg: msg });
              })
            )
      ),

      // Modals
      showAdd && h(AddAgentModal, {
        onSave: function () { setShowAdd(false); loadData(); },
        onClose: function () { setShowAdd(false); },
      }),
      sendingTo && h(SendMessageModal, {
        agent: sendingTo,
        onSend: function () { loadData(); },
        onClose: function () { setSendingTo(null); },
      })
    );
  }

  // --- Register plugin ---
  if (window.__HERMES_PLUGINS__) {
    window.__HERMES_PLUGINS__.register("hermes-webhook", AgentsPage);
  }
})();
