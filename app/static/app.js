const $app = document.getElementById("app");
const $nav = document.getElementById("nav");
const $msg = document.getElementById("msg");
let me = null;

// Every value from the server goes in as a text node, never as HTML (blocks XSS).
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k.startsWith("on")) el[k] = v; else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid == null) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
function say(text, bad) { $msg.textContent = text || ""; $msg.className = bad ? "bad" : "ok"; }
function show(...nodes) { $app.replaceChildren(...nodes); }
function go(fn) { return () => { say(""); Promise.resolve().then(fn).catch(e => say(e.message, true)); }; }
function btn(label, fn) { return h("button", { type: "button", onclick: go(fn) }, label); }
function submit(fn) {
  return e => {
    e.preventDefault(); say("");
    const form = e.target, data = new FormData(form);
    Promise.resolve().then(() => fn(data, form)).catch(err => say(err.message, true));
  };
}
function field(label, name, type = "text", required = true) {
  const attrs = { name, type };
  if (required) attrs.required = "";
  return h("label", {}, label, h("input", attrs));
}
async function api(path, opts = {}) {
  const res = await fetch(path, { credentials: "same-origin", ...opts });
  let data = null;
  try { data = await res.json(); } catch (e) { /* not JSON */ }
  if (!res.ok) {
    const d = data && data.detail;
    throw new Error(typeof d === "string" ? d : "Invalid input (" + res.status + ")");
  }
  return data;
}
const jsonOpts = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

function table(rows, actions) {
  if (!rows.length) return h("p", {}, "Nothing to show.");
  const cols = Object.keys(rows[0]);
  return h("table", {},
    h("thead", {}, h("tr", {}, cols.map(c => h("th", {}, c)), actions ? h("th", {}, "actions") : null)),
    h("tbody", {}, rows.map(r => h("tr", {}, cols.map(c => h("td", {}, r[c] ?? "")),
      actions ? h("td", {}, actions(r)) : null))));
}

function nav() {
  const items = [];
  if (me) {
    items.push(btn("Documents", () => showDocs()));
    if (me.role === "owner") items.push(btn("Upload", () => showUpload()));
    if (me.role === "admin") items.push(btn("Admin", () => showAdmin()));
    items.push(h("span", {}, me.name + " (" + me.role + ")"));
    items.push(btn("Log out", logout));
  }
  $nav.replaceChildren(...items);
}

function showLogin() {
  me = null; nav();
  const login = h("form", { onsubmit: submit(async f => {
      await api("/auth/login", jsonOpts("POST", { email: f.get("email"), password: f.get("password") }));
      await start();
    }) }, h("h2", {}, "Log in"), field("Email", "email", "email"),
    field("Password", "password", "password"), h("button", {}, "Log in"));
  const role = h("select", { name: "role" }, h("option", { value: "viewer" }, "viewer"), h("option", { value: "owner" }, "owner"));
  const reg = h("form", { onsubmit: submit(async (f, form) => {
      await api("/auth/register", jsonOpts("POST", { email: f.get("email"), name: f.get("name"),
        password: f.get("password"), role: f.get("role") }));
      say("Registered. You can log in now."); form.reset();
    }) }, h("h2", {}, "Register"), field("Email", "email", "email"), field("Name", "name"),
    h("label", {}, "Password (10+ characters)", h("input", { name: "password", type: "password", required: "", minlength: "10" })),
    h("label", {}, "Role", role), h("button", {}, "Register"));
  show(login, reg);
}

async function start() {
  me = await api("/auth/me"); nav();
  if (me.role === "admin") await showAdmin(); else await showDocs();
}
async function logout() { await api("/auth/logout", { method: "POST" }); showLogin(); }

async function showDocs(params = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  const docs = await api("/documents" + (qs ? "?" + qs : ""));
  const filter = h("form", { onsubmit: submit(f => showDocs(Object.fromEntries(f))) },
    field("Name", "q", "text", false), field("Category", "category", "text", false),
    field("Owner", "owner", "text", false), field("From", "created_from", "date", false),
    field("To", "created_to", "date", false), h("button", {}, "Search"));
  const rows = docs.map(d => h("tr", {},
    h("td", {}, d.title), h("td", {}, d.category), h("td", {}, d.owner), h("td", {}, d.your_access),
    h("td", {}, new Date(d.created_at).toLocaleDateString()),
    h("td", {}, h("a", { href: "/documents/" + d.id + "/download" }, "Download"), " ",
      ["owner", "edit"].includes(d.your_access) ? btn("Rename", () => rename(d)) : null,
      d.your_access === "owner" ? [btn("Share", () => showShare(d)), btn("Delete", () => remove(d))] : null)));
  show(h("h2", {}, "Documents"), filter, docs.length
    ? h("table", {}, h("thead", {}, h("tr", {}, ["Title", "Category", "Owner", "Your access", "Created", "Actions"].map(c => h("th", {}, c)))), h("tbody", {}, rows))
    : h("p", {}, "No documents."));
}
async function rename(d) {
  const t = prompt("New title", d.title);
  if (!t) return;
  await api("/documents/" + d.id, jsonOpts("PATCH", { title: t }));
  await showDocs(); say("Renamed");
}
async function remove(d) {
  if (!confirm("Delete '" + d.title + "' for everyone?")) return;
  await api("/documents/" + d.id, { method: "DELETE" });
  await showDocs(); say("Deleted");
}

async function showShare(d) {
  const perms = await api("/documents/" + d.id + "/permissions");
  const list = table(perms, p => btn("Revoke", async () => {
    await api("/documents/" + d.id + "/permissions/" + p.user_id, { method: "DELETE" });
    await showShare(d); say("Access revoked");
  }));
  const add = h("form", { onsubmit: submit(async f => {
      await api("/documents/" + d.id + "/permissions", jsonOpts("POST", { email: f.get("email"), level: f.get("level") }));
      await showShare(d); say("Access granted");
    }) }, field("Person's email", "email", "email"),
    h("label", {}, "Level", h("select", { name: "level" }, h("option", { value: "read" }, "read"), h("option", { value: "edit" }, "edit"))),
    h("button", {}, "Grant"));
  show(h("h2", {}, "Share: " + d.title), list, add, btn("Back", () => showDocs()));
}

function showUpload() {
  show(h("h2", {}, "Upload a document"), h("p", {}, "PDF or UTF-8 text, up to 5 MB. It starts private."),
    h("form", { onsubmit: submit(async (f, form) => {
        await api("/documents", { method: "POST", body: f });
        say("Uploaded. It is private until you share it."); form.reset();
      }) }, field("Title", "title"), field("Category", "category", "text", false),
      h("label", {}, "File", h("input", { type: "file", name: "file", required: "" })), h("button", {}, "Upload")));
}

async function showAdmin() {
  const out = h("div");
  const views = {
    "Audit log": async () => table(await api("/admin/audit")),
    "Refused attempts": async () => table(await api("/admin/audit?outcome=denied")),
    "Permission changes": async () => table(await api("/admin/permission-changes")),
    "Alerts": async () => {
      const a = await api("/admin/alerts");
      return h("div", {}, h("h3", {}, "Many refused attempts (" + a.window + ")"), table(a.many_refused_attempts),
        h("h3", {}, "Many downloads"), table(a.many_downloads));
    },
    "Users": async () => table(await api("/admin/users"), u => btn(u.is_active ? "Deactivate" : "Activate", async () => {
      await api("/admin/users/" + u.id + "/" + (u.is_active ? "deactivate" : "activate"), { method: "POST" });
      await load("Users"); say("Done");
    })),
    "All documents": async () => table(await api("/admin/documents")),
    "Verify chain": async () => {
      const v = await api("/admin/verify-chain");
      return h("p", {}, v.valid ? "Audit chain is valid." : "TAMPERING DETECTED at row " + v.first_bad_row);
    }
  };
  async function load(name) { out.replaceChildren(await views[name]()); }
  show(h("h2", {}, "Admin"), h("div", {}, Object.keys(views).map(n => btn(n, () => load(n)))), out);
  await load("Audit log");
}

api("/auth/me").then(start).catch(showLogin);