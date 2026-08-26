const state = { services: [], editing: false, editId: null };

const $ = (sel) => document.querySelector(sel);
const app = $("#app");
const dlg = $("#dialog");
const form = dlg.querySelector("form");

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = j.detail || msg; } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

async function load() {
  state.services = await api("/api/services");
  render();
}

function render() {
  const cats = [...new Set(state.services.map((s) => s.category))];
  app.innerHTML = "";
  if (!cats.length) {
    app.innerHTML = '<div class="empty">还没有服务,点右上角 "+ 新增" 添加第一个 🎉</div>';
    return;
  }
  for (const cat of cats) {
    const sec = document.createElement("section");
    sec.className = "category";
    const h = document.createElement("h2");
    h.textContent = cat;
    const grid = document.createElement("div");
    grid.className = "grid";
    state.services.filter((s) => s.category === cat).forEach((s) => grid.appendChild(card(s)));
    sec.append(h, grid);
    app.appendChild(sec);
  }
}

/* ---------- 图标:设定图标 > 网站 favicon > 回形针 ---------- */

function fallbackIcon(box) {
  box.classList.add("emoji");
  box.textContent = "🔗";
}

function buildIcon(s, box) {
  // 1. 显式设定的图标
  if (s.icon) {
    if (s.icon.startsWith("http")) {
      const img = document.createElement("img");
      img.src = s.icon;
      img.alt = "";
      img.loading = "lazy";
      img.onerror = () => fallbackIcon(box);
      box.appendChild(img);
    } else {
      box.classList.add("emoji");
      box.textContent = s.icon;
    }
    return;
  }
  // 2. 未设定 → 走后端 favicon 代理(磁盘 + 浏览器双层缓存)
  let origin = "";
  try { origin = new URL(s.url).origin; } catch { fallbackIcon(box); return; }
  const img = document.createElement("img");
  img.src = "/api/favicon?u=" + encodeURIComponent(s.url);
  img.alt = "";
  img.loading = "lazy";
  const timer = setTimeout(() => {
    if (!img.complete) { img.onerror = null; img.remove(); fallbackIcon(box); }
  }, 8000);
  img.onload = () => clearTimeout(timer);
  img.onerror = () => { clearTimeout(timer); fallbackIcon(box); };
  box.appendChild(img);
}

function card(s) {
  const el = document.createElement("div");
  el.className = "card";

  const overlay = document.createElement("a");
  overlay.className = "link-overlay";
  overlay.href = s.url;
  overlay.target = "_blank";
  overlay.rel = "noopener";
  el.appendChild(overlay);

  const iconBox = document.createElement("div");
  iconBox.className = "icon-box";
  el.appendChild(iconBox);
  buildIcon(s, iconBox);

  const info = document.createElement("div");
  info.className = "info";
  const name = document.createElement("div");
  name.className = "name";
  name.textContent = s.name;
  info.appendChild(name);
  if (s.description) {
    const desc = document.createElement("div");
    desc.className = "desc";
    desc.textContent = s.description;
    info.appendChild(desc);
  }
  el.appendChild(info);

  if (state.editing) {
    const actions = document.createElement("div");
    actions.className = "actions";
    const btnE = document.createElement("button");
    btnE.title = "编辑";
    btnE.textContent = "✎";
    btnE.onclick = () => openEdit(s.id);
    const btnD = document.createElement("button");
    btnD.title = "删除";
    btnD.textContent = "🗑";
    btnD.onclick = () => delService(s.id);
    actions.append(btnE, btnD);
    el.appendChild(actions);
  }
  return el;
}

function toggleEdit() {
  state.editing = !state.editing;
  $("#btn-edit").textContent = state.editing ? "✔ 完成" : "✎ 编辑";
  render();
}

/* ---------- 分类:下拉选现有分类,或新建自定义分类 ---------- */

function fillCatSelect(selected) {
  const sel = form["category-select"];
  const inp = form["category"];
  sel.innerHTML = "";
  [...new Set(state.services.map((s) => s.category))].forEach((c) => {
    const o = document.createElement("option");
    o.value = c;
    o.textContent = c;
    sel.appendChild(o);
  });
  const oNew = document.createElement("option");
  oNew.value = "__new__";
  oNew.textContent = "➕ 新建分类…";
  sel.appendChild(oNew);

  if (selected && [...sel.options].some((o) => o.value === selected)) {
    sel.value = selected;
    inp.hidden = true;
    inp.value = "";
  } else {
    sel.value = "__new__";
    inp.hidden = false;
    inp.value = selected || "";
  }
}

function syncCatInput() {
  const sel = form["category-select"];
  const inp = form["category"];
  inp.hidden = sel.value !== "__new__";
  if (!inp.hidden) inp.focus();
}

function categoryValue() {
  const sel = form["category-select"];
  const inp = form["category"];
  if (sel.value === "__new__") return inp.value.trim() || "其他";
  return sel.value || "其他";
}

form["category-select"].addEventListener("change", syncCatInput);

/* ---------- 弹窗 ---------- */

function openAdd() {
  state.editId = null;
  form.reset();
  form.name.value = "";
  form.url.value = "";
  form.description.value = "";
  form.icon.value = "";
  fillCatSelect("其他");
  $("#dialog-title").textContent = "新增服务";
  dlg.showModal();
  form.name.focus();
}

function openEdit(id) {
  const s = state.services.find((x) => x.id === id);
  if (!s) return;
  state.editId = id;
  form.name.value = s.name;
  form.url.value = s.url;
  form.description.value = s.description || "";
  form.icon.value = s.icon || "";
  fillCatSelect(s.category);
  $("#dialog-title").textContent = "编辑服务";
  dlg.showModal();
}

async function delService(id) {
  if (!confirm("确定删除该服务?")) return;
  await api(`/api/services/${id}`, { method: "DELETE" });
  await load();
}

dlg.addEventListener("close", async () => {
  if (dlg.returnValue !== "ok") { state.editId = null; return; }
  const data = {
    name: form.name.value.trim(),
    url: form.url.value.trim(),
    description: form.description.value.trim(),
    icon: form.icon.value.trim(),
    category: categoryValue(),
  };
  try {
    if (state.editId) {
      await api(`/api/services/${state.editId}`, { method: "PUT", body: JSON.stringify(data) });
    } else {
      await api("/api/services", { method: "POST", body: JSON.stringify(data) });
    }
    await load();
  } catch (e) {
    alert("保存失败: " + e.message);
  }
  state.editId = null;
});

/* ---------- 导出 / 导入 ---------- */

async function exportJson() {
  const res = await fetch("/api/export");
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "services.json";
  a.click();
  URL.revokeObjectURL(a.href);
}

$("#file-import").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const arr = JSON.parse(await file.text());
    if (!Array.isArray(arr)) throw new Error("文件格式不正确,应为服务数组");
    if (!confirm(`将用文件中的 ${arr.length} 个服务替换当前清单,确定?`)) return;
    await api("/api/import", { method: "POST", body: JSON.stringify(arr) });
    await load();
  } catch (err) {
    alert("导入失败: " + err.message);
  }
  e.target.value = "";
});

$("#btn-edit").addEventListener("click", toggleEdit);
$("#btn-export").addEventListener("click", exportJson);
$("#btn-import").addEventListener("click", () => $("#file-import").click());
$("#btn-add").addEventListener("click", openAdd);

load().catch((e) => {
  app.innerHTML = `<div class="empty">加载失败: ${esc(e.message)}</div>`;
});
