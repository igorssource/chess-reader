// Chess Reader page: photo -> server -> moves with marks -> PGN.
(function () {
  "use strict";
  const API = (window.CHESS_READER_API || "").replace(/\/$/, "");
  const MAX_SIDE = 1600;           // resize photos before upload: faster and cheaper
  // How many photos one game may have. Stage 1: one. Later: 2nd page of the sheet,
  // opponent's sheet (the server already accepts several "files").
  const MAX_PHOTOS = 1;

  const T = {
    de: {
      title: "Partieformular → PGN",
      subtitle: "Handschriftliche Partien schnell digitalisieren",
      s1: "Foto", s2: "Erkennung", s3: "PGN",
      selected: "Ausgewähltes Foto", send: "Ausgewähltes Foto senden", replace: "Anderes Foto wählen",
      add: "Weiteres Foto hinzufügen", remove: "Foto entfernen",
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
      review_hint: "Tippe auf einen Zug, um ihn auf dem Brett zu sehen und zu korrigieren. Rote Züge zuerst prüfen.",
      "l-user": "von dir bestätigt", user: "Von dir gewählt.", flip: "⟲ Brett drehen",
      next_doubt: (n) => `Nächsten unsicheren Zug prüfen (${n})`, all_checked: "✓ Alle unsicheren Züge sind geprüft.",
      choose: "Richtiger Zug:", confirm: "✓ Stimmt", all_legal: (n) => `Alle erlaubten Züge (${n})`,
      fixing: "Rest der Partie wird neu berechnet …", fix_failed: "Konnte nicht neu berechnen: ",
      add_move: "+ Zug hinzufügen", add_title: "Neuer Zug am Ende der Partie", start_pos: "Anfangsstellung",
      photo_tap: "Antippen zum Vergrößern.", no_written: "Nicht auf dem Formular.",
      pieces: { K: "König", D: "Dame", T: "Turm", L: "Läufer", S: "Springer", "": "Bauer", "0": "Rochade" },
    },
    ru: {
      title: "Бланк партии → PGN",
      subtitle: "Быстро переводим рукописные партии в цифру",
      s1: "Фото", s2: "Распознавание", s3: "PGN",
      selected: "Выбранное фото", send: "Отправить выбранное фото", replace: "Выбрать другое фото",
      add: "Добавить ещё фото", remove: "Убрать фото",
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
      review_hint: "Нажмите на ход, чтобы увидеть его на доске и исправить. Красные ходы проверьте в первую очередь.",
      "l-user": "проверено вами", user: "Выбрано вами.", flip: "⟲ Перевернуть",
      next_doubt: (n) => `Проверить следующий сомнительный ход (${n})`, all_checked: "✓ Все сомнительные ходы проверены.",
      choose: "Правильный ход:", confirm: "✓ Верно", all_legal: (n) => `Все допустимые ходы (${n})`,
      fixing: "Пересчитываю остаток партии …", fix_failed: "Не удалось пересчитать: ",
      add_move: "+ Добавить ход", add_title: "Новый ход в конце партии", start_pos: "Начальная позиция",
      photo_tap: "Нажмите, чтобы увеличить.", no_written: "На бланке его нет.",
      pieces: { K: "Король", D: "Ферзь", T: "Ладья", L: "Слон", S: "Конь", "": "Пешка", "0": "Рокировка" },
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
    return await new Promise((res) => c.toBlob(res, "image/jpeg", 0.85));
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
    try {
      resp = await fetch(API + "/api/process", { method: "POST", body: form });
      data = await resp.json();
    } catch (e) {
      return fail(t("e_network"));
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
      skipped_cells: data.skipped_cells || [], cells: data.cells || null, layout: data.layout || [],
      language: data.language || "de", photo: photos[0].blob });
    fillHeader(data.header);
    startReview();
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
      cells: g.cells || null, layout: g.layout || [], language: g.language || "de" };
    if (resultPhotoUrl) URL.revokeObjectURL(resultPhotoUrl);
    resultPhotoUrl = g.photo ? URL.createObjectURL(g.photo) : null;
    $("preview").hidden = !resultPhotoUrl;
    if (resultPhotoUrl) $("preview").src = resultPhotoUrl;
    fillHeader(g.header);
    startReview();
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

  // ---- Stage 2: review. Board next to the photo, every move can be checked and fixed by
  // picking from the legal moves; the server then decodes the rest of the game again
  // (no model call, no cost). Positions and legal moves come from chess.js (docs/vendor).
  let sel = -1;          // selected half-move (-1 = start position, plies.length = "add a move")
  let flipped = false;
  let fens = [];         // fens[k] = position before half-move k; fens[n] = final position

  const DE = { N: "S", B: "L", R: "T", Q: "D", K: "K" };
  function localSan(san) {
    // English SAN from chess.js -> German letters, castling with zeros (as the server writes it)
    return san.replace(/[NBRQK]/g, (c) => DE[c]).replace(/O/g, "0");
  }

  function computeFens() {
    const c = new window.Chess();
    fens = [c.fen()];
    for (const p of state.plies) {
      if (!c.move(p.san)) break;
      fens.push(c.fen());
    }
  }

  function startReview() {
    computeFens();
    const first = state.plies.findIndex((p) => p.status === "doubtful");
    renderResult();
    select(first >= 0 ? first : state.plies.length - 1, false);
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
        const s = document.createElement("button");
        s.type = "button";
        s.className = "m " + p.status + (p.reason === "user" ? " user" : "") + (i + j === sel ? " sel" : "");
        s.textContent = p.local;
        s.dataset.ply = i + j;
        s.onclick = () => select(i + j, true);
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
    $("next-doubt").hidden = d === 0;
    $("next-doubt").textContent = t("next_doubt")(d);
    $("all-checked").hidden = d > 0 || !plies.length;
    $("add-move").classList.toggle("sel", sel === plies.length);
    $("pgn").textContent = state.pgn;
    showOpening();
    if (sel >= -1) { renderBoard(); renderEditor(); }
  }

  function moveNo(k) { return Math.floor(k / 2) + 1 + (k % 2 ? "… " : ". "); }

  function select(k, scroll) {
    sel = Math.max(-1, Math.min(k, state.plies.length));
    document.querySelectorAll("#moves .m").forEach((x) => x.classList.toggle("sel", +x.dataset.ply === sel));
    $("add-move").classList.toggle("sel", sel === state.plies.length);
    renderBoard();
    renderEditor();
    if (scroll) {
      const el = document.querySelector(`#moves .m[data-ply="${sel}"]`);
      if (el && el.scrollIntoView) el.scrollIntoView({ block: "nearest" });
    }
  }

  // Board: position after the selected move (before it for "add a move").
  const GLYPH = { k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟" };
  function renderBoard() {
    const n = state.plies.length;
    const after = sel >= n ? n : sel + 1;
    const fen = fens[Math.min(after, fens.length - 1)] || fens[0];
    const rows = fen.split(" ")[0].split("/");
    const grid = [];
    rows.forEach((r) => {
      const row = [];
      for (const ch of r) {
        if (/\d/.test(ch)) for (let i = 0; i < +ch; i++) row.push(null);
        else row.push(ch);
      }
      grid.push(row);
    });
    let from = "", to = "";
    if (sel >= 0 && sel < n && fens[sel]) {
      const c = new window.Chess(fens[sel]);
      const m = c.move(state.plies[sel].san);
      if (m) { from = m.from; to = m.to; }
    }
    const b = $("board");
    b.innerHTML = "";
    for (let ri = 0; ri < 8; ri++) {
      for (let fi = 0; fi < 8; fi++) {
        const r = flipped ? 7 - ri : ri, f = flipped ? 7 - fi : fi;
        const sq = "abcdefgh"[f] + (8 - r);
        const d = document.createElement("div");
        d.className = "sq " + ((r + f) % 2 ? "dark" : "light") + (sq === from || sq === to ? " hl" : "");
        const pc = grid[r][f];
        if (pc) {
          const s = document.createElement("span");
          s.className = "pc " + (pc === pc.toUpperCase() ? "w" : "b");
          s.textContent = GLYPH[pc.toLowerCase()] + "︎";
          d.appendChild(s);
        }
        if (fi === 0) d.insertAdjacentHTML("beforeend", `<i class="rk">${8 - r}</i>`);
        if (ri === 7) d.insertAdjacentHTML("beforeend", `<i class="fl">${"abcdefgh"[f]}</i>`);
        b.appendChild(d);
      }
    }
    $("nav-label").textContent = sel < 0 ? t("start_pos") : sel >= n ? "+" : moveNo(sel) + state.plies[sel].local;
  }

  // Editor for the selected move: zoomed part of the photo, what was written, the choices.
  function renderEditor() {
    const n = state.plies.length;
    const ed = $("editor");
    $("ed-error").hidden = true;
    if (sel < 0 || !fens[Math.min(sel, n)]) { ed.hidden = true; return; }
    ed.hidden = false;
    const p = sel < n ? state.plies[sel] : null;
    const ttl = $("ed-title");
    if (p) {
      ttl.innerHTML = `<span class="m ${p.status}${p.reason === "user" ? " user" : ""}">${esc(moveNo(sel) + p.local)}</span> ` +
        esc(p.reason === "user" ? t("user") : t(p.reason) || "");
    } else {
      ttl.textContent = moveNo(sel) + "… " + t("add_title");
    }
    const info = [];
    if (p) info.push(p.written ? `${esc(t("written"))}: «${esc(p.written)}»` : esc(t("no_written")));
    $("ed-info").innerHTML = info.join("<br>");
    drawCrop(p, sel);

    // Legal moves in this position, in the sheet's notation
    const c = new window.Chess(fens[sel]);
    const legal = c.moves({ verbose: true }).map((m) => ({ san: m.san, local: localSan(m.san), piece: m.piece }));
    const bySan = {}, byLocal = {};
    legal.forEach((m) => { bySan[m.san] = m; byLocal[m.local] = m; });
    const ch = $("ed-choices");
    ch.innerHTML = "";
    const add = (box, m, cls, label) => {
      const btn = document.createElement("button");
      btn.type = "button"; btn.className = "chip " + (cls || "");
      btn.textContent = label || m.local;
      btn.onclick = () => fixMove(sel, m.san);
      box.appendChild(btn);
    };
    if (p) {
      const lab = document.createElement("span");
      lab.className = "choose"; lab.textContent = t("choose");
      ch.appendChild(lab);
      if (bySan[p.san]) add(ch, bySan[p.san], "cur", `${t("confirm")}: ${p.local}`);
      const seen = new Set([p.san]);
      (p.alternatives || []).forEach((a) => {
        const m = byLocal[a] || byLocal[a.replace(/[+#]$/, "")];
        if (m && !seen.has(m.san)) { seen.add(m.san); add(ch, m, "alt"); }
      });
    }
    // all legal moves grouped by piece
    const ORDER = { k: "K", q: "D", r: "T", b: "L", n: "S", p: "" };
    const groups = {};
    legal.forEach((m) => {
      const g = m.san.startsWith("O-O") ? "0" : ORDER[m.piece];
      (groups[g] = groups[g] || []).push(m);
    });
    const box = $("ed-legal");
    box.innerHTML = "";
    ["", "S", "L", "T", "D", "K", "0"].forEach((g) => {
      if (!groups[g]) return;
      const row = document.createElement("div");
      row.className = "lgroup";
      row.innerHTML = `<b>${esc(t("pieces")[g])}</b>`;
      groups[g].sort((a, b) => a.local.localeCompare(b.local)).forEach((m) => add(row, m, p && m.san === p.san ? "cur" : ""));
      box.appendChild(row);
    });
    $("ed-all-sum").textContent = t("all_legal")(legal.length);
    $("ed-all").open = !p || !p.alternatives || !p.alternatives.length;
  }

  // Where the cell of a move is on the photo: the model gives the rectangle of each block
  // of move rows; rows are spread evenly, White on the left half, Black on the right half.
  function cellRect(p, k) {
    const L = state.layout || [];
    if (!L.length) return null;
    const cell = p && p.token != null && state.cells ? state.cells[p.token] : null;
    const num = (cell && cell.number) || Math.floor(k / 2) + 1;
    const color = (cell && cell.color) || (k % 2 ? "b" : "w");
    const b = L.find((x) => num >= x.first_move && num <= x.last_move);
    if (!b) return null;
    const rows = b.last_move - b.first_move + 1, rh = (b.bottom - b.top) / rows;
    const y = b.top + (num - b.first_move) * rh, mid = (b.left + b.right) / 2;
    return { block: b, rh, x0: color === "w" ? b.left : mid, x1: color === "w" ? mid : b.right, y0: y, y1: y + rh };
  }

  function drawCrop(p, k) {
    const cv = $("crop"), img = $("preview");
    const r = cellRect(p, k);
    if (!r || !img.src || !img.naturalWidth) { cv.hidden = true; if (r && img.src) img.onload = () => drawCrop(p, k); return; }
    const W = img.naturalWidth / 1000, H = img.naturalHeight / 1000;
    const bw = r.block.right - r.block.left;
    const sx0 = Math.max(0, r.block.left - bw * 0.12), sx1 = Math.min(1000, r.block.right + bw * 0.04);
    const sy0 = Math.max(0, r.y0 - r.rh * 1.6), sy1 = Math.min(1000, r.y1 + r.rh * 1.6);
    const sw = (sx1 - sx0) * W, sh = (sy1 - sy0) * H;
    const outW = Math.min(900, Math.max(320, sw));
    const scale = outW / sw;
    cv.width = Math.round(outW); cv.height = Math.round(sh * scale);
    const g = cv.getContext("2d");
    g.drawImage(img, sx0 * W, sy0 * H, sw, sh, 0, 0, cv.width, cv.height);
    g.strokeStyle = "#e53935"; g.lineWidth = 3;
    g.strokeRect((r.x0 - sx0) * W * scale, (r.y0 - sy0) * H * scale, (r.x1 - r.x0) * W * scale, (r.y1 - r.y0) * H * scale);
    cv.hidden = false;
  }

  let fixing = false;
  async function fixMove(k, san) {
    if (fixing) return;
    fixing = true;
    $("ed-busy").hidden = false; $("ed-error").hidden = true;
    let data;
    try {
      const resp = await fetch(API + "/api/redecode", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ header: header(), plies: state.plies, cells: state.cells || null, ply: k, san,
          language: state.language || "de" }),
      });
      data = await resp.json();
      if (!resp.ok) throw new Error((data && data.message) || resp.status);
    } catch (e) {
      fixing = false; $("ed-busy").hidden = true;
      $("ed-error").textContent = t("fix_failed") + (e.message === "Failed to fetch" ? t("e_network") : e.message);
      $("ed-error").hidden = false;
      return;
    }
    fixing = false; $("ed-busy").hidden = true;
    state.plies = data.plies; state.cells = data.cells; state.skipped_cells = data.skipped_cells; state.pgn = data.pgn;
    if (currentId) {
      const id = currentId;
      DB.get(id).then((g) => {
        if (!g) return;
        Object.assign(g, { plies: data.plies, cells: data.cells, skipped_cells: data.skipped_cells, pgn: data.pgn, header: header() });
        return saveGame(g);
      }).catch(() => {});
    }
    computeFens();
    // go on with the next doubtful move after this one (or stay here)
    let next = state.plies.findIndex((p, i) => i > k && p.status === "doubtful");
    if (next < 0) next = state.plies.findIndex((p) => p.status === "doubtful");
    sel = next >= 0 ? next : k;
    renderResult();
    select(sel, true);
  }

  $("nav-first").onclick = () => select(-1);
  $("nav-prev").onclick = () => select(sel - 1, true);
  $("nav-next").onclick = () => select(sel + 1, true);
  $("nav-last").onclick = () => select(state.plies.length - 1, true);
  $("flip").onclick = () => { flipped = !flipped; renderBoard(); };
  $("add-move").onclick = () => select(state.plies.length, false);
  $("next-doubt").onclick = () => {
    const ps = state.plies;
    let i = ps.findIndex((p, j) => j > sel && p.status === "doubtful");
    if (i < 0) i = ps.findIndex((p) => p.status === "doubtful");
    if (i >= 0) select(i, true);
  };
  $("preview").onclick = () => $("preview").classList.toggle("zoom");
  document.addEventListener("keydown", (e) => {
    if ($("step-result").hidden || /INPUT|SELECT|TEXTAREA/.test((e.target || {}).tagName || "")) return;
    if (e.key === "ArrowLeft") { select(sel - 1, true); e.preventDefault(); }
    if (e.key === "ArrowRight") { select(sel + 1, true); e.preventDefault(); }
  });

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
