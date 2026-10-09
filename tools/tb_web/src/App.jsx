import { useState, useEffect, useMemo, useRef, useDeferredValue } from "react";
import {
  LayoutGrid,
  BookOpen,
  Network,
  CalendarDays,
  Settings2,
  Search,
  ChevronDown,
  ChevronRight,
  ArrowUpRight,
  ArrowUp,
  ArrowDown,
  X,
  Sun,
  Moon,
  RotateCcw,
  Undo2,
  Redo2,
  PanelRight,
  Maximize2,
  Minimize2,
  Check,
  CheckCheck,
  Command,
  Sparkles,
  SlidersHorizontal,
  Inbox,
  Circle,
  Layers3,
  ArrowLeft,
  Keyboard,
  LoaderCircle,
  Star,
  BookmarkPlus,
} from "lucide-react";
import PracticePlanner from "./PracticePlanner.jsx";
import { normalizeMarkdown } from "./normalizeMarkdown.js";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import {
  STATES,
  STATE_CLASS,
  QUEUES,
  passed,
  filteredRows,
  categoryStats,
  organizeCategories,
} from "./model.js";

const pages = [
  { id: "library", label: "题目总表", icon: LayoutGrid },
  { id: "knowledge", label: "知识点地图", icon: Network },
  { id: "today", label: "今天要做的", icon: CalendarDays },
];
const defaults = {
  theme: "dark",
  accent: "violet",
  motion: true,
  compact: false,
  rowTint: true,
  previewWidth: 560,
  favorites: [],
  views: [],
  keys: { search: "f", preview: "Enter", settings: "?", focus: "Control" },
};
const readPrefs = () => {
  try {
    return {
      ...defaults,
      ...JSON.parse(localStorage.getItem("tb.preferences") || "{}"),
    };
  } catch {
    return defaults;
  }
};
const fmt = (n) => Number(n || 0).toLocaleString("zh-CN");
async function api(path, options) {
  const res = await fetch("/api/" + path, options);
  const data = await res.json();
  if (!res.ok) throw Error(data.error || "操作失败，请重试");
  return data;
}
function StateBadge({ state }) {
  return (
    <span className={"state-badge " + STATE_CLASS[STATES.indexOf(state)]}>
      <span />
      {state}
    </span>
  );
}
function Empty({ icon: Icon = Search, title, description, action }) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon size={26} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
function Tag({ name, onClick }) {
  return (
    <button
      className="tag"
      onClick={(e) => {
        e.stopPropagation();
        onClick?.(name);
      }}
    >
      {name}
    </button>
  );
}
function CategoryNode({ node, rows, depth = 0, onFilter }) {
  const [open, setOpen] = useState(depth === 0);
  const stat = useMemo(() => categoryStats(node, rows), [node, rows]);
  const kids = node.children || [];
  if (!stat.total) return null;
  return (
    <div className="category-node">
      <div
        className={"category-line depth-" + Math.min(depth, 2)}
        style={{ paddingLeft: 16 + depth * 24 }}
      >
        <button
          className="category-toggle"
          aria-label={(open ? "收起" : "展开") + node.name}
          disabled={!kids.length}
          onClick={() => setOpen(!open)}
        >
          {kids.length ? (
            open ? (
              <ChevronDown size={15} />
            ) : (
              <ChevronRight size={15} />
            )
          ) : (
            <span className="leaf-dot" />
          )}
        </button>
        <button className="category-name" onClick={() => onFilter(node)}>
          {node.name}
          {depth === 0 && <span className="category-kind">领域</span>}
        </button>
        <span className="category-total">
          {stat.total}
          <small>题</small>
        </span>
        <div className="mini-track">
          <span style={{ width: (stat.passed / stat.total) * 100 + "%" }} />
        </div>
        <span className="category-ratio">
          {Math.round((stat.passed / stat.total) * 100)}%
        </span>
        <button
          className={"category-weak " + (!stat.weak ? "muted" : "")}
          onClick={() => onFilter(node, "weak")}
        >
          {stat.weak ? stat.weak + " 待攻克" : "—"}
        </button>
        <button
          className="category-go"
          aria-label={"查看" + node.name + "题目"}
          onClick={() => onFilter(node)}
        >
          <ArrowUpRight size={16} />
        </button>
      </div>
      {open && kids.length > 0 && (
        <div className="category-children">
          {kids.map((c, i) => (
            <CategoryNode
              key={c.name + "-" + i}
              node={c}
              rows={rows}
              depth={depth + 1}
              onFilter={onFilter}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const [prefs, setPrefs] = useState(readPrefs),
    [page, setPage] = useState("library"),
    [previousPage, setPreviousPage] = useState("library");
  const [query, setQuery] = useState(""),
    [status, setStatus] = useState(""),
    [platform, setPlatform] = useState(""),
    [category, setCategory] = useState(null),
    [weakOnly, setWeakOnly] = useState(false);
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [plannerOpen, setPlannerOpen] = useState(false);
  const [saveViewOpen, setSaveViewOpen] = useState(false);
  const [viewName, setViewName] = useState("");
  const [min, setMin] = useState(""),
    [max, setMax] = useState(""),
    [sort, setSort] = useState("contest"),
    [desc, setDesc] = useState(false),
    [showFilters, setShowFilters] = useState(false);
  const [selected, setSelected] = useState(null),
    [preview, setPreview] = useState(false),
    [fullPreview, setFullPreview] = useState(false),
    [solution, setSolution] = useState(null),
    [solutionError, setSolutionError] = useState("");
  const [statusMenu, setStatusMenu] = useState(null),
    [menuIndex, setMenuIndex] = useState(0),
    [saving, setSaving] = useState(false),
    [toast, setToast] = useState(null),
    [queue, setQueue] = useState("all"),
    [mapMode, setMapMode] = useState("knowledge");
  const [undoStack, setUndoStack] = useState([]),
    [redoStack, setRedoStack] = useState([]),
    [inbox, setInbox] = useState(null),
    [inboxOpen, setInboxOpen] = useState(false),
    [inboxBusy, setInboxBusy] = useState(false);
  const deferredQuery = useDeferredValue(query),
    searchRef = useRef(null),
    tableRef = useRef(null),
    readerRef = useRef(null),
    ctrlSolo = useRef(false),
    writeLock = useRef(false),
    toastTimer = useRef(null),
    oldPage = useRef(null),
    solutionSeq = useRef(0);
  const rows = data?.rows || [];
  const categories = useMemo(
    () => organizeCategories(data?.categories || []),
    [data?.categories],
  );
  const counts = useMemo(
    () =>
      Object.fromEntries(
        STATES.map((s) => [s, rows.filter((r) => r.status === s).length]),
      ),
    [rows],
  );
  const platforms = useMemo(
    () => [...new Set(rows.map((r) => r.platform))],
    [rows],
  );
  const queueCounts = useMemo(
    () =>
      Object.fromEntries(
        QUEUES.map((q) => [q.id, rows.filter((r) => r.queue === q.id).length]),
      ),
    [rows],
  );
  const filtered = useMemo(
    () =>
      filteredRows(rows, {
        query: deferredQuery,
        status,
        platform,
        tags: category?.tags || null,
        min,
        max,
        sort,
        desc,
      }).filter(
        (r) =>
          (!weakOnly || ["不会", "待重写"].includes(r.status)) &&
          (!favoritesOnly || prefs.favorites.includes(r.id)),
      ),
    [
      rows,
      deferredQuery,
      status,
      platform,
      category,
      min,
      max,
      sort,
      desc,
      weakOnly,
      favoritesOnly,
      prefs.favorites,
    ],
  );
  const visible = useMemo(
    () =>
      page === "today"
        ? filtered.filter(
            (r) => r.queue && (queue === "all" || r.queue === queue),
          )
        : filtered,
    [page, filtered, queue],
  );
  const current = rows.find((r) => r.id === selected) || null;
  const totalQueue = Object.values(queueCounts).reduce((a, b) => a + b, 0),
    ac = rows.filter(passed).length;
  const recent = rows.filter(
    (r) =>
      ["复现AC", "独立AC"].includes(r.status) &&
      r.date &&
      data?.today &&
      Math.floor((new Date(data.today) - new Date(r.date)) / 86400000) >= 0 &&
      Math.floor((new Date(data.today) - new Date(r.date)) / 86400000) < 7,
  ).length;
  const hasFilters = !!(
    query ||
    status ||
    platform ||
    category ||
    min !== "" ||
    max !== "" ||
    weakOnly ||
    favoritesOnly
  );
  function notify(message, type = "success") {
    setToast({ message, type });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  }
  function updatePrefs(patch) {
    setPrefs((p) => ({ ...p, ...patch }));
  }
  async function reload(quiet = false) {
    if (!quiet) setLoading(true);
    try {
      const d = await api("data");
      setData(d);
      setError("");
      try {
        setInbox(await api("inbox"));
      } catch {}
      if (!quiet) notify("题库已同步");
    } catch (e) {
      setError(e.message);
      if (quiet) notify(e.message, "error");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    reload(true);
    return () => clearTimeout(toastTimer.current);
  }, []);
  useEffect(() => {
    localStorage.setItem("tb.preferences", JSON.stringify(prefs));
    document.documentElement.dataset.theme = prefs.theme;
    document.documentElement.dataset.accent = prefs.accent;
    document.documentElement.dataset.motion = prefs.motion ? "on" : "off";
    document.documentElement.dataset.density = prefs.compact
      ? "compact"
      : "comfortable";
    document.documentElement.dataset.tint = prefs.rowTint ? "on" : "off";
  }, [prefs]);
  useEffect(() => {
    if (!visible.some((r) => r.id === selected))
      setSelected(visible[0]?.id || null);
  }, [visible, selected]);
  useEffect(() => {
    if (page === "settings") {
      setPreview(false);
      setFullPreview(false);
    } else oldPage.current = page;
  }, [page]);
  useEffect(() => {
    if (!statusMenu && !inboxOpen && !saveViewOpen) return;
    const previous = document.activeElement;
    const dialog = document.querySelector('.modal-backdrop [role="dialog"]');
    const targets = () =>
      [
        ...(dialog?.querySelectorAll(
          'button:not(:disabled),input,select,[tabindex="0"]',
        ) || []),
      ].filter((el) => el.getClientRects().length);
    (dialog?.querySelector("input") || targets()[0])?.focus();
    function trap(e) {
      if (e.key !== "Tab") return;
      const items = targets(),
        first = items[0],
        last = items.at(-1);
      if (
        e.shiftKey &&
        (document.activeElement === first ||
          !dialog?.contains(document.activeElement))
      ) {
        e.preventDefault();
        last?.focus();
      } else if (
        !e.shiftKey &&
        (document.activeElement === last ||
          !dialog?.contains(document.activeElement))
      ) {
        e.preventDefault();
        first?.focus();
      }
    }
    document.addEventListener("keydown", trap, true);
    return () => {
      document.removeEventListener("keydown", trap, true);
      if (previous?.isConnected) previous.focus();
    };
  }, [statusMenu?.id, inboxOpen, saveViewOpen]);
  useEffect(() => {
    if (!preview || !selected) return;
    const seq = ++solutionSeq.current;
    const abort = new AbortController();
    setSolution(null);
    setSolutionError("");
    api("solution?id=" + encodeURIComponent(selected), { signal: abort.signal })
      .then((s) => {
        if (seq === solutionSeq.current) setSolution(s);
      })
      .catch((e) => {
        if (e.name !== "AbortError" && seq === solutionSeq.current)
          setSolutionError(e.message);
      });
    return () => abort.abort();
  }, [selected, preview]);
  useEffect(() => {
    tableRef.current
      ?.querySelector('[data-selected="true"]')
      ?.scrollIntoView({ block: "nearest" });
  }, [selected]);
  function clearFilters() {
    setQuery("");
    setStatus("");
    setPlatform("");
    setCategory(null);
    setMin("");
    setMax("");
    setWeakOnly(false);
    setFavoritesOnly(false);
  }
  function toggleFavorite(id) {
    updatePrefs({
      favorites: prefs.favorites.includes(id)
        ? prefs.favorites.filter((x) => x !== id)
        : [...prefs.favorites, id],
    });
  }
  function saveView() {
    const name = viewName.trim();
    if (!name) return;
    const view = {
      name,
      query,
      status,
      platform,
      category,
      min,
      max,
      weakOnly,
      sort,
      desc,
      favoritesOnly,
    };
    updatePrefs({
      views: [...prefs.views.filter((v) => v.name !== name), view],
    });
    setSaveViewOpen(false);
    setViewName("");
    notify("筛选已保存：" + name);
  }
  function loadView(v) {
    setQuery(v.query);
    setStatus(v.status);
    setPlatform(v.platform);
    setCategory(v.category);
    setMin(v.min);
    setMax(v.max);
    setWeakOnly(v.weakOnly);
    setSort(v.sort);
    setDesc(v.desc);
    setFavoritesOnly(v.favoritesOnly || false);
    setPage("library");
  }
  function startPractice(row) {
    clearFilters();
    setPage("library");
    setSelected(row.id);
    setPreview(false);
    setFullPreview(false);
    setPlannerOpen(false);
    notify(
      "已选中 " + row.contest + " " + row.problem + "，开始独立思考",
      "info",
    );
    setTimeout(() => tableRef.current?.focus(), 0);
  }
  function navigate(next) {
    if (next === "settings") {
      setPreviousPage(page === "settings" ? previousPage : page);
      setPage(page === "settings" ? previousPage : "settings");
    } else {
      setPage(next);
      setFullPreview(false);
      tableRef.current?.focus();
    }
  }
  function selectCategory(node, mode) {
    clearFilters();
    setCategory(node);
    setWeakOnly(mode === "weak");
    setStatus("");
    setPage("library");
    setPreview(false);
  }
  function move(n) {
    if (!visible.length) return;
    const i = visible.findIndex((r) => r.id === selected);
    setSelected(visible[Math.min(Math.max(i + n, 0), visible.length - 1)].id);
  }
  async function changeState(row, nextState, date, history = "new", expected) {
    if (!row || writeLock.current) return;
    if (
      row.status === nextState &&
      date === undefined &&
      row.date === data.today
    ) {
      notify("状态已是 " + nextState);
      setStatusMenu(null);
      return;
    }
    writeLock.current = true;
    setSaving(true);
    setStatusMenu(null);
    try {
      const before = { status: row.status, date: row.date };
      const payload = {
        id: row.id,
        status: nextState,
        expected: expected || before,
      };
      if (date !== undefined) payload.date = date;
      const result = await api("status", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-TB-Token": data.token,
        },
        body: JSON.stringify(payload),
      });
      const after = result.row;
      setData((d) => ({
        ...d,
        revision: result.revision,
        rows: d.rows.map((r) => (r.id === row.id ? after : r)),
      }));
      if (
        history === "new" &&
        after &&
        (before.status !== after.status || before.date !== after.date)
      ) {
        setUndoStack((s) => [
          ...s,
          {
            id: row.id,
            before,
            after: { status: after.status, date: after.date },
          },
        ]);
        setRedoStack([]);
      }
      notify(
        (history === "undo"
          ? "已撤销："
          : history === "redo"
            ? "已恢复："
            : "已保存：") +
          row.contest +
          " " +
          row.problem +
          " → " +
          nextState,
      );
      api("data")
        .then(setData)
        .catch(() => notify("已保存；题库刷新失败，请按 F5 重试", "info"));
      return true;
    } catch (e) {
      notify(e.message, "error");
      await reload(true);
      return false;
    } finally {
      writeLock.current = false;
      setSaving(false);
    }
  }
  async function undo() {
    const entry = undoStack.at(-1);
    if (!entry) {
      notify("没有可撤销的状态改动", "info");
      return;
    }
    const row = rows.find((r) => r.id === entry.id);
    if (
      await changeState(
        row,
        entry.before.status,
        entry.before.date,
        "undo",
        entry.after,
      )
    ) {
      setUndoStack((s) => s.slice(0, -1));
      setRedoStack((s) => [...s, entry]);
    }
  }
  async function redo() {
    const entry = redoStack.at(-1);
    if (!entry) {
      notify("没有可恢复的状态改动", "info");
      return;
    }
    const row = rows.find((r) => r.id === entry.id);
    if (
      await changeState(
        row,
        entry.after.status,
        entry.after.date,
        "redo",
        entry.before,
      )
    ) {
      setRedoStack((s) => s.slice(0, -1));
      setUndoStack((s) => [...s, entry]);
    }
  }
  async function openOriginal(row = current) {
    if (!row) return;
    try {
      const s =
        solution && row.id === selected
          ? solution
          : await api("solution?id=" + encodeURIComponent(row.id));
      if (s.url) window.open(s.url, "_blank", "noopener,noreferrer");
      else notify("这道题暂时没有原题链接", "info");
    } catch (e) {
      notify(e.message, "error");
    }
  }
  function toggleReader() {
    if (!current) return;
    setPreview((p) => !p);
    setFullPreview(false);
  }
  async function importInbox(action = "import") {
    setInboxBusy(true);
    try {
      const result = await api("inbox", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-TB-Token": data.token,
        },
        body: JSON.stringify({ action }),
      });
      if (result.needsChoice) {
        setInbox(result);
        return;
      }
      notify(result.message || "收件箱已处理");
      setInboxOpen(false);
      await reload(true);
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setInboxBusy(false);
    }
  }
  useEffect(() => {
    function keydown(e) {
      const input = e.target.closest?.(
        'input,textarea,select,[contenteditable="true"]',
      );
      if (e.isComposing) return;
      if (plannerOpen) return;
      if (saveViewOpen) {
        if (e.key === "Escape") {
          e.preventDefault();
          setSaveViewOpen(false);
        } else if (e.key === "Enter") {
          e.preventDefault();
          saveView();
        }
        return;
      }
      if (e.key === "Control") {
        ctrlSolo.current = true;
        return;
      }
      ctrlSolo.current = false;
      if (input) {
        if (e.key === "Escape") {
          e.preventDefault();
          query ? setQuery("") : tableRef.current?.focus();
        } else if (
          e.target === searchRef.current &&
          ["Enter", "ArrowDown", "ArrowUp"].includes(e.key)
        ) {
          e.preventDefault();
          tableRef.current?.focus();
        }
        return;
      }
      const k = e.key.toLowerCase();
      const reader = e.target.closest?.(".reader");
      if (statusMenu) {
        if (e.key === "Escape") {
          setStatusMenu(null);
          e.preventDefault();
        } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          e.preventDefault();
          setMenuIndex((i) => (i + (e.key === "ArrowDown" ? 1 : 5)) % 6);
        } else if (e.key === "Enter") {
          e.preventDefault();
          changeState(statusMenu, STATES[menuIndex]);
        } else if (/^[1-6]$/.test(e.key)) {
          e.preventDefault();
          changeState(statusMenu, STATES[Number(e.key) - 1]);
        }
        return;
      }
      if (e.ctrlKey && k === "z") {
        e.preventDefault();
        undo();
        return;
      }
      if (e.ctrlKey && k === "y") {
        e.preventDefault();
        redo();
        return;
      }
      if (e.key === "F5") {
        e.preventDefault();
        reload();
        return;
      }
      if (e.key === "F11") {
        e.preventDefault();
        if (document.fullscreenElement) document.exitFullscreen();
        else
          document.documentElement
            .requestFullscreen?.()
            .catch(() => notify("此窗口请使用右上角最大化", "info"));
        return;
      }
      if (
        k === (prefs.keys.search || "f").toLowerCase() ||
        (e.ctrlKey && k === "f")
      ) {
        e.preventDefault();
        if (page === "settings" || page === "knowledge") setPage("library");
        setTimeout(() => searchRef.current?.focus(), 0);
        return;
      }
      if (e.key === (prefs.keys.settings || "?")) {
        e.preventDefault();
        navigate("settings");
        return;
      }
      if (e.key === "Escape" || e.key === "Backspace") {
        e.preventDefault();
        if (inboxOpen) setInboxOpen(false);
        else if (fullPreview) {
          setFullPreview(false);
          tableRef.current?.focus();
        } else if (preview) {
          setPreview(false);
          tableRef.current?.focus();
        } else if (page === "settings") setPage(previousPage);
        else if (hasFilters) clearFilters();
        else setPage("library");
        return;
      }
      if (e.ctrlKey && e.key === "1") {
        e.preventDefault();
        setPage("today");
        return;
      }
      if (e.ctrlKey && e.key === "2") {
        e.preventDefault();
        setPage("knowledge");
        return;
      }
      if (e.ctrlKey && k === "p") {
        e.preventDefault();
        if (current) {
          setPreview(true);
          setFullPreview((f) => !f);
          setTimeout(() => readerRef.current?.focus(), 0);
        }
        return;
      }
      if (e.altKey && e.key === "Enter") {
        e.preventDefault();
        openOriginal();
        return;
      }
      if (e.ctrlKey && e.key === "Enter") {
        e.preventDefault();
        if (current) {
          setStatusMenu(current);
          setMenuIndex(STATES.indexOf(current.status));
        }
        return;
      }
      if (page === "settings") return;
      if (e.ctrlKey && ["ArrowLeft", "ArrowRight"].includes(e.key)) {
        e.preventDefault();
        const sorts = ["contest", "difficulty", "date"];
        setSort(
          (s) =>
            sorts[(sorts.indexOf(s) + (e.key === "ArrowRight" ? 1 : 2)) % 3],
        );
        return;
      }
      if (e.ctrlKey && ["ArrowUp", "ArrowDown"].includes(e.key)) {
        e.preventDefault();
        setDesc((d) => !d);
        return;
      }
      if (e.ctrlKey && ["Home", "End"].includes(e.key)) {
        e.preventDefault();
        setSelected(
          visible[e.key === "Home" ? 0 : visible.length - 1]?.id || null,
        );
        return;
      }
      if (e.key === (prefs.keys.preview || "Enter")) {
        e.preventDefault();
        toggleReader();
        return;
      }
      if (/^[1-6]$/.test(e.key) && page !== "knowledge") {
        e.preventDefault();
        changeState(current, STATES[Number(e.key) - 1]);
        return;
      }
      if (
        [
          "ArrowDown",
          "ArrowUp",
          "w",
          "s",
          "W",
          "S",
          "PageDown",
          "PageUp",
        ].includes(e.key) &&
        page !== "knowledge"
      ) {
        e.preventDefault();
        const n = ["ArrowDown", "s", "S", "PageDown"].includes(e.key) ? 1 : -1;
        if (reader)
          readerRef.current?.scrollBy({
            top: n * (e.key.startsWith("Page") ? 400 : 60),
            behavior: "auto",
          });
        else move(n * (e.key.startsWith("Page") ? 12 : 1));
        return;
      }
      if (["ArrowLeft", "ArrowRight", "a", "d", "A", "D"].includes(e.key)) {
        e.preventDefault();
        const n = ["ArrowRight", "d", "D"].includes(e.key) ? 1 : -1;
        if (reader || fullPreview) move(n);
        else
          setPage(
            (p) => pages[(pages.findIndex((x) => x.id === p) + n + 3) % 3].id,
          );
        return;
      }
      if (e.key === "'" && page === "knowledge") {
        e.preventDefault();
        setMapMode((m) => (m === "knowledge" ? "contest" : "knowledge"));
      }
    }
    function keyup(e) {
      if (
        e.key === "Control" &&
        ctrlSolo.current &&
        preview &&
        !e.target.closest?.("input,textarea,select")
      ) {
        e.preventDefault();
        e.target.closest?.(".reader")
          ? tableRef.current?.focus()
          : readerRef.current?.focus();
      }
      ctrlSolo.current = false;
    }
    window.addEventListener("keydown", keydown);
    window.addEventListener("keyup", keyup);
    return () => {
      window.removeEventListener("keydown", keydown);
      window.removeEventListener("keyup", keyup);
    };
  });
  function resizeReader(e) {
    e.preventDefault();
    const start = e.clientX,
      width = prefs.previewWidth;
    const drag = (ev) =>
      updatePrefs({
        previewWidth: Math.min(
          window.innerWidth - 430,
          Math.max(380, width + start - ev.clientX),
        ),
      });
    const stop = () => {
      window.removeEventListener("pointermove", drag);
      window.removeEventListener("pointerup", stop);
    };
    window.addEventListener("pointermove", drag);
    window.addEventListener("pointerup", stop);
  }
  const table = (items = visible) => (
    <div
      className="table-scroll"
      ref={tableRef}
      tabIndex={0}
      aria-label="题目列表"
    >
      <table className="problem-table">
        <thead>
          <tr>
            {[
              ["contest", "场次 / 题号"],
              ["title", "题目"],
              ["knowledge", "知识点"],
              ["difficulty", "难度"],
              ["status", "状态"],
              ["date", "更新日期"],
            ].map(([id, label]) => (
              <th key={id}>
                {["contest", "title", "difficulty", "date"].includes(id) ? (
                  <button
                    onClick={() => {
                      sort === id
                        ? setDesc(!desc)
                        : (setSort(id), setDesc(false));
                    }}
                  >
                    {label}
                    {sort === id &&
                      (desc ? <ArrowDown size={12} /> : <ArrowUp size={12} />)}
                  </button>
                ) : (
                  label
                )}
              </th>
            ))}
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((r, i) => (
            <tr
              key={r.id}
              data-selected={r.id === selected}
              data-state={STATE_CLASS[STATES.indexOf(r.status)]}
              aria-selected={r.id === selected}
              onClick={() => {
                setSelected(r.id);
                tableRef.current?.focus();
              }}
              onDoubleClick={() => {
                setSelected(r.id);
                setPreview(true);
              }}
            >
              <td>
                <div className="contest-cell">
                  <span className={"platform-mark platform-" + r.platform}>
                    {(r.platform || "?").slice(0, 1)}
                  </span>
                  <div>
                    <strong>{r.contest}</strong>
                    <small>题目 {r.problem}</small>
                  </div>
                </div>
              </td>
              <td>
                <button
                  className="problem-title"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelected(r.id);
                    setPreview(true);
                  }}
                >
                  {r.title}
                </button>
                <span className="problem-subtitle">
                  {r.queue
                    ? QUEUES.find((q) => q.id === r.queue)?.name
                    : "题解已归档"}
                </span>
              </td>
              <td>
                <div className="tags">
                  {r.tags.slice(0, 2).map((t) => (
                    <Tag
                      key={t}
                      name={t}
                      onClick={(name) => selectCategory({ name, tags: [name] })}
                    />
                  ))}
                  {r.tags.length > 2 && (
                    <span className="tag-more" title={r.knowledge}>
                      +{r.tags.length - 2}
                    </span>
                  )}
                </div>
              </td>
              <td>
                <span
                  className={
                    "difficulty " +
                    (r.difficulty >= 2000
                      ? "hard"
                      : r.difficulty >= 1600
                        ? "medium"
                        : "")
                  }
                >
                  {r.difficulty ?? "—"}
                </span>
              </td>
              <td>
                <button
                  className="state-control"
                  disabled={saving}
                  aria-label={"修改 " + r.contest + " " + r.problem + " 状态"}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelected(r.id);
                    setStatusMenu(r);
                    setMenuIndex(STATES.indexOf(r.status));
                  }}
                >
                  <StateBadge state={r.status} />
                  <ChevronDown size={12} />
                </button>
              </td>
              <td className="date-cell">{r.date || "—"}</td>
              <td>
                <div className="row-actions">
                  <button
                    className={
                      "favorite-button " +
                      (prefs.favorites.includes(r.id) ? "on" : "")
                    }
                    aria-label={
                      (prefs.favorites.includes(r.id) ? "取消收藏 " : "收藏 ") +
                      r.title
                    }
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFavorite(r.id);
                    }}
                  >
                    <Star size={14} />
                  </button>
                  <button
                    className="row-open"
                    title="阅读题解"
                    aria-label={"阅读 " + r.title}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelected(r.id);
                      setPreview(true);
                    }}
                  >
                    <BookOpen size={16} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!items.length && (
        <Empty
          title={page === "today" ? "这一组暂时没有待办" : "没有匹配的题目"}
          description={
            hasFilters
              ? "试试减少筛选条件，或换个关键词。"
              : page === "today"
                ? "题目状态更新后，会按复习间隔自动进入对应队列。"
                : "题库中暂时没有题目。"
          }
          action={
            hasFilters && (
              <button className="button" onClick={clearFilters}>
                清除筛选
              </button>
            )
          }
        />
      )}
    </div>
  );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate("library");
          }}
        >
          <span className="brand-icon">
            tb
            <span />
          </span>
          <div>
            <strong>
              TB<span className="brand-version">WORKSPACE</span>
            </strong>
            <small>让每一道题，真正掌握</small>
          </div>
        </a>
        <div className="nav-caption">训练工作台</div>
        <nav>
          {pages.map((p) => (
            <button
              key={p.id}
              className={"nav-item " + (page === p.id ? "active" : "")}
              onClick={() => navigate(p.id)}
            >
              <p.icon size={19} />
              <span>{p.label}</span>
              {p.id === "today" && totalQueue > 0 && <b>{totalQueue}</b>}
              {page === p.id && <span className="nav-active-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-divider" />
        <div className="nav-caption">
          知识领域 <span>{categories.length}</span>
        </div>
        <div className="sidebar-categories">
          {categories
            .filter((c) => categoryStats(c, rows).total > 0)
            .map((c) => (
              <button
                key={c.name}
                className={
                  "sidebar-category " +
                  (category?.name === c.name ? "chosen" : "")
                }
                onClick={() => selectCategory(c)}
              >
                <span className="category-bullet" />
                <span>{c.name}</span>
                <small>{categoryStats(c, rows).total}</small>
              </button>
            ))}
        </div>
        <div className="sidebar-bottom">
          <div className="progress-card">
            <span>
              <Sparkles size={15} /> 掌握是一个过程
            </span>
            <strong>
              {ac}
              <small> / {rows.length} 题已 AC</small>
            </strong>
            <div className="progress-track">
              <span
                style={{
                  width: rows.length ? (ac / rows.length) * 100 + "%" : "0%",
                }}
              />
            </div>
            <p>思考 · 复现 · 复习 · 巩固</p>
          </div>
          <button
            className={"nav-item " + (page === "settings" ? "active" : "")}
            onClick={() => navigate("settings")}
          >
            <Settings2 size={18} />
            <span>偏好设置</span>
            <kbd>?</kbd>
          </button>
          <div className="local-status">
            <span />
            本地题库 <span className="version-label">React 版</span>
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            工作台 <ChevronRight size={13} />{" "}
            <strong>
              {page === "settings"
                ? "偏好设置"
                : pages.find((p) => p.id === page)?.label}
            </strong>
          </div>
          <div className="topbar-actions">
            <span className="today-date">
              {data?.today?.replaceAll("-", " / ")}
            </span>
            <button
              className="icon-button"
              title="收件箱"
              aria-label="收件箱"
              onClick={() => setInboxOpen(true)}
            >
              <Inbox size={18} />
              {(inbox?.pending || inbox?.count) > 0 && (
                <span className="notification-dot" />
              )}
            </button>
            <button
              className="icon-button"
              title="切换明暗主题"
              aria-label="切换明暗主题"
              onClick={() =>
                updatePrefs({
                  theme: prefs.theme === "dark" ? "light" : "dark",
                })
              }
            >
              {prefs.theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button
              className="icon-button"
              title="重新读取题库 F5"
              aria-label="重新读取题库"
              onClick={() => reload()}
            >
              <RotateCcw size={17} className={loading ? "spin" : ""} />
            </button>
            <div className="avatar">TB</div>
          </div>
        </header>
        {error ? (
          <div className="load-error">
            <Empty
              icon={Inbox}
              title="题库暂时无法读取"
              description={error}
              action={
                <button className="button primary" onClick={() => reload()}>
                  重试
                </button>
              }
            />
          </div>
        ) : loading && !data ? (
          <div className="loading-view">
            <LoaderCircle className="spin" size={26} />
            <p>正在打开你的训练工作台…</p>
          </div>
        ) : page === "settings" ? (
          <div className="page settings-page">
            <div className="page-heading">
              <div>
                <div className="eyebrow">MAKE IT YOURS</div>
                <h1>
                  偏好设置
                  <span className="heading-dot" />
                </h1>
                <p>调整到你用起来最顺手的样子。</p>
              </div>
              <button className="button" onClick={() => setPage(previousPage)}>
                <ArrowLeft size={15} />
                返回工作台
              </button>
            </div>
            <div className="settings-grid">
              <section className="settings-card">
                <div className="section-title">
                  <Sun size={19} />
                  <div>
                    <h2>外观与主题</h2>
                    <p>明暗之间，保持清晰的层次。</p>
                  </div>
                </div>
                <div className="theme-choices">
                  {["dark", "light"].map((t) => (
                    <button
                      className={
                        "theme-choice " +
                        t +
                        " " +
                        (prefs.theme === t ? "selected" : "")
                      }
                      onClick={() => updatePrefs({ theme: t })}
                      key={t}
                    >
                      <div className="theme-preview">
                        <i />
                        <div>
                          <span />
                          <span />
                          <span />
                        </div>
                      </div>
                      <span>
                        {t === "dark" ? "石墨深色" : "云白浅色"}
                        {prefs.theme === t && <Check size={15} />}
                      </span>
                    </button>
                  ))}
                </div>
                <div className="setting-label">强调色</div>
                <div className="accent-choices">
                  {[
                    ["violet", "鸢尾紫"],
                    ["blue", "澄空蓝"],
                    ["teal", "松石绿"],
                    ["amber", "暖琥珀"],
                  ].map(([a, l]) => (
                    <button
                      key={a}
                      className={
                        "accent-option " +
                        a +
                        " " +
                        (prefs.accent === a ? "selected" : "")
                      }
                      onClick={() => updatePrefs({ accent: a })}
                    >
                      <span>{prefs.accent === a && <Check size={12} />}</span>
                      {l}
                    </button>
                  ))}
                </div>
              </section>
              <section className="settings-card">
                <div className="section-title">
                  <SlidersHorizontal size={19} />
                  <div>
                    <h2>显示与动效</h2>
                    <p>为长时间阅读调整节奏。</p>
                  </div>
                </div>
                {[
                  ["motion", "界面动效", "切页、浮层和反馈的柔和过渡"],
                  ["compact", "紧凑列表", "更小的行高，同屏显示更多题目"],
                  ["rowTint", "状态行底色", "用柔和的整行颜色区分掌握状态"],
                ].map(([key, label, detail]) => (
                  <label className="toggle-setting" key={key}>
                    <span>
                      <strong>{label}</strong>
                      <small>{detail}</small>
                    </span>
                    <input
                      type="checkbox"
                      checked={prefs[key]}
                      onChange={(e) => updatePrefs({ [key]: e.target.checked })}
                    />
                    <span className="toggle" />
                  </label>
                ))}
              </section>
              <section className="settings-card shortcut-card">
                <div className="section-title">
                  <Keyboard size={19} />
                  <div>
                    <h2>快捷键</h2>
                    <p>熟悉的键盘操作，随时可用。</p>
                  </div>
                </div>
                <div className="editable-shortcuts">
                  {[
                    ["search", "搜索题目"],
                    ["preview", "打开 / 收起题解"],
                    ["settings", "偏好设置"],
                  ].map(([id, l]) => (
                    <label key={id}>
                      {l}
                      <input
                        aria-label={l + "快捷键"}
                        value={prefs.keys[id] || defaults.keys[id]}
                        readOnly
                        onKeyDown={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          if (e.key === "Escape") return e.target.blur();
                          if (
                            e.ctrlKey ||
                            e.altKey ||
                            e.metaKey ||
                            e.key === "Shift" ||
                            e.key === "Tab"
                          ) {
                            notify("请使用单个字母、符号或 Enter", "info");
                            return;
                          }
                          if (!/^[a-z?/]$/i.test(e.key) && e.key !== "Enter") {
                            notify("请使用单个字母、符号或 Enter", "info");
                            return;
                          }
                          const key =
                            e.key.length === 1 ? e.key.toLowerCase() : e.key;
                          const other = Object.entries({
                            ...defaults.keys,
                            ...prefs.keys,
                          }).some(
                            ([k, v]) =>
                              k !== id && v.toLowerCase() === key.toLowerCase(),
                          );
                          if (other || /^[wasd]$/i.test(key)) {
                            notify("这个键已用于其他操作", "info");
                            return;
                          }
                          updatePrefs({ keys: { ...prefs.keys, [id]: key } });
                          e.target.blur();
                        }}
                        onFocus={() =>
                          notify("按下想要使用的键；Esc 取消", "info")
                        }
                      />
                    </label>
                  ))}
                </div>
                <div className="shortcut-list">
                  {[
                    ["↑ ↓ / W S", "移动选中题目"],
                    ["← → / A D", "切换页面；题解里翻题"],
                    ["1 – 6", "直接修改状态"],
                    ["Ctrl + Enter", "打开状态选择"],
                    ["Ctrl + Z / Y", "撤销 / 恢复状态改动"],
                    ["Ctrl + P", "题解全屏 / 分栏"],
                    ["Ctrl 单按", "列表与题解焦点轮换"],
                    ["Ctrl + ← →", "切换排序字段"],
                    ["Ctrl + ↑ ↓", "反转排序方向"],
                    ["F5", "重新读取题库"],
                    ["Esc", "逐层返回"],
                  ].map(([key, l]) => (
                    <div key={key}>
                      <span>{l}</span>
                      <kbd>{key}</kbd>
                    </div>
                  ))}
                </div>
              </section>
              <section className="settings-card about-card">
                <div className="about-symbol">
                  <Layers3 size={32} />
                </div>
                <h2>练过，才算自己的。</h2>
                <p>
                  TB 帮你把一次解题，变成长期掌握。
                  <br />
                  保留思考的节奏，给复习留出位置。
                </p>
                <div className="learning-flow">
                  思考
                  <ChevronRight size={14} />
                  复现
                  <ChevronRight size={14} />
                  复习
                  <ChevronRight size={14} />
                  巩固
                </div>
                <button
                  className="button"
                  onClick={() =>
                    updatePrefs({
                      ...defaults,
                      keys: { ...defaults.keys },
                      favorites: prefs.favorites,
                      views: prefs.views,
                    })
                  }
                >
                  恢复默认偏好
                </button>
              </section>
            </div>
          </div>
        ) : (
          <div className="workspace-content">
            <div className="page">
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    {page === "library"
                      ? "YOUR PROBLEM LIBRARY"
                      : page === "knowledge"
                        ? "CONNECT THE KNOWLEDGE"
                        : "A LITTLE BETTER, EVERY DAY"}
                  </div>
                  <h1>
                    {page === "library"
                      ? "题目总表"
                      : page === "knowledge"
                        ? "知识点地图"
                        : "今天要做的"}
                    <span className="heading-dot" />
                  </h1>
                  <p>
                    {page === "library"
                      ? "从一道题出发，把知识连成体系。"
                      : page === "knowledge"
                        ? "看清知识的结构，找到下一步的方向。"
                        : "先补短板，再用间隔复习留下掌握。"}
                  </p>
                </div>
                <div className="heading-actions">
                  <button
                    className="button primary"
                    onClick={() => setPlannerOpen(true)}
                  >
                    <Sparkles size={15} />
                    训练推荐
                  </button>
                  {page === "library" && (
                    <>
                      <button
                        className="icon-button"
                        disabled={!undoStack.length || saving}
                        aria-label="撤销状态改动"
                        title="撤销 Ctrl+Z"
                        onClick={undo}
                      >
                        <Undo2 size={17} />
                      </button>
                      <button
                        className="icon-button"
                        disabled={!redoStack.length || saving}
                        aria-label="恢复状态改动"
                        title="恢复 Ctrl+Y"
                        onClick={redo}
                      >
                        <Redo2 size={17} />
                      </button>
                      <button
                        className={"button " + (preview ? "active-button" : "")}
                        disabled={!current}
                        onClick={toggleReader}
                      >
                        <PanelRight size={16} />
                        {preview ? "收起题解" : "题解分栏"}
                      </button>
                    </>
                  )}
                  {page === "knowledge" && (
                    <div className="segmented">
                      <button
                        className={mapMode === "knowledge" ? "active" : ""}
                        onClick={() => setMapMode("knowledge")}
                      >
                        按知识点
                      </button>
                      <button
                        className={mapMode === "contest" ? "active" : ""}
                        onClick={() => setMapMode("contest")}
                      >
                        按场次
                      </button>
                    </div>
                  )}
                </div>
              </div>
              <div className="stat-cards">
                <div className="stat-card">
                  <span>
                    收录题目 <BookOpen size={16} />
                  </span>
                  <div>
                    {fmt(rows.length)}
                    <small>题</small>
                  </div>
                  <p>
                    {new Set(rows.map((r) => r.contest)).size} 场比赛 ·{" "}
                    {platforms.length} 个平台
                  </p>
                </div>
                <div className="stat-card">
                  <span>
                    已经 AC <CheckCheck size={17} />
                  </span>
                  <div>
                    {fmt(ac)}
                    <small>题</small>
                    <b className="stat-percent">
                      {rows.length ? Math.round((ac / rows.length) * 100) : 0}%
                    </b>
                  </div>
                  <p>
                    复现 {counts["复现AC"] || 0} · 独立 {counts["独立AC"] || 0}{" "}
                    · 巩固 {counts["巩固"] || 0}
                  </p>
                </div>
                <div className="stat-card">
                  <span>
                    待补与待重写 <Layers3 size={16} />
                  </span>
                  <div>
                    {fmt((counts["不会"] || 0) + (counts["待重写"] || 0))}
                    <small>题</small>
                  </div>
                  <p>优先解决尚未掌握的题目</p>
                </div>
                <div className="stat-card accent-stat">
                  <span>
                    最近 7 天 AC <Sparkles size={16} />
                  </span>
                  <div>
                    {fmt(recent)}
                    <small>题</small>
                  </div>
                  <p>每一次独立思考，都在积累</p>
                  <span className="stat-decoration" />
                </div>
              </div>
              {page === "knowledge" ? (
                <section className="map-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>
                        {mapMode === "knowledge" ? "知识结构" : "比赛归档"}
                      </h2>
                      <p>
                        {mapMode === "knowledge"
                          ? "点击分类筛选题目，展开查看更细的知识分支。"
                          : "按平台与场次整理，点击进入对应题目。"}
                      </p>
                    </div>
                    <span className="subtle-badge">
                      {mapMode === "knowledge"
                        ? "一题多标签 · 按题去重"
                        : "按场次统计"}
                    </span>
                  </div>
                  {mapMode === "knowledge" ? (
                    <>
                      <div className="category-header">
                        <span>知识领域 / 知识点</span>
                        <span>题目数</span>
                        <span>AC 占比</span>
                        <span>待攻克</span>
                      </div>
                      {categories.map((c) => (
                        <CategoryNode
                          key={c.name}
                          node={c}
                          rows={rows}
                          onFilter={selectCategory}
                        />
                      ))}
                    </>
                  ) : (
                    <div className="contest-groups">
                      {platforms.map((p) => (
                        <section key={p}>
                          <h3>
                            <span className={"platform-mark platform-" + p}>
                              {p.slice(0, 1)}
                            </span>
                            {p}
                            <small>
                              {rows.filter((r) => r.platform === p).length} 题
                            </small>
                          </h3>
                          {[
                            ...new Set(
                              rows
                                .filter((r) => r.platform === p)
                                .map((r) => r.contest),
                            ),
                          ]
                            .sort((a, b) =>
                              a.localeCompare(b, "zh-CN", { numeric: true }),
                            )
                            .map((c) => {
                              const cr = rows.filter((r) => r.contest === c);
                              return (
                                <button
                                  className="contest-card"
                                  key={c}
                                  onClick={() => {
                                    clearFilters();
                                    setQuery(c);
                                    setPlatform(p);
                                    setPage("library");
                                  }}
                                >
                                  <div>
                                    <strong>{c}</strong>
                                    <small>
                                      {cr.length} 题 ·{" "}
                                      {cr.filter(passed).length} 题 AC
                                    </small>
                                  </div>
                                  <div className="mini-track">
                                    <span
                                      style={{
                                        width:
                                          (cr.filter(passed).length /
                                            cr.length) *
                                            100 +
                                          "%",
                                      }}
                                    />
                                  </div>
                                  <ArrowUpRight size={17} />
                                </button>
                              );
                            })}
                        </section>
                      ))}
                    </div>
                  )}
                </section>
              ) : (
                <>
                  {page === "today" && (
                    <div className="queue-cards">
                      {QUEUES.map((q) => (
                        <button
                          key={q.id}
                          className={
                            "queue-card " +
                            q.color +
                            " " +
                            (queue === q.id ? "active" : "")
                          }
                          onClick={() =>
                            setQueue(queue === q.id ? "all" : q.id)
                          }
                        >
                          <span>
                            {q.name}
                            <b>{queueCounts[q.id]}</b>
                          </span>
                          <p>{q.desc}</p>
                        </button>
                      ))}
                    </div>
                  )}
                  <div
                    className={
                      "table-and-reader " + (preview ? "has-reader" : "")
                    }
                  >
                    <section className="library-panel">
                      <div className="library-toolbar">
                        <div className="search-field">
                          <Search size={17} />
                          <input
                            ref={searchRef}
                            aria-label="搜索题目"
                            placeholder="搜索题目、场次、知识点…"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                          />
                          {query ? (
                            <button
                              aria-label="清空搜索"
                              onClick={() => setQuery("")}
                            >
                              <X size={14} />
                            </button>
                          ) : (
                            <kbd>{prefs.keys.search.toUpperCase()}</kbd>
                          )}
                        </div>
                        <div className="toolbar-extras">
                          <button
                            className={
                              "button favorite-toggle " +
                              (favoritesOnly ? "active-button" : "")
                            }
                            aria-label="收藏题目筛选"
                            onClick={() => setFavoritesOnly(!favoritesOnly)}
                          >
                            <Star size={14} />
                            收藏 {prefs.favorites.length}
                          </button>
                          <button
                            className={
                              "button filter-button " +
                              (showFilters || hasFilters ? "active-button" : "")
                            }
                            onClick={() => setShowFilters(!showFilters)}
                          >
                            <SlidersHorizontal size={15} />
                            筛选{hasFilters && <span className="filter-dot" />}
                          </button>
                        </div>
                      </div>
                      {prefs.views.length > 0 && (
                        <div className="saved-views">
                          <span>常用筛选</span>
                          {prefs.views.map((v) => (
                            <div className="saved-view" key={v.name}>
                              <button onClick={() => loadView(v)}>
                                {v.name}
                              </button>
                              <button
                                aria-label={"删除筛选 " + v.name}
                                onClick={() =>
                                  updatePrefs({
                                    views: prefs.views.filter(
                                      (x) => x.name !== v.name,
                                    ),
                                  })
                                }
                              >
                                <X size={11} />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="status-tabs">
                        <button
                          className={!status ? "active" : ""}
                          onClick={() => setStatus("")}
                        >
                          全部<span>{rows.length}</span>
                        </button>
                        {STATES.map((s, i) => (
                          <button
                            key={s}
                            className={
                              status === s ? "active " + STATE_CLASS[i] : ""
                            }
                            onClick={() => setStatus(status === s ? "" : s)}
                          >
                            <span className={"tab-dot " + STATE_CLASS[i]} />
                            {s}
                            <span>{counts[s] || 0}</span>
                          </button>
                        ))}
                      </div>
                      {showFilters && (
                        <div className="filter-panel">
                          <label>
                            平台
                            <select
                              aria-label="平台筛选"
                              value={platform}
                              onChange={(e) => setPlatform(e.target.value)}
                            >
                              <option value="">全部平台</option>
                              {platforms.map((p) => (
                                <option key={p}>{p}</option>
                              ))}
                            </select>
                          </label>
                          <label>
                            最低难度
                            <input
                              aria-label="最低难度"
                              type="number"
                              min="0"
                              max="5000"
                              step="100"
                              placeholder="不限"
                              value={min}
                              onChange={(e) => setMin(e.target.value)}
                            />
                          </label>
                          <span className="filter-range">—</span>
                          <label>
                            最高难度
                            <input
                              aria-label="最高难度"
                              type="number"
                              min="0"
                              max="5000"
                              step="100"
                              placeholder="不限"
                              value={max}
                              onChange={(e) => setMax(e.target.value)}
                            />
                          </label>
                          <button
                            className="text-button"
                            onClick={clearFilters}
                          >
                            重置筛选
                          </button>
                          <button
                            className="text-button"
                            onClick={() => {
                              setViewName(
                                category?.name || query || "我的训练范围",
                              );
                              setSaveViewOpen(true);
                            }}
                          >
                            <BookmarkPlus size={13} /> 保存筛选
                          </button>
                          {min !== "" &&
                            max !== "" &&
                            Number(min) > Number(max) && (
                              <span className="filter-error">
                                最低难度不能超过最高难度
                              </span>
                            )}
                        </div>
                      )}
                      {category && (
                        <div className="filter-chips">
                          <span>
                            <Network size={13} />
                            {category.name}
                            {weakOnly ? " · 待攻克" : ""}
                            <button
                              aria-label="清除知识点筛选"
                              onClick={() => {
                                setCategory(null);
                                setWeakOnly(false);
                              }}
                            >
                              <X size={12} />
                            </button>
                          </span>
                        </div>
                      )}
                      {table()}
                      <footer className="table-footer">
                        <span>
                          {hasFilters ? "匹配" : "共"}{" "}
                          <strong>{fmt(visible.length)}</strong> 题
                          {page === "today" && queue !== "all" && (
                            <button
                              className="text-button"
                              onClick={() => setQueue("all")}
                            >
                              查看全部待办
                            </button>
                          )}
                        </span>
                        <span>
                          {saving ? (
                            <>
                              <LoaderCircle size={13} className="spin" />
                              保存中
                            </>
                          ) : (
                            <>
                              <span className="saved-dot" />
                              更改自动保存
                            </>
                          )}
                        </span>
                      </footer>
                    </section>
                    {preview && (
                      <>
                        <div
                          className="split-handle"
                          role="separator"
                          aria-label="调整题解宽度"
                          onPointerDown={resizeReader}
                        />
                        <aside
                          className={
                            "reader-panel " + (fullPreview ? "full-reader" : "")
                          }
                          style={{
                            width: fullPreview ? undefined : prefs.previewWidth,
                          }}
                        >
                          <div className="reader-header">
                            <div>
                              <BookOpen size={16} />
                              <strong>题解阅读</strong>
                              <span>
                                {current?.contest} · {current?.problem}
                              </span>
                            </div>
                            <div>
                              <button
                                className="icon-button"
                                title="打开原题 Alt+Enter"
                                aria-label="打开原题"
                                onClick={() => openOriginal()}
                              >
                                <ArrowUpRight size={16} />
                              </button>
                              <button
                                className="icon-button"
                                title="切换全屏 Ctrl+P"
                                aria-label="切换题解全屏"
                                onClick={() => setFullPreview(!fullPreview)}
                              >
                                {fullPreview ? (
                                  <Minimize2 size={16} />
                                ) : (
                                  <Maximize2 size={16} />
                                )}
                              </button>
                              <button
                                className="icon-button"
                                aria-label="收起题解"
                                onClick={() => {
                                  setPreview(false);
                                  setFullPreview(false);
                                }}
                              >
                                <X size={17} />
                              </button>
                            </div>
                          </div>
                          <div
                            className="reader"
                            ref={readerRef}
                            tabIndex={0}
                            aria-label="题解阅读区"
                          >
                            {solutionError ? (
                              <Empty
                                icon={BookOpen}
                                title="暂时无法打开题解"
                                description={solutionError}
                              />
                            ) : solution ? (
                              <>
                                <div className="reader-topic">
                                  <span>{current?.knowledge}</span>
                                  <h2>{current?.title}</h2>
                                  <StateBadge state={current?.status} />
                                </div>
                                <article className="markdown">
                                  <ReactMarkdown
                                    remarkPlugins={[remarkGfm, remarkMath]}
                                    rehypePlugins={[
                                      [rehypeKatex, { strict: false }],
                                    ]}
                                    components={{
                                      a: ({ children, ...props }) => (
                                        <a
                                          {...props}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                        >
                                          {children}
                                        </a>
                                      ),
                                      pre: ({ children }) => (
                                        <div className="code-block">
                                          <button
                                            className="code-copy"
                                            onClick={(e) => {
                                              const text =
                                                e.currentTarget.parentElement.querySelector(
                                                  "pre",
                                                )?.innerText;
                                              navigator.clipboard
                                                .writeText(text || "")
                                                .then(() =>
                                                  notify("代码已复制"),
                                                )
                                                .catch(() =>
                                                  notify(
                                                    "请选中代码手动复制",
                                                    "info",
                                                  ),
                                                );
                                            }}
                                          >
                                            复制代码
                                          </button>
                                          <pre>{children}</pre>
                                        </div>
                                      ),
                                    }}
                                  >
                                    {normalizeMarkdown(
                                      solution.markdown || "暂无题解内容",
                                    )}
                                  </ReactMarkdown>
                                </article>
                              </>
                            ) : (
                              <div className="reader-loading">
                                <LoaderCircle className="spin" size={22} />
                                <p>正在打开题解…</p>
                              </div>
                            )}
                          </div>
                          <div className="reader-footer">
                            <button
                              className="button"
                              disabled={
                                visible.findIndex((r) => r.id === selected) <= 0
                              }
                              onClick={() => move(-1)}
                            >
                              ← 上一题
                            </button>
                            <span>
                              {current?.problem} · {current?.difficulty ?? "—"}
                            </span>
                            <button
                              className="button"
                              disabled={
                                visible.findIndex((r) => r.id === selected) >=
                                visible.length - 1
                              }
                              onClick={() => move(1)}
                            >
                              下一题 →
                            </button>
                          </div>
                        </aside>
                      </>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </main>
      {plannerOpen && (
        <PracticePlanner
          rows={rows}
          onClose={() => setPlannerOpen(false)}
          onSelect={startPractice}
          onStart={startPractice}
        />
      )}
      {saveViewOpen && (
        <div
          className="modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setSaveViewOpen(false);
          }}
        >
          <form
            className="status-dialog"
            role="dialog"
            aria-modal="true"
            aria-label="保存常用筛选"
            onSubmit={(e) => {
              e.preventDefault();
              saveView();
            }}
          >
            <div className="dialog-heading">
              <h2>保存常用筛选</h2>
              <button
                type="button"
                className="icon-button"
                aria-label="关闭保存筛选"
                onClick={() => setSaveViewOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <p>下次点击名称，就能回到这组筛选条件。</p>
            <input
              className="save-view-input"
              aria-label="筛选名称"
              autoFocus
              maxLength={24}
              value={viewName}
              onChange={(e) => setViewName(e.target.value)}
            />
            <button
              className="button primary"
              disabled={!viewName.trim()}
              type="submit"
            >
              保存筛选
            </button>
          </form>
        </div>
      )}
      {statusMenu && (
        <div
          className="modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setStatusMenu(null);
          }}
        >
          <div
            className="status-dialog"
            role="dialog"
            aria-modal="true"
            aria-label="修改题目状态"
          >
            <div className="dialog-heading">
              <div>
                <span className="eyebrow">UPDATE PROGRESS</span>
                <h2>记录这次进展</h2>
              </div>
              <button
                className="icon-button"
                aria-label="关闭状态选择"
                onClick={() => setStatusMenu(null)}
              >
                <X size={19} />
              </button>
            </div>
            <p>
              {statusMenu.contest} · {statusMenu.problem} · {statusMenu.title}
            </p>
            <div className="state-options">
              {STATES.map((s, i) => (
                <button
                  key={s}
                  className={
                    (menuIndex === i ? "focused " : "") +
                    (statusMenu.status === s ? "current" : "")
                  }
                  onMouseEnter={() => setMenuIndex(i)}
                  onClick={() => changeState(statusMenu, s)}
                >
                  <kbd>{i + 1}</kbd>
                  <StateBadge state={s} />
                  <span>
                    {
                      [
                        "尚未开始",
                        "自己还没做出来",
                        "看过题解，待独立重写",
                        "关掉题解重写通过",
                        "独立完成，没有参考材料",
                        "间隔复习再次通过",
                      ][i]
                    }
                  </span>
                  {statusMenu.status === s && <Check size={16} />}
                </button>
              ))}
            </div>
            <div className="dialog-footnote">同时更新日期 · 支持撤销</div>
          </div>
        </div>
      )}
      {inboxOpen && (
        <div
          className="modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setInboxOpen(false);
          }}
        >
          <div
            className="status-dialog"
            role="dialog"
            aria-modal="true"
            aria-label="题解收件箱"
          >
            <div className="dialog-heading">
              <h2>题解收件箱</h2>
              <button
                className="icon-button"
                aria-label="关闭收件箱"
                onClick={() => setInboxOpen(false)}
              >
                <X size={19} />
              </button>
            </div>
            <p>把题解 Markdown 放进题解目录的「_收件箱」，即可导入题库。</p>
            {(inbox?.pending || inbox?.count) > 0 ? (
              <>
                <p>待导入：{inbox.pending || inbox.count} 份</p>
                {inbox.conflicts?.length > 0 && (
                  <div className="inbox-conflicts">
                    {inbox.conflicts.map((c, i) => (
                      <p key={i}>
                        {typeof c === "string" ? c : JSON.stringify(c)}
                      </p>
                    ))}
                  </div>
                )}
                <div className="inbox-actions">
                  <button
                    disabled={inboxBusy}
                    className="button primary"
                    onClick={() => importInbox()}
                  >
                    导入新题解
                  </button>
                  {inbox.conflicts?.length > 0 && (
                    <>
                      <button
                        className="button"
                        disabled={inboxBusy}
                        onClick={() => importInbox("overwrite")}
                      >
                        覆盖冲突项
                      </button>
                      <button
                        className="button"
                        disabled={inboxBusy}
                        onClick={() => importInbox("skip")}
                      >
                        跳过冲突项
                      </button>
                    </>
                  )}
                </div>
              </>
            ) : (
              <Empty
                icon={Inbox}
                title="收件箱是空的"
                description="新的题解放进来后，会出现在这里。"
              />
            )}
          </div>
        </div>
      )}
      {toast && (
        <div className={"toast " + toast.type} role="status">
          {toast.type === "success" ? (
            <Check size={16} />
          ) : toast.type === "error" ? (
            <X size={16} />
          ) : (
            <Circle size={15} />
          )}
          <span>{toast.message}</span>
          <button aria-label="关闭提示" onClick={() => setToast(null)}>
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
