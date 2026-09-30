const state = {
  services: [],
  editing: false,
  editId: null,
  isAdmin: false,
  token: localStorage.getItem("navi_token") || null,
};

const $ = (sel) => document.querySelector(sel);
const app = $("#app");
const dlg = $("#dialog");
const form = dlg.querySelector("form");
const pwdDlg = $("#pwd-dialog");

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const res = await fetch(path, { headers, ...opts });
  if (res.status === 401) {
    state.token = null;
    localStorage.removeItem("navi_token");
    if (state.isAdmin) showLogin();
    throw new Error("未授权");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = j.detail || msg; } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

/* ---------- 启动 ---------- */

async function init() {
  const isAdminPage = location.pathname === "/admin";
  state.isAdmin = isAdminPage;
  document.title = isAdminPage ? "Navi · 管理" : "Navi";
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
  if (isAdminPage) {
    if (state.token) {
      try {
        await api("/api/admin/check");
        enterAdmin();
        return;
      } catch (e) { /* token 失效,showLogin 已触发 */ }
    }
    showLogin();
  } else {
    $("#tools").style.display = "none";
    await load();
  }
}

function enterAdmin() {
  $("#tools").style.display = "flex";
  $("#btn-edit").textContent = "✎ 编辑";
  state.editing = false;
  load().catch((e) => {
    app.innerHTML = `<div class="empty">加载失败: ${esc(e.message)}</div>`;
  });
}

function showLogin() {
  $("#tools").style.display = "none";
  app.innerHTML = `
    <div class="login-box">
      <div class="login-logo">🧭</div>
      <h2>Navi 管理</h2>
      <p>请输入管理密码</p>
      <input type="password" id="login-pass" autocomplete="current-password" placeholder="管理密码">
      <button id="login-btn" class="tool-btn primary">登 录</button>
      <div class="login-err"></div>
      <a href="/" class="login-back">← 返回导航页</a>
    </div>`;
  const input = $("#login-pass");
  const errBox = document.querySelector(".login-err");
  const doLogin = async () => {
    const pass = input.value;
    if (!pass) return;
    errBox.textContent = "";
    try {
      const res = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: pass }),
      });
      if (!res.ok) {
        errBox.textContent = "密码错误,请重试";
        return;
      }
      const data = await res.json();
      state.token = data.token;
      localStorage.setItem("navi_token", data.token);
      enterAdmin();
    } catch (e) {
      errBox.textContent = "登录失败: " + e.message;
    }
  };
  $("#login-btn").onclick = doLogin;
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") doLogin(); });
  input.focus();
}

/* ---------- 服务列表 ---------- */

async function load() {
  state.services = await api("/api/services");
  render();
}

const SVG_UP = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>';
const SVG_DOWN = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
const SVG_EDIT = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>';

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
    const hBox = document.createElement("div");
    hBox.className = "cat-head";
    hBox.appendChild(h);
    if (state.isAdmin && state.editing) {
      const rename = document.createElement("button");
      rename.className = "sort-btn";
      rename.title = "重命名分类";
      rename.innerHTML = SVG_EDIT;
      rename.onclick = () => renameCategory(cat);
      const up = document.createElement("button");
      up.className = "sort-btn";
      up.title = "上移分类";
      up.innerHTML = SVG_UP;
      up.onclick = () => moveCategory(cat, -1);
      const down = document.createElement("button");
      down.className = "sort-btn";
      down.title = "下移分类";
      down.innerHTML = SVG_DOWN;
      down.onclick = () => moveCategory(cat, 1);
      hBox.append(rename, up, down);
    }
    const grid = document.createElement("div");
    grid.className = "grid";
    state.services.filter((s) => s.category === cat).forEach((s) => grid.appendChild(card(s)));
    sec.append(hBox, grid);
    app.appendChild(sec);
  }
}

/* ---------- 图标:设定图标 > 网站 favicon > 回形针 ---------- */

function fallbackIcon(box) {
  box.classList.add("emoji");
  box.textContent = "🔗";
}

function buildIcon(s, box) {
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
  if (state.isAdmin && state.editing) {
    const badge = document.createElement("span");
    badge.className = "sort-badge";
    badge.title = "排序随机数(10~200,小的在前)";
    badge.textContent = s.sort_order;
    name.appendChild(badge);
  }
  info.appendChild(name);
  if (s.description) {
    const desc = document.createElement("div");
    desc.className = "desc";
    desc.textContent = s.description;
    info.appendChild(desc);
  }
  el.appendChild(info);

  if (state.isAdmin && state.editing) {
    const actions = document.createElement("div");
    actions.className = "actions";
    const btnUp = document.createElement("button");
    btnUp.className = "sort-btn";
    btnUp.title = "上移";
    btnUp.innerHTML = SVG_UP;
    btnUp.onclick = () => moveCard(s.id, -1);
    const btnDown = document.createElement("button");
    btnDown.className = "sort-btn";
    btnDown.title = "下移";
    btnDown.innerHTML = SVG_DOWN;
    btnDown.onclick = () => moveCard(s.id, 1);
    const btnE = document.createElement("button");
    btnE.title = "编辑";
    btnE.textContent = "✎";
    btnE.onclick = () => openEdit(s.id);
    const btnD = document.createElement("button");
    btnD.title = "删除";
    btnD.textContent = "🗑";
    btnD.onclick = () => delService(s.id);
    actions.append(btnUp, btnDown, btnE, btnD);
    el.appendChild(actions);
  }
  return el;
}

/* ---------- 排序:卡片(随机数 100~500,取中间值/重置)/ 分类 ---------- */

function reorderPayload() {
  const cats = [...new Set(state.services.map((s) => s.category))];
  const services = {};
  for (const c of cats) {
    services[c] = state.services.filter((s) => s.category === c).map((s) => ({ id: s.id, sort: s.sort_order }));
  }
  return { categories: cats, services };
}

async function saveOrder() {
  await api("/api/reorder", { method: "POST", body: JSON.stringify(reorderPayload()) });
  await load();
}

function moveCard(id, dir) {
  const arr = state.services;
  const idx = arr.findIndex((s) => s.id === id);
  if (idx < 0) return;
  const cat = arr[idx].category;
  const inCat = arr.filter((s) => s.category === cat);
  const ci = inCat.findIndex((s) => s.id === id);
  const target = ci + dir;
  if (target < 0 || target >= inCat.length) return;
  // 取出并插入目标位置
  const [item] = inCat.splice(ci, 1);
  inCat.splice(target, 0, item);

  // 在目标区间内挑选新排序随机数
  const prev = target > 0 ? inCat[target - 1].sort_order : null;
  const next = target < inCat.length - 1 ? inCat[target + 1].sort_order : null;
  let newSort = null;
  if (prev === null && next !== null) newSort = next > 100 ? next - 1 : null;          // 移到最前
  else if (next === null && prev !== null) newSort = prev < 500 ? prev + 1 : null;    // 移到最后
  else if (prev !== null && next !== null && next - prev >= 2) newSort = prev + Math.floor((next - prev) / 2); // 中间有空隙
  if (newSort === null) {
    // 无整数可用:重置该分类全部随机数,均匀分配,目标顺序不变
    const n = inCat.length;
    inCat.forEach((s, j) => { s.sort_order = n > 1 ? Math.round(100 + (j * 400) / (n - 1)) : 100; });
  } else {
    item.sort_order = newSort;
  }
  // 按分类顺序 + 排序值重排
  const cats = [...new Set(arr.map((s) => s.category))];
  state.services = arr.filter((s) => s.category !== cat).concat(inCat)
    .sort((a, b) => {
      const ra = cats.indexOf(a.category), rb = cats.indexOf(b.category);
      if (ra !== rb) return ra - rb;
      return a.sort_order - b.sort_order;
    });
  saveOrder().catch((e) => alert("排序保存失败: " + e.message));
}

function moveCategory(catName, dir) {
  const cats = [...new Set(state.services.map((s) => s.category))];
  const i = cats.indexOf(catName);
  const j = i + dir;
  if (j < 0 || j >= cats.length) return;
  [cats[i], cats[j]] = [cats[j], cats[i]];
  state.services.sort((a, b) => cats.indexOf(a.category) - cats.indexOf(b.category));
  saveOrder().catch((e) => alert("排序保存失败: " + e.message));
}

function renameCategory(oldName) {
  const newName = prompt("将分类「" + oldName + "」重命名为:", oldName);
  if (!newName || !newName.trim() || newName.trim() === oldName) return;
  api("/api/category/rename", {
    method: "POST",
    body: JSON.stringify({ old: oldName, new: newName.trim() }),
  })
    .then(() => load())
    .catch((e) => alert("重命名失败: " + e.message));
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

/* ---------- 服务弹窗 ---------- */

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
  const res = await fetch("/api/export", {
    headers: state.token ? { Authorization: "Bearer " + state.token } : {},
  });
  if (!res.ok) { alert("导出失败: " + res.status); return; }
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

/* ---------- 改密码 / 退出 ---------- */

$("#btn-pwd").addEventListener("click", () => {
  pwdDlg.querySelector("form").reset();
  pwdDlg.showModal();
});

pwdDlg.addEventListener("close", async () => {
  if (pwdDlg.returnValue !== "ok") return;
  const f = pwdDlg.querySelector("form");
  const oldP = f.old.value;
  const newP = f.new.value;
  const confirmP = f.confirm.value;
  if (newP.length < 6) { alert("新密码至少 6 位"); return; }
  if (newP !== confirmP) { alert("两次输入的新密码不一致"); return; }
  try {
    await api("/api/admin/password", {
      method: "POST",
      body: JSON.stringify({ old_password: oldP, new_password: newP }),
    });
    alert("密码已修改 ✓");
    f.reset();
  } catch (e) {
    alert("修改失败: " + e.message);
  }
});

$("#btn-logout").addEventListener("click", async () => {
  try { await api("/api/admin/logout", { method: "POST" }); } catch {}
  state.token = null;
  localStorage.removeItem("navi_token");
  location.href = "/";
});

/* ---------- 事件绑定 ---------- */

$("#btn-edit").addEventListener("click", toggleEdit);
$("#btn-export").addEventListener("click", exportJson);
$("#btn-import").addEventListener("click", () => $("#file-import").click());
$("#btn-add").addEventListener("click", openAdd);

/* ---------- 图标缓存管理 ---------- */

$("#btn-clear-icons").addEventListener("click", async () => {
  if (!confirm("清空全部图标缓存并重新抓取?")) return;
  try {
    const r = await api("/api/favicon/all", { method: "DELETE" });
    alert(`已清除 ${r.cleared} 个图标缓存,重新抓取中…`);
    await load();
  } catch (e) {
    alert("操作失败: " + e.message);
  }
});

$("#btn-refresh-icon").addEventListener("click", async () => {
  const url = form.url.value.trim();
  if (!url) { alert("请先填写服务地址"); return; }
  try {
    const r = await api("/api/favicon?u=" + encodeURIComponent(url), { method: "DELETE" });
    alert(`图标缓存已清除${r.cleared ? "(" + r.cleared + " 个文件)" : ""},重新抓取中…`);
    await load();
  } catch (e) {
    alert("操作失败: " + e.message);
  }
});

init().catch((e) => {
  app.innerHTML = `<div class="empty">加载失败: ${esc(e.message)}</div>`;
});
