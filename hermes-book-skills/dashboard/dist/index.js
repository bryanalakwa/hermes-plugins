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
  const { Card, CardContent, CardHeader, CardTitle, Badge, Button, Input, Label } = SDK.components;

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

  const EditIcon = (props) => h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
    h("path", { d: "M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 1-2-2v-7" }),
    h("path", { d: "M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 7.5-8.5z" })
  );

  const EyeIcon = (props) => h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
    h("path", { d: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8 0 0 0 0 0-.7.3-1 3-1 1 0 0 0 .7.3 1 3 2.7A7.7 7.7 0 0 1 11.7 21 7.7 7.7 0 0 1 2 12c0-2.9 2.3-5 5-5s5 2.1 5 5a11 11 0 0 1-22 0c0-2.4 1.8-4.5 4.3-4.9-.2.7-.3 1.4-.3 2.1z" }),
    h("circle", { cx: 12, cy: 12, r: 3 })
  );

  const CheckIcon = (props) => h("svg", Object.assign({ xmlns: "http://www.w3.org/2000/svg", width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 }, props || {}),
    h("path", { d: "M20 6L9 17l-5-5" })
  );

  // --- File upload handler component ---
  function FileUploadButton({ onUpload, disabled }) {
    const [inputKey, setInputKey] = useState(Date.now());

    const handleChange = async (e) => {
      await onUpload(e);
      setInputKey(Date.now());
    };

    return h("label", { className: "bs-cursor-pointer bs-inline-flex bs-items-center bs-gap-1 bs-px-3 bs-py-1 bs-rounded bs-text-sm bs-font-medium bs-border bs-border-border", style: { cursor: "pointer" } },
      h("input", {
        key: inputKey,
        type: "file",
        accept: ".pdf,.epub,.txt,.mobi,.azw",
        onChange: handleChange,
        className: "bs-hidden",
      }),
      h(UploadIcon, { className: "bs-w-4 bs-h-4" }),
      "Upload Book"
    );
  }

  // --- Progress Bar Component ---
  function ProgressBar({ progress, status }) {
    return h("div", { className: "bs-w-full bs-bg-secondary bs-rounded-full bs-h-2 bs-overflow-hidden bs-mb-3" },
      h("div", {
        className: "bs-h-full bs-bg-blue-500 bs-transition-all bs-duration-300",
        style: { width: progress + "%" }
      })
    );
  }

  // --- Main Component ---
  function BookSkillsApp() {
    const [activeTab, setActiveTab] = useState("books");
    const [books, setBooks] = useState([]);
    const [skills, setSkills] = useState([]);
    const [initialLoad, setInitialLoad] = useState(true);
    const [processing, setProcessing] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressStatus, setProgressStatus] = useState("");
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [showViewModal, setShowViewModal] = useState(false);
    const [viewingSkill, setViewingSkill] = useState(null);
    const [skillContent, setSkillContent] = useState("");

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
      setProgress(25);
      setProgressStatus("Uploading file...");

      const token = window.__HERMES_SESSION_TOKEN__ || localStorage.getItem("__hermes_pw_token__") || "";
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch(API_BASE + "/books/upload", {
          method: "POST",
          headers: { "X-Hermes-Session-Token": token },
          body: formData,
        });

        if (res.status === 401) {
          localStorage.removeItem("__hermes_pw_token__");
          window.location.reload();
          return;
        }

        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || res.statusText);

        setProgress(100);
        setProgressStatus("Done!");
        setSuccess("Uploaded: " + result.uploaded + ". Click 'Create Skill' to generate a skill.");
        fetchBooks();
      } catch (err) {
        setError(err.message);
      } finally {
        setProcessing(false);
        setTimeout(() => { setProgress(0); setProgressStatus(""); }, 2000);
      }
    };

    const handleCreateSkill = async (book) => {
      setProcessing(true);
      setError(null);
      setProgress(0);
      setProgressStatus("Extracting text...");

      try {
        setProgress(25);
        const data = await api("/books/" + encodeURIComponent(book.id) + "/extract");
        setProgress(50);
        setProgressStatus("Running LLM extraction...");

        const res = await api("/books/" + encodeURIComponent(book.id) + "/create", { method: "POST" });

        setProgress(100);
        setProgressStatus("Skill created!");
        setSuccess("Skill generated: " + res.skill_name + " (" + (res.extraction?.concepts?.length || 0) + " concepts, " + (res.extraction?.methods?.length || 0) + " methods)");

        fetchSkills();
        fetchBooks();
      } catch (err) {
        setError(err.message);
      } finally {
        setProcessing(false);
        setTimeout(() => { setProgress(0); setProgressStatus(""); }, 3000);
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

    const handleViewSkill = async (skillName) => {
      // Toggle: close modal if already viewing this skill
      if (showViewModal && viewingSkill === skillName) {
        setShowViewModal(false);
        return;
      }
      setViewingSkill(skillName);
      try {
        const skill = skills.find(s => s.name === skillName);
        if (skill && skill.has_skill_md) {
          const content = await api("/skills/" + encodeURIComponent(skillName) + "/content");
          setSkillContent(content.content || "No content");
        } else {
          setSkillContent("# " + skillName + "\n\nNo SKILL.md found.");
        }
        setShowViewModal(true);
      } catch (err) {
        setError(err.message);
      }
    };

    const handleSaveSkill = async () => {
      if (!viewingSkill) return;
      try {
        await api("/skills/" + encodeURIComponent(viewingSkill) + "/content", {
          method: "PUT",
          body: JSON.stringify({ content: skillContent }),
        });
        setSuccess("Skill saved!");
        setShowViewModal(false);
        fetchSkills();
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

    const HeaderSection = () => {
      return h("div", { className: "bs-mb-6 bs-pb-4 bs-border-b bs-border-border" },
        h("div", { className: "bs-flex bs-items-center bs-gap-3 bs-mb-3" },
          h("div", { className: "bs-w-12 bs-h-12 bs-rounded-lg bs-flex bs-items-center bs-justify-center bs-shrink-0" },
            h(BookIcon, { className: "bs-w-7 bs-h-7 bs-text-white" })
          ),
          h("div", null,
            h("h1", { className: "bs-text-2xl bs-font-bold bs-text-white bs-m-0" }, "BookSkills"),
            h("p", { className: "bs-text-sm bs-text-muted-foreground bs-m-0 bs-mt-1" },
              "Upload PDF, EPUB, or TXT books to generate reusable Hermes skills."
            )
          )
        ),
        progress > 0 && h(ProgressBar, { progress, status: progressStatus }),
        progressStatus && h("div", { className: "bs-text-xs bs-text-muted-foreground bs-mb-2" }, progressStatus)
      );
    };

    const SkillViewModal = () => {
      if (!showViewModal || !viewingSkill) return null;

      return h("div", { className: "bs-fixed bs-inset-0 bs-z-50 bs-bg-black/80 bs-flex bs-items-center bs-justify-center bs-p-4" },
        h("div", { className: "bs-bg-card bs-rounded-lg bs-border bs-border-border bs-w-full bs-max-w-4xl bs-flex bs-flex-col", style: { height: "85vh", maxHeight: "85vh" } },
          h("div", { className: "bs-flex bs-items-center bs-justify-between bs-px-6 bs-py-4 bs-border-b bs-border-border bs-flex-shrink-0" },
            h("div", { className: "bs-flex bs-items-center bs-gap-2" },
              h(BookIcon, { className: "bs-w-5 bs-h-5 bs-text-amber-400" }),
              h("h2", { className: "bs-text-lg bs-font-bold bs-m-0" }, viewingSkill.replace(/-/g, " "))
            ),
            h(Button, { variant: "ghost", size: "sm", onClick: () => setShowViewModal(false) }, "✕")
          ),
          h("div", { className: "bs-px-6 bs-py-4 bs-flex-1 bs-overflow-hidden", style: { height: "calc(85vh - 120px)" } },
            h("textarea", {
              className: "bs-w-full bs-bg-secondary bs-text-xs bs-font-mono bs-rounded bs-resize-none bs-overflow-y-auto bs-p-4",
              style: { height: "56vh", minHeight: "56vh" },
              value: skillContent,
              onChange: (e) => setSkillContent(e.target.value),
              spellcheck: false,
            })
          ),
          h("div", { className: "bs-flex bs-justify-end bs-gap-3 bs-px-6 bs-py-4 bs-border-t bs-border-border bs-flex-shrink-0" },
            h(Button, { variant: "ghost", size: "sm", onClick: () => setShowViewModal(false) }, "Cancel"),
            h(Button, { variant: "default", size: "sm", onClick: handleSaveSkill }, "Save Changes")
          )
        )
      );
    };

    const renderBooksTab = () => {
      return h("div", { className: "bs-space-y-4" },
        h("div", { className: "bs-flex bs-items-center bs-gap-3 bs-mb-4" },
          h("h2", { className: "bs-text-lg bs-font-semibold" }, "Book Library"),
          h(FileUploadButton, { onUpload: handleFileUpload, disabled: processing })
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
                        " • uploaded " + (typeof book.uploaded_at === "string" ? book.uploaded_at : "")
                      )
                    ),
                    h("div", { className: "bs-flex bs-items-center bs-gap-2" },
                      book.has_skill ?
                        h(Badge, { variant: "outline", className: "bs-text-green-400 bs-border-green-400/30" }, "Skill Generated") :
                        h(Button, {
                          variant: "default",
                          size: "sm",
                          onClick: () => handleCreateSkill(book),
                          disabled: processing,
                        }, "Create Skill"),
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
                        onClick: () => handleViewSkill(skill.name),
                        title: "View/Edit skill",
                      },
                        h(EyeIcon, { className: "bs-w-3.5 bs-h-3.5 bs-text-blue-400" })
                      ),
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
      success && h("div", { className: "bs-text-xs bs-text-green-400 bs-bg-green-500/10 bs-rounded bs-p-2 bs-mb-4" }, h(CheckIcon, { className: "bs-inline bs-w-3 bs-h-3 bs-mr-1" }), success),

      h(HeaderSection),

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

      h(SkillViewModal)
    );
  }

  // --- Register plugin ---
  window.__HERMES_PLUGINS__.register("hermes-book-skills", BookSkillsApp);
})();