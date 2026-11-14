// Chess Reader page: photo -> server -> moves with marks -> PGN.
(function () {
  "use strict";
  const API = (window.CHESS_READER_API || "").replace(/\/$/, "");
  // Photos are sent in good resolution: the server reads a smaller copy, and cuts zoomed
  // crops of doubtful moves from the full-size one. Two photos must stay under ~4 MB.
  const MAX_SIDE = 2400;
  // How many photos one game may have. Stage 1: one. Later: 2nd page of the sheet,
  // opponent's sheet (the server already accepts several "files").
  // 2nd photo: the opponent's sheet of the same game or the 2nd page (the server tells them apart).
  const MAX_PHOTOS = 2;

  const T = {
    de: {
      title: "Partieformular → PGN",
      subtitle: "Handschriftliche Partien schnell digitalisieren",
      s1: "Foto", s2: "Erkennung", s3: "PGN",
      selected: "Ausgewähltes Foto", send: "Ausgewähltes Foto senden", replace: "Anderes Foto wählen",
      add: "Weiteres Foto hinzufügen", remove: "Foto entfernen",
      second: "Tipp: Füge ein zweites Foto hinzu – das Formular des Gegners zur selben Partie oder die zweite Seite. Dann werden die Züge zuverlässiger erkannt.",
      intro: "Fotografiere ein handschriftliches Partieformular. Die App liest die Züge, prüft sie nach den Schachregeln, markiert unsichere Stellen und erstellt eine PGN-Datei.",
      privacy: "Hinweis: Das Foto wird zur Erkennung an den KI-Anbieter Anthropic gesendet und auf unserem Server gespeichert, um die Erkennung zu verbessern. Lade nur Formulare hoch, mit deren Weitergabe du einverstanden bist.",
      camera: "Foto aufnehmen", upload: "Bild hochladen",
      tips: "Tipps: Formular flach hinlegen, gutes Licht, ganzes Formular im Bild.",
      busy: "Formular wird gelesen … das kann bis zu einer Minute dauern.",
      header: "Partiedaten", white: "Weiß", black: "Schwarz", event: "Turnier", site: "Ort", date: "Datum", round: "Runde", result: "Ergebnis",
      opening: "Eröffnung", moves: "Züge", "l-ok": "sicher", "l-fixed": "automatisch korrigiert", "l-doubtful": "bitte prüfen",
      download: "PGN herunterladen", copy: "PGN kopieren", copied: "Kopiert", again: "Neues Formular",
      history: "Meine Partien", history_hint: "Gespeichert nur in diesem Browser auf diesem Gerät.",
      open: "Öffnen", del: "Löschen", del_sure: "Wirklich löschen?", last: "zuletzt", unnamed: "Partie ohne Namen",
      lichess: "In Lichess öffnen", lichess_busy: "Lichess wird geöffnet …",
      lichess_failed: "Lichess hat die Partie gerade nicht angenommen (vielleicht zu viele Uploads). Die PGN ist kopiert: auf der geöffneten Lichess-Seite einfügen.",
      footer: "STRATEG Stuttgart · Partieformular-Leser",
      written: "Auf dem Formular", alternatives: "Andere Möglichkeiten", missing: "Dieser Zug fehlt auf dem Formular und wurde aus der Stellung ergänzt.",
      fill: "Leeres Feld: Zug aus der Stellung ergänzt.", similar: "Ähnlich geschriebener legaler Zug gewählt.", alternative: "Vom KI-Modell als zweite Lesart vorgeschlagen.", exact: "Wie geschrieben.",
      summary: (n, f, d) => `${n} Halbzüge · ${f} automatisch korrigiert · ${d} bitte prüfen`,
      skipped: (s) => `Nicht verwendete Felder: ${s}`,
      e_daily_limit: "Das Tageslimit ist erreicht. Bitte versuche es morgen wieder.",
      e_model_error: "Das Formular konnte nicht gelesen werden: ", e_network: "Keine Verbindung zum Server.",
      e_too_large: "Das Foto ist zu groß.", e_other: "Fehler: ",
      e_server: (c) => c === 504 ? "Der Server hat zu lange gebraucht (504). Bitte noch einmal versuchen." : `Serverfehler (${c}). Bitte noch einmal versuchen.`,
      tap_hint: "Tippe auf einen Zug, um ihn zu korrigieren.", user: "Von dir bestätigt.", fix_ok: "stimmt", fix_ph: "anderer Zug, z. B. Thd1", fix_go: "OK",
      undo: "↶ Letzte Korrektur rückgängig", did_you_mean: "Meintest du:", fixing: "Rest der Partie wird neu berechnet …", fix_failed: "Hat nicht geklappt: ",
    },
    ru: {
      title: "Бланк партии → PGN",
      subtitle: "Быстро переводим рукописные партии в цифру",
      s1: "Фото", s2: "Распознавание", s3: "PGN",
      selected: "Выбранное фото", send: "Отправить выбранное фото", replace: "Выбрать другое фото",
      add: "Добавить ещё фото", remove: "Убрать фото",
      second: "Совет: добавьте второе фото — бланк соперника этой же партии или вторую страницу. Тогда ходы распознаются надёжнее.",
      intro: "Сфотографируйте рукописный бланк партии. Приложение прочитает ходы, проверит их по правилам шахмат, отметит сомнительные места и подготовит файл PGN.",
      privacy: "Обратите внимание: фото отправляется на распознавание в Anthropic (поставщик ИИ) и сохраняется на нашем сервере для улучшения распознавания. Загружайте только бланки, которыми вы готовы поделиться.",
      camera: "Сделать фото", upload: "Загрузить файл",
      tips: "Советы: положите бланк ровно, хорошее освещение, весь бланк в кадре.",
      busy: "Читаю бланк … это может занять до минуты.",
      header: "Данные партии", white: "Белые", black: "Чёрные", event: "Турнир", site: "Место", date: "Дата", round: "Тур", result: "Результат",
      opening: "Дебют", moves: "Ходы", "l-ok": "уверенно", "l-fixed": "исправлено автоматически", "l-doubtful": "проверьте",
      download: "Скачать PGN", copy: "Копировать PGN", copied: "Скопировано", again: "Новый бланк",
      history: "Мои партии", history_hint: "Хранятся только в этом браузере на этом устройстве.",
      open: "Открыть", del: "Удалить", del_sure: "Точно удалить?", last: "последняя", unnamed: "Партия без названия",
      lichess: "Открыть в Lichess", lichess_busy: "Открываю Lichess …",
      lichess_failed: "Lichess сейчас не принял партию (возможно, слишком много загрузок подряд). PGN скопирован: вставьте его на открывшейся странице Lichess.",
      footer: "STRATEG Stuttgart · распознаватель бланков",
      written: "На бланке", alternatives: "Другие варианты", missing: "Этого хода нет на бланке, он восстановлен по позиции.",
      fill: "Пустая клетка: ход восстановлен по позиции.", similar: "Выбран легальный ход, похожий по написанию.", alternative: "Второй вариант прочтения от модели.", exact: "Как написано.",
      summary: (n, f, d) => `${n} полуходов · ${f} исправлено автоматически · ${d} проверьте`,
      skipped: (s) => `Неиспользованные клетки: ${s}`,
      e_daily_limit: "Дневной лимит исчерпан. Попробуйте завтра.",
      e_model_error: "Не удалось прочитать бланк: ", e_network: "Нет связи с сервером.",
      e_too_large: "Фото слишком большое.", e_other: "Ошибка: ",
      e_server: (c) => c === 504 ? "Сервер не успел ответить (504). Попробуйте ещё раз." : `Ошибка сервера (${c}). Попробуйте ещё раз.`,
      tap_hint: "Нажмите на ход, чтобы исправить его.", user: "Подтверждено вами.", fix_ok: "верно", fix_ph: "другой ход, напр. Thd1", fix_go: "OK",
      undo: "↶ Отменить последнее исправление", did_you_mean: "Может быть:", fixing: "Пересчитываю остаток партии …", fix_failed: "Не получилось: ",
    },
  };

  let lang = pick(localGet("lang") || (navigator.language || "de").slice(0, 2));
  let state = null;   // last server result
  let photos = [];    // selected photos: [{blob, url}], sent only after the user confirms
  let currentId = null;  // id of the shown game in the browser history (IndexedDB)
  let resultPhotoUrl = null;

  // ---- History: every recognised game is kept in this browser (IndexedDB), so it
  // survives closing the browser and needs no new upload (no extra cost).
  const DB = (() => {
    let dbp = null;
    function open() {
      if (!dbp) dbp = new Promise((res, rej) => {
        if (!window.indexedDB) return rej(new Error("no indexedDB"));
        const r = indexedDB.open("chess-reader", 1);
        r.onupgradeneeded = () => r.result.createObjectStore("games", { keyPath: "id" });
        r.onsuccess = () => res(r.result);
        r.onerror = () => rej(r.error);
      });
      return dbp;
    }
    async function run(mode, fn) {
      const db = await open();
      return new Promise((res, rej) => {
        const tx = db.transaction("games", mode);
        const req = fn(tx.objectStore("games"));
        tx.oncomplete = () => res(req && req.result);
        tx.onerror = tx.onabort = () => rej(tx.error);
      });
    }
    return {
      put: (g) => run("readwrite", (st) => st.put(g)),
      get: (id) => run("readonly", (st) => st.get(id)),
      all: () => run("readonly", (st) => st.getAll()),
      del: (id) => run("readwrite", (st) => st.delete(id)),
    };
  })();

  async function saveGame(g) {
    try { await DB.put(g); }
    catch (e) {
      // Some browsers refuse to store photos: keep the game without its photo.
      try { const c = Object.assign({}, g); delete c.photo; await DB.put(c); } catch (e2) { /* storage unavailable */ }
    }
  }
  const $ = (id) => document.getElementById(id);

  function pick(l) { return T[l] ? l : "de"; }
  function localGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function localSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } }
  function t(k) { return T[lang][k]; }

  function applyLang() {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-t]").forEach((el) => {
      const v = T[lang][el.dataset.t];
      if (typeof v === "string") el.textContent = v;
    });
    document.querySelectorAll(".lang button").forEach((b) => b.classList.toggle("on", b.dataset.lang === lang));
    document.title = t("title");
    if (state) renderResult();
    renderSelected();
    renderHistory();
  }

  function show(step) {
    ["step-upload", "step-busy", "step-error", "step-result"].forEach((s) => ($(s).hidden = s !== step));
    const n = { "step-upload": 1, "step-busy": 2, "step-error": 2, "step-result": 3 }[step];
    document.querySelectorAll("#steps li").forEach((li) => {
      const k = +li.dataset.step;
      li.className = k < n ? "done" : k === n ? "now" : "";
    });
    window.scrollTo(0, 0);
  }

  async function resize(file) {
    const img = await new Promise((res, rej) => {
      const i = new Image();
      i.onload = () => res(i); i.onerror = rej;
      i.src = URL.createObjectURL(file);
    });
    const k = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight));
    const c = document.createElement("canvas");
    c.width = Math.round(img.naturalWidth * k); c.height = Math.round(img.naturalHeight * k);
    c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
    return await new Promise((res) => c.toBlob(res, "image/jpeg", 0.82));
  }

  // Step 1: the user picks a photo. We only show it; nothing is sent yet.
  async function addPhoto(file) {
    if (!file) return;
    let blob;
    try { blob = await resize(file); } catch (e) { blob = file; }
    if (photos.length >= MAX_PHOTOS) clearPhotos();   // with one photo: "pick again" replaces it
    photos.push({ blob, url: URL.createObjectURL(blob) });
    $("camera").value = ""; $("file").value = "";
    renderSelected();
  }

  function removePhoto(i) {
    URL.revokeObjectURL(photos[i].url);
    photos.splice(i, 1);
    renderSelected();
  }

  function clearPhotos() {
    photos.forEach((p) => URL.revokeObjectURL(p.url));
    photos = [];
  }

  function renderSelected() {
    const has = photos.length > 0;
    $("selected").hidden = !has;
    $("send-buttons").hidden = !has;
    // Pick buttons: shown while nothing is chosen, or while more photos may be added.
    $("pick-buttons").hidden = has && photos.length >= MAX_PHOTOS;
    $("replace").hidden = MAX_PHOTOS > 1;
    $("second-hint").hidden = photos.length !== 1 || MAX_PHOTOS < 2;
    $("camera-btn").classList.toggle("primary", !has);   // with a photo chosen, "send" is the main button
    const box = $("thumbs");
    box.innerHTML = "";
    photos.forEach((p, i) => {
      const fig = document.createElement("figure");
      fig.className = "thumb";
      const img = document.createElement("img");
      img.src = p.url; img.alt = "";
      const x = document.createElement("button");
      x.className = "remove"; x.type = "button"; x.textContent = "×";
      x.title = t("remove"); x.setAttribute("aria-label", t("remove"));
      x.onclick = () => removePhoto(i);
      fig.append(img, x);
      box.appendChild(fig);
    });
  }

  // Step 2: the user confirmed. Send all selected photos to the server.
  async function send() {
    if (!photos.length) return;
    $("preview-busy").src = photos[0].url; $("preview").src = photos[0].url; $("preview").hidden = false;
    show("step-busy");
    const form = new FormData();
    photos.forEach((p, i) => form.append("files", p.blob, `sheet-${i + 1}.jpg`));
    const adminToken = localGet("admin_token");
    if (adminToken) {
      form.append("admin", adminToken);
      if ($("admin-model").value) form.append("model", $("admin-model").value);
      if ($("admin-ref").value) form.append("ref", $("admin-ref").value);
    }
    let resp, data;
    const started = Date.now();
    try {
      resp = await fetch(API + "/api/process", { method: "POST", body: form });
    } catch (e) {
      // the host's own error pages (time-out) carry no CORS headers and look like a lost connection
      return fail(Date.now() - started > 200000 ? t("e_server")(504) : t("e_network"));
    }
    try { data = await resp.json(); } catch (e) {
      // not our JSON: the host answered (too large, took too long, crashed)
      return fail(resp.status === 413 ? t("e_too_large") : t("e_server")(resp.status));
    }
    if (!resp.ok) {
      const code = data && data.error;
      if (code === "daily_limit") return fail(t("e_daily_limit"));
      if (code === "model_error") return fail(t("e_model_error") + (data.message || ""));
      if (code === "too_large") return fail(t("e_too_large"));
      return fail(t("e_other") + (data && (data.message || data.detail) || resp.status));
    }
    state = data;
    currentId = String(Date.now());
    await saveGame({ id: currentId, created: Date.now(), header: data.header, plies: data.plies, pgn: data.pgn,
      skipped_cells: data.skipped_cells || [], cells: data.cells || null, language: data.language || "de",
      photo: photos[0].blob });
    fillHeader(data.header);
    undoState = null; $("undo").hidden = true;
    renderResult();
    showAdminResult(data.admin);
    show("step-result");
  }

  // ---- Hidden admin test mode: choose the model and a reference game per upload.
  function initAdmin() {
    const m = location.hash.match(/admin=([^&]+)/);
    if (m) {
      localSet("admin_token", decodeURIComponent(m[1]));
      history.replaceState(null, "", location.pathname + location.search);   // token out of the address bar
    }
    const on = !!localGet("admin_token");
    $("admin").hidden = !on;
    if (!on) return;
    $("admin-model").value = localGet("admin_model") || "";
    $("admin-model").onchange = () => localSet("admin_model", $("admin-model").value);
    $("admin-off").onclick = () => {
      try { localStorage.removeItem("admin_token"); } catch (e) { /* ignore */ }
      $("admin").hidden = true;
    };
  }

  function showAdminResult(a) {
    const el = $("admin-result");
    el.hidden = !a;
    if (!a) return;
    let txt = `Модель: ${a.model} · вызовов: ${state.model_calls} · стоимость: ${(a.cost_eur * 100).toFixed(2)} ct`;
    if (a.escalated) txt += " · Haiku сомневалась, перечитано через Sonnet";
    if (a.accuracy) txt += ` · совпадение с эталоном ${a.accuracy.ref}: ${a.accuracy.match_until} из ${a.accuracy.ref_plies} полуходов (${a.accuracy.match_pct}%)`;
    el.textContent = txt;
  }

  async function openGame(id) {
    let g;
    try { g = await DB.get(id); } catch (e) { return; }
    if (!g) return;
    $("admin-result").hidden = true;
    currentId = g.id;
    state = { header: g.header, plies: g.plies, pgn: g.pgn, skipped_cells: g.skipped_cells,
      cells: g.cells || null, language: g.language || "de" };
    if (resultPhotoUrl) URL.revokeObjectURL(resultPhotoUrl);
    resultPhotoUrl = g.photo ? URL.createObjectURL(g.photo) : null;
    $("preview").hidden = !resultPhotoUrl;
    if (resultPhotoUrl) $("preview").src = resultPhotoUrl;
    fillHeader(g.header);
    undoState = null; $("undo").hidden = true;
    renderResult();
    show("step-result");
  }

  // Header edits are saved too, so the corrected names stay with the game.
  let saveTimer = null;
  function saveHeaderSoon() {
    if (!currentId) return;
    clearTimeout(saveTimer);
    const id = currentId, h = header();
    saveTimer = setTimeout(async () => {
      try { const g = await DB.get(id); if (g) { g.header = h; await saveGame(g); } } catch (e) { /* ignore */ }
    }, 400);
  }

  function gameTitle(h) {
    const w = h.white && h.white !== "?" ? h.white : "", b = h.black && h.black !== "?" ? h.black : "";
    return w || b ? `${w || "?"} – ${b || "?"}` : t("unnamed");
  }

  async function renderHistory() {
    let games = [];
    try { games = await DB.all(); } catch (e) { /* no storage */ }
    games.sort((a, b) => b.created - a.created);
    $("history").hidden = !games.length;
    const list = $("history-list");
    list.querySelectorAll("img").forEach((i) => URL.revokeObjectURL(i.src));
    list.innerHTML = "";
    games.forEach((g, i) => {
      const li = document.createElement("li");
      li.className = "game";
      const thumb = document.createElement(g.photo ? "img" : "div");
      thumb.className = "gthumb";
      if (g.photo) { thumb.src = URL.createObjectURL(g.photo); thumb.alt = ""; }
      const info = document.createElement("button");
      info.type = "button"; info.className = "ginfo";
      const h = g.header || {};
      const op = openingFrom(g.pgn);
      const meta = [h.result && h.result !== "*" ? h.result : "", op ? op.local : "", h.event && h.event !== "?" ? h.event : "",
        new Date(g.created).toLocaleString(lang === "ru" ? "ru-RU" : "de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })]
        .filter(Boolean).join(" · ");
      info.innerHTML = `<b>${esc(gameTitle(h))}</b>${i === 0 ? ` <span class="tag">${esc(t("last"))}</span>` : ""}<small>${esc(meta)}</small>`;
      info.title = t("open");
      info.onclick = () => openGame(g.id);
      const del = document.createElement("button");
      del.type = "button"; del.className = "gdel"; del.textContent = "🗑"; del.title = t("del"); del.setAttribute("aria-label", t("del"));
      // Two taps to delete (no pop-up dialog): first tap asks, second deletes.
      del.onclick = async () => {
        if (!del.classList.contains("sure")) {
          del.classList.add("sure"); del.textContent = t("del_sure");
          setTimeout(() => { del.classList.remove("sure"); del.textContent = "🗑"; }, 3000);
          return;
        }
        try { await DB.del(g.id); } catch (e) { /* ignore */ }
        if (currentId === g.id) currentId = null;
        renderHistory();
      };
      li.append(thumb, info, del);
      list.appendChild(li);
    });
  }

  function fail(msg) { $("error-text").textContent = msg; show("step-error"); }

  function fillHeader(h) {
    for (const k of ["white", "black", "event", "site", "round"]) $("h-" + k).value = h[k] === "?" ? "" : (h[k] || "");
    $("h-date").value = (h.date || "").includes("?") ? "" : (h.date || "");
    $("h-result").value = h.result || "*";
  }

  function header() {
    const h = {};
    for (const k of ["white", "black", "event", "site", "date", "round"]) h[k] = $("h-" + k).value.trim() || (k === "date" ? "????.??.??" : "?");
    h.result = $("h-result").value;
    return h;
  }

  function renderResult() {
    const body = $("moves");
    body.innerHTML = "";
    const plies = state.plies;
    for (let i = 0; i < plies.length; i += 2) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td class="n">${i / 2 + 1}.</td><td></td><td></td>`;
      [plies[i], plies[i + 1]].forEach((p, j) => {
        if (!p) return;
        const s = document.createElement("span");
        s.className = "m " + p.status + (p.reason === "user" ? " user" : "");
        s.dataset.ply = p.ply;
        s.textContent = p.local;
        s.tabIndex = 0;
        s.onkeydown = (e) => { if (e.key === "Enter") showDetail(p, s); };
        s.onclick = () => showDetail(p, s);
        tr.children[j + 1].appendChild(s);
      });
      body.appendChild(tr);
    }
    const f = plies.filter((p) => p.status === "fixed").length;
    const d = plies.filter((p) => p.status === "doubtful").length;
    let sum = t("summary")(plies.length, f, d);
    if (state.skipped_cells && state.skipped_cells.length)
      sum += " · " + t("skipped")(state.skipped_cells.map((c) => `${c.number || "?"}${c.color === "b" ? "…" : "."} ${c.text}`).join(", "));
    $("summary").textContent = sum;
    DETAIL.hidden = true;
    $("pgn").textContent = state.pgn;
    showOpening();
  }

  // ---- Opening name: the server writes [ECO] and [Opening] (English) into the PGN;
  // here the family part is translated (docs/openings.js).
  function openingFrom(pgn) {
    const tag = (k) => { const m = (pgn || "").match(new RegExp(`\\[${k} "([^"]*)"\\]`)); return m ? m[1] : ""; };
    const name = tag("Opening"), eco = tag("ECO");
    if (!name) return null;
    const i = name.indexOf(":");
    const family = i < 0 ? name : name.slice(0, i), variation = i < 0 ? "" : name.slice(i + 1).trim();
    const tr = (window.OPENING_NAMES || {})[family];
    const local = tr ? tr[lang === "ru" ? 0 : 1] : family;
    return { eco, name, local, variation: tr ? name : variation };
  }

  function showOpening() {
    const o = openingFrom(state && state.pgn), el = $("opening");
    el.hidden = !o;
    if (!o) return;
    el.innerHTML = `<b>${esc(t("opening"))}:</b> ${esc(o.local)}${o.eco ? ` <span class="eco">${esc(o.eco)}</span>` : ""}` +
      (o.variation ? `<small>${esc(o.variation)}</small>` : "");
  }

  // Detail of one move, shown right under its row: what was written, and a quick fix:
  // tap "correct" or another reading, or type the move. The server then decodes the
  // rest of the game again (no model call, free).
  const DETAIL = $("detail");
  let detailPly = -1;

  function showDetail(p, el) {
    document.querySelectorAll(".m.sel").forEach((x) => x.classList.remove("sel"));
    el.classList.add("sel");
    detailPly = p.ply;
    const n = Math.floor(p.ply / 2) + 1 + (p.ply % 2 ? "… " : ". ");
    const reason = p.reason === "user" ? t("user") : t(p.reason) || "";
    let html = `<div><b>${n}${esc(p.local)}</b> — ${esc(reason)}`;
    if (p.written) html += `<br>${esc(t("written"))}: «${esc(p.written)}»`;
    html += `</div><div class="fix-chips"></div>
      <form class="fix-form"><input class="fix-text" autocomplete="off" autocapitalize="off" spellcheck="false"
        placeholder="${esc(t("fix_ph"))}" aria-label="${esc(t("fix_ph"))}"><button class="btn small" type="submit">${esc(t("fix_go"))}</button></form>
      <p class="fix-msg" hidden></p><div class="fix-options" hidden></div>`;
    DETAIL.innerHTML = html;
    const chips = DETAIL.querySelector(".fix-chips");
    if (p.reason !== "user") chips.appendChild(chip(`✓ ${p.local} ${t("fix_ok")}`, { san: p.san }, "ok"));
    (p.alternatives || []).forEach((a) => chips.appendChild(chip(a, { text: a })));
    DETAIL.querySelector(".fix-form").onsubmit = (e) => {
      e.preventDefault();
      const v = DETAIL.querySelector(".fix-text").value.trim();
      if (v) fixMove(p.ply, { text: v });
    };
    // put the box right under the row of this move (phones: no scrolling to the bottom)
    const tr = el.closest("tr");
    let row = DETAIL.closest("tr.detail-row");
    if (!row) {
      row = document.createElement("tr");
      row.className = "detail-row";
      row.appendChild(document.createElement("td")).colSpan = 3;
    }
    row.firstChild.appendChild(DETAIL);
    tr.after(row);
    DETAIL.hidden = false;
    if (fixing) busy(true);
  }

  // While the server recalculates: show it and block more taps (a second fix would use old moves)
  function busy(on) {
    DETAIL.classList.toggle("busy-fix", on);
    DETAIL.querySelectorAll("button, input").forEach((x) => (x.disabled = on));
    const msg = DETAIL.querySelector(".fix-msg");
    if (msg && on) { msg.hidden = false; msg.className = "fix-msg"; msg.textContent = t("fixing"); }
  }

  function chip(label, move, cls) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip " + (cls || ""); b.textContent = label;
    b.onclick = () => fixMove(detailPly, move);
    return b;
  }

  // One step back after a fix (a wrong choice can change the rest of the game a lot).
  let undoState = null;
  function applyMoves(data) {
    Object.assign(state, { plies: data.plies, cells: data.cells, skipped_cells: data.skipped_cells, pgn: data.pgn });
    if (currentId) {
      const id = currentId;
      DB.get(id).then((g) => {
        if (!g) return;
        Object.assign(g, { plies: data.plies, cells: data.cells, skipped_cells: data.skipped_cells, pgn: data.pgn, header: header() });
        return saveGame(g);
      }).catch(() => {});
    }
    renderResult();
    $("undo").hidden = !undoState;
  }
  $("undo").onclick = () => {
    if (!undoState || fixing) return;
    const u = undoState;
    undoState = null;
    applyMoves(u);
  };

  let fixing = false;
  async function fixMove(k, move) {
    if (fixing) return;
    fixing = true;
    DETAIL.querySelector(".fix-options").hidden = true;
    busy(true);
    let resp, data;
    try {
      resp = await fetch(API + "/api/redecode", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.assign({ header: header(), plies: state.plies, cells: state.cells || null,
          ply: k, language: state.language || "de" }, move)),
      });
      data = await resp.json();
    } catch (e) {
      data = null;
    }
    fixing = false;
    busy(false);
    if (!resp || !data || !resp.ok) {
      if (detailPly !== k || DETAIL.hidden) return;   // the person already looks at another move
      const msg = DETAIL.querySelector(".fix-msg"), opts = DETAIL.querySelector(".fix-options");
      msg.className = "fix-msg bad"; msg.hidden = false;
      msg.textContent = t("fix_failed") + (!data ? t("e_network") : data.message || resp.status);
      if (data && data.options && data.options.length) {
        msg.textContent = t("did_you_mean");
        msg.className = "fix-msg";
        opts.innerHTML = "";
        data.options.forEach((o) => opts.appendChild(chip(o, { text: o })));
        opts.hidden = false;
      }
      return;
    }
    undoState = { plies: state.plies, cells: state.cells, skipped_cells: state.skipped_cells, pgn: state.pgn };
    applyMoves(data);
    // go on with the next move that needs a look, if there is one
    const next = state.plies.find((p) => p.ply > k && p.status === "doubtful");
    const el = next && document.querySelector(`#moves .m[data-ply="${next.ply}"]`);
    if (el) showDetail(next, el);
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  async function currentPgn() {
    try {
      const resp = await fetch(API + "/api/pgn", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ header: header(), moves: state.plies }),
      });
      const data = await resp.json();
      if (!data.pgn) throw new Error("no pgn");
      $("pgn").textContent = data.pgn;
      state.pgn = data.pgn;
      showOpening();
      if (currentId) { const id = currentId; DB.get(id).then((g) => { if (g) { g.pgn = data.pgn; g.header = header(); return saveGame(g); } }).catch(() => {}); }
      return data.pgn;
    } catch (e) {
      return state.pgn;   // offline: the PGN saved with the game
    }
  }

  $("download").onclick = async () => {
    const pgn = await currentPgn();
    const h = header();
    const name = [h.white, h.black].filter((x) => x && x !== "?").join("-").replace(/[^\w\-äöüÄÖÜß]+/g, "_") || "partie";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([pgn], { type: "application/x-chess-pgn" }));
    a.download = name + ".pgn";
    a.click();
  };
  $("copy").onclick = async () => {
    const pgn = await currentPgn();
    try { await navigator.clipboard.writeText(pgn); $("copy").textContent = t("copied"); setTimeout(() => ($("copy").textContent = t("copy")), 1500); } catch (e) { /* ignore */ }
  };
  // Lichess: import through its public API (no login needed) and open the game.
  // The tab is opened right away, before any waiting, so phones do not block it as a pop-up.
  $("lichess").onclick = async () => {
    const btn = $("lichess");
    const win = window.open("about:blank", "_blank");
    btn.disabled = true; btn.textContent = t("lichess_busy");
    let pgn = "";
    try {
      pgn = await currentPgn();
      const resp = await fetch("https://lichess.org/api/import", {
        method: "POST", headers: { Accept: "application/json" }, body: new URLSearchParams({ pgn }),
      });
      const data = await resp.json();
      if (!resp.ok || !data.url) throw new Error(resp.status);
      if (win) win.location.href = data.url; else location.href = data.url;
    } catch (e) {
      // Fallback: copy the PGN and open the manual import page.
      try { if (pgn) await navigator.clipboard.writeText(pgn); } catch (e2) { /* ignore */ }
      if (win) win.location.href = "https://lichess.org/paste";
      alert(t("lichess_failed"));
    } finally {
      btn.disabled = false; btn.textContent = t("lichess");
    }
  };
  // New sheet: forget everything. After an error: keep the photo so it can be sent again.
  $("again").onclick = () => { $("admin-result").hidden = true; state = null; currentId = null; clearPhotos(); renderSelected(); renderHistory(); show("step-upload"); };
  $("again-error").onclick = () => { state = null; renderSelected(); show("step-upload"); };
  $("camera").onchange = (e) => addPhoto(e.target.files[0]);
  $("file").onchange = (e) => addPhoto(e.target.files[0]);
  $("send").onclick = send;
  $("replace").onclick = () => { clearPhotos(); renderSelected(); };
  document.querySelectorAll(".lang button").forEach((b) => (b.onclick = () => { lang = b.dataset.lang; localSet("lang", lang); applyLang(); }));
  document.querySelectorAll(".grid input, .grid select").forEach((el) => el.addEventListener("input", saveHeaderSoon));
  initAdmin();
  applyLang();
  show("step-upload");
})();
