import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import { basicSetup } from 'codemirror';
import { EditorView, keymap } from '@codemirror/view';
import { Annotation, Compartment, EditorState, Prec } from '@codemirror/state';
import { indentLess, indentMore } from '@codemirror/commands';
import { cpp } from '@codemirror/lang-cpp';
import { HighlightStyle, indentUnit, syntaxHighlighting } from '@codemirror/language';
import { acceptCompletion, autocompletion, completionStatus, snippetCompletion } from '@codemirror/autocomplete';
import { tags } from '@lezer/highlight';
import './CodeEditor.css';

const externalChange = Annotation.define();
const keywordOptions = 'alignas alignof auto bool break case catch char class const constexpr continue decltype default delete do double else enum explicit extern false float for friend if inline int long namespace new noexcept nullptr operator private protected public return short signed sizeof static struct switch template this throw true try typedef typename union unsigned using virtual void volatile while'.split(' ').map(label => ({ label, type: 'keyword' }));
const completions = [
  ...keywordOptions,
  ...'cin cout cerr endl string vector pair map set unordered_map unordered_set queue priority_queue deque stack sort lower_bound upper_bound min max swap reverse next_permutation accumulate iota gcd make_pair push_back emplace_back size begin end'.split(' ').map(label => ({ label, type: 'variable', detail: 'C++ 常用名称' })),
  snippetCompletion('for (int ${i} = 0; ${i} < ${n}; ++${i}) {\n    ${}\n}', { label: 'fori', type: 'snippet', detail: '计数循环' }),
  snippetCompletion('for (auto &${item} : ${container}) {\n    ${}\n}', { label: 'forr', type: 'snippet', detail: '范围循环' }),
  snippetCompletion('if (${condition}) {\n    ${}\n}', { label: 'ifblock', type: 'snippet', detail: '条件分支' }),
  snippetCompletion('while (${condition}) {\n    ${}\n}', { label: 'whileblock', type: 'snippet', detail: '循环' }),
  snippetCompletion('int main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n\n    ${}\n    return 0;\n}', { label: 'main', type: 'snippet', detail: 'C++17 入口模板' }),
];
function completeCpp(context) {
  const word = context.matchBefore(/[A-Za-z_][A-Za-z_0-9]*/);
  if (!word && !context.explicit) return null;
  return { from: word ? word.from : context.pos, options: completions, validFor: /^[A-Za-z_0-9]*$/ };
}
const colors = HighlightStyle.define([
  { tag: tags.keyword, color: 'var(--code-keyword)' },
  { tag: [tags.typeName, tags.className], color: 'var(--code-type)' },
  { tag: [tags.string, tags.character], color: 'var(--code-string)' },
  { tag: [tags.number, tags.bool, tags.null], color: 'var(--code-number)' },
  { tag: tags.comment, color: 'var(--code-comment)', fontStyle: 'italic' },
  { tag: [tags.function(tags.variableName), tags.definition(tags.variableName)], color: 'var(--code-function)' },
  { tag: [tags.meta, tags.processingInstruction], color: 'var(--code-meta)' },
  { tag: [tags.operator, tags.punctuation], color: 'var(--code-operator)' },
]);
const theme = EditorView.theme({
  '&': { height: '100%', color: 'var(--text)', backgroundColor: 'var(--panel)' },
  '.cm-scroller': { overflow: 'auto', fontFamily: 'Consolas, "Cascadia Code", monospace', fontSize: '1rem', lineHeight: '1.7' },
  '.cm-content': { padding: '12px 0', caretColor: 'var(--accent)' },
  '.cm-line': { padding: '0 13px' },
  '.cm-gutters': { backgroundColor: 'var(--panel-2)', color: 'var(--muted)', borderRight: '1px solid var(--line)' },
  '.cm-activeLineGutter': { backgroundColor: 'var(--accent-soft)', color: 'var(--accent)' },
  '.cm-activeLine': { backgroundColor: 'var(--accent-soft)' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--accent)' },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection': { backgroundColor: 'color-mix(in srgb, var(--accent) 24%, transparent)' },
  '.cm-matchingBracket': { backgroundColor: 'var(--accent-soft)', outline: '1px solid var(--accent)' },
  '.cm-tooltip': { backgroundColor: 'var(--panel-2)', border: '1px solid var(--line)', color: 'var(--text)' },
  '.cm-tooltip-autocomplete > ul > li[aria-selected]': { backgroundColor: 'var(--accent-soft)', color: 'var(--text)' },
  '.cm-panels': { backgroundColor: 'var(--panel-2)', color: 'var(--text)' },
  '.cm-searchMatch': { backgroundColor: 'color-mix(in srgb, var(--warning) 25%, transparent)' },
  '.cm-searchMatch-selected': { backgroundColor: 'color-mix(in srgb, var(--warning) 45%, transparent)' },
});

const CodeEditor = forwardRef(function CodeEditor({ value = '', onChange, onCursorChange, onCommand, onLeave, readOnly = false, disabled = false, docKey = '', ariaLabel = 'C++ 代码' }, ref) {
  const host = useRef(null), viewRef = useRef(null), readonlyCompartment = useRef(new Compartment());
  const callbacks = useRef({ onChange, onCursorChange, onCommand, onLeave });
  callbacks.current = { onChange, onCursorChange, onCommand, onLeave };
  useImperativeHandle(ref, () => ({
    focus: () => viewRef.current?.focus(),
    get value() { return viewRef.current?.state.doc.toString() || ''; },
    getSelection: () => ({ start: viewRef.current?.state.selection.main.from || 0, end: viewRef.current?.state.selection.main.to || 0 }),
    get selectionStart() { return viewRef.current?.state.selection.main.from || 0; },
    get selectionEnd() { return viewRef.current?.state.selection.main.to || 0; },
    setSelectionRange: (start, end = start) => { const view = viewRef.current; if (view) view.dispatch({ selection: { anchor: Math.min(start, view.state.doc.length), head: Math.min(end, view.state.doc.length) }, scrollIntoView: true }); },
    get scrollTop() { return viewRef.current?.scrollDOM.scrollTop || 0; },
    set scrollTop(value) { if (viewRef.current) viewRef.current.scrollDOM.scrollTop = value; },
    getDOM: () => viewRef.current?.contentDOM,
    getView: () => viewRef.current,
  }), []);
  useEffect(() => {
    const notifyCursor = view => { const position = view.state.selection.main.head, line = view.state.doc.lineAt(position); callbacks.current.onCursorChange?.({ line: line.number, column: position - line.from + 1 }); };
    const view = new EditorView({ parent: host.current, state: EditorState.create({ doc: value, extensions: [
      Prec.highest(EditorView.domEventHandlers({ keydown(event, editor) {
        if (event.isComposing || editor.composing || event.keyCode === 229) return false;
        let command;
        if ((event.ctrlKey || event.metaKey) && !event.altKey) {
          if (event.key === 'Enter') command = event.shiftKey ? 'official' : 'submit';
          else if (!event.shiftKey && event.key.toLowerCase() === 'r') command = 'run';
          else if (!event.shiftKey && event.key.toLowerCase() === 's') command = 'save';
          else if (event.key === 'Tab') { event.preventDefault(); event.stopPropagation(); callbacks.current.onLeave?.(); return true; }
        } else if (event.altKey && !event.ctrlKey && !event.metaKey && ['0', '1', '2'].includes(event.key)) command = 'pane-' + event.key;
        if (!command) return false;
        event.preventDefault(); event.stopPropagation(); callbacks.current.onCommand?.(command); return true;
      } })),
      Prec.highest(keymap.of([{ key: 'Tab', run: editor => (completionStatus(editor.state) === 'active' && acceptCompletion(editor)) || indentMore(editor), shift: indentLess }])),
      basicSetup, cpp(), indentUnit.of('    '), theme, syntaxHighlighting(colors),
      autocompletion({ override: [completeCpp], activateOnTyping: true, maxRenderedOptions: 12 }),
      readonlyCompartment.current.of([EditorState.readOnly.of(readOnly || disabled), EditorView.editable.of(!disabled)]),
      EditorView.contentAttributes.of(editor => ({ 'aria-label': ariaLabel, 'aria-multiline': 'true', 'aria-readonly': editor.state.readOnly ? 'true' : 'false', role: 'textbox', spellcheck: 'false', autocapitalize: 'off' })),
      EditorView.updateListener.of(update => {
        if (update.docChanged && !update.transactions.some(transaction => transaction.annotation(externalChange))) callbacks.current.onChange?.(update.state.doc.toString());
        if (update.docChanged || update.selectionSet) notifyCursor(update.view);
      }),
    ] }) });
    viewRef.current = view;
    notifyCursor(view);
    return () => { viewRef.current = null; view.destroy(); };
    // Changing document identity creates a fresh undo history; mirrored value
    // updates below preserve the current caret and history during ordinary edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docKey]);
  useEffect(() => {
    const view = viewRef.current;
    if (view && view.state.doc.toString() !== value) view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value }, annotations: externalChange.of(true) });
  }, [value, docKey]);
  useEffect(() => { viewRef.current?.dispatch({ effects: readonlyCompartment.current.reconfigure([EditorState.readOnly.of(readOnly || disabled), EditorView.editable.of(!disabled)]) }); }, [readOnly, disabled, docKey]);
  return <div className="code-editor" ref={host} data-readonly={readOnly || disabled} onKeyDown={event => { if (event.defaultPrevented) event.stopPropagation(); }} />;
});
export default CodeEditor;
