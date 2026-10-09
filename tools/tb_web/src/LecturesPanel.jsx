import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { ArrowLeft, ArrowRight, BookOpen, LoaderCircle, Search } from 'lucide-react';
import { normalizeMarkdown } from './normalizeMarkdown.js';
import './LecturesPanel.css';

function LessonTitle({ children }) {
  return <span className="inline-lesson-markdown"><ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[[rehypeKatex, { strict: 'ignore', throwOnError: false }]]} components={{ p: ({ children }) => <span>{children}</span> }}>{normalizeMarkdown(children || '')}</ReactMarkdown></span>;
}

function LessonMarkdown({ lesson }) {
  return <div className="lecture-markdown"><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={{
    img: ({ src, alt, ...rest }) => <img {...rest} alt={alt || ''} src={lesson.images?.[src] || src} loading="lazy" />,
    a: ({ children, ...props }) => <a {...props} target="_blank" rel="noreferrer">{children}</a>,
  }}>{normalizeMarkdown(lesson.markdown || '')}</ReactMarkdown></div>;
}

export function LectureDisclosure({ lecture = {}, inlineMarkdown, api, onTrain, onError }) {
  const [open, setOpen] = useState(false), [content, setContent] = useState(null), [error, setError] = useState('');
  useEffect(() => {
    if (!open || content || !lecture.id) return;
    let cancelled = false;
    api('lecture?id=' + encodeURIComponent(lecture.id)).then(value => {
      if (!cancelled) { setContent(value); setError(''); }
    }).catch(issue => { if (!cancelled) { setError(issue.message); onError?.(issue.message); } });
    return () => { cancelled = true; };
  }, [open, lecture.id, api, !!content]);
  const display = content || (inlineMarkdown ? { ...lecture, markdown: inlineMarkdown } : null);
  return <details className="lecture-disclosure" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary><BookOpen size={15} /><span><LessonTitle>{lecture.displayTitle || lecture.concept || lecture.title || '从零讲'}</LessonTitle></span><small>展开讲解</small></summary>
    {open && <div className="lecture-disclosure-body">
      {display ? <LessonMarkdown lesson={display} /> : error ? <p role="alert">{error}</p> : <p role="status"><LoaderCircle size={15} className="spin" />正在读取完整讲解</p>}
      {lecture.sourceContest && <div className="lecture-source"><span>来源：{lecture.sourceContest} · {lecture.sourceProblem} {lecture.sourceTitle}</span>{onTrain && lecture.sourceProblemIds?.[0] && <button onClick={() => onTrain(lecture.sourceProblemIds[0])}>练习原题<ArrowRight size={13} /></button>}</div>}
    </div>}
  </details>;
}

export function LecturesPanel({ lectures, api, initialLecture, onTrain, onError }) {
  const [snapshot, setSnapshot] = useState(lectures || null), [query, setQuery] = useState(''), [selected, setSelected] = useState(initialLecture || null);
  const [classification, setClassification] = useState('');
  const [lesson, setLesson] = useState(null), [error, setError] = useState(''), [refresh, setRefresh] = useState(0);
  const seq = useRef(0);
  useEffect(() => { if (initialLecture) setSelected(initialLecture); }, [initialLecture]);
  useEffect(() => {
    if (lectures) { setSnapshot(lectures); return; }
    let cancelled = false;
    api('lectures').then(value => { if (!cancelled) { setSnapshot(value); setError(''); } }).catch(issue => { if (!cancelled) { setError(issue.message); onError?.(issue.message); } });
    return () => { cancelled = true; };
  }, [api, lectures, refresh]);
  useEffect(() => {
    if (!selected) { setLesson(null); return; }
    const current = ++seq.current; setLesson(null); setError('');
    api('lecture?id=' + encodeURIComponent(selected)).then(value => { if (seq.current === current) setLesson(value); }).catch(issue => { if (seq.current === current) setError(issue.message); });
    return () => { seq.current++; };
  }, [selected, api]);
  const entries = Array.isArray(snapshot) ? snapshot : snapshot?.lectures || [];
  const classifications = [...new Set(entries.map(item => item.category || item.categories?.[0]).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-CN'));
  const filtered = entries.filter(item => (!classification || item.category === classification || item.categories?.includes(classification)) && `${item.concept} ${item.displayTitle || ''} ${item.originalTitle || item.title} ${(item.tags || []).join(' ')} ${item.category || ''} ${item.sourceContest} ${item.sourceTitle}`.toLowerCase().includes(query.trim().toLowerCase()));
  return <div className="lectures-page" aria-label="从零讲知识总结">
    <header className="lectures-header"><div><h2><BookOpen size={20} />从零讲</h2><p>题解里的完整基础讲解集中在这里；遇到相同知识点时，可按需展开。</p></div><span>{entries.length} 个完整讲解</span></header>
    <div className="lectures-toolbar"><label><Search size={16} /><input aria-label="搜索从零讲知识" placeholder="搜索知识点、题目或比赛" value={query} onChange={event => setQuery(event.target.value)} /></label>{classifications.length > 0 && <select aria-label="从零讲知识分类" value={classification} onChange={event => setClassification(event.target.value)}><option value="">全部知识分类</option>{classifications.map(item => <option key={item}>{item}</option>)}</select>}<button onClick={() => setRefresh(value => value + 1)}>刷新讲解</button></div>
    <div className={'lectures-layout' + (selected ? ' has-selection' : '')}>
      <nav className="lectures-list" aria-label="完整知识讲解">{filtered.map(item => <button key={item.id} className={selected === item.id ? 'selected' : ''} onClick={() => setSelected(item.id)}><strong><LessonTitle>{item.displayTitle || item.concept || item.title}</LessonTitle></strong>{item.category && <span className="lecture-category">{item.category}</span>}<span>{(item.tags || []).join(' / ')}</span><small>{item.sourceContest} · {item.sourceProblem} {item.sourceTitle}</small></button>)}{snapshot && !filtered.length && <p>没有匹配的完整讲解。仅有指针的段落会链接已有讲解。</p>}</nav>
      <article className="lectures-detail" tabIndex={0} aria-label="知识讲解正文">
        {selected ? <><div className="lectures-detail-bar"><button onClick={() => setSelected(null)}><ArrowLeft size={14} />全部讲解</button>{lesson && onTrain && lesson.sourceProblemIds?.[0] && <button onClick={() => onTrain(lesson.sourceProblemIds[0])}>练习来源题<ArrowRight size={14} /></button>}</div>{lesson ? <><p className="lecture-source">{lesson.sourceContest} · {lesson.sourceProblem} {lesson.sourceTitle}</p>{lesson.originalTitle && lesson.originalTitle !== lesson.concept && <p className="lecture-original-title">原题应用：<LessonTitle>{lesson.originalTitle}</LessonTitle></p>}<LessonMarkdown lesson={lesson} /></> : error ? <p role="alert">{error}</p> : <p role="status">正在读取完整讲解…</p>}</> : <div className="lectures-intro"><BookOpen size={25} /><h3>选一个知识点开始阅读</h3><p>按标准知识点名称与分类查阅基础定义、例子、推导及代码。</p>{entries.length > 0 && <button onClick={() => setSelected(filtered[0]?.id || entries[0].id)}>阅读第一篇<ArrowRight size={14} /></button>}{error && <p role="alert">{error}</p>}</div>}
      </article>
    </div>
  </div>;
}
