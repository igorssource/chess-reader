// Chess Reader: photo -> server -> the game on a board you can step through.
// The previous look without the board is kept in docs/old/ (same server, same saved games).
(function () {
  "use strict";
  const API = (window.CHESS_READER_API || "").replace(/\/$/, "");
  const MAX_SIDE = 2400;     // see ../app.js: the server cuts zoomed crops from the full-size photo
  const MAX_PHOTOS = 2;      // the sheet + the opponent's sheet or the 2nd page

  const T = {
    de: {
      title: "Partieformular → PGN",
      intro: "Fotografiere ein handschriftliches Partieformular. Die App liest die Züge, prüft sie nach den Schachregeln und zeigt die Partie auf dem Brett.",
      camera: "Foto aufnehmen", upload: "Bild hochladen", send: "Foto senden", send_n: (n) => `${n} Fotos senden`, remove: "Foto entfernen",
      second: "Tipp: Ein zweites Foto (Formular des Gegners oder 2. Seite) macht die Erkennung zuverlässiger.",
      privacy: "Das Foto wird zur Erkennung an den KI-Anbieter Anthropic gesendet und auf unserem Server 90 Tage lang gespeichert, danach automatisch gelöscht. Lade nur Formulare hoch, mit deren Weitergabe du einverstanden bist.",
      tips_title: "Tipps für ein gutes Foto", tips: "Formular flach hinlegen, gutes Licht, ganzes Formular im Bild.",
      busy: "Formular wird gelesen … meist 1–2 Minuten, schwierige Formulare bis 4.", busy2: "Beide Formulare werden gelesen und verglichen … meist 2–3 Minuten, bis 4.",
      busy_hint: "Der Bildschirm bleibt an. Reißt die Verbindung ab, geht nichts verloren: Seite einfach wieder öffnen.",
      busy_wait: "Verbindung unterbrochen – das Ergebnis wird vom Server geholt …",
      e_lost: "Das Ergebnis ist nicht angekommen. Bitte das Foto noch einmal senden.",
      sheets_opp: (lang) => `Foto 2 ist das Formular des Gegners${lang === "en" ? " (englische Notation)" : ""}; beide wurden Zug für Zug verglichen.`,
      sheets_cont: "Foto 2 wurde als Fortsetzung gelesen.", photo_n: (n) => `Foto ${n}`,
      white: "Weiß", black: "Schwarz", event: "Turnier", site: "Ort", date: "Datum", round: "Runde", result: "Ergebnis", edit: "ändern",
      board: "Brett", sheet: "Formular", start: "Anfang", flip: "Brett drehen", show_pgn: "PGN-Text zeigen", hide_pgn: "PGN-Text ausblenden",
      old_page: "Alte Ansicht (ohne Brett)", back: "Zurück",
      st_ok: "sicher", st_fixed: "automatisch korrigiert", st_doubtful: "bitte prüfen", st_user: "von dir bestätigt",
      written: "auf dem Formular", fix: "korrigieren",
      next_doubt: (n) => `⚠ Nächster unsicherer Zug (${n})`,
      start_hint: "Mit ◀ ▶ (oder Wischen über das Brett) durch die Partie gehen. Tippe auf einen Zug in der Liste, um direkt dorthin zu springen.",
      download: "PGN herunterladen", copy: "PGN kopieren", copied: "Kopiert ✓", again: "Neues Formular",
      history: "Meine Partien", history_hint: "Gespeichert nur in diesem Browser auf diesem Gerät.",
      open: "Öffnen", del: "Löschen", del_sure: "Wirklich?", last: "zuletzt", unnamed: "Partie ohne Namen",
      lichess: "In Lichess öffnen", lichess_busy: "Lichess …",
      lichess_failed: "Lichess hat die Partie gerade nicht angenommen. Die PGN ist kopiert: auf der geöffneten Lichess-Seite einfügen.",
      footer: "Partieformular-Leser",
      missing: "fehlt auf dem Formular, aus der Stellung ergänzt", fill: "leeres Feld, aus der Stellung ergänzt",
      similar: "ähnlich geschriebener legaler Zug", alternative: "zweite Lesart des KI-Modells", exact: "",
      summary: (n, f, d) => `${n} Halbzüge · ${f} korrigiert · ${d} prüfen`, skipped: (s) => `Nicht verwendet: ${s}`,
      e_ip_limit: (n) => `Für heute ist Schluss: Von deinem Internetanschluss wurden schon ${n} Partien gelesen – das ist das Tageslimit. Morgen geht es wieder. Deine gespeicherten Partien kannst du weiter ansehen und korrigieren.`,
      e_daily_limit: "Das Tageslimit ist erreicht. Bitte versuche es morgen wieder.",
      e_model_error: "Das Formular konnte nicht gelesen werden: ", e_network: "Keine Verbindung zum Server.",
      e_too_large: "Das Foto ist zu groß.", e_other: "Fehler: ",
      e_server: (c) => c === 504 ? "Der Server hat zu lange gebraucht (504). Bitte noch einmal versuchen." : `Serverfehler (${c}). Bitte noch einmal versuchen.`,
      fix_ok: "stimmt", fix_ph: "anderer Zug, z. B. Thd1", fix_go: "OK",
      undo: "↶ Letzte Korrektur rückgängig", did_you_mean: "Meintest du:", fixing: "Rest der Partie wird neu berechnet …", fix_failed: "Hat nicht geklappt: ",
    },
    ru: {
      title: "Бланк партии → PGN",
      intro: "Сфотографируйте рукописный бланк партии. Приложение прочитает ходы, проверит их по правилам шахмат и покажет партию на доске.",
      camera: "Сделать фото", upload: "Загрузить файл", send: "Отправить фото", send_n: (n) => `Отправить ${n} фото`, remove: "Убрать фото",
      second: "Совет: второе фото (бланк соперника или вторая страница) делает распознавание надёжнее.",
      privacy: "Фото отправляется на распознавание в Anthropic (поставщик ИИ) и хранится на нашем сервере 90 дней, потом удаляется автоматически. Загружайте только бланки, которыми вы готовы поделиться.",
      tips_title: "Советы для хорошего фото", tips: "Положите бланк ровно, хорошее освещение, весь бланк в кадре.",
      busy: "Читаю бланк … обычно 1–2 минуты, трудный бланк — до 4.", busy2: "Читаю оба бланка и сверяю их … обычно 2–3 минуты, до 4.",
      busy_hint: "Экран не погаснет. Если связь прервётся, ничего не пропадёт: просто откройте страницу снова.",
      busy_wait: "Связь прервалась — забираю результат с сервера …",
      e_lost: "Результат не пришёл. Отправьте фото ещё раз.",
      sheets_opp: (lang) => `Фото 2 — бланк соперника${lang === "en" ? " (английская запись)" : ""}; бланки сверены ход за ходом.`,
      sheets_cont: "Фото 2 прочитано как продолжение.", photo_n: (n) => `Фото ${n}`,
      white: "Белые", black: "Чёрные", event: "Турнир", site: "Место", date: "Дата", round: "Тур", result: "Результат", edit: "изменить",
      board: "Доска", sheet: "Бланк", start: "Начало", flip: "Перевернуть доску", show_pgn: "Показать текст PGN", hide_pgn: "Скрыть текст PGN",
      old_page: "Старый вид (без доски)", back: "Назад",
      st_ok: "уверенно", st_fixed: "исправлено автоматически", st_doubtful: "проверьте", st_user: "подтверждено вами",
      written: "на бланке", fix: "исправить",
      next_doubt: (n) => `⚠ Следующий сомнительный ход (${n})`,
      start_hint: "Листайте партию стрелками ◀ ▶ (или проведите пальцем по доске). Нажмите на ход в списке, чтобы сразу перейти к нему.",
      download: "Скачать PGN", copy: "Копировать PGN", copied: "Скопировано ✓", again: "Новый бланк",
      history: "Мои партии", history_hint: "Хранятся только в этом браузере на этом устройстве.",
      open: "Открыть", del: "Удалить", del_sure: "Точно?", last: "последняя", unnamed: "Партия без названия",
      lichess: "Открыть в Lichess", lichess_busy: "Lichess …",
      lichess_failed: "Lichess сейчас не принял партию. PGN скопирован: вставьте его на открывшейся странице Lichess.",
      footer: "распознаватель бланков",
      missing: "нет на бланке, восстановлен по позиции", fill: "пустая клетка, ход восстановлен по позиции",
      similar: "выбран легальный ход, похожий по написанию", alternative: "второй вариант прочтения от модели", exact: "",
      summary: (n, f, d) => `${n} полуходов · ${f} исправлено · ${d} проверить`, skipped: (s) => `Не использовано: ${s}`,
      e_ip_limit: (n) => `На сегодня всё: с вашего интернет-подключения уже распознано ${n} партий — это дневной лимит. Завтра можно снова. Сохранённые партии можно и дальше смотреть и исправлять.`,
      e_daily_limit: "Дневной лимит исчерпан. Попробуйте завтра.",
      e_model_error: "Не удалось прочитать бланк: ", e_network: "Нет связи с сервером.",
      e_too_large: "Фото слишком большое.", e_other: "Ошибка: ",
      e_server: (c) => c === 504 ? "Сервер не успел ответить (504). Попробуйте ещё раз." : `Ошибка сервера (${c}). Попробуйте ещё раз.`,
      fix_ok: "верно", fix_ph: "другой ход, напр. Thd1", fix_go: "OK",
      undo: "↶ Отменить последнее исправление", did_you_mean: "Может быть:", fixing: "Пересчитываю остаток партии …", fix_failed: "Не получилось: ",
    },
  };

  const $ = (id) => document.getElementById(id);
  function pick(l) { return T[l] ? l : "de"; }
  function localGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function localSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } }
  function t(k) { return T[lang][k]; }
  function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  let lang = pick(localGet("lang") || (navigator.language || "de").slice(0, 2));
  let state = null;      // the game: server result (or a saved game)
  let photos = [];       // chosen photos [{blob, url}], sent only after "send"
  let currentId = null;  // id of the shown game in the browser history
  let resultUrls = [];   // object URLs of the shown game's photos
  let line = [];         // line[k] = {fen, from, to}: position after k half-moves
  let cur = 0;           // how many half-moves are played on the board
  let flipped = localGet("v2_flip") === "1";
  let fixOpen = false;   // the fix box of a "sure" move is opened by hand
  let undoState = null, fixing = false, showPgn = false;

  // ---- Saved games (same store as the main page) ----
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
    catch (e) { try { const c = Object.assign({}, g); delete c.photo; delete c.photos; await DB.put(c); } catch (e2) { /* no storage */ } }
  }
  function updateSaved(fields) {
    if (!currentId) return;
    const id = currentId;
    DB.get(id).then((g) => { if (g) { Object.assign(g, fields); return saveGame(g); } }).catch(() => {});
  }

  // ---- Language, screens, menu ----
  function applyLang() {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-t]").forEach((el) => {
      const v = T[lang][el.dataset.t];
      if (typeof v === "string") el.textContent = v;
    });
    document.querySelectorAll(".lang button").forEach((b) => b.classList.toggle("on", b.dataset.lang === lang));
    document.title = t("title");
    $("m-pgn").textContent = showPgn ? t("hide_pgn") : t("show_pgn");
    if (state) renderGame();
    renderSelected();
    renderHistory();
  }

  function show(step) {
    ["step-upload", "step-busy", "step-error", "step-result"].forEach((s) => ($(s).hidden = s !== step));
    document.body.classList.toggle("has-result", step === "step-result");
    window.scrollTo(0, 0);
  }

  function menu(open) {
    $("menu").hidden = !open;
    $("menu-btn").setAttribute("aria-expanded", String(open));
  }
  $("menu-btn").onclick = (e) => { e.stopPropagation(); menu($("menu").hidden); };
  document.addEventListener("click", (e) => { if (!$("menu").hidden && !$("menu").contains(e.target)) menu(false); });
  $("menu").addEventListener("click", (e) => { if (e.target.closest(".mi")) menu(false); });

  // ---- Step 1: photos ----
  async function resize(file) {
    const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = URL.createObjectURL(file); });
    const k = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight));
    const c = document.createElement("canvas");
    c.width = Math.round(img.naturalWidth * k); c.height = Math.round(img.naturalHeight * k);
    c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
    return await new Promise((res) => c.toBlob(res, "image/jpeg", 0.82));
  }
  async function addPhoto(file) {
    if (!file) return;
    let blob;
    try { blob = await resize(file); } catch (e) { blob = file; }
    if (photos.length >= MAX_PHOTOS) clearPhotos();
    photos.push({ blob, url: URL.createObjectURL(blob) });
    $("camera").value = ""; $("file").value = "";
    renderSelected();
  }
  function clearPhotos() { photos.forEach((p) => URL.revokeObjectURL(p.url)); photos = []; }
  function renderSelected() {
    const has = photos.length > 0;
    $("selected").hidden = !has;
    $("send").textContent = photos.length > 1 ? t("send_n")(photos.length) : t("send");
    $("send-buttons").hidden = !has;
    $("pick-buttons").hidden = photos.length >= MAX_PHOTOS;
    $("second-hint").hidden = photos.length !== 1;
    $("camera-btn").classList.toggle("primary", !has);
    const box = $("thumbs");
    box.innerHTML = "";
    photos.forEach((p, i) => {
      const fig = document.createElement("figure");
      fig.className = "thumb";
      const img = document.createElement("img"); img.src = p.url; img.alt = "";
      const x = document.createElement("button");
      x.className = "remove"; x.type = "button"; x.textContent = "×"; x.title = t("remove"); x.setAttribute("aria-label", t("remove"));
      x.onclick = () => { URL.revokeObjectURL(p.url); photos.splice(i, 1); renderSelected(); };
      fig.append(img, x);
      box.appendChild(fig);
    });
  }

  // ---- Step 2: send ----
  // The reading takes 1-4 minutes. The screen is kept on, and every upload gets a job id:
  // the server keeps the answer for a day, so if the phone slept or the connection broke,
  // the page fetches the finished game later (also after reopening the page).
  let activeJob = null, wakeLock = null, busyTimer = null;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function keepAwake(on) {
    try {
      if (on && !wakeLock && navigator.wakeLock && document.visibilityState === "visible") {
        wakeLock = await navigator.wakeLock.request("screen");
        wakeLock.addEventListener("release", () => { wakeLock = null; });
      } else if (!on && wakeLock) { const w = wakeLock; wakeLock = null; await w.release(); }
    } catch (e) { wakeLock = null; }
  }
  function busyStart(urls, text, started) {
    const bt = $("busy-thumbs");
    bt.innerHTML = "";
    urls.forEach((u) => { const i = document.createElement("img"); i.src = u; i.alt = ""; bt.appendChild(i); });
    bt.classList.toggle("two", urls.length > 1);
    $("busy-text").textContent = text;
    clearInterval(busyTimer);
    const tick = () => { const s = Math.max(0, Math.round((Date.now() - started) / 1000)); $("busy-time").textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
    tick(); busyTimer = setInterval(tick, 1000);
    show("step-busy");
    keepAwake(true);
  }
  function busyStop() { clearInterval(busyTimer); busyTimer = null; keepAwake(false); }
  function clearPending() { try { localStorage.removeItem("pending"); } catch (e) { /* ignore */ } DB.del("pending").catch(() => {}); }
  function newJob() {
    const a = new Uint8Array(16);
    (window.crypto || window.msCrypto).getRandomValues(a);
    return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  async function send() {
    if (!photos.length) return;
    const blobs = photos.map((p) => p.blob), urls = photos.map((p) => p.url);
    const pend = { job: newJob(), started: Date.now(), n: blobs.length };
    activeJob = pend.job;
    localSet("pending", JSON.stringify(pend));
    saveGame({ id: "pending", pending: true, job: pend.job, created: pend.started, photos: blobs });
    busyStart(urls, blobs.length > 1 ? t("busy2") : t("busy"), pend.started);
    const form = new FormData();
    blobs.forEach((b, i) => form.append("files", b, `sheet-${i + 1}.jpg`));
    form.append("job", pend.job);
    const adminToken = localGet("admin_token");
    if (adminToken) {
      form.append("admin", adminToken);
      if ($("admin-model").value) form.append("model", $("admin-model").value);
      if ($("admin-ref").value) form.append("ref", $("admin-ref").value);
    }
    let resp, data;
    try { resp = await fetch(API + "/api/process", { method: "POST", body: form }); }
    catch (e) { return waitForResult(pend, blobs, urls, false); }   // phone slept / connection broke
    try { data = await resp.json(); } catch (e) {
      if (resp.status >= 500) return waitForResult(pend, blobs, urls, false);   // a gateway gave up, the server may still finish
      return answer(pend.job, resp.status, null, blobs, urls);
    }
    return answer(pend.job, resp.status, data, blobs, urls);
  }

  // Ask the server for the kept answer until it is there.
  async function waitForResult(pend, blobs, urls, quiet) {
    if (activeJob !== pend.job) return;
    const lostAt = Date.now();
    $("busy-text").textContent = t("busy_wait");
    for (;;) {
      const r = await checkResult(pend.job);
      if (activeJob !== pend.job) return;        // answered meanwhile
      if (r && r.status) return answer(pend.job, r.status, r.body, blobs, urls);
      const now = Date.now();
      const neverArrived = r === null && now - (quiet ? pend.started : lostAt) > 30000;   // server does not know the job
      const tooLong = now - pend.started > 330000 && now - lostAt > 15000;  // the server stops after 5 minutes
      if (neverArrived || tooLong) {
        activeJob = null; busyStop();
        if (r === undefined) return quiet ? show("step-upload") : fail(t("e_network"));   // offline: kept for the next visit
        clearPending();
        if (quiet) { show("step-upload"); return; }
        return fail(t("e_lost"));
      }
      await sleep(4000);
    }
  }
  // {status, body} when the server has the answer, {status: 0} while reading,
  // null if the server has never heard of the job, undefined if there is no connection.
  async function checkResult(job) {
    try {
      const x = await fetch(API + "/api/result/" + job, { cache: "no-store" });
      if (x.status === 404) return null;
      return x.ok ? await x.json() : undefined;
    } catch (e) { return undefined; }
  }

  async function answer(job, status, data, blobs, urls) {
    if (activeJob !== job) return;
    activeJob = null;
    busyStop();
    clearPending();
    if (status !== 200 || !data) {
      if (!data) return fail(status === 413 ? t("e_too_large") : t("e_server")(status));
      const code = data.error;
      if (code === "ip_limit") return fail(t("e_ip_limit")(data.limit || ""));
      if (code === "daily_limit") return fail(t("e_daily_limit"));
      if (code === "model_error") return fail(t("e_model_error") + (data.message || ""));
      if (code === "too_large") return fail(t("e_too_large"));
      return fail(t("e_other") + (data.message || data.detail || status));
    }
    currentId = String(Date.now());
    await saveGame({ id: currentId, created: Date.now(), header: data.header, plies: data.plies, pgn: data.pgn,
      skipped_cells: data.skipped_cells || [], cells: data.cells || null, language: data.language || "de", layout: data.layout || [],
      sheets: data.sheets || [], photo: blobs[0], photos: blobs });
    openResult(data, urls, data.sheets || []);
    showAdminResult(data.admin);
  }

  // The page was closed or reloaded during a reading: pick the result up.
  async function resumePending() {
    let pend = null;
    try { pend = JSON.parse(localGet("pending") || "null"); } catch (e) { /* ignore */ }
    if (!pend || !pend.job || Date.now() - pend.started > 24 * 3600 * 1000) { if (pend) clearPending(); return; }
    let rec = null;
    try { rec = await DB.get("pending"); } catch (e) { /* no storage */ }
    const blobs = rec && rec.job === pend.job && rec.photos ? rec.photos : [];
    resultUrls.forEach((u) => URL.revokeObjectURL(u));
    resultUrls = blobs.map((b) => URL.createObjectURL(b));
    activeJob = pend.job;
    busyStart(resultUrls, t("busy_wait"), pend.started);
    waitForResult(pend, blobs, resultUrls, true);
  }
  document.addEventListener("visibilitychange", async () => {
    if (document.visibilityState !== "visible" || !activeJob) return;
    keepAwake(true);
    const job = activeJob;            // the request may hang after sleep: look whether the answer is already there
    const r = await checkResult(job);
    if (r && r.status && activeJob === job) {
      let rec = null;
      try { rec = await DB.get("pending"); } catch (e) { /* ignore */ }
      const blobs = photos.length ? photos.map((p) => p.blob) : (rec && rec.photos) || [];
      answer(job, r.status, r.body, blobs, photos.length ? photos.map((p) => p.url) : blobs.map((b) => URL.createObjectURL(b)));
    }
  });
  function fail(msg) { $("error-text").textContent = msg; show("step-error"); }

  function initAdmin() {
    const m = location.hash.match(/admin=([^&]+)/);
    if (m) { localSet("admin_token", decodeURIComponent(m[1])); history.replaceState(null, "", location.pathname + location.search); }
    const on = !!localGet("admin_token");
    $("admin").hidden = !on;
    if (!on) return;
    $("admin-model").value = localGet("admin_model") || "";
    $("admin-model").onchange = () => localSet("admin_model", $("admin-model").value);
    $("admin-off").onclick = () => { try { localStorage.removeItem("admin_token"); } catch (e) { /* ignore */ } $("admin").hidden = true; };
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

  // ---- History ----
  function gameTitle(h) {
    const w = h.white && h.white !== "?" ? h.white : "", b = h.black && h.black !== "?" ? h.black : "";
    return w || b ? `${w || "?"} – ${b || "?"}` : t("unnamed");
  }
  async function renderHistory() {
    let games = [];
    try { games = (await DB.all()).filter((g) => !g.pending); } catch (e) { /* no storage */ }
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
      const h = g.header || {}, op = openingFrom(g.pgn);
      const meta = [h.result && h.result !== "*" ? h.result : "", op ? op.local : "",
        new Date(g.created).toLocaleDateString(lang === "ru" ? "ru-RU" : "de-DE", { day: "2-digit", month: "2-digit", year: "numeric" })]
        .filter(Boolean).join(" · ");
      info.innerHTML = `<b>${esc(gameTitle(h))}</b>${i === 0 ? ` <span class="tag">${esc(t("last"))}</span>` : ""}<small>${esc(meta)}</small>`;
      info.title = t("open");
      info.onclick = () => openGame(g.id);
      const del = document.createElement("button");
      del.type = "button"; del.className = "gdel"; del.textContent = "🗑"; del.title = t("del"); del.setAttribute("aria-label", t("del"));
      del.onclick = async () => {   // two taps: no pop-up dialog
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
  async function openGame(id) {
    let g;
    try { g = await DB.get(id); } catch (e) { return; }
    if (!g) return;
    $("admin-result").hidden = true;
    currentId = g.id;
    resultUrls.forEach((u) => URL.revokeObjectURL(u));
    resultUrls = (g.photos || (g.photo ? [g.photo] : [])).map((b) => URL.createObjectURL(b));
    openResult({ header: g.header, plies: g.plies, pgn: g.pgn, skipped_cells: g.skipped_cells, cells: g.cells || null, layout: g.layout || [],
      language: g.language || "de" }, resultUrls, g.sheets || []);
  }

  // ---- Step 3: the game ----
  function openResult(data, urls, sheets) {
    state = data;
    undoState = null; fixOpen = false; showPgn = false;
    $("pgn").hidden = true;
    fillHeader(data.header);
    showPhotos(urls, sheets);
    setView("board");
    computeLine();
    const first = state.plies.find((p) => p.status === "doubtful");
    cur = first ? first.ply + 1 : 0;   // start at the first move to check
    renderGame();
    show("step-result");
  }

  // Positions are worked out here from the moves (chess.js), once per change of the moves.
  // A move that does not fit (should not happen: the server checked them) ends the line there,
  // so the board always shows a real position.
  function computeLine() {
    const c = new window.Chess();
    line = [{ fen: c.fen() }];
    for (const p of state.plies) {
      let m = null;
      try { m = c.move(p.san, { sloppy: true }); } catch (e) { m = null; }
      if (!m) break;
      line.push({ fen: c.fen(), from: m.from, to: m.to });
    }
  }
  const maxCur = () => line.length - 1;

  function renderGame() {
    renderMoves();
    renderPosition();
    const plies = state.plies;
    const f = plies.filter((p) => p.status === "fixed").length, d = plies.filter((p) => p.status === "doubtful").length;
    let sum = t("summary")(plies.length, f, d);
    if (state.skipped_cells && state.skipped_cells.length)
      sum += " · " + t("skipped")(state.skipped_cells.map((c) => `${c.number || "?"}${c.color === "b" ? "…" : "."} ${c.text}`).join(", "));
    $("summary").textContent = sum;
    $("undo").hidden = !undoState;
    $("pgn").textContent = state.pgn;
    showOpening();
    headerSummary();
  }

  // Everything that depends on the shown position (cheap: called on every arrow press).
  function renderPosition() {
    cur = Math.max(0, Math.min(cur, maxCur()));
    renderBoard();
    renderNav();
    renderInfo();
    focusPhoto();
    document.querySelectorAll("#moves .m.sel").forEach((x) => x.classList.remove("sel"));
    const el = document.querySelector(`#moves .m[data-ply="${cur - 1}"]`);
    if (el) el.classList.add("sel");
    const d = state.plies.filter((p) => p.status === "doubtful").length;
    $("next-doubt").hidden = !d;
    if (d) $("next-doubt").textContent = t("next_doubt")(d);
  }

  function go(k) {
    if (k === cur) return;
    cur = k; fixOpen = false;
    renderPosition();
  }

  // Board: 64 squares made once; each render only changes classes.
  const board = $("board");
  const squares = [];
  for (let i = 0; i < 64; i++) {
    const d = document.createElement("div");
    d.appendChild(document.createElement("span")).className = "pc";
    board.appendChild(d);
    squares.push(d);
  }
  function renderBoard() {
    const pos = line[cur] || line[0];
    const rows = pos.fen.split(" ")[0].split("/");
    const grid = rows.map((r) => r.replace(/\d/g, (n) => ".".repeat(+n)));   // grid[0] = rank 8
    const ply = cur > 0 ? state.plies[cur - 1] : null;
    const bad = ply && ply.status === "doubtful";
    for (let i = 0; i < 64; i++) {
      const vr = Math.floor(i / 8), vc = i % 8;               // place on screen
      const r = flipped ? 7 - vr : vr, c = flipped ? 7 - vc : vc;   // place on the board (r 0 = rank 8)
      const name = "abcdefgh"[c] + (8 - r);
      const ch = (grid[r] || "")[c] || ".";
      const sq = squares[i];
      const hl = pos.from === name || pos.to === name;
      sq.className = "sq " + ((r + c) % 2 ? "d" : "l") + (hl ? " hl" : "") + (hl && bad ? " bad" : "");
      sq.firstChild.className = "pc" + (ch === "." ? "" : " pc-" + (ch === ch.toUpperCase() ? "w" : "b") + ch.toUpperCase());
      // coordinates: letters on the bottom row, numbers on the left column
      let co = "";
      if (vr === 7) co += `<span class="co f">${"abcdefgh"[c]}</span>`;
      if (vc === 0) co += `<span class="co r">${8 - r}</span>`;
      sq.querySelectorAll(".co").forEach((x) => x.remove());
      if (co) sq.insertAdjacentHTML("beforeend", co);
    }
  }

  function moveNo(p) { return Math.floor(p.ply / 2) + 1 + (p.ply % 2 ? "… " : ". "); }

  function renderNav() {
    const p = cur > 0 ? state.plies[cur - 1] : null;
    const b = $("n-cur");
    b.textContent = p ? moveNo(p) + p.local : t("start");
    b.className = "cur " + (p ? p.status : "");
    $("n-first").disabled = $("n-prev").disabled = cur === 0;
    $("n-last").disabled = $("n-next").disabled = cur >= maxCur();
  }

  // Under the arrows: what was written on the sheet; for unsure moves the quick fix right away.
  function renderInfo() {
    const box = $("info");
    const p = cur > 0 ? state.plies[cur - 1] : null;
    if (!p) { box.innerHTML = `<p class="hint">${esc(t("start_hint"))}</p>`; return; }
    const st = p.reason === "user" ? t("st_user") : t("st_" + p.status) || "";
    const why = p.reason && p.reason !== "user" ? t(p.reason) || "" : "";
    const needs = p.status !== "ok" && p.reason !== "user";
    // an empty cell already says "missing" in the reason: no "written: nothing" then
    const written = p.written ? `<span class="why">${esc(t("written"))}:</span> <span class="w">«${esc(p.written)}»</span> · ` : "";
    box.innerHTML = `<div class="line"><span>${written}<span class="why">${esc(st)}${why ? ", " + esc(why) : ""}</span></span>` +
      (needs || fixOpen ? "" : `<button type="button" class="link" id="fix-open">✎ ${esc(t("fix"))}</button>`) + `</div>`;
    if (needs || fixOpen) box.appendChild(fixBox(p));
    const o = $("fix-open");
    if (o) o.onclick = () => { fixOpen = true; renderInfo(); const i = box.querySelector(".fix-text"); if (i) i.focus(); };
  }

  function fixBox(p) {
    const d = document.createElement("div");
    d.className = "fixbox";
    d.innerHTML = `<div class="fix-chips"></div>
      <form class="fix-form"><input class="fix-text" autocomplete="off" autocapitalize="off" spellcheck="false"
        placeholder="${esc(t("fix_ph"))}" aria-label="${esc(t("fix_ph"))}"><button class="btn small" type="submit">${esc(t("fix_go"))}</button></form>
      <p class="fix-msg" hidden></p><div class="fix-chips fix-options" hidden></div>`;
    const chips = d.querySelector(".fix-chips");
    if (p.reason !== "user") chips.appendChild(chip(`✓ ${p.local} ${t("fix_ok")}`, p.ply, { san: p.san }, "ok"));
    (p.alternatives || []).forEach((a) => chips.appendChild(chip(a, p.ply, { text: a })));
    d.querySelector(".fix-form").onsubmit = (e) => {
      e.preventDefault();
      const v = d.querySelector(".fix-text").value.trim();
      if (v) fixMove(p.ply, { text: v });
    };
    if (fixing) setBusy(d, true);
    return d;
  }
  function chip(label, k, move, cls) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip " + (cls || ""); b.textContent = label;
    b.onclick = () => fixMove(k, move);
    return b;
  }
  function setBusy(d, on) {
    d.classList.toggle("busy-fix", on);
    d.querySelectorAll("button, input").forEach((x) => (x.disabled = on));
    const msg = d.querySelector(".fix-msg");
    if (msg && on) { msg.hidden = false; msg.className = "fix-msg"; msg.textContent = t("fixing"); }
  }

  // Move list: flowing text, tap a move = show it on the board.
  function renderMoves() {
    const box = $("moves");
    box.innerHTML = "";
    let group = null;   // one full move ("12. Sf3 d6") never breaks over two lines
    state.plies.forEach((p) => {
      if (p.ply % 2 === 0 || !group) {
        group = box.appendChild(document.createElement("span"));
        group.className = "pair";
        const n = group.appendChild(document.createElement("span"));
        n.className = "no"; n.textContent = Math.floor(p.ply / 2) + 1 + (p.ply % 2 ? "…" : ".");
        box.appendChild(document.createTextNode(" "));
      }
      const b = document.createElement("button");
      b.type = "button";
      b.className = "m " + p.status + (p.reason === "user" ? " user" : "");
      b.dataset.ply = p.ply;
      b.textContent = p.local;
      b.onclick = () => go(Math.min(p.ply + 1, maxCur()));
      group.appendChild(b);
    });
  }

  // ---- Fix one move: the server decodes the rest again (no model call, free) ----
  async function fixMove(k, move) {
    if (fixing) return;
    fixing = true;
    const box = $("info").querySelector(".fixbox");
    if (box) { box.querySelector(".fix-options").hidden = true; setBusy(box, true); }
    let resp, data;
    try {
      resp = await fetch(API + "/api/redecode", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.assign({ header: header(), plies: state.plies, cells: state.cells || null,
          ply: k, language: state.language || "de" }, move)),
      });
      data = await resp.json();
    } catch (e) { data = null; }
    fixing = false;
    const nowBox = $("info").querySelector(".fixbox");
    if (nowBox) setBusy(nowBox, false);
    if (!resp || !data || !resp.ok) {
      if (cur - 1 !== k || !nowBox) return;   // the person already looks at another move
      const msg = nowBox.querySelector(".fix-msg"), opts = nowBox.querySelector(".fix-options");
      msg.className = "fix-msg bad"; msg.hidden = false;
      msg.textContent = t("fix_failed") + (!data ? t("e_network") : data.message || resp.status);
      if (data && data.options && data.options.length) {
        msg.textContent = t("did_you_mean"); msg.className = "fix-msg";
        opts.innerHTML = "";
        data.options.forEach((o) => opts.appendChild(chip(o, k, { text: o })));
        opts.hidden = false;
      }
      return;
    }
    undoState = { plies: state.plies, cells: state.cells, skipped_cells: state.skipped_cells, pgn: state.pgn, cur };
    applyMoves(data);
    // on to the next move that needs a look, else stay on the fixed move
    const next = state.plies.find((p) => p.ply > k && p.status === "doubtful");
    cur = next ? next.ply + 1 : k + 1;
    fixOpen = false;
    renderPosition();
  }
  function applyMoves(data) {
    Object.assign(state, { plies: data.plies, cells: data.cells, skipped_cells: data.skipped_cells, pgn: data.pgn });
    updateSaved({ plies: data.plies, cells: data.cells, skipped_cells: data.skipped_cells, pgn: data.pgn, header: header() });
    computeLine();
    renderGame();
  }
  $("undo").onclick = () => {
    if (!undoState || fixing) return;
    const u = undoState;
    undoState = null;
    applyMoves(u);
    cur = u.cur; fixOpen = false;
    renderPosition();
  };

  // ---- Arrows, swipe, keys ----
  $("n-first").onclick = () => go(0);
  $("n-prev").onclick = () => go(Math.max(0, cur - 1));
  $("n-next").onclick = () => go(Math.min(maxCur(), cur + 1));
  $("n-last").onclick = () => go(maxCur());
  $("n-cur").onclick = () => { if (cur > 0 && state.plies[cur - 1].status === "ok") { fixOpen = !fixOpen; renderInfo(); } };
  $("next-doubt").onclick = () => {
    const d = state.plies.filter((p) => p.status === "doubtful" && p.ply + 1 <= maxCur());
    if (!d.length) return;
    const next = d.find((p) => p.ply + 1 > cur) || d[0];   // after the shown move, else from the start
    go(next.ply + 1);
  };
  let touch = null;
  board.addEventListener("touchstart", (e) => { const p = e.touches[0]; touch = { x: p.clientX, y: p.clientY }; }, { passive: true });
  board.addEventListener("touchend", (e) => {
    if (!touch) return;
    const p = e.changedTouches[0], dx = p.clientX - touch.x, dy = p.clientY - touch.y;
    touch = null;
    if (Math.abs(dx) > 40 && Math.abs(dx) > 1.5 * Math.abs(dy)) go(dx < 0 ? Math.min(maxCur(), cur + 1) : Math.max(0, cur - 1));
  });
  document.addEventListener("keydown", (e) => {
    if ($("step-result").hidden || /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)) return;
    if (e.key === "ArrowLeft") { e.preventDefault(); go(Math.max(0, cur - 1)); }
    else if (e.key === "ArrowRight") { e.preventDefault(); go(Math.min(maxCur(), cur + 1)); }
    else if (e.key === "Home") go(0);
    else if (e.key === "End") go(maxCur());
  });

  // ---- Board / photo of the sheet ----
  function setView(v) {
    $("board").hidden = v !== "board";
    $("photo-view").hidden = v !== "photo";
    $("v-board").classList.toggle("on", v === "board"); $("v-board").setAttribute("aria-pressed", String(v === "board"));
    $("v-photo").classList.toggle("on", v === "photo"); $("v-photo").setAttribute("aria-pressed", String(v === "photo"));
    if (v === "photo") focusPhoto();
  }

  // On the photo: zoom to the cell of the shown move and frame it. The cell comes from the
  // model's rough layout of the move rows (0..1000 of the photo, only for photo 1). The model's
  // left/right are good, but its top/bottom can be off by many rows, so the printed lines of the
  // table are looked up on the photo itself and the rows are counted from them.
  let photoIdx = 0;
  let gray = null;   // the photo in shades of grey, small: { src, g, W, H }
  const linesCache = new Map();
  function sheetGray(img) {
    if (gray && gray.src === img.src) return gray;
    gray = { src: img.src, g: null };
    try {
      const H = Math.min(1400, img.naturalHeight), W = Math.max(1, Math.round(img.naturalWidth * H / img.naturalHeight));
      const c = document.createElement("canvas"); c.width = W; c.height = H;
      const ctx = c.getContext("2d", { willReadFrequently: true });
      ctx.drawImage(img, 0, 0, W, H);
      const px = ctx.getImageData(0, 0, W, H).data, g = new Uint8Array(W * H);
      for (let i = 0, j = 0; i < g.length; i++, j += 4) g[i] = (px[j] * 77 + px[j + 1] * 150 + px[j + 2] * 29) >> 8;
      Object.assign(gray, { g, W, H });
    } catch (e) { /* no canvas: stay with the model's layout */ }
    return gray;
  }
  // The y positions (0..1000) of the longest evenly spaced run of printed horizontal lines
  // between x0 and x1 (0..1000), or null. A missing line here and there is filled in.
  function tableLines(img, x0, x1) {
    const key = img.src + "|" + Math.round(x0) + "|" + Math.round(x1);
    if (linesCache.has(key)) return linesCache.get(key);
    const s = sheetGray(img);
    let res = null;
    if (s.g) {
      const { g, W, H } = s, a = Math.max(0, Math.round(x0 / 1000 * W)), n = Math.min(W, Math.round(x1 / 1000 * W)) - a;
      if (n >= 10) res = findLines(g, W, H, a, n);
      if (res) res = res.map((y) => y / H * 1000);
    }
    linesCache.set(key, res);
    return res;
  }
  function findLines(g, W, H, a, n) {
    const K = 4, T = 18, dark = new Uint8Array(H * n);
    for (let y = K; y < H - K; y++) {
      const r = y * W + a, up = r - K * W, dn = r + K * W, o = y * n;
      for (let i = 0; i < n; i++) if (Math.min(g[up + i], g[dn + i]) - g[r + i] > T) dark[o + i] = 1;
    }
    // longest piece of a thin dark line here, as a share of the width (±2 px, as a photo is never
    // quite straight; short gaps are where the handwriting crosses the line). Printed text and
    // handwriting give only short pieces.
    const f = new Float32Array(H), GAP = Math.max(4, Math.round(n / 25));
    for (let y = 2; y < H - 2; y++) {
      let run = 0, gap = 0, best = 0;
      for (let i = 0; i < n; i++) {
        if (dark[(y - 2) * n + i] | dark[(y - 1) * n + i] | dark[y * n + i] | dark[(y + 1) * n + i] | dark[(y + 2) * n + i]) { run += gap + 1; gap = 0; if (run > best) best = run; }
        else if (run && ++gap > GAP) { run = 0; gap = 0; }
      }
      f[y] = best / n;
    }
    const P = [];   // one y per line: middle of the strongest part of each run above the threshold
    for (let y = 0; y < H; y++) {
      if (f[y] < 0.6) continue;
      let e = y, m = 0;
      while (e < H && f[e] >= 0.6) { m = Math.max(m, f[e]); e++; }
      let s0 = -1, s1 = -1;
      for (let k = y; k < e; k++) if (f[k] >= 0.9 * m) { if (s0 < 0) s0 = k; s1 = k; }
      P.push((s0 + s1) / 2);
      y = e;
    }
    let best = null, bestScore = 0;
    for (let i = 0; i < P.length; i++) {
      for (let j = i + 1; j < P.length; j++) {
        const d0 = P[j] - P[i];
        if (d0 < H / 120) continue;
        if (d0 > H / 6) break;
        const chain = [P[i], P[j]];
        let d = d0, last = P[j], k = j, found = 2, miss = 0, filled = 0;
        for (;;) {
          const want = last + d;
          let hit = -1;
          for (let m = k + 1; m < P.length && P[m] <= want + 0.12 * d; m++)
            if (Math.abs(P[m] - want) <= 0.12 * d && (hit < 0 || Math.abs(P[m] - want) < Math.abs(P[hit] - want))) hit = m;
          if (hit >= 0) {
            d = 0.8 * d + 0.2 * (P[hit] - last); last = P[hit]; k = hit; found++; miss = 0; chain.push(last);
          } else {
            if (miss || want > H) break;
            miss = 1; last = want; chain.push(want); filled++;
          }
        }
        if (miss) { chain.pop(); filled--; }   // a run does not end on a filled-in line
        const score = found - 2 * filled;   // a run made of every second line is not the table
        if (score > bestScore) { bestScore = score; best = chain; }
      }
    }
    return bestScore >= 6 ? best : null;
  }
  function cellBox(p, img) {
    const layout = state && state.layout;
    if (!p || !layout || !layout.length) return null;
    const cell = state.cells && p.token != null ? state.cells[p.token] : null;
    if (cell && cell.sheet) return null;                  // the move is on photo 2: no layout for it
    const number = (cell && cell.number) || Math.floor(p.ply / 2) + 1;
    const color = (cell && cell.color) || "wb"[p.ply % 2];
    for (const b of layout) {
      if (b.first_move <= number && number <= b.last_move) {
        const rows = b.last_move - b.first_move + 1, r = number - b.first_move;
        const rh = (b.bottom - b.top) / rows;
        const mid = (b.left + b.right) / 2, x0 = color === "w" ? b.left : mid, x1 = color === "w" ? mid : b.right;
        const box = { x0, x1, y0: b.top + r * rh, y1: b.top + (r + 1) * rh };
        const L = img ? tableLines(img, x0 + (x1 - x0) * 0.1, x1 - (x1 - x0) * 0.1) : null;
        if (L) {
          const n = L.length - 1, d = (L[n] - L[0]) / n;
          // Which run of `rows` rows is the block? The model's top/bottom say roughly where, but
          // sometimes it measures the height in units of the width, so they come out too low by
          // the photo's proportions. Its rectangle is read both ways and the reading that fits
          // the lines found best wins. An edge put at the very edge of the photo is not used.
          const at = (i) => (i < 0 ? L[0] + i * d : i > n ? L[n] + (i - n) * d : L[i]);
          const useTop = b.top > 5, useBot = b.bottom < 995, ar = img.naturalWidth / img.naturalHeight;
          let o = Math.max(0, n - rows), bestCost = Infinity;
          for (const k of ar && Math.abs(ar - 1) > 0.05 ? [1, ar] : [1]) {
            const top = b.top * k, bot = b.bottom * k;
            for (let i = Math.min(0, n - rows); i <= Math.max(0, n - rows); i++) {
              let c = useTop || useBot ? (useTop ? Math.abs(at(i) - top) : 0) + (useBot ? Math.abs(at(i + rows) - bot) : 0)
                : Math.abs(at(i) + at(i + rows) - top - bot);
              if (useTop && useBot) c += Math.abs((bot - top) - rows * d) / 2;   // the row height must fit too
              if (c < bestCost - 1e-6) { bestCost = c; o = i; }
            }
          }
          box.y0 = Math.max(0, at(o + r)); box.y1 = Math.min(1000, at(o + r + 1));
          if (box.y1 - box.y0 < 2) return null;
        }
        return box;
      }
    }
    return null;
  }
  function focusPhoto() {
    const view = $("photo-view"), mark = $("ph-mark"), img = $("preview");
    mark.hidden = true;
    if (view.hidden || photoIdx !== 0 || cur === 0) return;
    const p = state.plies[cur - 1];
    const show = () => {
      if (view.hidden || photoIdx !== 0 || state.plies[cur - 1] !== p) return;
      const box = cellBox(p, img);
      if (!box) return;
      view.classList.add("zoom");
      const pad = 4;   // a bit more than the cell, so the line under the writing stays visible
      Object.assign(mark.style, { left: (box.x0 - pad) / 10 + "%", top: (box.y0 - pad) / 10 + "%",
        width: (box.x1 - box.x0 + 2 * pad) / 10 + "%", height: (box.y1 - box.y0 + 2 * pad) / 10 + "%" });
      mark.className = "ph-mark " + p.status;
      mark.hidden = false;
      const w = $("ph-wrap").offsetWidth, h = $("ph-wrap").offsetHeight;
      view.scrollTo({ left: (box.x0 + box.x1) / 2000 * w - view.clientWidth / 2,
        top: (box.y0 + box.y1) / 2000 * h - view.clientHeight / 2, behavior: "smooth" });
    };
    if (img.complete && img.naturalWidth) show(); else img.addEventListener("load", show, { once: true });
  }
  $("v-board").onclick = () => setView("board");
  $("preview").onclick = () => $("photo-view").classList.toggle("zoom");   // tap the sheet: 2x bigger, tap again: back
  $("v-photo").onclick = () => setView("photo");
  function showPhotos(urls, sheets) {
    const pv = $("preview"), tabs = $("photo-tabs"), note = $("sheets-note");
    $("v-photo").hidden = !urls.length;
    if (urls.length) pv.src = urls[0];
    photoIdx = 0;
    tabs.innerHTML = "";
    tabs.hidden = urls.length < 2;
    urls.forEach((u, i) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "ptab" + (i ? "" : " on"); b.textContent = t("photo_n")(i + 1);
      b.onclick = () => { pv.src = u; photoIdx = i; $("photo-view").scrollTop = 0; focusPhoto(); tabs.querySelectorAll(".ptab").forEach((x, j) => x.classList.toggle("on", j === i)); };
      tabs.appendChild(b);
    });
    const second = (sheets || []).find((sh) => sh.image === 1);
    note.hidden = urls.length < 2 || !second;
    if (second) note.textContent = second.role === "continuation" ? t("sheets_cont") : t("sheets_opp")(second.language);
  }

  // ---- Game data (players etc.), folded by default ----
  function fillHeader(h) {
    for (const k of ["white", "black", "event", "site", "round"]) $("h-" + k).value = h[k] === "?" ? "" : (h[k] || "");
    $("h-date").value = (h.date || "").includes("?") ? "" : (h.date || "");
    $("h-result").value = h.result || "*";
    $("header-box").open = false;
  }
  function header() {
    const h = {};
    for (const k of ["white", "black", "event", "site", "date", "round"]) h[k] = $("h-" + k).value.trim() || (k === "date" ? "????.??.??" : "?");
    h.result = $("h-result").value;
    return h;
  }
  function headerSummary() {
    const h = header();
    $("header-sum").textContent = gameTitle(h) + (h.result !== "*" ? " · " + h.result : "");
  }
  let saveTimer = null;
  document.querySelectorAll(".grid input, .grid select").forEach((el) => el.addEventListener("input", () => {
    headerSummary();
    clearTimeout(saveTimer);
    const h = header();
    saveTimer = setTimeout(() => updateSaved({ header: h }), 400);
  }));

  // ---- Opening name (from the PGN tags written by the server) ----
  function openingFrom(pgn) {
    const tag = (k) => { const m = (pgn || "").match(new RegExp(`\\[${k} "([^"]*)"\\]`)); return m ? m[1] : ""; };
    const name = tag("Opening"), eco = tag("ECO");
    if (!name) return null;
    const i = name.indexOf(":");
    const family = i < 0 ? name : name.slice(0, i);
    const tr = (window.OPENING_NAMES || {})[family];
    return { eco, name, local: tr ? tr[lang === "ru" ? 0 : 1] : family };
  }
  function showOpening() {
    const o = openingFrom(state && state.pgn), el = $("opening");
    el.innerHTML = o ? `<b>${esc(o.local)}</b>${o.eco ? " " + esc(o.eco) : ""}` : "";
    el.title = o ? o.name : "";
  }

  // ---- PGN out ----
  async function currentPgn() {
    try {
      const resp = await fetch(API + "/api/pgn", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ header: header(), moves: state.plies }),
      });
      const data = await resp.json();
      if (!data.pgn) throw new Error("no pgn");
      state.pgn = data.pgn;
      $("pgn").textContent = data.pgn;
      showOpening();
      updateSaved({ pgn: data.pgn, header: header() });
      return data.pgn;
    } catch (e) { return state.pgn; }
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
  $("m-copy").onclick = async () => {
    const pgn = await currentPgn();
    try { await navigator.clipboard.writeText(pgn); flash(t("copied")); } catch (e) { /* ignore */ }
  };
  $("m-pgn").onclick = async () => {
    showPgn = !showPgn;
    $("pgn").hidden = !showPgn;
    $("m-pgn").textContent = showPgn ? t("hide_pgn") : t("show_pgn");
    if (showPgn) { await currentPgn(); $("pgn").scrollIntoView({ behavior: "smooth", block: "nearest" }); }
  };
  $("m-flip").onclick = () => { flipped = !flipped; localSet("v2_flip", flipped ? "1" : "0"); renderBoard(); };
  function flash(msg) {
    const b = $("download"), old = b.textContent;
    b.textContent = msg;
    setTimeout(() => (b.textContent = old), 1500);
  }
  $("lichess").onclick = async () => {
    const btn = $("lichess");
    const win = window.open("about:blank", "_blank");   // opened before waiting, so phones do not block it
    btn.disabled = true; btn.textContent = t("lichess_busy");
    let pgn = "";
    try {
      pgn = await currentPgn();
      const resp = await fetch("https://lichess.org/api/import", { method: "POST", headers: { Accept: "application/json" }, body: new URLSearchParams({ pgn }) });
      const data = await resp.json();
      if (!resp.ok || !data.url) throw new Error(resp.status);
      if (win) win.location.href = data.url; else location.href = data.url;
    } catch (e) {
      try { if (pgn) await navigator.clipboard.writeText(pgn); } catch (e2) { /* ignore */ }
      if (win) win.location.href = "https://lichess.org/paste";
      alert(t("lichess_failed"));
    } finally { btn.disabled = false; btn.textContent = t("lichess"); }
  };

  // ---- Start / new sheet ----
  function newSheet() { $("admin-result").hidden = true; state = null; currentId = null; clearPhotos(); renderSelected(); renderHistory(); show("step-upload"); }
  $("m-new").onclick = newSheet;
  $("home").onclick = () => { if ($("step-busy").hidden) { renderHistory(); show("step-upload"); } };
  $("m-history").onclick = () => {
    if (!$("step-busy").hidden) return;
    renderHistory(); show("step-upload");
    setTimeout(() => $("history").scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  };
  $("again-error").onclick = () => { renderSelected(); show("step-upload"); };
  $("camera").onchange = (e) => addPhoto(e.target.files[0]);
  $("file").onchange = (e) => addPhoto(e.target.files[0]);
  $("send").onclick = send;
  document.querySelectorAll(".lang button").forEach((b) => (b.onclick = () => { lang = b.dataset.lang; localSet("lang", lang); applyLang(); }));
  initAdmin();
  applyLang();
  show("step-upload");
  resumePending();
})();
