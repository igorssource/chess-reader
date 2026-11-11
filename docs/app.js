// Chess Reader page: photo -> server -> moves with marks -> PGN.
(function () {
  "use strict";
  const API = (window.CHESS_READER_API || "").replace(/\/$/, "");
  const MAX_SIDE = 1600;           // resize photos before upload: faster and cheaper

  const T = {
    de: {
      title: "Partieformular → PGN",
      intro: "Fotografiere ein handschriftliches Partieformular. Die App liest die Züge, prüft sie nach den Schachregeln, markiert unsichere Stellen und erstellt eine PGN-Datei.",
      privacy: "Hinweis: Das Foto wird zur Erkennung an den KI-Anbieter Anthropic gesendet und auf unserem Server gespeichert, um die Erkennung zu verbessern. Lade nur Formulare hoch, mit deren Weitergabe du einverstanden bist.",
      camera: "Foto aufnehmen", upload: "Bild hochladen",
      tips: "Tipps: Formular flach hinlegen, gutes Licht, ganzes Formular im Bild.",
      busy: "Formular wird gelesen … das kann bis zu einer Minute dauern.",
      header: "Partiedaten", white: "Weiß", black: "Schwarz", event: "Turnier", site: "Ort", date: "Datum", round: "Runde", result: "Ergebnis",
      moves: "Züge", "l-ok": "sicher", "l-fixed": "automatisch korrigiert", "l-doubtful": "bitte prüfen",
      download: "PGN herunterladen", copy: "PGN kopieren", copied: "Kopiert", again: "Neues Formular",
      footer: "STRATEG Stuttgart · Partieformular-Leser",
      written: "Auf dem Formular", alternatives: "Andere Möglichkeiten", missing: "Dieser Zug fehlt auf dem Formular und wurde aus der Stellung ergänzt.",
      fill: "Leeres Feld: Zug aus der Stellung ergänzt.", similar: "Ähnlich geschriebener legaler Zug gewählt.", alternative: "Vom KI-Modell als zweite Lesart vorgeschlagen.", exact: "Wie geschrieben.",
      summary: (n, f, d) => `${n} Halbzüge · ${f} automatisch korrigiert · ${d} bitte prüfen`,
      skipped: (s) => `Nicht verwendete Felder: ${s}`,
      e_daily_limit: "Das Tageslimit ist erreicht. Bitte versuche es morgen wieder.",
      e_model_error: "Das Formular konnte nicht gelesen werden: ", e_network: "Keine Verbindung zum Server.",
      e_too_large: "Das Foto ist zu groß.", e_other: "Fehler: ",
    },
    ru: {
      title: "Бланк партии → PGN",
      intro: "Сфотографируйте рукописный бланк партии. Приложение прочитает ходы, проверит их по правилам шахмат, отметит сомнительные места и подготовит файл PGN.",
      privacy: "Обратите внимание: фото отправляется на распознавание в Anthropic (поставщик ИИ) и сохраняется на нашем сервере для улучшения распознавания. Загружайте только бланки, которыми вы готовы поделиться.",
      camera: "Сделать фото", upload: "Загрузить файл",
      tips: "Советы: положите бланк ровно, хорошее освещение, весь бланк в кадре.",
      busy: "Читаю бланк … это может занять до минуты.",
      header: "Данные партии", white: "Белые", black: "Чёрные", event: "Турнир", site: "Место", date: "Дата", round: "Тур", result: "Результат",
      moves: "Ходы", "l-ok": "уверенно", "l-fixed": "исправлено автоматически", "l-doubtful": "проверьте",
      download: "Скачать PGN", copy: "Копировать PGN", copied: "Скопировано", again: "Новый бланк",
      footer: "STRATEG Stuttgart · распознаватель бланков",
      written: "На бланке", alternatives: "Другие варианты", missing: "Этого хода нет на бланке, он восстановлен по позиции.",
      fill: "Пустая клетка: ход восстановлен по позиции.", similar: "Выбран легальный ход, похожий по написанию.", alternative: "Второй вариант прочтения от модели.", exact: "Как написано.",
      summary: (n, f, d) => `${n} полуходов · ${f} исправлено автоматически · ${d} проверьте`,
      skipped: (s) => `Неиспользованные клетки: ${s}`,
      e_daily_limit: "Дневной лимит исчерпан. Попробуйте завтра.",
      e_model_error: "Не удалось прочитать бланк: ", e_network: "Нет связи с сервером.",
      e_too_large: "Фото слишком большое.", e_other: "Ошибка: ",
    },
  };

  let lang = pick(localGet("lang") || (navigator.language || "de").slice(0, 2));
  let state = null;   // last server result
  let photoUrl = null;
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
  }

  function show(step) {
    ["step-upload", "step-busy", "step-error", "step-result"].forEach((s) => ($(s).hidden = s !== step));
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

  async function handleFile(file) {
    if (!file) return;
    let blob;
    try { blob = await resize(file); } catch (e) { blob = file; }
    if (photoUrl) URL.revokeObjectURL(photoUrl);
    photoUrl = URL.createObjectURL(blob);
    $("preview-busy").src = photoUrl; $("preview").src = photoUrl;
    show("step-busy");
    const form = new FormData();
    form.append("files", blob, "sheet.jpg");
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
    fillHeader(data.header);
    renderResult();
    show("step-result");
  }

  function fail(msg) { $("error-text").textContent = msg; show("step-error"); }

  function fillHeader(h) {
    for (const k of ["white", "black", "event", "site", "round"]) $("h-" + k).value = h[k] === "?" ? "" : (h[k] || "");
    $("h-date").value = (h.date || "").includes("?") ? "" : h.date;
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
        s.className = "m " + p.status;
        s.textContent = p.local;
        s.tabIndex = p.status === "ok" ? -1 : 0;
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
    $("detail").hidden = true;
    $("pgn").textContent = state.pgn;
  }

  function showDetail(p, el) {
    document.querySelectorAll(".m.sel").forEach((x) => x.classList.remove("sel"));
    el.classList.add("sel");
    const d = $("detail");
    const n = Math.floor(p.ply / 2) + 1 + (p.ply % 2 ? "… " : ". ");
    let html = `<b>${n}${esc(p.local)}</b> — ${esc(t(p.reason) || "")}`;
    if (p.written) html += `<br>${esc(t("written"))}: «${esc(p.written)}»`;
    if (p.alternatives && p.alternatives.length) html += `<br>${esc(t("alternatives"))}: ${p.alternatives.map(esc).join(", ")}`;
    d.innerHTML = html;
    d.hidden = false;
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  async function currentPgn() {
    const resp = await fetch(API + "/api/pgn", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ header: header(), moves: state.plies }),
    });
    const data = await resp.json();
    $("pgn").textContent = data.pgn;
    return data.pgn;
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
  const again = () => { state = null; $("camera").value = ""; $("file").value = ""; show("step-upload"); };
  $("again").onclick = again; $("again-error").onclick = again;
  $("camera").onchange = (e) => handleFile(e.target.files[0]);
  $("file").onchange = (e) => handleFile(e.target.files[0]);
  document.querySelectorAll(".lang button").forEach((b) => (b.onclick = () => { lang = b.dataset.lang; localSet("lang", lang); applyLang(); }));
  applyLang();
})();
