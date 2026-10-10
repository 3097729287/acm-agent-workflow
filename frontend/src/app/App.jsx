import { request } from '@/api/client';
import {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
  useDeferredValue,
} from "react";
import {
  BookOpen,
  Library,
  CalendarDays,
  Flag,
  History,
  Network,
  Settings2,
  Search,
  ChevronRight,
  ChevronDown,
  ChevronLeft,
  PanelLeftClose,
  PanelLeftOpen,
  Sun,
  Moon,
  Command,
  Plus,
  X,
  Play,
  Check,
  Star,
  SlidersHorizontal,
  ArrowUp,
  ArrowDown,
  ArrowUpRight,
  Inbox,
  LoaderCircle,
  Keyboard,
  Maximize2,
  Minimize2,
  Clock,
  Trophy,
  Medal,
  ListOrdered,
  RefreshCw,
  Target,
  Code2,
  Copy,
  BookmarkPlus,
  Layers,
  ArrowLeft,
  Bell,
  ChartNoAxesCombined,
  Activity,
  MinusCircle,
  Award,
  UserRound,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import Workbench from "./Workbench.jsx";
import { LecturesPanel, LectureDisclosure } from "@/pages/LecturesPanel.jsx";
import { difficultyBand, solutionBlocks } from "@/lib/practiceMetadata.js";
import {
  GrowthPage,
  ActivityPage,
  CompetitionPage,
  ConnectionsPanel,
  UpdatePanel,
  TranslationSettings,
  AchievementPanel,
} from "@/pages/ProgressPanels.jsx";
import { organizeCategories } from "@/models/model.js";
import NavigationSettings, { orderedPages } from "@/pages/NavigationSettings.jsx";
import RankingsPage, { ProfileSettings } from "@/pages/CommunityPanel.jsx";
import MockSetup from "./MockSetup.jsx";
import SubmissionRecords, { MockHistory } from "@/pages/SubmissionRecords.jsx";
import { normalizeMarkdown } from "@/lib/normalizeMarkdown.js";
import {
  QUEUES,
  verdictLabel,
  verdictTone,
  progressRows,
  filterRows,
  groupContests,
  categoryCounts,
  remainingSeconds,
  timerText,
  nextSurviving,
  emptyWorkspace,
} from "@/models/workspaceModel.js";

const PAGES = [
  { id: "mine", label: "我的训练", icon: Target, key: "1" },
  { id: "library", label: "题库", icon: Library, key: "2" },
  { id: "today", label: "今日待办", icon: CalendarDays, key: "3" },
  { id: "competitions", label: "比赛", icon: Flag, key: "4" },
  { id: "mock", label: "模拟赛", icon: Clock, key: "5" },
  { id: "records", label: "提交记录", icon: History, key: "6" },
  { id: "growth", label: "成长与能力", icon: ChartNoAxesCombined, key: "7" },
  { id: "activity", label: "活动记录", icon: Activity, key: "8" },
  { id: "lectures", label: "从零讲", icon: BookOpen, key: "9" },
  { id: "rankings", label: "排行榜", icon: ListOrdered, key: "" },
];
const DEFAULTS = {
  theme: "dark",
  accent: "violet",
  motion: true,
  compact: true,
  collapsed: false,
  favorites: [],
  views: [],
  readerWidth: 520,
  fontSize: 15,
  navOrder: ["mine", "today", "library", "lectures", "competitions", "mock", "records", "growth", "activity", "rankings"],
  navLabels: {},
  navGroups: {},
  pageBookmarks: [],
  seenAchievements: [],
};
function readPreferences() {
  try {
    return {
      ...DEFAULTS,
      ...JSON.parse(localStorage.getItem("tb.preferences") || "{}"),
    };
  } catch {
    return { ...DEFAULTS };
  }
}
const blankFilters = () => ({
  query: "",
  platform: "",
  category: null,
  min: "",
  max: "",
  result: "",
  favoritesOnly: false,
  contest: "",
  sort: "contestDate",
  ids: null,
  updateTitle: "",
  desc: false,
  setId: "",
});
const formatDate = (value) =>
  value
    ? new Date(value).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
const num = (value) => Number(value || 0).toLocaleString("zh-CN");
const isTyping = (el) =>
  el instanceof Element &&
  !!el.closest('input,textarea,select,[contenteditable="true"],[data-editor]');

function Empty({ icon: Icon = Search, title, description, children }) {
  return (
    <div className="empty">
      <div className="empty-symbol">
        <Icon size={26} />
      </div>
      <h2>{title}</h2>
      <p>{description}</p>
      {children && <div className="empty-actions">{children}</div>}
    </div>
  );
}
function Verdict({ value, accepted = false }) {
  const current = value || (accepted ? "AC" : null);
  return (
    <span className={"verdict " + verdictTone(current)}>
      <span />
      {verdictLabel(current)}
      {accepted && current !== "AC" && (
        <Check
          size={11}
          style={{ color: "var(--success)" }}
          aria-label="曾通过本地评测"
          title="曾通过本地评测"
        />
      )}
    </span>
  );
}
function Difficulty({ value }) {
  return <span className={"difficulty band-" + difficultyBand(value)}>{value ?? "—"}</span>;
}
function IconButton({ label, icon: Icon, onClick, children, ...props }) {
  return (
    <button
      className="icon-button"
      title={label}
      aria-label={label}
      onClick={onClick}
      {...props}
    >
      {Icon && <Icon size={17} />} {children}
    </button>
  );
}
function Modal({ title, onClose, children, wide = false, footer }) {
  const ref = useRef(null),
    restore = useRef(document.activeElement),
    close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const node = ref.current;
    const focusable = () =>
      [
        ...node.querySelectorAll(
          'button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]',
        ),
      ].filter((el) => el.getClientRects().length);
    (
      focusable().find((el) => el.matches("input")) ||
      focusable()[0] ||
      node
    ).focus();
    const key = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        close.current?.();
      }
      if (e.key === "Tab") {
        const all = focusable();
        if (!all.length) {
          e.preventDefault();
          return;
        }
        const first = all[0],
          last = all.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    node.addEventListener("keydown", key);
    return () => {
      node.removeEventListener("keydown", key);
      if (restore.current?.isConnected) restore.current.focus();
    };
  }, []);
  return (
    <div
      className="modal-overlay"
      onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}
    >
      <section
        className={"modal " + (wide ? "wide" : "")}
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <IconButton label="关闭" icon={X} onClick={onClose} />
        </header>
        <div className="modal-body">{children}</div>
        {footer && <footer>{footer}</footer>}
      </section>
    </div>
  );
}
function Markdown({ text, onCopy, images = {} }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[
          [rehypeKatex, { throwOnError: false, strict: "ignore" }],
        ]}
        components={{
          img: ({ node, src, alt, ...props }) => <img {...props} src={images[src] || src} alt={alt || ""} loading="lazy" />,
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noreferrer" />
          ),
          pre: (props) => (
            <div className="code-block">
              <button
                className="copy-code"
                onClick={() => onCopy?.(props.children?.props?.children || "")}
              >
                <Copy size={13} />
                复制
              </button>
              <pre {...props} />
            </div>
          ),
        }}
      >
        {normalizeMarkdown(text || "")}
      </ReactMarkdown>
    </div>
  );
}

// Each tree item owns one tab stop. Arrow keys follow the visible tree, rather than the question table.
function KnowledgeTree({
  nodes,
  rows,
  training,
  onFilter,
  selected,
  large = false,
}) {
  const [expanded, setExpanded] = useState(new Set()),
    [focused, setFocused] = useState(null),
    [query, setQuery] = useState("");
  const items = useMemo(() => {
    const out = [];
    const needle = query.trim().toLowerCase();
    const matchesNode = node => !needle || `${node.name} ${(node.tags || []).join(" ")}`.toLowerCase().includes(needle) || (node.children || []).some(matchesNode);
    function walk(branches, parent = null, depth = 0) {
      branches.forEach((node, i) => {
        const key = (parent ? parent + "/" : "") + i + ":" + node.name,
          counts = categoryCounts(node, rows, training);
        if (!counts.available || !matchesNode(node)) return;
        out.push({ node, key, parent, depth, counts });
        if (expanded.has(key) || needle) walk(node.children || [], key, depth + 1);
      });
    }
    walk(nodes);
    return out;
  }, [nodes, rows, training, expanded, query]);
  const expandAll = () => {
    const keys = new Set();
    const walk = (branches, parent = null) => branches.forEach((node, index) => { const key = (parent ? parent + "/" : "") + index + ":" + node.name; if (node.children?.length) keys.add(key); walk(node.children || [], key); });
    walk(nodes); setExpanded(keys);
  };
  const focusKey = items.some((item) => item.key === focused)
    ? focused
    : items[0]?.key;
  const focusItem = (key) => {
    setFocused(key);
    const target = document.querySelector(
      `[data-tree-key="${CSS.escape(key)}"][data-tree-size="${large ? "large" : "small"}"]`,
    );
    if (target) target.focus();
    else
      requestAnimationFrame(() =>
        document
          .querySelector(
            `[data-tree-key="${CSS.escape(key)}"][data-tree-size="${large ? "large" : "small"}"]`,
          )
          ?.focus(),
      );
  };
  const toggle = (key) =>
    setExpanded((current) => {
      const next = new Set(current);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  function keyDown(e, item, index) {
    if (e.ctrlKey || e.altKey || e.metaKey) return;
    if (
      [
        "ArrowDown",
        "ArrowUp",
        "Home",
        "End",
        "ArrowRight",
        "ArrowLeft",
      ].includes(e.key)
    ) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (e.key === "ArrowDown")
      focusItem(items[Math.min(items.length - 1, index + 1)]?.key);
    if (e.key === "ArrowUp") focusItem(items[Math.max(0, index - 1)]?.key);
    if (e.key === "Home") focusItem(items[0]?.key);
    if (e.key === "End") focusItem(items.at(-1)?.key);
    if (e.key === "ArrowRight") {
      if (item.node.children?.length && !expanded.has(item.key))
        toggle(item.key);
      else if (items[index + 1]?.parent === item.key)
        focusItem(items[index + 1].key);
    }
    if (e.key === "ArrowLeft") {
      if (expanded.has(item.key)) toggle(item.key);
      else if (item.parent) focusItem(item.parent);
    }
    if (e.key === "Enter" && !item.node.children?.length) {
      e.preventDefault();
      e.stopPropagation();
      onFilter(item.node);
    }
  }
  return (
    <div className="knowledge-tree-shell">
    <label className="knowledge-search"><Search size={14} /><input aria-label={large ? "搜索完整知识清单" : "搜索知识清单"} placeholder="搜索知识点" value={query} onChange={event => setQuery(event.target.value)} />{query && <button aria-label="清空知识清单搜索" onClick={() => setQuery("")}><X size={13} /></button>}</label>
    <div className="knowledge-tree-tools"><button onClick={expandAll}>展开全部</button><button onClick={() => { setExpanded(new Set()); setQuery(""); }}>收起全部</button><span>{items.length} 项</span></div>
    <div
      className={"knowledge-tree " + (large ? "tree-large" : "")}
      role="tree"
      aria-label={large ? "知识点完整目录" : "知识点目录"}
    >
      {items.map((item, index) => {
        const { node, key, depth, counts } = item,
          kids = !!node.children?.length,
          isOpen = expanded.has(key) || !!query.trim();
        return (
          <div
            className={"tree-line " + (selected === node.name ? "active" : "")}
            key={key}
            data-depth={depth}
            data-branch={kids ? "true" : "false"}
            style={{ "--depth": depth }}
          >
            <button
              role="treeitem"
              aria-level={depth + 1}
              aria-expanded={kids ? isOpen : undefined}
              aria-selected={selected === node.name}
              className="tree-item"
              data-tree-key={key}
              data-tree-size={large ? "large" : "small"}
              tabIndex={focusKey === key ? 0 : -1}
              onFocus={() => setFocused(key)}
              onKeyDown={(e) => keyDown(e, item, index)}
              onClick={() => (kids ? toggle(key) : onFilter(node))}
              title={
                kids
                  ? (isOpen ? "收起" : "展开") + node.name
                  : "筛选 " + node.name
              }
            >
              {kids ? (
                isOpen ? (
                  <ChevronDown size={14} />
                ) : (
                  <ChevronRight size={14} />
                )
              ) : (
                <span className="leaf-dot" />
              )}
              <span className="tree-name">{node.name}</span>
              <span
                className="tree-count"
                aria-label={`题库 ${counts.available} 题，参与 ${counts.active} 题，通过 ${counts.accepted} 题，待办 ${counts.due} 题`}
              >
                <span>{counts.available}</span>
                {!large && counts.active > 0 && (
                  <span className="tree-personal-count">
                    {counts.accepted}/{counts.active}
                    {counts.due > 0 && <em> · {counts.due}待补</em>}
                  </span>
                )}
              </span>
              {large && (
                <>
                  <span className="tree-active">
                    {counts.active ? counts.active + " 题参与" : "—"}
                  </span>
                  <span className="tree-ac">
                    {counts.active
                      ? counts.accepted + "/" + counts.active + " AC"
                      : "尚未开始"}
                  </span>
                </>
              )}
            </button>
            {kids && (
              <button
                className="tree-filter"
                aria-label={"筛选 " + node.name}
                title={"筛选 " + node.name}
                onClick={() => onFilter(node)}
              >
                <ArrowUpRight size={13} />
              </button>
            )}
          </div>
        );
      })}
      {!items.length && <p className="knowledge-empty">没有匹配的知识点</p>}
    </div>
    </div>
  );
}

export default function App() {
  const [prefs, setPrefs] = useState(readPreferences),
    [data, setData] = useState(null),
    [workspace, setWorkspace] = useState(emptyWorkspace),
    [inbox, setInbox] = useState(null),
    [hub, setHub] = useState(null),
    [insights, setInsights] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [page, setPage] = useState("mine"),
    [filters, setFilters] = useState({
      library: blankFilters(),
      mine: blankFilters(),
    }),
    [todayQuery, setTodayQuery] = useState(""),
    [todayQueue, setTodayQueue] = useState("all"),
    [showFilters, setShowFilters] = useState(false);
  const [libraryPage, setLibraryPage] = useState(1),
    [libraryPageSize, setLibraryPageSize] = useState(50);
  const [selected, setSelected] = useState(null),
    [practiceId, setPracticeId] = useState(null),
    [mockSlot, setMockSlot] = useState(null),
    [record, setRecord] = useState(null),
    [recordOnlyPending, setRecordOnlyPending] = useState(false),
    [mockTab, setMockTab] = useState("create"),
    [selectedSubmission, setSelectedSubmission] = useState(null),
    [settingsTab, setSettingsTab] = useState("appearance"),
    [submissionLog, setSubmissionLog] = useState([]),
    [submissionPage, setSubmissionPage] = useState({ total: 0, nextOffset: 0, hasMore: false }),
    [submissionLoading, setSubmissionLoading] = useState(false);
  const [dialog, setDialog] = useState(null),
    [toast, setToast] = useState(null),
    [busy, setBusy] = useState(false),
    [viewName, setViewName] = useState(""),
    [commandQuery, setCommandQuery] = useState("");
  const [readerId, setReaderId] = useState(null),
    [reader, setReader] = useState(null),
    [readerError, setReaderError] = useState(""),
    [readerFull, setReaderFull] = useState(false),
    [lectureId, setLectureId] = useState(null),
    [now, setNow] = useState(Date.now());
  const token = useRef(""),
    loadSeq = useRef(0),
    workspaceTime = useRef(0),
    searchRef = useRef(null),
    listRef = useRef(null),
    toastTimer = useRef(null),
    readerSeq = useRef(0),
    submissionSeq = useRef(0),
    contextRef = useRef(null),
    advanceRef = useRef(null),
    visibleRef = useRef([]),
    selectedRef = useRef(null),
    serverOffset = useRef(0),
    previousActive = useRef(null);
  const api = useCallback((path, body) => request(path, body, token.current), []);
  const notice = useCallback((message, type = "info", action = null) => {
    clearTimeout(toastTimer.current);
    setToast({ message, type, action });
    toastTimer.current = setTimeout(() => setToast(null), 4200);
  }, []);
  const applyWorkspace = useCallback((value) => {
    if (!value) return;
    const stamp = value.now ? Date.parse(value.now) : Date.now();
    if (stamp >= workspaceTime.current) {
      workspaceTime.current = stamp;
      setWorkspace(value);
      if (value.now) {
        serverOffset.current = stamp - Date.now();
        setNow(stamp);
      }
    }
  }, []);
  const reload = useCallback(
    async (initial = false) => {
      const seq = ++loadSeq.current;
      if (initial) setLoading(true);
      try {
        const [library, personal, incoming, connections, evidence] =
          await Promise.all([
            api("data"),
            api("workspace"),
            api("inbox"),
            api("hub").catch(() => null),
            api("insights").catch(() => null),
          ]);
        if (seq !== loadSeq.current) return;
        token.current = library.token;
        setData(library);
        applyWorkspace(personal);
        setInbox(incoming);
        setHub(connections);
        setInsights(evidence);
        setError("");
      } catch (e) {
        if (seq === loadSeq.current) setError(e.message);
      } finally {
        if (seq === loadSeq.current) setLoading(false);
      }
    },
    [api, applyWorkspace],
  );
  useEffect(() => {
    reload(true);
    return () => clearTimeout(toastTimer.current);
  }, [reload]);
  useEffect(() => {
    localStorage.setItem("tb.preferences", JSON.stringify(prefs));
    const root = document.documentElement;
    root.dataset.theme = prefs.theme;
    root.dataset.accent = prefs.accent;
    root.dataset.motion = prefs.motion ? "on" : "off";
    root.dataset.density = prefs.compact ? "compact" : "comfortable";
    root.style.setProperty(
      "--ui-font-size",
      `${Math.min(18, Math.max(13, Number(prefs.fontSize) || 15))}px`,
    );
  }, [prefs]);
  useEffect(() => {
    const tick = setInterval(
      () => setNow(Date.now() + serverOffset.current),
      1000,
    );
    return () => clearInterval(tick);
  }, []);
  useEffect(() => {
    if (!data) return;
    const refresh = () =>
      api("workspace")
        .then(applyWorkspace)
        .catch(() => {});
    const timer = setInterval(
      refresh,
      workspace.activeContest || workspace.summary?.pending ? 2500 : 15000,
    );
    window.addEventListener("focus", refresh);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", refresh);
    };
  }, [
    !!data,
    workspace.activeContest?.id,
    workspace.summary?.pending,
    api,
    applyWorkspace,
  ]);
  useEffect(() => {
    const old = previousActive.current;
    if (old && !workspace.activeContest) {
      const finished = workspace.contests.find((c) => c.id === old);
      if (finished && page === "mock") {
        setRecord(finished);
        setPage("mock");
        setMockTab("history");
        setRecordOnlyPending(false);
        if (Date.parse(finished.deadline) <= Date.now() + serverOffset.current) notice("计时结束，提交记录已保存，可以开始复盘");
      }
    }
    previousActive.current = workspace.activeContest?.id || null;
  }, [workspace.activeContest?.id, workspace.contests, page, notice]);
  useEffect(() => {
    if (
      workspace.activeContest &&
      remainingSeconds(workspace.activeContest, now) === 0
    )
      api("workspace")
        .then(applyWorkspace)
        .catch(() => {});
  }, [
    workspace.activeContest?.id,
    Math.floor(now / 10000),
    api,
    applyWorkspace,
  ]);
  useEffect(() => {
    const seq = ++submissionSeq.current;
    if (page !== "records") return;
    setSubmissionLoading(true);
    api("submissions?limit=100&offset=0")
      .then((value) => {
        if (seq !== submissionSeq.current) return;
        const logs = value.submissions || [];
        setSubmissionLog(logs);
        setSubmissionPage({ total: value.total ?? logs.length, nextOffset: (value.offset || 0) + logs.length, hasMore: !!value.hasMore });
      })
      .catch((e) => { if (seq === submissionSeq.current) notice(e.message, "error"); })
      .finally(() => { if (seq === submissionSeq.current) setSubmissionLoading(false); });
  }, [page, workspace.summary?.attempts, api, notice]);
  async function loadMoreSubmissions() {
    if (submissionLoading || !submissionPage.hasMore) return;
    const seq = submissionSeq.current;
    setSubmissionLoading(true);
    try {
      const value = await api(`submissions?limit=100&offset=${submissionPage.nextOffset}`);
      if (seq !== submissionSeq.current) return;
      const logs = value.submissions || [];
      setSubmissionLog((previous) => { const known = new Set(previous.map(item => item.id)); return [...previous, ...logs.filter(item => !known.has(item.id))]; });
      setSubmissionPage({ total: value.total ?? submissionPage.total, nextOffset: (value.offset ?? submissionPage.nextOffset) + logs.length, hasMore: !!value.hasMore && logs.length > 0 });
    } catch (e) { if (seq === submissionSeq.current) notice(e.message, "error"); }
    finally { if (seq === submissionSeq.current) setSubmissionLoading(false); }
  }
  useEffect(() => {
    if (!data) return;
    const refresh = () =>
      Promise.all([api("hub"), api("insights")])
        .then(([h, i]) => {
          setHub(h);
          setInsights(i);
        })
        .catch(() => {});
    refresh();
    const timer = setInterval(refresh, hub?.sync?.busy ? 3000 : 60000);
    return () => clearInterval(timer);
  }, [
    !!data,
    workspace.summary?.attempts,
    workspace.summary?.total,
    workspace.summary?.accepted,
    hub?.sync?.busy,
    api,
  ]);
  useEffect(() => {
    if (!hub?.sync?.lastSuccessAt) return;
    let cancelled = false;
    Promise.all([api("data"), api("workspace")])
      .then(([library, personal]) => {
        if (cancelled) return;
        token.current = library.token;
        setData(library);
        applyWorkspace(personal);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [hub?.sync?.lastSuccessAt, api, applyWorkspace]);
  const rows = useMemo(
      () => progressRows(data?.rows || [], workspace),
      [data?.rows, workspace],
    ),
    mine = useMemo(() => rows.filter((r) => r.active), [rows]);
  const categories = useMemo(
    () => organizeCategories(data?.categories || []),
    [data?.categories],
  );
  const libraryQuery = useDeferredValue(filters.library.query),
    mineQuery = useDeferredValue(filters.mine.query),
    dueQuery = useDeferredValue(todayQuery);
  const currentFilters = filters[page] || blankFilters(),
    query =
      page === "today" ? dueQuery : page === "mine" ? mineQuery : libraryQuery;
  const visible = useMemo(() => {
    if (page === "today") {
      const order = new Map(QUEUES.map((q, i) => [q.id, i]));
      return filterRows(
        mine.filter(
          (r) => r.queue && (todayQueue === "all" || r.queue === todayQueue),
        ),
        { query, sort: "difficulty" },
      ).sort((a, b) => (order.get(a.queue) ?? 9) - (order.get(b.queue) ?? 9));
    }
    if (!["library", "mine"].includes(page)) return [];
    const base = page === "mine" ? mine : rows,
      params = { ...currentFilters, query, favorites: prefs.favorites };
    let filtered = filterRows(base, params);
    if (page === "mine" && params.setId === "@single") {
      const grouped = new Set([...workspace.sets.flatMap(set => set.ids || []), ...workspace.contests.flatMap(contest => contest.slots?.map(slot => slot.id) || [])]);
      filtered = filtered.filter(row => !grouped.has(row.id));
    } else if (page === "mine" && params.setId) {
      const set =
        workspace.sets?.find((s) => s.id === params.setId) ||
        workspace.contests?.find((s) => s.id === params.setId);
      const ids = new Set(set?.ids || set?.slots?.map((s) => s.id) || []);
      filtered = filtered.filter((r) => ids.has(r.id));
    }
    return filtered;
  }, [
    page,
    mine,
    rows,
    currentFilters,
    query,
    prefs.favorites,
    todayQueue,
    workspace.sets,
    workspace.contests,
  ]);
  const libraryPages = Math.max(1, Math.ceil(visible.length / libraryPageSize)),
    currentLibraryPage = Math.min(libraryPage, libraryPages),
    libraryStart = (currentLibraryPage - 1) * libraryPageSize;
  const displayedRows = useMemo(
    () => page === "library" ? visible.slice(libraryStart, libraryStart + libraryPageSize) : visible,
    [page, visible, libraryStart, libraryPageSize],
  );
  useEffect(() => { setLibraryPage(1); }, [filters.library, libraryQuery]);
  useEffect(() => { if (page === "library") setLibraryPage(currentLibraryPage); }, [page, currentLibraryPage]);
  useEffect(() => { if (page === "library") listRef.current?.scrollTo({ top: 0 }); }, [page, currentLibraryPage, libraryPageSize]);
  visibleRef.current = visible;
  selectedRef.current = selected;
  useEffect(() => {
    if (!["mine", "library", "today"].includes(page) || practiceId) return;
    if (!displayedRows.some((r) => r.id === selected))
      setSelected(displayedRows[0]?.id || null);
  }, [displayedRows, page, practiceId, selected]);
  useEffect(() => {
    if (practiceId || !selected) return;
    const element = listRef.current?.querySelector(
      `tr[data-id="${CSS.escape(selected)}"]`,
    );
    element?.scrollIntoView({ block: "nearest" });
  }, [selected, practiceId]);
  const active = workspace.activeContest,
    summary = workspace.summary || emptyWorkspace.summary;
  const passedCount = mine.filter((r) => r.accepted).length,
    totalCount = mine.length,
    dueCount = mine.filter((r) => r.queue).length;
  const setFilter = (patch, target = page) =>
    setFilters((current) => ({
      ...current,
      [target]: { ...current[target], ...patch },
    }));
  function go(next) {
    document.querySelectorAll(".topbar details[open]").forEach(node => node.removeAttribute("open"));
    setPracticeId(null);
    setRecord(null);
    setPage(next);
    setShowFilters(false);
    setReaderId(null);
    setReaderFull(false);
    setDialog(null);
    requestAnimationFrame(() => listRef.current?.focus());
  }
  function filterCategory(node, explicitTarget) {
    const target =
      explicitTarget ||
      (["mine", "library"].includes(page) && mine.length ? page : "library");
    setPracticeId(null);
    setPage(target);
    setFilter({ category: node, setId: "" }, target);
    notice("已筛选：" + node.name);
    requestAnimationFrame(() => listRef.current?.focus());
  }
  async function openUpdate(notification) {
    try {
      const library = await api("data");
      setData(library);
      const targets = new Set([...(notification.problemIds || []), ...(notification.solutionIds || [])]);
      const urls = new Set((notification.problemUrls || []).map(url => String(url).replace(/[?#].*$/, "").replace(/\/$/, "")));
      const ids = library.rows.filter(row => targets.has(row.id) || urls.has(String(row.url || "").replace(/[?#].*$/, "").replace(/\/$/, ""))).map(row => row.id);
      if (!ids.length) {
        notice(notification.url ? "该内容尚未加入本地题库，可查看通知中的仓库链接" : "这条旧通知没有可核对的具体题目，新的通知会保留题目列表");
        return;
      }
      go("library");
      setFilter({ ...blankFilters(), ids, updateTitle: notification.title }, "library");
      setSelected(ids[0]);
      api("hub/dismiss", { id: notification.id }).then(setHub).catch(() => {});
      focusList();
    } catch (e) { notice(e.message, "error"); }
  }
  function resetFilters() {
    if (page === "today") {
      setTodayQuery("");
      setTodayQueue("all");
    } else setFilters((f) => ({ ...f, [page]: blankFilters() }));
  }
  function toggleFavorite(id) {
    setPrefs((p) => ({
      ...p,
      favorites: p.favorites.includes(id)
        ? p.favorites.filter((x) => x !== id)
        : [...p.favorites, id],
    }));
  }
  function focusList() {
    requestAnimationFrame(() => listRef.current?.focus());
  }
  async function openPractice(id) {
    if (!id || busy) return;
    if (active?.slots.some((s) => s.id === id)) {
      setReaderId(null);
      setPracticeId(null);
      setPage("mock");
      setMockSlot(id);
      return;
    }
    setBusy(true);
    try {
      const result = await api("training/start", { id });
      applyWorkspace(result.workspace);
      contextRef.current = {
        page,
        ids: visibleRef.current.map((r) => r.id),
        id,
      };
      advanceRef.current = null;
      setPracticeId(id);
      setReaderId(null);
      setReaderFull(false);
    } catch (e) {
      notice(e.message, "error");
    } finally {
      setBusy(false);
    }
  }
  async function removeTraining(id) {
    if (!id || busy) return;
    setBusy(true);
    try {
      const ids = visibleRef.current.map((r) => r.id);
      const result = await api("training/remove", { id });
      applyWorkspace(result.workspace);
      setSelected(
        nextSurviving(
          ids,
          id,
          ids.filter((x) => x !== id),
        ),
      );
      notice("已取消训练，代码与历史记录保留。", "info", {
        label: "恢复",
        run: async () => {
          try {
            const restored = await api("training/start", { id });
            applyWorkspace(restored.workspace);
            setSelected(id);
            notice("已恢复训练");
            focusList();
          } catch (e) {
            notice(e.message, "error");
          }
        },
      });
      focusList();
    } catch (e) {
      notice(e.message, "error");
    } finally {
      setBusy(false);
    }
  }
  function progressChanged(value) {
    const id = practiceId;
    if (id) {
      const previous = workspace.training.find((r) => r.id === id),
        next = value.training.find((r) => r.id === id);
      if (next?.accepted && !previous?.accepted) advanceRef.current = id;
    }
    applyWorkspace(value);
  }
  function exitPractice() {
    const context = contextRef.current;
    setPracticeId(null);
    setReaderId(null);
    if (context) {
      const id = advanceRef.current ? nextSurviving(
          context.ids,
          advanceRef.current,
          visibleRef.current.map((r) => r.id),
        ) : context.id;
      if (page === "library") {
        const index = visibleRef.current.findIndex(row => row.id === id);
        if (index >= 0) setLibraryPage(Math.floor(index / libraryPageSize) + 1);
      }
      setSelected(id);
    }
    advanceRef.current = null;
    focusList();
    api("workspace")
      .then(applyWorkspace)
      .catch(() => {});
  }
  async function nextPractice() {
    const context = contextRef.current;
    const ids = context?.ids || visibleRef.current.map((r) => r.id);
    const index = ids.indexOf(practiceId);
    const next = ids[index + 1];
    if (next) {
      setPracticeId(null);
      await openPractice(next);
    } else {
      exitPractice();
      notice("这组题已经到最后一题");
    }
  }
  async function startOriginalContest(name) {
    setBusy(true);
    try {
      const result = await api("training/contest", { contest: name });
      applyWorkspace(result.workspace);
      setPage("mine");
      setPracticeId(null);
      setFilter({ ...blankFilters(), setId: result.set.id }, "mine");
      setSelected(result.set.ids[0]);
      notice("已加入训练：" + name);
      focusList();
    } catch (e) {
      notice(e.message, "error");
    } finally {
      setBusy(false);
    }
  }
  function startedMock(result) {
    applyWorkspace(result.workspace);
    setPracticeId(null);
    setReaderId(null);
    setReader(null);
    setReaderFull(false);
    setPage("mock");
    setMockTab("create");
    setMockSlot(result.contest.slots[0]?.id);
    notice("计时已开始，祝你专注", "success");
  }
  async function finishMock() {
    if (!active) return;
    setBusy(true);
    try {
      const result = await api("contests/finish", { contestId: active.id });
      applyWorkspace(result.workspace);
      setRecord(result.contest);
      setPage("mock");
      setMockTab("history");
      setDialog(null);
      setReaderId(null);
      notice("比赛已结束，可以开始复盘");
    } catch (e) {
      notice(e.message, "error");
    } finally {
      setBusy(false);
    }
  }
  async function openRecord(contest) {
    try {
      const result = await api("contest?id=" + encodeURIComponent(contest.id));
      setRecord(result.contest);
      setPage("mock");
      setMockTab("history");
      setRecordOnlyPending(false);
      setPracticeId(null);
    } catch (e) {
      notice(e.message, "error");
    }
  }
  async function openSolution(id) {
    if (!id) return;
    if (active?.slots.some((slot) => slot.id === id)) {
      notice("比赛进行中，结束后可查看题解", "error");
      return;
    }
    const sequence = ++readerSeq.current;
    setReaderId(id);
    setReader(null);
    setReaderError("");
    try {
      const result = await api("solution?id=" + encodeURIComponent(id));
      if (readerSeq.current === sequence) {
        setReader(result);
        api("workspace")
          .then(applyWorkspace)
          .catch(() => {});
      }
    } catch (e) {
      if (readerSeq.current === sequence) setReaderError(e.message);
    }
  }
  useEffect(() => {
    if (readerId && active?.slots.some((slot) => slot.id === readerId)) {
      readerSeq.current++;
      setReaderId(null);
      setReader(null);
      setReaderFull(false);
    }
  }, [active?.id, readerId]);
  const copy = async (text) => {
    try {
      await navigator.clipboard.writeText(String(text).replace(/\n$/, ""));
      notice("已复制");
    } catch {
      notice("复制未完成，请选择文字后按 Ctrl+C", "error");
    }
  };
  function resizeReader(e) {
    const start = e.clientX,
      width = prefs.readerWidth;
    const controller = new AbortController();
    e.currentTarget.setPointerCapture?.(e.pointerId);
    window.addEventListener(
      "pointermove",
      (event) =>
        setPrefs((p) => ({
          ...p,
          readerWidth: Math.min(
            900,
            Math.max(340, width + start - event.clientX),
          ),
        })),
      { signal: controller.signal },
    );
    window.addEventListener("pointerup", () => controller.abort(), {
      once: true,
      signal: controller.signal,
    });
  }
  const commands = [
    ...orderedPages(PAGES, prefs).map((p) => ({
      name: "打开" + p.label,
      detail: p.key ? "Ctrl+" + p.key : "",
      action: () => go(p.id),
    })),
    {
      name: "收起 / 展开侧栏",
      detail: "Ctrl+B",
      action: () => setPrefs((p) => ({ ...p, collapsed: !p.collapsed })),
    },
    {
      name: "搜索当前页面",
      detail: "Ctrl+F",
      action: () => searchRef.current?.focus(),
    },
    {
      name: "切换深浅主题",
      action: () =>
        setPrefs((p) => ({
          ...p,
          theme: p.theme === "dark" ? "light" : "dark",
        })),
    },
    { name: "打开键盘帮助", detail: "?", action: () => setDialog("help") },
    { name: "查看训练概览", action: () => setDialog("summary") },
    { name: "偏好设置", detail: "Ctrl+,", action: () => go("settings") },
  ];
  useEffect(() => {
    function keyboard(e) {
      if (e.defaultPrevented || e.isComposing) return;
      if (document.querySelector('[aria-modal="true"]')) return;
      const control = e.ctrlKey || e.metaKey,
        typing = isTyping(e.target),
        button =
          e.target instanceof Element &&
          !!e.target.closest('button,a,[role="treeitem"]');
      if (control && e.key.toLowerCase() === "k") {
        e.preventDefault();
        e.stopPropagation();
        setCommandQuery("");
        setDialog("commands");
        return;
      }
      if (control && e.key.toLowerCase() === "b") {
        e.preventDefault();
        e.stopPropagation();
        setPrefs((p) => ({ ...p, collapsed: !p.collapsed }));
        return;
      }
      if (control && /^[1-9]$/.test(e.key)) {
        e.preventDefault();
        e.stopPropagation();
        go(PAGES[Number(e.key) - 1].id);
        return;
      }
      if (control && [",", "0"].includes(e.key)) {
        e.preventDefault();
        e.stopPropagation();
        go("settings");
        return;
      }
      if (e.key === "F6") {
        e.preventDefault();
        e.stopPropagation();
        const regions = [
          document.querySelector('.sidebar nav [aria-current="page"]') ||
            document.querySelector(".sidebar nav button"),
          document.querySelector(
            '.sidebar-tree-scroll [role="treeitem"][tabindex="0"]',
          ),
          listRef.current ||
            document.querySelector(
              ".workspace-area input,.workspace-area button",
            ),
          document.querySelector(".cm-content"),
          document.querySelector('.wb-console [tabindex="0"]'),
        ].filter(
          (x, i, a) => x && x.getClientRects().length && a.indexOf(x) === i,
        );
        const focus = document.activeElement;
        const index = regions.findIndex(
          (x) =>
            x === focus ||
            x.contains(focus) ||
            (x.closest(".sidebar nav") &&
              x.closest(".sidebar nav")?.contains(focus)) ||
            (x.closest(".sidebar-tree-scroll") &&
              x.closest(".sidebar-tree-scroll")?.contains(focus)),
        );
        regions[
          (index + (e.shiftKey ? -1 : 1) + regions.length) % regions.length
        ]?.focus();
        return;
      }
      if (
        control &&
        e.key.toLowerCase() === "f" &&
        !practiceId &&
        !(page === "mock" && active)
      ) {
        e.preventDefault();
        searchRef.current?.focus();
        searchRef.current?.select();
        return;
      }
      if (e.key === "F5") {
        e.preventDefault();
        reload().then(() => notice("已刷新"));
        return;
      }
      if (e.key === "Escape") {
        if (readerId) {
          e.preventDefault();
          readerSeq.current++;
          setReaderId(null);
          setReaderFull(false);
          focusList();
          return;
        }
        if (typing && e.target === searchRef.current) {
          e.preventDefault();
          if (page === "today") setTodayQuery("");
          else setFilter({ query: "" });
          focusList();
          return;
        }
        if (practiceId && !typing) {
          e.preventDefault();
          exitPractice();
          return;
        }
        if (record && !typing) {
          e.preventDefault();
          setRecord(null);
          return;
        }
      }
      if (typing || control || e.altKey || button) return;
      if (e.key === "?") {
        e.preventDefault();
        setDialog("help");
        return;
      }
      if (page === "mock" && active && /^[1-9]$/.test(e.key)) {
        const slot = active.slots[Number(e.key) - 1];
        if (slot) {
          e.preventDefault();
          setMockSlot(slot.id);
        }
        return;
      }
      if (practiceId) return;
      if (!["mine", "library", "today"].includes(page)) return;
      if (e.key === "f" || e.key === "/") {
        e.preventDefault();
        searchRef.current?.focus();
        return;
      }
      const list = listRef.current;
      if (
        !list?.contains(document.activeElement) &&
        document.activeElement !== document.body
      )
        return;
      const items = visibleRef.current,
        current = items.findIndex((r) => r.id === selectedRef.current);
      if (
        [
          "ArrowDown",
          "ArrowUp",
          "j",
          "k",
          "Home",
          "End",
          "PageDown",
          "PageUp",
        ].includes(e.key)
      ) {
        e.preventDefault();
        let index = current;
        if (e.key === "Home") index = 0;
        else if (e.key === "End") index = items.length - 1;
        else
          index += ["ArrowDown", "j"].includes(e.key)
            ? 1
            : ["ArrowUp", "k"].includes(e.key)
              ? -1
              : e.key === "PageDown"
                ? 10
                : -10;
        const nextIndex = Math.max(0, Math.min(items.length - 1, index));
        if (page === "library") setLibraryPage(Math.floor(nextIndex / libraryPageSize) + 1);
        setSelected(items[nextIndex]?.id || null);
        list.focus();
      }
      if (e.key === "Enter" && selectedRef.current) {
        e.preventDefault();
        openPractice(selectedRef.current);
      }
      if (e.key.toLowerCase() === "u" && selectedRef.current) {
        e.preventDefault();
        openSolution(selectedRef.current);
      }
      if (e.key.toLowerCase() === "s" && selectedRef.current) {
        e.preventDefault();
        toggleFavorite(selectedRef.current);
      }
      if (
        e.key === "Delete" &&
        selectedRef.current &&
        ["mine", "today"].includes(page)
      ) {
        e.preventDefault();
        removeTraining(selectedRef.current);
      }
    }
    window.addEventListener("keydown", keyboard, true);
    return () => window.removeEventListener("keydown", keyboard, true);
  });

  function renderRows(items) {
    return items.map((row) => (
      <tr
        key={row.id}
        data-id={row.id}
        data-selected={selected === row.id}
        aria-selected={selected === row.id}
        onClick={(e) => {
          if (!e.target.closest("button,a")) {
            setSelected(row.id);
            listRef.current?.focus();
          }
        }}
        onDoubleClick={(e) =>
          !e.target.closest("button,a") && openPractice(row.id)
        }
      >
        <td className="title-cell">
          <span
            className={"platform-symbol " + row.platform}
            title={row.platform}
          >
            {row.platform === "牛客"
              ? "牛"
              : row.platform === "洛谷"
                ? "洛"
                : row.platform === "AtCoder"
                  ? "At"
                  : "CF"}
          </span>
          <div>
            <button
              className="problem-title"
              onClick={() => {
                setSelected(row.id);
                openPractice(row.id);
              }}
            >
              {row.title}
            </button>
            <span className="problem-source">
              {row.contest} · {row.problem}
              {row.solutionAvailable === false && (
                <em className="missing-solution"> · 题解未生成</em>
              )}
            </span>
          </div>
        </td>
        <td className="tags-cell">
          {row.tags.slice(0, 3).map((tag) => (
            <button
              key={tag}
              className="tag"
              onClick={() => filterCategory({ name: tag, tags: [tag] })}
            >
              {tag}
            </button>
          ))}
          {row.tags.length > 3 && (
            <span className="more-tags" title={row.tags.slice(3).join(" / ")}>
              +{row.tags.length - 3}
            </span>
          )}
        </td>
        <td>
          <Difficulty value={row.difficulty} />
        </td>
        <td>
          <Verdict value={row.verdict} accepted={row.accepted} />
        </td>
        <td className="last-date">
          {row.lastSubmittedAt
            ? formatDate(row.lastSubmittedAt)
            : row.active
              ? "已加入训练"
              : "—"}
        </td>
        <td className="row-actions">
          <button
            aria-label={
              (prefs.favorites.includes(row.id) ? "取消收藏 " : "收藏 ") +
              row.title
            }
            className={
              "row-icon " +
              (prefs.favorites.includes(row.id) ? "favorited" : "")
            }
            onClick={() => toggleFavorite(row.id)}
          >
            <Star
              size={15}
              fill={prefs.favorites.includes(row.id) ? "currentColor" : "none"}
            />
          </button>
          <button
            className="row-icon"
            aria-label={"题解 " + row.title}
            onClick={() => openSolution(row.id)}
            disabled={
              row.solutionAvailable === false ||
              !!active?.slots.some((s) => s.id === row.id)
            }
          >
            <BookOpen size={15} />
          </button>
          <button
            className="row-icon start"
            aria-label={"练习 " + row.title}
            onClick={() => openPractice(row.id)}
            disabled={busy}
          >
            <Play size={15} />
          </button>
          {row.active && (
            <button
              className="row-icon remove-training"
              aria-label={"取消训练 " + row.title}
              onClick={() => removeTraining(row.id)}
              disabled={busy || !!active?.slots.some((s) => s.id === row.id)}
              title="取消训练，保留代码与历史记录（列表 Delete）"
            >
              <MinusCircle size={15} />
            </button>
          )}
        </td>
      </tr>
    ));
  }
  function renderTable(items, { today = false } = {}) {
    return (
      <div
        className="table-scroll"
        ref={listRef}
        tabIndex={0}
        role="region"
        aria-label={today ? "今日待办题目" : "题目列表"}
      >
        <table className="problem-table">
          <thead>
            <tr>
              <th className="title-head">题目 / 来源</th>
              <th>知识点</th>
              <th>
                <button
                  onClick={() =>
                    !today &&
                    setFilter({
                      sort: "difficulty",
                      desc:
                        currentFilters.sort === "difficulty"
                          ? !currentFilters.desc
                          : false,
                    })
                  }
                >
                  难度
                  {!today &&
                    currentFilters.sort === "difficulty" &&
                    (currentFilters.desc ? (
                      <ArrowDown size={12} />
                    ) : (
                      <ArrowUp size={12} />
                    ))}
                </button>
              </th>
              <th>提交结果</th>
              <th>最近练习</th>
              <th>
                <span className="sr-only">操作</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {today
              ? QUEUES.map((q) => {
                  const group = items.filter((r) => r.queue === q.id);
                  return group.length ? (
                    <FragmentRows
                      key={q.id}
                      header={
                        <tr className={"queue-heading " + q.color}>
                          <td colSpan={6}>
                            <strong>{q.name}</strong>
                            <span>{group.length} 题</span>
                            <small>{q.description}</small>
                          </td>
                        </tr>
                      }
                    >
                      {renderRows(group)}
                    </FragmentRows>
                  ) : null;
                })
              : renderRows(items)}
          </tbody>
        </table>
        {!items.length && (
          <Empty
            icon={today ? Check : Search}
            title={today ? "今天的待办已清空" : "没有匹配的题目"}
            description={
              today
                ? "继续新的练习，或等下一次复习到期。"
                : "试试减少筛选条件，或换一个关键词。"
            }
          >
            <button className="secondary" onClick={resetFilters}>
              清除筛选
            </button>
            {today && (
              <button className="primary" onClick={() => go("library")}>
                选择新的练习
              </button>
            )}
          </Empty>
        )}
      </div>
    );
  }
  function toolbar() {
    const today = page === "today";
    return (
      <>
        <div className="table-toolbar">
          <div className="search-box">
            <Search size={17} />
            <input
              ref={searchRef}
              aria-label="搜索题目"
              placeholder={today ? "搜索今日待办…" : "搜索题目、场次、知识点…"}
              value={today ? todayQuery : currentFilters.query}
              onChange={(e) =>
                today
                  ? setTodayQuery(e.target.value)
                  : setFilter({ query: e.target.value })
              }
              onKeyDown={(e) => {
                if (e.key === "ArrowDown") {
                  e.preventDefault();
                  focusList();
                }
                if (e.key === "Enter") {
                  e.preventDefault();
                  focusList();
                }
              }}
            />
            {(today ? todayQuery : currentFilters.query) ? (
              <IconButton
                label="清空搜索"
                icon={X}
                onClick={() =>
                  today ? setTodayQuery("") : setFilter({ query: "" })
                }
              />
            ) : (
              <kbd>F</kbd>
            )}
          </div>
          {!today && (
            <>
              <button
                className={
                  "secondary favorite-filter " +
                  (currentFilters.favoritesOnly ? "active" : "")
                }
                aria-label="收藏题目筛选"
                aria-pressed={currentFilters.favoritesOnly}
                onClick={() =>
                  setFilter({ favoritesOnly: !currentFilters.favoritesOnly })
                }
              >
                <Star size={15} />
                <span>收藏</span>
              </button>
              <button
                className={"secondary " + (showFilters ? "active" : "")}
                onClick={() => setShowFilters(!showFilters)}
                aria-expanded={showFilters}
              >
                <SlidersHorizontal size={15} />
                筛选
              </button>
              <select
                className="sort-select"
                aria-label="排序方式"
                value={currentFilters.sort}
                onChange={(e) =>
                  setFilter({
                    sort: e.target.value,
                    desc: e.target.value === "date",
                  })
                }
              >
                <option value="contestDate">比赛时间 · 最新在前</option>
                <option value="contest">按场次</option>
                <option value="difficulty">按难度</option>
                <option value="date">最近练习</option>
                <option value="title">按题名</option>
              </select>
            </>
          )}
          <span className="toolbar-count">{visible.length} 题</span>
        </div>
        {today ? (
          <div className="filter-tabs">
            <button
              className={todayQueue === "all" ? "active" : ""}
              onClick={() => setTodayQueue("all")}
            >
              全部待办 <small>{dueCount}</small>
            </button>
            {QUEUES.filter((q) => mine.some((r) => r.queue === q.id)).map(
              (q) => (
                <button
                  key={q.id}
                  className={todayQueue === q.id ? "active" : ""}
                  onClick={() => setTodayQueue(q.id)}
                >
                  {q.name}{" "}
                  <small>{mine.filter((r) => r.queue === q.id).length}</small>
                </button>
              ),
            )}
          </div>
        ) : (
          <>
            {showFilters && (
              <div className="filter-fields">
                <label>
                  平台
                  <select
                    aria-label="平台筛选"
                    value={currentFilters.platform}
                    onChange={(e) => setFilter({ platform: e.target.value })}
                  >
                    <option value="">全部平台</option>
                    {[...new Set(rows.map((r) => r.platform))].map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                  </select>
                </label>
                <label>
                  最低难度
                  <input
                    aria-label="最低难度"
                    type="number"
                    step={100}
                    value={currentFilters.min}
                    onChange={(e) => setFilter({ min: e.target.value })}
                  />
                </label>
                <span>—</span>
                <label>
                  最高难度
                  <input
                    aria-label="最高难度"
                    type="number"
                    step={100}
                    value={currentFilters.max}
                    onChange={(e) => setFilter({ max: e.target.value })}
                  />
                </label>
                <label>
                  提交结果
                  <select
                    aria-label="提交结果筛选"
                    value={currentFilters.result}
                    onChange={(e) => setFilter({ result: e.target.value })}
                  >
                    <option value="">全部结果</option>
                    <option value="accepted">本地 AC</option>
                    <option value="pending">尚未 AC</option>
                    <option value="sample">样例通过</option>
                    {["WA", "CE", "TLE", "MLE", "RE"].map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </label>
                <button className="text-button" onClick={resetFilters}>
                  重置
                </button>
                <button
                  className="secondary"
                  onClick={() => {
                    setViewName("");
                    setDialog("saveView");
                  }}
                >
                  <BookmarkPlus size={14} />
                  保存筛选
                </button>
              </div>
            )}
            {(currentFilters.category ||
              currentFilters.contest ||
              currentFilters.ids ||
              prefs.views?.length > 0) && (
              <div className="filter-chips">
                {currentFilters.ids && <button className="selected-chip" aria-label="清除更新内容筛选" onClick={() => setFilter({ ids: null, updateTitle: "" })}><Bell size={12} />{currentFilters.updateTitle || "新增内容"} · {currentFilters.ids.length}题<X size={12} /></button>}
                {currentFilters.category && (
                  <button
                    className="selected-chip"
                    aria-label="清除知识点筛选"
                    onClick={() => setFilter({ category: null })}
                  >
                    <Network size={12} />
                    {currentFilters.category.name}
                    <X size={12} />
                  </button>
                )}
                {currentFilters.contest && (
                  <button
                    className="selected-chip"
                    onClick={() => setFilter({ contest: "" })}
                  >
                    {currentFilters.contest}
                    <X size={12} />
                  </button>
                )}
                {prefs.views?.map((view) => (
                  <button
                    key={view.id}
                    className="saved-chip"
                    onClick={() =>
                      setFilter({ ...blankFilters(), ...view.filters })
                    }
                  >
                    {view.name}
                  </button>
                ))}
              </div>
            )}
            {page === "mine" && (
              <div className="filter-tabs">
                <button
                  className={!currentFilters.result ? "active" : ""}
                  onClick={() => setFilter({ result: "" })}
                >
                  全部 <small>{totalCount}</small>
                </button>
                <button
                  className={
                    currentFilters.result === "pending" ? "active" : ""
                  }
                  onClick={() => setFilter({ result: "pending" })}
                >
                  尚未 AC <small>{totalCount - passedCount}</small>
                </button>
                <button
                  className={
                    currentFilters.result === "accepted" ? "active" : ""
                  }
                  onClick={() => setFilter({ result: "accepted" })}
                >
                  本地 AC <small>{passedCount}</small>
                </button>
                <button
                  className={currentFilters.result === "sample" ? "active" : ""}
                  onClick={() => setFilter({ result: "sample" })}
                >
                  样例通过
                </button>
              </div>
            )}
          </>
        )}
      </>
    );
  }
  function renderListPage() {
    if (page === "mine" && !mine.length)
      return (
        <Empty
          icon={Target}
          title="从第一道题开始"
          description="选择一题、一场比赛，或组成自己的模拟赛。你的进度从这里积累。"
        >
          <button className="primary" onClick={() => go("library")}>
            <Library size={16} />
            去题库选题
          </button>
          <button className="secondary" onClick={() => go("mock")}>
            <Flag size={16} />
            创建模拟赛
          </button>
        </Empty>
      );
    if (page === "today" && !dueCount && !todayQuery)
      return (
        <Empty
          icon={Check}
          title="今天没有到期的待办"
          description={
            mine.length
              ? "提交未通过的题和到期复习会出现在这里。"
              : "开始练习后，这里会整理需要攻克和复习的题。"
          }
        >
          <button className="primary" onClick={() => go("library")}>
            选择一道题
          </button>
          {mine.length > 0 && (
            <button className="secondary" onClick={() => go("mine")}>
              回到我的训练
            </button>
          )}
        </Empty>
      );
    return (
      <div className="list-page">
        {page === "mine" && (
            <div className="set-strip">
              <select
                aria-label="训练分组"
                value={currentFilters.setId}
                onChange={(e) => setFilter({ setId: e.target.value })}
              >
                <option value="">全部训练题</option>
                <option value="@single">单题练习</option>
                {workspace.sets.map((set) => (
                  <option key={set.id} value={set.id}>
                    {set.name} · {set.accepted}/{set.total} AC
                  </option>
                ))}
                {workspace.contests.map((contest) => (
                  <option key={contest.id} value={contest.id}>
                    {contest.name} · {contest.accepted}/{contest.total} AC
                  </option>
                ))}
              </select>
              <span>同一道题在个人进度中只计一次</span>
            </div>
          )}
        {toolbar()}
        {renderTable(displayedRows, { today: page === "today" })}
        {page === "library" && (
          <nav className="library-pagination" aria-label="题库分页">
            <label>每页
              <select aria-label="题库每页题数" value={libraryPageSize} onChange={(event) => { setLibraryPageSize(Number(event.target.value)); setLibraryPage(1); }}>
                {[25, 50, 100].map(size => <option key={size} value={size}>{size} 题</option>)}
              </select>
            </label>
            <span role="status">{visible.length ? `${libraryStart + 1}–${Math.min(libraryStart + libraryPageSize, visible.length)}` : "0"} / {visible.length} 题</span>
            <div className="pagination-actions">
              <button aria-label="题库上一页" disabled={currentLibraryPage === 1} onClick={() => setLibraryPage(currentLibraryPage - 1)}><ChevronLeft size={15} />上一页</button>
              <span>第 {currentLibraryPage} / {libraryPages} 页</span>
              <button aria-label="题库下一页" disabled={currentLibraryPage === libraryPages} onClick={() => setLibraryPage(currentLibraryPage + 1)}>下一页<ChevronRight size={15} /></button>
            </div>
          </nav>
        )}
        <div className="list-footer">
          <span>
            {page === "library"
              ? "题库用于选题"
              : page === "today"
                ? "只显示真实待办"
                : "个人训练"}{" "}
            · {visible.length} 题
          </span>
          <span className="footer-hint">
            <kbd>↑ ↓</kbd>选题 <kbd>Enter</kbd>练习 <kbd>U</kbd>题解{" "}
            <kbd>S</kbd>收藏
          </span>
          <span className="autosave-dot">本地保存</span>
        </div>
      </div>
    );
  }
  function recordDetail() {
    return (
      <div className="record-detail">
        <div className="record-bar">
          <button className="secondary" onClick={() => setRecord(null)}>
            <ArrowLeft size={15} />
            所有记录
          </button>
          <h2>{record.name}</h2>
          <span>
            {record.accepted}/{record.total} 本地 AC
          </span>
          <button
            className={"secondary " + (recordOnlyPending ? "active" : "")}
            onClick={() => setRecordOnlyPending(!recordOnlyPending)}
          >
            只看未 AC
          </button>
        </div>
        <div className="record-meta">
          <span>{formatDate(record.startedAt)}</span>
          <span>限时 {record.duration} 分钟</span>
          <span>{record.status === "running" ? "进行中" : "已结束"}</span>
          {record.penalty > 0 && <span>罚时 {record.penalty} 分钟</span>}
        </div>
        <div className="record-slots scroll-panel">
          {record.slots
            .filter((slot) => !recordOnlyPending || !slot.accepted)
            .map((slot) => (
              <article className="record-slot" key={slot.id}>
                <span
                  className={"slot-letter " + (slot.accepted ? "solved" : "")}
                >
                  {slot.letter}
                </span>
                <div>
                  <strong>{slot.title}</strong>
                  {record.status !== "running" && <small>{slot.tags?.join(" / ")}</small>}
                </div>
                {record.status !== "running" && <Difficulty value={slot.difficulty} />}
                <Verdict value={slot.verdict} accepted={slot.accepted} />
                <span>{slot.attempts || 0} 次提交</span>
                <button
                  className="secondary"
                  onClick={() => openPractice(slot.id)}
                >
                  {slot.accepted ? "再练一次" : "继续攻克"}
                </button>
                <IconButton
                  label={"题解 " + slot.title}
                  icon={BookOpen}
                  onClick={() => openSolution(slot.id)}
                />
              </article>
            ))}
          {record.slots.filter((slot) => !recordOnlyPending || !slot.accepted)
            .length === 0 && (
            <Empty
              icon={Trophy}
              title="这套题已经全部通过"
              description="下一步可以选择更高一档的试卷。"
            />
          )}
        </div>
      </div>
    );
  }
  function settingsPage() {
    return (
      <div className="settings-page scroll-panel">
        <div className="settings-tabs" role="tablist" aria-label="设置分类">{[["appearance", "外观与导航"], ["accounts", "账号与身份"], ["translation", "翻译 API"], ["updates", "更新"], ["training", "训练与键盘"]].map(([value, label]) => <button key={value} role="tab" aria-selected={settingsTab === value} className={settingsTab === value ? "active" : ""} onClick={() => setSettingsTab(value)}>{label}</button>)}</div>
        <div className="settings-column">
        <section className="settings-appearance" hidden={settingsTab !== "appearance"}>
          <h2>让界面适合你</h2>
          <p>偏好自动保存，下一次打开继续使用。</p>
          <div className="settings-row">
            <div>
              <strong>主题</strong>
              <small>长时间阅读也保持清楚</small>
            </div>
            <div className="choice-group">
              <button
                className={prefs.theme === "dark" ? "active" : ""}
                onClick={() => setPrefs((p) => ({ ...p, theme: "dark" }))}
              >
                <Moon size={15} />
                石墨深色
              </button>
              <button
                className={prefs.theme === "light" ? "active" : ""}
                onClick={() => setPrefs((p) => ({ ...p, theme: "light" }))}
              >
                <Sun size={15} />
                云白浅色
              </button>
            </div>
          </div>
          <div className="settings-row">
            <div>
              <strong>强调色</strong>
              <small>用于当前焦点与主要操作</small>
            </div>
            <div className="accent-options">
              {[
                { id: "violet", name: "雾紫", color: "#9d8df1" },
                { id: "blue", name: "澄空蓝", color: "#6fa5e8" },
                { id: "teal", name: "松石绿", color: "#5bbda4" },
                { id: "amber", name: "暖琥珀", color: "#d7a45e" },
              ].map((a) => (
                <button
                  key={a.id}
                  aria-label={a.name}
                  className={prefs.accent === a.id ? "active" : ""}
                  style={{ "--swatch": a.color }}
                  onClick={() => setPrefs((p) => ({ ...p, accent: a.id }))}
                >
                  <span />
                  {a.name}
                  {prefs.accent === a.id && <Check size={13} />}
                </button>
              ))}
            </div>
          </div>
          <div className="settings-row font-setting">
            <div>
              <strong>界面字号</strong>
              <small>题目、列表和阅读区同步调整</small>
            </div>
            <div className="font-options">
              {[13, 15, 17, 18].map((size) => (
                <button
                  key={size}
                  className={prefs.fontSize === size ? "active" : ""}
                  aria-label={`字号 ${size}`}
                  onClick={() => setPrefs((p) => ({ ...p, fontSize: size }))}
                >
                  {size}px
                </button>
              ))}
            </div>
          </div>
          {[
            { id: "compact", title: "紧凑列表", desc: "在同一屏显示更多题目" },
            {
              id: "motion",
              title: "界面动效",
              desc: "遵循系统减少动态效果设置",
            },
            {
              id: "collapsed",
              title: "收起左侧栏",
              desc: "保留导航图标，Ctrl+B 随时切换",
            },
          ].map((item) => (
            <label className="settings-row" key={item.id}>
              <div>
                <strong>{item.title}</strong>
                <small>{item.desc}</small>
              </div>
              <input
                className="toggle"
                aria-label={item.title}
                type="checkbox"
                checked={prefs[item.id]}
                onChange={(e) =>
                  setPrefs((p) => ({ ...p, [item.id]: e.target.checked }))
                }
              />
            </label>
          ))}
        </section>
        {settingsTab === "appearance" && <NavigationSettings pages={PAGES} prefs={prefs} setPrefs={setPrefs} onOpen={go} />}
        <section hidden={settingsTab !== "training"}>
          <h2>训练与评测</h2>
          <div className="settings-information">
            <p>
              个人进度只统计主动加入或提交的题，同题只计一次。取消训练保留代码和历史，重新加入可恢复。
            </p>
            <p>
              <strong>本地 AC</strong>：通过已审核的本地测试。
              <strong>样例通过</strong>
              ：通过题面样例，单独统计。比赛结束后可以查阅题解、重练未完成的题。
            </p>
            <p>
              看过题解后完成的题会进入“独立重写”；独立通过后按 7 天 / 30
              天安排复习。提交结果会保留，练习失败不会抹去以前的 AC。
            </p>
          </div>
        </section>
        <section hidden={settingsTab !== "training"}>
          <h2>键盘与常用筛选</h2>
          <div className="settings-row">
            <div>
              <strong>完整键盘操作</strong>
              <small>导航、知识点树、选题、编辑与提交</small>
            </div>
            <button className="secondary" onClick={() => setDialog("help")}>
              <Keyboard size={16} />
              查看键位
            </button>
          </div>
          {prefs.views?.map((view) => (
            <div className="settings-row" key={view.id}>
              <strong>{view.name}</strong>
              <IconButton
                label={"删除筛选 " + view.name}
                icon={X}
                onClick={() =>
                  setPrefs((p) => ({
                    ...p,
                    views: p.views.filter((v) => v.id !== view.id),
                  }))
                }
              />
            </div>
          ))}
        </section>
        </div>
        <div className="settings-column">
        {settingsTab === "accounts" && <ProfileSettings api={api} onError={(message) => notice(message, "error")} />}
        <section className="settings-connections" hidden={settingsTab !== "accounts"}>
          <h2>平台账号</h2>
          <ConnectionsPanel
            includeTranslation={false}
            hub={hub}
            api={api}
            onChanged={setHub}
            onError={(message) => notice(message, "error")}
          />
        </section>
        {settingsTab === "translation" && <section className="settings-translation"><TranslationSettings api={api} onError={(message) => notice(message, "error")} /></section>}
        <section className="settings-updates" hidden={settingsTab !== "updates"}>
          <h2>更新与自动收录</h2>
          <UpdatePanel
            showNotifications={false}
            onContent={openUpdate}
            hub={hub}
            api={api}
            onChanged={setHub}
            onError={(message) => notice(message, "error")}
          />
          <button className="text-button" onClick={() => setDialog("updates")}><Bell size={14} />在铃铛查看更新通知</button>
        </section>
        </div>
      </div>
    );
  }

  const navigationPages = orderedPages(PAGES, prefs);
  const navigationEntries = navigationPages.reduce((entries, item) => {
    if (!item.group) entries.push(item);
    else if (!entries.some(entry => entry.group === item.group)) { const members = navigationPages.filter(member => member.group === item.group); entries.push({ ...item, id: "group:" + item.group, label: item.group, icon: Layers, key: "", members }); }
    return entries;
  }, []);
  const mergedPages = navigationPages.filter(item => item.group && item.group === navigationPages.find(entry => entry.id === page)?.group);
  const achievements = insights?.achievements || [], unlockedAchievements = achievements.filter(item => item.unlocked);
  const unseenAchievements = unlockedAchievements.filter(item => !(prefs.seenAchievements || []).includes(item.id));
  function openAchievements() { setPrefs(previous => ({ ...previous, seenAchievements: unlockedAchievements.map(item => item.id) })); setDialog("achievements"); }
  const currentPage = navigationPages.find((p) => p.id === page),
    currentMockSlot =
      active?.slots.find((slot) => slot.id === mockSlot) || active?.slots[0];
  const readerPanel = readerId && (
    <aside
      className={"reader-panel " + (readerFull ? "reader-full" : "")}
      style={!readerFull ? { width: prefs.readerWidth } : undefined}
      aria-label="题解阅读"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.preventDefault();
          e.stopPropagation();
          readerSeq.current++;
          setReaderId(null);
          setReaderFull(false);
          focusList();
        }
      }}
    >
      <div
        className="reader-resizer"
        role="separator"
        aria-label="调整题解宽度"
        aria-orientation="vertical"
        tabIndex={0}
        onPointerDown={resizeReader}
        onKeyDown={(e) => {
          if (["ArrowLeft", "ArrowRight"].includes(e.key)) {
            e.preventDefault();
            setPrefs((p) => ({
              ...p,
              readerWidth: Math.max(
                340,
                Math.min(
                  900,
                  p.readerWidth + (e.key === "ArrowLeft" ? 30 : -30),
                ),
              ),
            }));
          }
        }}
      />
      <header>
        <BookOpen size={17} />
        <strong>
          {reader?.title ||
            rows.find((r) => r.id === readerId)?.title ||
            "题解"}
        </strong>
        <IconButton
          label={readerFull ? "退出题解全屏" : "题解全屏"}
          icon={readerFull ? Minimize2 : Maximize2}
          onClick={() => setReaderFull(!readerFull)}
        />
        <IconButton
          label="收起题解"
          icon={X}
          onClick={() => {
            readerSeq.current++;
            setReaderId(null);
            setReaderFull(false);
            focusList();
          }}
        />
      </header>
      <div className="reader-content">
        {reader ? (
          <>
            {solutionBlocks(reader.markdown, reader.lectures || []).map((block, index) => block.type === "lecture" ? <LectureDisclosure key={index} lecture={block.lecture || {title: block.heading}} inlineMarkdown={block.markdown} api={api} onTrain={openPractice} onError={(message) => notice(message, "error")} /> : <Markdown key={index} text={block.markdown} images={reader.images} onCopy={copy} />)}
            {!!reader.lectures?.length && <div className="reader-lecture-references"><h3>本题的基础讲解与引用</h3>{reader.lectures.filter(item => !solutionBlocks(reader.markdown, reader.lectures).some(block => block.lecture?.id === item.id)).map(item => <LectureDisclosure key={item.id} lecture={item} api={api} onTrain={openPractice} onError={(message) => notice(message, "error")} />)}<button className="text-button" onClick={() => go("lectures")}>查看全部知识讲解 <ArrowUpRight size={13} /></button></div>}
          </>
        ) : readerError ? (
          <Empty title="暂时无法读取题解" description={readerError} />
        ) : (
          <div className="loading-small">
            <LoaderCircle size={22} className="spin" />
            正在读取题解
          </div>
        )}
      </div>
      {reader?.url && (
        <footer>
          <a href={reader.url} target="_blank" rel="noreferrer">
            原题链接 <ArrowUpRight size={12} />
          </a>
          <span>题解仅在比赛结束后可用</span>
        </footer>
      )}
    </aside>
  );
  return (
    <div
      className={"app-shell " + (prefs.collapsed ? "sidebar-collapsed" : "")}
    >
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            tb
            <span />
          </div>
          {!prefs.collapsed && (
            <div>
              <strong>TB</strong>
              <small>训练工作台</small>
            </div>
          )}
          <IconButton
            label={prefs.collapsed ? "展开侧栏" : "收起侧栏"}
            icon={prefs.collapsed ? PanelLeftOpen : PanelLeftClose}
            onClick={() => setPrefs((p) => ({ ...p, collapsed: !p.collapsed }))}
          />
        </div>
        <nav aria-label="主导航">
          {navigationEntries.map((p) => (
            <button
              key={p.id}
              className={"nav-item " + (page === p.id || p.members?.some(member => member.id === page) ? "active" : "")}
              aria-current={page === p.id || p.members?.some(member => member.id === page) ? "page" : undefined}
              aria-label={p.label}
              title={prefs.collapsed ? p.label + (p.key ? " · Ctrl+" + p.key : "") : undefined}
              onClick={() => go(p.members ? p.members.find(member => member.id === page)?.id || p.members[0].id : p.id)}
            >
              <p.icon size={18} />
              {!prefs.collapsed && (
                <>
                  <span>{p.label}</span>
                  {p.id === "mock" && active && <span className="live-dot" />}
                </>
              )}
            </button>
          ))}
          {!prefs.collapsed && (prefs.pageBookmarks || []).filter(item => PAGES.some(page => page.id === item.page)).slice(0, 6).map(item => <button className="nav-item nav-bookmark" key={item.id} onClick={() => go(item.page)} aria-label={`书签 ${item.name}`}><BookmarkPlus size={16} /><span>{item.name}</span></button>)}
        </nav>
        {!prefs.collapsed && (
          <div className="sidebar-knowledge">
            <div className="sidebar-section-title">
              <span>知识清单</span>
              <button
                aria-label="聚焦知识清单"
                onClick={() =>
                  document
                    .querySelector(
                      '.sidebar-tree-scroll [role="treeitem"][tabindex="0"]',
                    )
                    ?.focus()
                }
              >
                <ArrowUpRight size={13} />
              </button>
            </div>
            <div className="sidebar-tree-scroll">
              <KnowledgeTree
                nodes={categories}
                rows={rows}
                training={mine}
                onFilter={(node) => filterCategory(node, "library")}
                selected={currentFilters.category?.name}
              />
            </div>
          </div>
        )}
        <div className="sidebar-bottom">
          <button
            className="nav-item"
            aria-label="命令面板"
            title="命令面板 · Ctrl+K"
            onClick={() => {
              setCommandQuery("");
              setDialog("commands");
            }}
          >
            <Command size={18} />
            {!prefs.collapsed && (
              <>
                <span>快捷操作</span>
                <kbd>Ctrl K</kbd>
              </>
            )}
          </button>
          <button
            className={"nav-item " + (page === "settings" ? "active" : "")}
            aria-label="偏好设置"
            title="偏好设置 · Ctrl+,"
            onClick={() => go("settings")}
          >
            <Settings2 size={18} />
            {!prefs.collapsed && (
              <>
                <span>偏好设置</span>
                <span className="local-indicator">本地</span>
              </>
            )}
          </button>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="page-identity">
            <span className="breadcrumb">
              工作台 <ChevronRight size={13} />
            </span>
            <h1>
              {practiceId
                ? rows.find((r) => r.id === practiceId)?.title
                : currentPage?.label || "偏好设置"}
            </h1>
            {practiceId && <span className="practice-label">单题练习</span>}
          </div>
          <div className="topbar-actions">
            {active && page !== "mock" && (
              <button className="live-contest" onClick={() => go("mock")}>
                <Clock size={14} />
                {timerText(remainingSeconds(active, now))}
              </button>
            )}
            <details className="topbar-overview"><summary aria-label="训练概览"><Award size={16} /><strong>Lv.{insights?.growth?.level || 1}</strong><span>{passedCount}/{totalCount} AC</span><ChevronDown size={13} /></summary><div className="overview-popover"><div className="overview-level"><strong>{insights?.growth?.levelName || "开始积累"}</strong><span>{num(insights?.growth?.totalXp || 0)} XP</span></div><div className="overview-statistics"><button onClick={() => go("mine")}><b>{passedCount}/{totalCount}</b><span>训练通过</span></button><button onClick={() => go("activity")}><b>{insights?.summary?.streak || summary.streak || 0} 天</b><span>连续训练</span></button><button onClick={() => { go("mock"); setMockTab("history"); }}><b>{workspace.contests.filter(contest => contest.status === "finished").length} 场</b><span>完成模拟赛</span></button><button onClick={() => go("growth")}><b>{num(insights?.growth?.totalXp || 0)} XP</b><span>成长与每日任务</span></button></div><button className="text-button" onClick={() => { document.querySelector(".topbar-overview")?.removeAttribute("open"); setDialog("summary"); }}>查看训练概览<ChevronRight size={13} /></button></div></details>
            <button className="achievement-top-button" aria-label="成就" onClick={openAchievements}><Medal size={17} /><span>成就</span><small>{unlockedAchievements.length}/{achievements.length}</small>{unseenAchievements.length > 0 && <i className="notification-dot" />}</button>
            {["mine", "library", "today"].includes(page) && !practiceId && (
              <button className="primary new-mock" onClick={() => go("mock")}>
                <Plus size={15} />
                模拟赛
              </button>
            )}
            <IconButton
              label="更新通知"
              icon={Bell}
              onClick={() => setDialog("updates")}
            >
              {(hub?.notifications || []).some((n) => !n.read) && (
                <span className="notification-dot" />
              )}
            </IconButton>
            <IconButton
              label="收件箱"
              icon={Inbox}
              onClick={() => setDialog("inbox")}
            >
              {inbox?.pending > 0 && <span className="notification-dot" />}
            </IconButton>
            <IconButton
              label="切换主题"
              icon={prefs.theme === "dark" ? Sun : Moon}
              onClick={() =>
                setPrefs((p) => ({
                  ...p,
                  theme: p.theme === "dark" ? "light" : "dark",
                }))
              }
            />
            <IconButton
              label="键盘帮助"
              icon={Keyboard}
              onClick={() => setDialog("help")}
            />
          </div>
        </header>
        {error && (
          <div className="error-banner" role="alert">
            {error}
            <button onClick={() => reload(true)}>重新读取</button>
          </div>
        )}
        {!practiceId && mergedPages.length > 1 && <div className="merged-page-tabs" role="tablist" aria-label={`组合页面 ${currentPage?.group}`}>{mergedPages.map(item => <button key={item.id} role="tab" aria-selected={page === item.id} className={page === item.id ? "active" : ""} onClick={() => go(item.id)}><item.icon size={15} />{item.label}</button>)}</div>}
        <div className={"workspace-area " + (practiceId ? "practicing" : "")}>
          {loading ? (
            <div className="loading-screen">
              <LoaderCircle size={27} className="spin" />
              <p>正在打开训练工作台</p>
            </div>
          ) : practiceId ? (
            <Workbench
              key={"practice:" + practiceId}
              problemId={practiceId}
              contest={null}
              api={api}
              onProgress={progressChanged}
              onExit={exitPractice}
              onSolution={openSolution}
              onNext={nextPractice}
            />
          ) : ["mine", "library", "today"].includes(page) ? (
            renderListPage()
          ) : page === "mock" ? (
            <div className="mock-page"><div className="mock-page-tabs filter-tabs" role="tablist" aria-label="模拟赛页面"><button role="tab" aria-selected={mockTab === "create" && !record} className={mockTab === "create" && !record ? "active" : ""} onClick={() => { setMockTab("create"); setRecord(null); }}>{active ? "进行中的比赛" : "创建训练"}</button><button role="tab" aria-selected={mockTab === "history" || !!record} className={mockTab === "history" || record ? "active" : ""} onClick={() => { setMockTab("history"); setRecord(null); }}>模拟赛记录 <small>{workspace.contests.length}</small></button></div>{record ? recordDetail() : mockTab === "history" ? <MockHistory contests={workspace.contests} onSelect={openRecord} onResume={(contest) => { setMockTab("create"); setMockSlot(contest.slots[0]?.id); }} onCreate={() => setMockTab("create")} /> : active ? (
              <div className="contest-player">
                <div className="contest-control">
                  <div>
                    <Flag size={16} />
                    <strong>{active.name}</strong>
                    <span>
                      {active.accepted}/{active.total} 本地 AC
                    </span>
                  </div>
                  <span
                    className={
                      "contest-clock " +
                      (remainingSeconds(active, now) < 600 ? "urgent" : "")
                    }
                  >
                    <Clock size={15} />
                    {timerText(remainingSeconds(active, now))}
                  </span>
                  <button
                    className="secondary finish-contest"
                    onClick={() => setDialog("finish")}
                  >
                    结束比赛
                  </button>
                </div>
                <div
                  className="contest-tabs"
                  role="tablist"
                  aria-label="模拟赛题目"
                >
                  {active.slots.map((slot, i) => (
                    <button
                      role="tab"
                      aria-selected={currentMockSlot?.id === slot.id}
                      className={
                        "contest-tab " +
                        (currentMockSlot?.id === slot.id ? "active " : "") +
                        (slot.accepted
                          ? "solved"
                          : slot.verdict
                            ? "attempted"
                            : "")
                      }
                      key={slot.id}
                      onClick={() => setMockSlot(slot.id)}
                      title={
                        slot.letter +
                        " · " +
                        slot.title +
                        " · " +
                        verdictLabel(slot.verdict)
                      }
                    >
                      <strong>{slot.letter}</strong>
                      <span>{slot.title}</span>
                      {slot.accepted ? (
                        <Check size={14} />
                      ) : slot.verdict ? (
                        <span className="attempt-dot" />
                      ) : (
                        <kbd>{i + 1}</kbd>
                      )}
                    </button>
                  ))}
                </div>
                {currentMockSlot && (
                  <Workbench
                    key={active.id + ":" + currentMockSlot.id}
                    problemId={currentMockSlot.id}
                    contest={active}
                    api={api}
                    onProgress={applyWorkspace}
                    onExit={() => go("mine")}
                    onSolution={null}
                    onNext={() => {
                      const index = active.slots.findIndex(
                        (s) => s.id === currentMockSlot.id,
                      );
                      setMockSlot(
                        active.slots[(index + 1) % active.slots.length].id,
                      );
                    }}
                  />
                )}
              </div>
            ) : (
              <MockSetup
                api={api}
                activeContest={active}
                onResume={() => go("mock")}
                categories={categories}
                platforms={[...new Set(rows.map(row => row.platform).filter(Boolean))]}
                onStarted={startedMock}
                onError={notice}
              />
            )}</div>
          ) : page === "records" ? (
            <SubmissionRecords submissions={submissionLog} total={submissionPage.total} hasMore={submissionPage.hasMore} loading={submissionLoading} onLoadMore={loadMoreSubmissions} rows={rows} onSelect={(submission) => { setSelectedSubmission(submission); setDialog("submission"); }} />
          ) : page === "competitions" ? (
            <CompetitionPage
              rows={rows}
              workspace={workspace}
              hub={hub}
              onTrain={openPractice}
              onJoin={startOriginalContest}
            />
          ) : page === "growth" ? (
            <GrowthPage
              insights={insights}
              hub={hub}
              onTrain={openPractice}
              onTopic={(node) => filterCategory(node, "library")}
              onSync={() =>
                api("hub/sync", {})
                  .then(setHub)
                  .catch((e) => notice(e.message, "error"))
              }
              onAccounts={() => { setSettingsTab("accounts"); go("settings"); }}
              onAchievements={openAchievements}
              onClaimTask={async (id, date) => { try { await api("daily-tasks/claim", { id, date }); setInsights(await api("insights")); notice("每日任务经验已领取", "success"); } catch (issue) { notice(issue.message, "error"); throw issue; } }}
            />
          ) : page === "activity" ? (
            <ActivityPage insights={insights} onTrain={openPractice} />
          ) : page === "lectures" ? (
            <LecturesPanel api={api} initialLecture={lectureId} onTrain={openPractice} onError={(message) => notice(message, "error")} />
          ) : page === "rankings" ? (
            <RankingsPage api={api} onConfigure={() => { setSettingsTab("accounts"); go("settings"); }} onError={(message) => notice(message, "error")} />
          ) : (
            settingsPage()
          )}
          {readerPanel}
        </div>
      </main>
      {toast && (
        <div className={"toast " + toast.type} role="status">
          {toast.type === "success" ? (
            <Trophy size={17} />
          ) : toast.type === "error" ? (
            <X size={16} />
          ) : (
            <Check size={16} />
          )}
          <span>{toast.message}</span>
          {toast.action && (
            <button onClick={toast.action.run}>{toast.action.label}</button>
          )}
        </div>
      )}
      {dialog === "achievements" && <Modal title={`成就 · ${unlockedAchievements.length}/${achievements.length}`} onClose={() => setDialog(null)} wide><AchievementPanel achievements={achievements} /></Modal>}
      {dialog === "submission" && selectedSubmission && <Modal title={selectedSubmission.title + " · 历史提交"} onClose={() => setDialog(null)} wide footer={<button className="primary" onClick={() => { setDialog(null); openPractice(selectedSubmission.problemId); }}><Play size={14} />继续练习</button>}><div className="submission-detail-meta"><Verdict value={selectedSubmission.verdict} /><span>{formatDate(selectedSubmission.submittedAt)}</span><span>{selectedSubmission.contestName}</span><button className="secondary" disabled={!selectedSubmission.code} onClick={() => copy(selectedSubmission.code)}><Copy size={14} />复制本次代码</button></div><pre className="submission-source"><code>{selectedSubmission.code || "这条记录没有保存代码。"}</code></pre>{selectedSubmission.message && <p className="submission-message">{selectedSubmission.message}</p>}</Modal>}
      {dialog === "updates" && (
        <Modal title="更新与新内容" onClose={() => setDialog(null)} wide>
          <UpdatePanel
            onContent={openUpdate}
            hub={hub}
            api={api}
            onChanged={setHub}
            onError={(message) => notice(message, "error")}
          />
        </Modal>
      )}
      {dialog === "summary" && (
        <Modal title="你的训练概览" onClose={() => setDialog(null)}>
          <div className="summary-score">
            <Trophy size={27} />
            <strong>
              {passedCount}
              <small> / {totalCount}</small>
            </strong>
            <span>题已通过本地评测</span>
          </div>
          <div className="summary-grid">
            <div>
              <strong>{num(summary.attempts)}</strong>
              <span>代码提交</span>
            </div>
            <div>
              <strong>{num(summary.samplePassed)}</strong>
              <span>仅样例通过</span>
            </div>
            <div>
              <strong>{dueCount}</strong>
              <span>今日待办</span>
            </div>
            <div>
              <strong>
                {
                  workspace.contests.filter((c) => c.status === "finished")
                    .length
                }
              </strong>
              <span>完成模拟赛</span>
            </div>
          </div>
          <p className="summary-description">
            题库 {rows.length}{" "}
            题可供选择。个人分母只包含主动加入的单题、比赛和模拟赛，同题只计一次。
          </p>
          <div className="milestones">
            {[
              { goal: 1, name: "第一次通过" },
              { goal: 10, name: "积累十题" },
              { goal: 50, name: "五十题里程碑" },
            ].map((m) => (
              <div
                key={m.goal}
                className={passedCount >= m.goal ? "earned" : ""}
              >
                <Trophy size={16} />
                <span>{m.name}</span>
                <small>
                  {passedCount >= m.goal ? "已达成" : m.goal + " AC"}
                </small>
              </div>
            ))}
          </div>
        </Modal>
      )}
      {dialog === "help" && (
        <Modal title="键盘操作" onClose={() => setDialog(null)} wide>
          <div className="shortcut-grid">
            <section>
              <h3>工作台</h3>
              {[
                [
                  "Ctrl+1 … 9",
                  "训练 / 题库 / 待办 / 比赛 / 模拟赛 / 记录 / 成长 / 活动 / 从零讲",
                ],
                ["Ctrl+B", "收起或展开左侧栏"],
                ["Ctrl+K", "命令面板"],
                ["F6 / Shift+F6", "切换导航、知识清单、主区与代码焦点"],
                ["Ctrl+0 / Ctrl+,", "偏好设置"],
                ["F 或 Ctrl+F", "搜索当前列表"],
                ["Esc", "关闭题解、清空搜索或返回"],
                ["?", "打开这张键位表"],
              ].map(([key, action]) => (
                <div key={key}>
                  <kbd>{key}</kbd>
                  <span>{action}</span>
                </div>
              ))}
            </section>
            <section>
              <h3>选题与知识树</h3>
              {[
                ["↑ ↓ / J K", "选择上一题 / 下一题"],
                ["Home / End", "跳到首题 / 末题"],
                ["PageUp / PageDown", "移动十题"],
                ["Enter", "开始练习所选题"],
                ["U / S", "查看题解 / 切换收藏"],
                ["Delete", "取消所选训练，保留历史记录"],
                ["树中 → / ←", "展开分支 / 收起或返回上层"],
                ["Tab / Shift+Tab", "切换按钮与输入框"],
              ].map(([key, action]) => (
                <div key={key}>
                  <kbd>{key}</kbd>
                  <span>{action}</span>
                </div>
              ))}
            </section>
            <section>
              <h3>代码与模拟赛</h3>
              {[
                ["Ctrl+Enter", "本地评测"],
                ["Ctrl+Shift+Enter", "在主窗口提交到官方"],
                ["Ctrl+R", "运行样例 / 自定义输入"],
                ["Ctrl+S", "保存当前代码"],
                ["Tab / Shift+Tab", "缩进 / 取消缩进"],
                ["Alt+1 / Alt+2", "聚焦题面 / 代码"],
                ["1 … 9", "比赛中切题（编辑时不触发）"],
              ].map(([key, action]) => (
                <div key={key}>
                  <kbd>{key}</kbd>
                  <span>{action}</span>
                </div>
              ))}
            </section>
          </div>
          <p className="help-note">
            结果由提交代码自动生成。列表中的 1–6
            不再手动改状态，输入框与按钮保留自己的按键行为。
          </p>
        </Modal>
      )}
      {dialog === "commands" && (
        <Modal title="快捷操作" onClose={() => setDialog(null)}>
          <div className="command-search">
            <Search size={17} />
            <input
              autoFocus
              aria-label="搜索快捷操作"
              placeholder="输入要去的地方或操作…"
              value={commandQuery}
              onChange={(e) => setCommandQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  const command = commands.find((c) =>
                    c.name.includes(commandQuery),
                  );
                  if (command) {
                    setDialog(null);
                    requestAnimationFrame(() => command.action());
                  }
                }
              }}
            />
          </div>
          <div className="command-list">
            {commands
              .filter((c) => c.name.includes(commandQuery))
              .map((command) => (
                <button
                  key={command.name}
                  onClick={() => {
                    setDialog(null);
                    requestAnimationFrame(() => command.action());
                  }}
                >
                  <span>{command.name}</span>
                  {command.detail && <kbd>{command.detail}</kbd>}
                  <ChevronRight size={14} />
                </button>
              ))}
          </div>
        </Modal>
      )}
      {dialog === "saveView" && (
        <Modal
          title="保存常用筛选"
          onClose={() => setDialog(null)}
          footer={
            <button
              className="primary"
              disabled={!viewName.trim()}
              onClick={() => {
                setPrefs((p) => ({
                  ...p,
                  views: [
                    ...p.views,
                    {
                      id: String(Date.now()),
                      name: viewName.trim(),
                      filters: currentFilters,
                    },
                  ],
                }));
                setDialog(null);
                notice("已保存筛选");
              }}
            >
              保存筛选
            </button>
          }
        >
          <label className="modal-field">
            筛选名称
            <input
              aria-label="筛选名称"
              value={viewName}
              onChange={(e) => setViewName(e.target.value)}
              maxLength={40}
            />
          </label>
        </Modal>
      )}
      {dialog === "finish" && (
        <Modal
          title="结束这场模拟赛"
          onClose={() => !busy && setDialog(null)}
          footer={
            <>
              <button
                className="secondary"
                onClick={() => setDialog(null)}
                disabled={busy}
              >
                继续比赛
              </button>
              <button className="primary" onClick={finishMock} disabled={busy}>
                {busy ? (
                  <LoaderCircle size={15} className="spin" />
                ) : (
                  <Check size={15} />
                )}
                结束并复盘
              </button>
            </>
          }
        >
          <p>
            已通过 {active?.accepted} / {active?.total}{" "}
            题。结束后可查看题解，未完成的题会进入今日待办。
          </p>
        </Modal>
      )}
      {dialog === "inbox" && (
        <Modal title="题解收件箱" onClose={() => !busy && setDialog(null)}>
          <p className="inbox-description">
            把题解 Markdown 放入收件箱后导入。新增内容只进入题库。
          </p>
          <div className="inbox-path">
            {inbox?.path || "D:\\Data\\Code\\题解\\_收件箱"}
          </div>
          <div className="inbox-count">待处理 {inbox?.pending || 0} 项</div>
          {inbox?.errors?.map((message, index) => (
            <p className="inline-error" key={index}>
              {typeof message === "string" ? message : JSON.stringify(message)}
            </p>
          ))}
          {inbox?.needsChoice ? (
            <>
              <p className="inline-error">存在冲突，请选择如何导入。</p>
              <div className="inbox-buttons">
                {[
                  { action: "skip", label: "跳过冲突项" },
                  { action: "overwrite", label: "覆盖冲突项" },
                ].map((item) => (
                  <button
                    className="secondary"
                    key={item.action}
                    disabled={busy}
                    onClick={() => importInbox(item.action)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <button
              className="primary"
              disabled={busy || !inbox?.pending}
              onClick={() => importInbox("import")}
            >
              {busy ? (
                <LoaderCircle size={16} className="spin" />
              ) : (
                <Inbox size={16} />
              )}
              导入新题解
            </button>
          )}
        </Modal>
      )}
    </div>
  );
  async function importInbox(action) {
    setBusy(true);
    try {
      const result = await api("inbox", { action });
      if (result.needsChoice) setInbox(result);
      else {
        setDialog(null);
        await reload();
        notice("收件箱已处理");
      }
    } catch (e) {
      notice(e.message, "error");
    } finally {
      setBusy(false);
    }
  }
}
function FragmentRows({ header, children }) {
  return (
    <>
      {header}
      {children}
    </>
  );
}
