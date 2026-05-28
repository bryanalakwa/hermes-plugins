/**
 * BookSkills Dashboard Plugin v1.0
 *
 * Upload books, generate skills, manage libraries.
 * Calls backend at /api/plugins/hermes-book-skills/
 */
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !window.__HERMES_PLUGINS__) return;

  const React = SDK.React;
  const h = React.createElement;
  const { useState, useEffect, useCallback, useRef } = SDK.hooks;
  const { Card, CardContent, CardHeader, CardTitle, Badge, Button, Input, Label, Textarea } = SDK.components;
  const { cn } = SDK.utils;

  const API_BASE = "/api/plugins/hermes-book-skills";

  async function api(path, opts) {
    const token = window.__HERMES_SESSION_TOKEN__ || localStorage.getItem("__hermes_pw_token__") || "";
    const headers = { "Content-Type": "application/json", ...(opts?.headers || {}) };
    if (token) headers["X-Hermes-Session-Token"] = token;
    const res = await fetch(API_BASE + path, { ...opts, headers });
    if (res.status === 401) {
      localStorage.removeItem("__hermes_pw_token__");
      localStorage.removeItem("__hermes_pw_token_ts__");
      window.location.reload();
      return;
    }
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(res.status + ": " + text);
    }
    return res.json();
  }

  // --- Icons ---
  const BookIcon = (props) => h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
    h("path", { d: "M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19" }),
    h("path", { d: "M6.5 2v19" }),
    h("path", { d: "M12 11h7" }),
    h("path", { d: "M12 16h7" })
  );

  const UploadIcon = (props) => h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
    h("path", { d: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" }),
    h("polyline", { points: "17 8 12 3 7 8" }),
    h("line", { x1: "12", y1: "3", x2: "12", y2: "15" })
  );

  const TrashIcon = (props) => h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
    h("path", { d: "M3 6h18" }),
    h("path", { d: "M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" }),
    h("path", { d: "M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" })
  );

  const RefreshIcon = (props) => h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
    h("path", { d: "M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" }),
    h("path", { d: "M21 3v5h-5" })
  );

  const EditIcon = (props) => h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
    h("path", { d: "M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" }),
    h("path", { d: "M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 7.5-8.5z" })
  );

  // --- Main Component ---
  function BookSkillsApp() {
    const [activeTab, setActiveTab] = useState("books");
    const [books, setBooks] = useState([]);
    const [skills, setSkills] = useState([]);
    const [initialLoad, setInitialLoad] = useState(true);
    const [selectedBook, setSelectedBook] = useState(null);
    const [showPreview, setShowPreview] = useState(false);
    const [previewData, setPreviewData] = useState(null);
    const [processing, setProcessing] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [renameModal, setRenameModal] = useState(null);

    const fetchBooks = useCallback(() => {
      api("/books")
        .then((r) => setBooks(r.books || []))
        .catch((e) => setError(e.message));
    }, []);

    const fetchSkills = useCallback(() => {
      api("/skills")
        .then((r) => setSkills(r.skills || []))
        .catch((e) => setError(e.message));
    }, []);

    useEffect(() => {
      if (initialLoad) {
        fetchBooks();
        fetchSkills();
        setInitialLoad(false);
      }
    }, [initialLoad, fetchBooks, fetchSkills]);

    const handleFileUpload = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      setProcessing(true);
      setError(null);

      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch(API_BASE + "/books/upload", {
          method: "POST",
          headers: { "X-Hermes-Session-Token": window.__HERMES_SESSION_TOKEN__ || localStorage.getItem("__hermes_pw_token__") || "" },
          body: JSON.stringify({ filename: file.name })
        });

        // For now, save file info and let the user process manually
        // Actual file upload would need different handling
        setSuccess("Book uploaded. Click 'Process' to extract content.");
        fetchBooks();
      } catch (err) {
        setError(err.message);
      } finally {
        setProcessing(false);
      }
    };

    const handleProcess = async (book) => {
      setProcessing(true);
      setError(null);
      setSelectedBook(book);

      try {
        const data = await api("/books/" + encodeURIComponent(book.id) + "/extract");
        setPreviewData(data);
        setShowPreview(true);
      } catch (err) {
        setError(err.message);
      } finally {
        setProcessing(false);
      }
    };

    const handleGenerateSkill = async (book) => {
      setProcessing(true);
      setError(null);

      try {
        const res = await api("/books/" + encodeURIComponent(book.id) + "/generate", {
          method: "POST",
          body: JSON.stringify({
            concepts: previewData?.concepts || [],
            methods: previewData?.methods || [],
            techniques: previewData?.techniques || [],
            skill_name: book.id,
          }),
        });

        setSuccess("Skill generated: " + res.skill_name);
        setShowPreview(false);
        fetchSkills();
      } catch (err) {
        setError(err.message);
      } finally {
        setProcessing(false);
      }
    };

    const handleDeleteBook = async (bookId) => {
      if (!confirm("Delete this book from library? The skill (if any) will remain.")) return;

      try {
        await api("/books/" + encodeURIComponent(bookId), { method: "DELETE" });
        fetchBooks();
      } catch (err) {
        setError(err.message);
      }
    };

    const handleDeleteSkill = async (skillName) => {
      if (!confirm("Delete this skill?")) return;

      try {
        await api("/skills/" + encodeURIComponent(skillName), { method: "DELETE" });
        fetchSkills();
      } catch (err) {
        setError(err.message);
      }
    };

    const handleRenameSkill = async (skillName) => {
      const newName = prompt("New skill name:", skillName);
      if (!newName || newName === skillName) return;

      try {
        await api("/skills/" + encodeURIComponent(skillName) + "/rename", {
          method: "PUT",
          body: JSON.stringify({ new_name: newName }),
        });
        setSuccess("Skill renamed: " + skillName + " -> " + newName);
        fetchSkills();
      } catch (err) {
        setError(err.message);
      }
    };

    const renderBooksTab = () => {
      return h("div", { className: "bs-space-y-4" },
        h("div", { className: "bs-flex bs-items-center bs-gap-4" },
          h("h2", { className: "bs-text-lg bs-font-semibold" }, "Book Library"),
          h("label", { className: "bs-cursor-pointer bs-bg-blue-500 bs-text-white bs-px-3 bs-py-1 bs-rounded bs-text-sm" },
            h("input", { type: "file", accept: ".pdf,.epub,.txt,.mobi,.azw", onChange: handleFileUpload, className: "bs-hidden" }),
            h("span", { className: "bs-flex bs-items-center bs-gap-1" },
              h(UploadIcon, { className: "bs-w-4 bs-h-4" }),
              "Upload Book"
            )
          )
        ),
        h(Card, { className: "bs-w-full" },
          h(CardContent, { className: "bs-p-0" },
            books.length === 0 ?
              h("div", { className: "bs-p-6 bs-text-center bs-text-muted-foreground" }, "No books uploaded yet.") :
              h("div", { className: "bs-divide-y" },
                books.map((book) =>
                  h("div", { key: book.id, className: "bs-flex bs-items-center bs-justify-between bs-p-3 bs-gap-3" },
                    h("div", { className: "bs-flex-1" },
                      h("div", { className: "bs-font-medium bs-text-sm" }, book.name),
                      h("div", { className: "bs-text-xs bs-text-muted-foreground" }, 
                        (typeof book.size === "number" ? (book.size / 1024).toFixed(1) + " KB" : book.size),
                        " uploaded " + (typeof book.uploaded_at === "string" ? book.uploaded_at : "")
                      )
                    ),
                    h("div", { className: "bs-flex bs-items-center bs-gap-2" },
                      book.has_skill ?
                        h(Badge, { variant: "outline", className: "bs-text-green-400 bs-border-green-400/30" }, "Skill Generated") :
                        h(Button, { 
                          variant: "default", 
                          size: "sm",
                          onClick: () => handleProcess(book),
                          disabled: processing,
                        }, "Process"),
                      h(Button, { 
                          variant: "ghost", 
                          size: "sm",
                          onClick: () => handleDeleteBook(book.id),
                          title: "Delete book",
                        },
                        h(TrashIcon, { className: "bs-w-3.5 bs-h-3.5 bs-text-red-400" })
                      )
                    )
                  )
                )
              )
          )
        )
      );
    };

    const renderSkillsTab = () => {
      return h("div", { className: "bs-space-y-4" },
        h("div", { className: "bs-flex bs-items-center bs-gap-4" },
          h("h2", { className: "bs-text-lg bs-font-semibold" }, "Skills Library"),
        ),
        h(Card, { className: "bs-w-full" },
          h(CardContent, { className: "bs-p-0" },
            skills.length === 0 ?
              h("div", { className: "bs-p-6 bs-text-center bs-text-muted-foreground" }, "No skills generated yet.") :
              h("div", { className: "bs-divide-y" },
                skills.map((skill) =>
                  h("div", { key: skill.name, className: "bs-flex bs-items-center bs-justify-between bs-p-3 bs-gap-3" },
                    h("div", { className: "bs-flex-1" },
                      h("div", { className: "bs-font-medium bs-text-sm bs-capitalize" }, skill.name.replace(/-/g, " ")),
                      h("div", { className: "bs-text-xs bs-text-muted-foreground" }, "Skill • " + (skill.has_skill_md ? "Ready" : "Missing SKILL.md"))
                    ),
                    h("div", { className: "bs-flex bs-items-center bs-gap-2" },
                      h(Button, { 
                        variant: "ghost", 
                        size: "sm",
                        onClick: () => handleRenameSkill(skill.name),
                        title: "Rename skill",
                      },
                        h(EditIcon, { className: "bs-w-3.5 bs-h-3.5 bs-text-blue-400" })
                      ),
                      h(Button, { 
                        variant: "ghost", 
                        size: "sm",
                        onClick: () => handleDeleteSkill(skill.name),
                        title: "Delete skill",
                      },
                        h(TrashIcon, { className: "bs-w-3.5 bs-h-3.5 bs-text-red-400" })
                      )
                    )
                  )
                )
              )
          )
        )
      );
    };

    return h("div", { className: "bs-max-w-4xl bs-mx-auto" },
      error && h("div", { className: "bs-text-xs bs-text-red-400 bs-bg-red-500/10 bs-rounded bs-p-2 bs-mb-4" }, "⚠ " + error),
      success && h("div", { className: "bs-text-xs bs-text-green-400 bs-bg-green-500/10 bs-rounded bs-p-2 bs-mb-4" }, "✓ " + success),

      h("div", { className: "bs-flex bs-gap-2 bs-mb-4 bs-border-b bs-border-border bs-pb-2" },
        h(Button, { 
          variant: activeTab === "books" ? "default" : "ghost", 
          size: "sm",
          onClick: () => setActiveTab("books"),
        }, "Books (" + books.length + ")"),
        h(Button, { 
          variant: activeTab === "skills" ? "default" : "ghost", 
          size: "sm",
          onClick: () => setActiveTab("skills"),
        }, "Skills (" + skills.length + ")")
      ),

      activeTab === "books" ? renderBooksTab() : renderSkillsTab(),

      showPreview && previewData && h("div", { className: "bs-fixed bs-inset-0 bs-z-50 bs-bg-black/60 bs-flex bs-items-center bs-justify-center bs-p-4" },
        h(Card, { className: "bs-max-w-2xl bs-w-full bs-max-h-[80vh] bs-overflow-y-auto" },
          h(CardHeader, null,
            h("div", { className: "bs-flex bs-items-center bs-justify-between" },
              h("div", { className: "bs-flex bs-items-center bs-gap-2" },
                h(BookIcon, { className: "bs-w-5 bs-h-5 bs-text-amber-400" }),
                h(CardTitle, null, "Process: " + (selectedBook && typeof selectedBook.name === "string" ? selectedBook.name : ""))
              ),
              h(Button, { variant: "ghost", size: "sm", onClick: () => setShowPreview(false) }, "✕")
            )
          ),
          h(CardContent, { className: "bs-space-y-4" },
            h("div", { className: "bs-text-xs bs-text-muted-foreground bs-bg-amber-500/5 bs-rounded bs-p-3 bs-mb-3" },
              "Extracted " + (typeof previewData.total_chunks === "number" ? previewData.total_chunks : 0) + " chunks (" + (typeof previewData.total_length === "number" ? previewData.total_length : 0) + " chars). " +
              "Use the chat interface to ask for key concepts, then generate the skill."
            ),

            h(Button, { 
              variant: "default", 
              onClick: () => handleGenerateSkill(selectedBook),
              disabled: processing,
            }, processing ? "Generating..." : "Generate Skill")
          )
        )
      )
    );
  }

  // --- Register plugin ---
  window.__HERMES_PLUGINS__.register("hermes-book-skills", BookSkillsApp);
})();