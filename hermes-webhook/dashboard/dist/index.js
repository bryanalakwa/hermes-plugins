/**
 * Inter-Agent Webhook — Dashboard Plugin v2.1
 *
 * Manage agent connections, send messages, view per-agent conversation history.
 * Calls the plugin backend at /api/plugins/webhook/.
 *
 * New in v2.1:
 *   - Conversations tab: per-agent chat threads with inbound + outbound messages
 *   - Chat-like conversation view with message bubbles
 *   - Send messages directly from the conversation view
 *
 * Plain IIFE, no build step. Uses window.__HERMES_PLUGIN_SDK__.
 */
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !window.__HERMES_PLUGINS__) return;

  const React = SDK.React;
  const h = React.createElement;
  const { useState, useEffect, useCallback, useRef } = SDK.hooks;
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
  function MessageCircleIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("path", { d: "M7.9 20A9 9 0 1 0 4 16.1L2 22Z" }));
  }
  function ChevronLeftIcon(props) {
    return h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
      h("path", { d: "m15 18-6-6 6-6" }));
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

  // --- Conversation List Item ---
  function ConversationItem({ conv, onClick }) {
    const isIncoming = conv.last_direction === "in";
    const preview = conv.last_message.length > 60
      ? conv.last_message.substring(0, 60) + "…"
      : conv.last_message;

    return h("div", {
      className: "flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 cursor-pointer border border-border/20 mb-2 transition-colors",
      onClick: function () { onClick(conv.nick); },
    },
      h("div", { className: "w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0" },
        h("span", { className: "text-sm font-bold text-blue-400" }, conv.nick.charAt(0).toUpperCase())
      ),
      h("div", { className: "flex-1 min-w-0" },
        h("div", { className: "flex items-center justify-between" },
          h("span", { className: "font-semibold text-sm" }, conv.nick),
          h("span", { className: "text-xs text-muted-foreground" }, conv.last_timestamp ? conv.last_timestamp.split(" ")[1] || conv.last_timestamp : "")
        ),
        h("div", { className: "text-xs text-muted-foreground truncate mt-0.5" },
          isIncoming ? "← " : "→ ",
          preview
        )
      ),
      h("div", { className: "text-xs text-muted-foreground shrink-0" },
        h(Badge, { variant: "outline", className: "text-xs" }, conv.count)
      )
    );
  }

  // --- Chat Bubble ---
  function ChatBubble({ msg }) {
    const isOut = msg.direction === "out";
    const isSuccess = msg.status === "delivered" || msg.status === "received" || msg.status === "accepted";

    return h("div", { className: cn("flex mb-3", isOut ? "justify-end" : "justify-start") },
      h("div", { className: cn(
        "max-w-[75%] rounded-xl px-4 py-2.5 text-sm",
        isOut
          ? "bg-blue-500/20 border border-blue-500/30 text-blue-100"
          : "bg-white/5 border border-white/10 text-gray-200"
      ) },
        // Header
        h("div", { className: "flex items-center gap-2 text-xs mb-1 opacity-60" },
          h("span", { className: "font-medium" }, isOut ? "You" : (msg.sender_name || msg.nick)),
          h("span", null, msg.timestamp ? msg.timestamp.split(" ").slice(0, 2).join(" ") : ""),
          h(Badge, { variant: "outline", className: "text-[10px] py-0 px-1" }, msg.mode),
          msg.is_test && h(Badge, { variant: "outline", className: "text-[10px] py-0 px-1 text-amber-400" }, "test")
        ),
        // Message body
        h("div", { className: "whitespace-pre-wrap break-words" }, msg.message),
        // Response (for inbound messages that have agent responses)
        msg.response && h("div", { className: "mt-2 pt-2 border-t border-white/10 text-xs opacity-70" },
          h("div", { className: "font-medium mb-0.5" }, "↳ Response:"),
          h("div", { className: "whitespace-pre-wrap" }, msg.response)
        ),
        // Status
        !isSuccess && h("div", { className: "text-xs text-red-400 mt-1" }, "⚠ Failed (HTTP " + (msg.http_status || "?") + ")")
      )
    );
  }

  // --- Conversation View (chat thread for one agent) ---
  function ConversationView({ nick, onBack, onSent }) {
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [mode, setMode] = useState("ping");
    const [message, setMessage] = useState("");
    const [sending, setSending] = useState(false);
    const [result, setResult] = useState(null);
    const bottomRef = useRef(null);

    const loadMessages = useCallback(function () {
      api("/history/" + nick + "?limit=100")
        .then(function (data) {
          // Reverse to show oldest first (chat order)
          setMessages((data.messages || []).reverse());
        })
        .catch(function () {})
        .finally(function () { setLoading(false); });
    }, [nick]);

    useEffect(function () { loadMessages(); }, [loadMessages]);

    // Auto-scroll to bottom when new messages arrive
    useEffect(function () {
      if (bottomRef.current) {
        bottomRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }, [messages]);

    const handleSend = useCallback(function () {
      if (!message.trim()) return;
      setSending(true);
      setResult(null);
      api("/send", {
        method: "POST",
        body: JSON.stringify({ nick: nick, mode: mode, message: message.trim() }),
      })
        .then(function (r) {
          setResult({ ok: true, data: r });
          setMessage("");
          loadMessages();
          if (onSent) onSent();
        })
        .catch(function (err) { setResult({ ok: false, error: err.message }); })
        .finally(function () { setSending(false); });
    }, [nick, mode, message, loadMessages, onSent]);

    return h("div", { className: "flex flex-col h-full" },
      // Header
      h("div", { className: "flex items-center gap-3 pb-3 border-b border-border/30 mb-3" },
        h(Button, { variant: "ghost", size: "sm", onClick: onBack },
          h(ChevronLeftIcon, { className: "w-4 h-4 mr-1" }), "Back"
        ),
        h("div", { className: "w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center" },
          h("span", { className: "text-xs font-bold text-blue-400" }, nick.charAt(0).toUpperCase())
        ),
        h("div", null,
          h("div", { className: "font-semibold text-sm" }, nick),
          h("div", { className: "text-xs text-muted-foreground" },
            messages.length + " message" + (messages.length !== 1 ? "s" : "")
          )
        )
      ),

      // Messages area
      h("div", { className: "flex-1 overflow-y-auto mb-3 space-y-1 px-1" },
        loading
          ? h("div", { className: "text-center text-muted-foreground py-8 text-sm" }, "Loading messages...")
          : messages.length === 0
            ? h("div", { className: "text-center text-muted-foreground py-8" },
                h(MessageCircleIcon, { className: "w-8 h-8 mx-auto mb-2 opacity-30" }),
                h("p", { className: "text-sm" }, "No messages yet with " + nick),
                h("p", { className: "text-xs mt-1" }, "Send a message to start the conversation.")
              )
            : messages.map(function (msg) {
                return h(ChatBubble, { key: msg.id + "-" + msg.timestamp, msg: msg });
              }),
        h("div", { ref: bottomRef })
      ),

      // Result notification
      result && h("div", { className: cn("text-xs rounded p-2 mb-2", result.ok ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400") },
        result.ok
          ? h("div", { className: "flex items-center gap-1.5" }, h(CheckIcon, null), "Delivered (HTTP " + (result.data && result.data.status || "?") + ")")
          : h("div", { className: "flex items-center gap-1.5" }, h(XIcon, null), "Failed: " + result.error)
      ),

      // Compose area
      h("div", { className: "border-t border-border/30 pt-3" },
        h("div", { className: "flex gap-2 mb-2" },
          h(Button, { variant: mode === "ping" ? "default" : "outline", size: "sm", onClick: function () { setMode("ping"); } },
            h(ZapIcon, { className: "w-3.5 h-3.5 mr-1.5" }), "AI Ping"
          ),
          h(Button, { variant: mode === "notify" ? "default" : "outline", size: "sm", onClick: function () { setMode("notify"); } },
            h(BellIcon, { className: "w-3.5 h-3.5 mr-1.5" }), "Direct Notify"
          )
        ),
        h("div", { className: "flex gap-2" },
          h("textarea", {
            className: "flex-1 rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none",
            placeholder: "Type a message to " + nick + "...",
            value: message,
            onChange: function (e) { setMessage(e.target.value); },
            rows: 2,
            onKeyDown: function (e) {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }
          }),
          h(Button, { onClick: handleSend, disabled: sending || !message.trim(), className: "self-end" },
            sending ? "Sending..." : h(SendIcon, { className: "w-4 h-4" })
          )
        )
      )
    );
  }

  // --- Main Page ---
  function AgentsPage() {
    const [agents, setAgents] = useState([]);
    const [conversations, setConversations] = useState([]);
    const [identity, setIdentity] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showAdd, setShowAdd] = useState(false);
    const [sendingTo, setSendingTo] = useState(null);
    const [activeTab, setActiveTab] = useState("conversations"); // "conversations" | "agents"
    const [activeConversation, setActiveConversation] = useState(null);

    const loadData = useCallback(function () {
      setLoading(true);
      setError(null);
      Promise.all([
        api("/agents").catch(function () { return null; }),
        api("/conversations").catch(function () { return null; }),
        api("/identity").catch(function () { return null; }),
      ])
        .then(function (results) {
          if (results[0]) setAgents(results[0].agents || []);
          if (results[1]) setConversations(results[1].conversations || []);
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

    // If viewing a conversation, render the chat view
    if (activeConversation) {
      return h("div", { className: "h-full flex flex-col" },
        h(ConversationView, {
          nick: activeConversation,
          onBack: function () { setActiveConversation(null); loadData(); },
          onSent: loadData,
        })
      );
    }

    if (loading) {
      return h("div", { className: "flex items-center justify-center py-12" },
        h("div", { className: "text-muted-foreground flex items-center gap-2" },
          h(SendIcon, { className: "w-5 h-5 animate-pulse" }), "Loading..."
        )
      );
    }

    return h("div", { className: "space-y-4" },
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
        h(Button, { variant: activeTab === "conversations" ? "default" : "ghost", size: "sm", onClick: function () { setActiveTab("conversations"); } },
          h(MessageCircleIcon, { className: "w-3.5 h-3.5 mr-1.5" }),
          "Conversations (" + conversations.length + ")"
        ),
        h(Button, { variant: activeTab === "agents" ? "default" : "ghost", size: "sm", onClick: function () { setActiveTab("agents"); } },
          "Agents (" + agents.length + ")"
        )
      ),

      error && h("div", { className: "text-xs text-red-400 bg-red-500/10 rounded p-2" }, "⚠ " + error),

      // Conversations tab
      activeTab === "conversations" && (
        conversations.length === 0
          ? h("div", { className: "text-center py-12 text-muted-foreground" },
              h(MessageCircleIcon, { className: "w-8 h-8 mx-auto mb-3 opacity-30" }),
              h("p", { className: "text-sm" }, "No conversations yet."),
              h("p", { className: "text-xs mt-1" }, "Send a message to an agent to start a conversation.")
            )
          : h("div", null,
              conversations.map(function (conv) {
                return h(ConversationItem, {
                  key: conv.nick,
                  conv: conv,
                  onClick: function (nick) { setActiveConversation(nick); },
                });
              })
            )
      ),

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

      // Modals
      showAdd && h(AddAgentModal, {
        onSave: function () { setShowAdd(false); loadData(); },
        onClose: function () { setShowAdd(false); }
      }),
      sendingTo && h(SendMessageModal, {
        agent: sendingTo,
        onSend: function () { loadData(); },
        onClose: function () { setSendingTo(null); }
      })
    );
  }

  // --- Register plugin ---
  if (window.__HERMES_PLUGINS__) {
    window.__HERMES_PLUGINS__.register("hermes-webhook", AgentsPage);
  }
})();
