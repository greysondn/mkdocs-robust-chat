/* Robust Chat — shared runtime.
   Identical file ships in both plugins. Exposes window.robustChat.enhance(root),
   which is idempotent and safe to call repeatedly. mkdocs calls it on DOMContentLoaded
   (and on the material instant-nav event); the Obsidian plugin calls it on each rendered
   block. Folding is native <details>, so this only handles timezone dates + the
   commentary column toggle. */
(function () {
  "use strict";

  function localizeDates(root) {
    var times = root.querySelectorAll("time.rc-date:not([data-rc-localized])");
    for (var i = 0; i < times.length; i++) {
      var el = times[i];
      var raw = el.getAttribute("datetime") || el.textContent;
      var d = new Date(raw);
      if (!isNaN(d.getTime())) {
        try {
          el.textContent = d.toLocaleString(undefined, {
            year: "numeric", month: "short", day: "numeric",
            hour: "2-digit", minute: "2-digit"
          });
          el.title = d.toLocaleString(undefined, {
            dateStyle: "full", timeStyle: "long"
          });
        } catch (e) { /* leave verbatim */ }
      }
      el.setAttribute("data-rc-localized", "1");
    }
  }

  var STORE = "robustChat.commentary";
  function readPref() {
    try { return window.localStorage.getItem(STORE); } catch (e) { return null; }
  }
  function writePref(v) {
    try { window.localStorage.setItem(STORE, v); } catch (e) {}
  }

  function wireCommentary(chat) {
    if (chat.getAttribute("data-rc-wired") === "1") return;
    var btn = chat.querySelector(".rc-commentary-toggle");
    if (!btn) { chat.setAttribute("data-rc-wired", "1"); return; }

    // a chat with no commentary at all: hide the toggle entirely
    var hasCommentary = false;
    var cols = chat.querySelectorAll(".rc-commentary");
    for (var i = 0; i < cols.length; i++) {
      if (cols[i].children.length > 0) { hasCommentary = true; break; }
    }
    if (!hasCommentary) {
      var tb = chat.querySelector(".rc-toolbar");
      if (tb) tb.style.display = "none";
      chat.setAttribute("data-rc-wired", "1");
      return;
    }

    var pref = readPref();
    if (pref === "collapsed" || pref === "expanded") apply(chat, btn, pref);

    btn.addEventListener("click", function () {
      var next = chat.getAttribute("data-commentary") === "collapsed"
        ? "expanded" : "collapsed";
      apply(chat, btn, next);
      writePref(next);
    });
    chat.setAttribute("data-rc-wired", "1");
  }

  function apply(chat, btn, state) {
    chat.setAttribute("data-commentary", state);
    btn.setAttribute("aria-pressed", state === "expanded" ? "true" : "false");
  }

  function enhance(root) {
    root = root || document;
    localizeDates(root);
    var chats = root.querySelectorAll(".rc-chat");
    for (var i = 0; i < chats.length; i++) wireCommentary(chats[i]);
  }

  window.robustChat = { enhance: enhance };

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () { enhance(document); });
    } else {
      enhance(document);
    }
    // mkdocs-material instant navigation (if enabled) swaps content without reload
    if (window.document$ && typeof window.document$.subscribe === "function") {
      window.document$.subscribe(function () { enhance(document); });
    }
  }
})();
