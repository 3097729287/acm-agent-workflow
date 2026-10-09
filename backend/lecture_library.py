"""Canonical foundations, unabridged archive derivations, and source audit."""
import copy
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from urllib.parse import urlsplit
import knowledge_dict as KD
import toolutil
from training import ServiceError
from knowledge import normalize_tags, asset_path, VERSION as KNOWLEDGE_VERSION
import lecture_curation as C

_SUMMARY_EXCLUDE={'images','sourceMarkdown','markdown','sourceCodeHashes'}
def summary(entry):return {k:v for k,v in entry.items() if k not in _SUMMARY_EXCLUDE}


def portable_markdown(markdown):
    """Turn local archive references into portable citations outside fenced code."""
    lines=markdown.splitlines(keepends=True);mask=C.fenced_mask(lines);count=0;result=[]
    def relative(path):
        nonlocal count
        path=path.replace('\\','/')
        if '/题解/' in path:path='题解/'+path.split('/题解/',1)[1]
        elif '/算法/' in path:path='知识库/'+path.split('/算法/',1)[1]
        else:path=path.rsplit('/',1)[-1]
        count+=1
        return path
    def citation(match):
        # The rendered reader has exact lesson relations for these citations.
        # A developer's local .md URL cannot be opened on another installation.
        return match[1]+'（`'+relative(match[2] or match[3]).strip()+'`）'
    local_link=r'(?<!!)\[([^\]\r\n]+)\]\(\s*(?:<([A-Za-z]:[\\/][^>\r\n]+)>|([A-Za-z]:[\\/][^)\r\n]+))\s*\)'
    for line,inside in zip(lines,mask):
        if inside:
            result.append(line);continue
        parts=re.split(r'(`+[^`\r\n]*`+)',line)
        for index,part in enumerate(parts):
            if index%2:
                match=re.fullmatch(r'`([A-Za-z]:[\\/][^`\r\n]+)`',part)
                if match:parts[index]='`'+relative(match[1])+'`'
            else:parts[index]=re.sub(local_link,citation,part)
        result.append(''.join(parts))
    return ''.join(result),count


class LectureLibrary:
    def __init__(self,store,state_dir=None,registry_path=None):
        self.store=store;root=Path(store.data_root).resolve()
        self.root=root/'题解' if (root/'题解').is_dir() else root
        self.registry=Path(registry_path) if registry_path else Path(toolutil.REPO_ROOT)/'memory'/'11-已讲过概念清单.md'
        self.state_dir=Path(state_dir) if state_dir else None
        self.bundle_path=asset_path('curated_lectures.json')
        self.lock=threading.RLock();self.signature=None;self.entries={};self.references={};self.sections={};self.last_check=0
        self.revision='';self.audit={}

    @staticmethod
    def _pointer(body):
        if not body or len(body)<90:return True
        return len(body)<300 and bool(re.search(r'详见|参见|见《|已讲过|这里直接用|不再展开',body))

    def _refresh(self):
        with self.lock:
            if hasattr(self.store,'library'):
                revision=self.store.library.metadata().get('revision','0')
                if self.signature==revision:return
                self.entries=self.store.library.lecture_entries()
                self.references={row['场次']+'::'+row['题号']:[i for i,k in self.store.library.references(row['场次']+'::'+row['题号'])] for row in self.store.raw_rows()}
                self.signature=revision;self.revision=revision
                self.audit={'lectureCount':len(self.entries),'usingDatabase':True}
                return
            if self.signature is not None and time.monotonic()-self.last_check<1:return
            self.last_check=time.monotonic()
            all_markdown=sorted(p for p in self.root.rglob('*.md') if not any(part.startswith('_') for part in p.relative_to(self.root).parts))
            files=[p for p in all_markdown if p.name.endswith('题解.md')]
            supplements=[p for p in all_markdown if p not in files and p.name!='TB.md']
            status_files=[p for p in all_markdown if p.name=='TB.md']
            signature=tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in all_markdown)
            for path in (self.registry,self.bundle_path):
                if path.is_file():signature+=((str(path),path.stat().st_mtime_ns,path.stat().st_size),)
            signature+=(('curation',C.VERSION,KNOWLEDGE_VERSION),)
            if signature==self.signature:return
            entries={};problem_text={};documents=[];problem_audit=[];exceptions=[];path_entries={}
            # Fresh installs have a portable educational corpus. Existing source
            # archives are always indexed from their own current content.
            if not files and self.bundle_path.is_file():
                try:
                    saved=json.loads(self.bundle_path.read_text(encoding='utf-8'))
                    if saved.get('curationVersion')==C.VERSION:
                        entries={e['id']:e for e in saved.get('lectures',[]) if e.get('id') and e.get('markdown')}
                        self.audit=copy.deepcopy(saved.get('audit',{}));self.audit['usingBundledCorpus']=True
                except (OSError,ValueError) as error:exceptions.append({'type':'bundle','message':str(error)[:200]})
            for path in files:
                relative=str(path.relative_to(self.root)).replace('\\','/')
                try:
                    original=path.read_text(encoding='utf-8-sig');parsed=C.parse_document(original)
                except (OSError,UnicodeError,ValueError) as error:
                    exceptions.append({'sourcePath':relative,'type':'source-read','message':str(error)[:200]});continue
                catalog=parsed['catalog'];series=path.parent.parent.name
                contest=toolutil.format_contest(series,path.parent.name) if series in toolutil.SERIES else re.sub(r'^#\s*|\s*题解.*$','',parsed['lines'][0] if parsed['lines'] else '').strip()
                documents.append({'sourcePath':relative,'sourceHash':hashlib.sha256(path.read_bytes()).hexdigest(),
                                  'problemCount':len(parsed['problems']),'catalogEntries':len(catalog),
                                  'codeHashes':C.code_hashes(original),'bytes':path.stat().st_size})
                for problem,markdown in parsed['problems'].items():
                    pid=contest+'::'+problem;problem_text[pid]=markdown
                    raw=catalog.get(problem,('','',''))[1];normalized=normalize_tags(KD.split_names(raw))
                    if normalized['unknown']:exceptions.append({'sourcePath':relative,'problem':problem,'type':'unknown-catalog','names':normalized['unknown']})
                    if problem not in catalog:exceptions.append({'sourcePath':relative,'problem':problem,'type':'missing-catalog'})
                    problem_audit.append({'id':pid,'sourcePath':relative,'catalogKnowledge':raw,
                                          'tags':normalized['tags'],'hasSourceCode':bool(C.code_hashes(markdown))})
                for heading in parsed['headings']:
                    title=heading['title'];problem=heading['problem'];body=heading['body']
                    registered=(contest=='周赛 163' and problem=='C' and heading['level']==3 and title=='思路' and 'Hall 定理' in body and '完美匹配' in body)
                    if not problem or heading['level']<3 or (not registered and not re.search(r'从零讲|先把.+讲明白|基础概念|基础知识',title)) or self._pointer(body):continue
                    identity='lecture:'+hashlib.sha256((str(path.relative_to(self.root))+'\n'+problem+'\n'+title).encode()).hexdigest()[:24]
                    source_tags=normalize_tags(KD.split_names(catalog.get(problem,('','',''))[1]))['tags']
                    concept=re.sub(r'^.*?从零讲\s*[:：]?\s*','',title)
                    tags=[t for t in source_tags if t in concept] or source_tags
                    entry={'id':identity,'title':title,'concept':concept,'tags':list(dict.fromkeys(tags)),
                           'sourceProblemIds':[contest+'::'+problem],'sourceContest':contest,'sourceProblem':problem,
                           'sourceTitle':catalog.get(problem,(heading['problemTitle'],))[0],
                           'available':True,'sourcePath':relative}
                    if registered:entry.update(title='从零讲：Hall 定理与二分图匹配',sourceHeading=title,registeredLesson=True)
                    entry=C.curate(entry,heading['markdown'],parsed['problems'].get(problem,''))
                    entry.update(catalogTags=source_tags,images=self._images(heading['markdown'],path))
                    entries[identity]=entry
            # Standalone source tutorials are educational sources as well. They
            # are audited independently; ordinary state tables are counted only
            # as metadata and never exported as lessons.
            for path in supplements:
                relative=str(path.relative_to(self.root)).replace('\\','/')
                try:original=path.read_text(encoding='utf-8-sig')
                except (OSError,UnicodeError) as error:
                    exceptions.append({'sourcePath':relative,'type':'source-read','message':str(error)[:200]});continue
                documents.append({'sourcePath':relative,'sourceHash':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'problemCount':0,'catalogEntries':0,'codeHashes':C.code_hashes(original),'bytes':path.stat().st_size,'standalone':True})
                parts=path.relative_to(self.root).parts
                if len(parts)<4 or parts[1] not in toolutil.SERIES:continue
                contest=toolutil.format_contest(parts[1],parts[2])
                problem=next((p for p in parts[3:-1] if re.fullmatch(r'[A-Z]\d?',p)),None)
                if not problem or len(original)<300:continue
                if 'DFS' in path.name:title='从零讲：博弈论与记忆化搜索'
                elif '全排列' in path.name:title='从零讲：枚举与全排列配对'
                elif '例子' in path.name:title='从零讲：二分图匹配与 Hall 定理手算'
                else:continue
                identity='lecture:'+hashlib.sha256((str(path.relative_to(self.root))+'\n'+problem+'\n'+title).encode()).hexdigest()[:24]
                entry={'id':identity,'title':title,'tags':normalize_tags(KD.split_names(title.replace('从零讲：','').replace('与',' + ')))['tags'],
                    'sourceProblemIds':[contest+'::'+problem],'sourceContest':contest,'sourceProblem':problem,
                    'sourceTitle':next((e['sourceTitle'] for e in entries.values() if e['sourceProblemIds']==[contest+'::'+problem]),'小月的对局'),
                    'available':True,'sourcePath':relative,'standalone':True}
                entry=C.curate(entry,original,problem_text.get(contest+'::'+problem,''))
                entry['images']=self._images(original,path);entries[identity]=entry
            for identity,e in entries.items():
                path_entries.setdefault(Path(e.get('sourcePath','')).name,[]).append(identity)
            references={key:[] for key in problem_text}
            registry=self.registry.read_text(encoding='utf-8-sig') if self.registry.is_file() else ''
            aliases={};previous=[]
            for line in registry.splitlines():
                cells=toolutil.split_cells(line)
                if not cells or len(cells)<3:continue
                names=re.findall(r'(\d+题解\.md)',cells[2])
                if names:previous=names
                names=names or (previous if '同上' in cells[2] else [])
                source=re.search(r'(.+?)\s+([A-Z]\d?)(?:\s|；|$)',cells[1])
                candidates=[i for name in names for i in path_entries.get(name,[]) if not source or entries[i]['sourceProblemIds']==[source[1].strip()+'::'+source[2]]]
                matching=[i for i in candidates if entries[i].get('originalConcept','') in cells[2] or entries[i].get('knowledgeName','') in cells[0] or C.plain_text(cells[0]).split('/')[0].strip() in C.plain_text(entries[i].get('originalConcept',''))]
                if matching:aliases[cells[0]]=list(dict.fromkeys(matching))
            for problem,markdown in problem_text.items():
                exact=[i for i,e in entries.items() if problem in e['sourceProblemIds']]
                named=set(re.findall(r'(?:《|\b)((?:周赛|小白月赛|练习赛|挑战赛|入门赛|基础赛|月赛|ABC|ARC|Div\.[234])\s*\d+)\s*题解',markdown))
                for identity,e in entries.items():
                    if e['sourceContest'] in named and (e.get('originalConcept') in markdown or e.get('knowledgeName') in markdown):exact.append(identity)
                for alias,identities in aliases.items():
                    if alias in markdown and re.search(r'讲过|从零讲|参见|详见',markdown):exact+=identities
                references[problem]=list(dict.fromkeys(exact))
            available_tags={t for e in entries.values() for t in e['tags']}
            for item in problem_audit:
                ids=references.get(item['id'],[])
                item.update(ownLessonIds=[i for i in ids if item['id'] in entries[i]['sourceProblemIds']],
                            pointerLessonIds=[i for i in ids if item['id'] not in entries[i]['sourceProblemIds']],
                            foundationTagsAvailable=sorted(available_tags.intersection(item['tags'])))
            if documents or not self.audit:
                self.audit={'curationVersion':C.VERSION,'knowledgeVersion':KNOWLEDGE_VERSION,
                    'sourceDocumentCount':len(documents),'contestDocumentCount':len(files),'standaloneDocumentCount':len(supplements),
                    'metadataDocumentCount':len(status_files),'sourceProblemCount':len(problem_audit),'lectureCount':len(entries),
                    'normalizedLectureCount':sum(bool(e.get('quality',{}).get('normalized')) for e in entries.values()),
                    'originalCompleteCount':sum(bool(e.get('quality',{}).get('original',{}).get('foundationComplete')) for e in entries.values()),
                    'renamedCount':sum(e.get('originalConcept')!=e.get('concept') for e in entries.values()),
                    'classificationChangedCount':sum(bool(e.get('quality',{}).get('catalogClassificationChanged')) for e in entries.values()),
                    'unreadSourceCount':sum(e['type']=='source-read' for e in exceptions),
                    'exceptions':exceptions,'documents':documents,'problems':problem_audit,
                    'lectures':[{'id':i,'sourcePath':e['sourcePath'],'problem':e['sourceProblem'],
                        'originalConcept':e.get('originalConcept'),'concept':e['concept'],'knowledgeName':e.get('knowledgeName'),
                        'sourceHash':e.get('sourceHash'),'sourceCodeHashes':e.get('sourceCodeHashes',[]),'quality':e.get('quality')} for i,e in entries.items()],
                    'sourceMutations':0,'sourceAlgorithmReverified':False}
            self.entries=entries;self.sections={i:e['markdown'] for i,e in entries.items()};self.references=references
            self.signature=signature;self.revision=hashlib.sha256(repr(signature).encode()).hexdigest();self._persist_audit()

    def _persist_audit(self):
        if not self.state_dir:return
        path=self.state_dir/'lecture-audit.json';self.state_dir.mkdir(parents=True,exist_ok=True)
        payload=json.dumps(self.audit,ensure_ascii=False,indent=2)
        if path.is_file() and path.read_text(encoding='utf-8')==payload:return
        if path.exists():toolutil.backup_to_repo(str(path))
        toolutil.write_text_atomic(str(path),payload)

    def _images(self,markdown,path):
        import base64
        images={}
        for target in re.findall(r'!\[[^\]]*\]\(([^)\s]+)\)',markdown):
            if urlsplit(target).scheme:continue
            resolved=(path.parent/target).resolve()
            if not resolved.is_relative_to(self.root) or not resolved.is_file() or resolved.stat().st_size>2*1024*1024:continue
            mime={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.gif':'image/gif','.webp':'image/webp'}.get(resolved.suffix.lower())
            if mime:images[target]='data:'+mime+';base64,'+base64.b64encode(resolved.read_bytes()).decode()
        return images

    def snapshot(self):
        self._refresh()
        with self.lock:
            brief={k:v for k,v in self.audit.items() if k not in ('documents','problems','lectures','exceptions')}
            brief['exceptionCount']=len(self.audit.get('exceptions',[]))
            return {'lectures':[copy.deepcopy(summary(e)) for e in self.entries.values()],
                    'revision':self.revision,'curationVersion':C.VERSION,'audit':brief}

    def get(self,identity):
        self._refresh()
        with self.lock:
            if identity not in self.entries:raise ServiceError(404,'没有找到完整的从零讲章节')
            return copy.deepcopy(self.entries[identity])

    def for_problem(self,identity):
        self._refresh()
        with self.lock:
            if hasattr(self.store,'library'):
                try:raw=self.store.row(identity)
                except Exception:return []
                from insights import canonical_url
                found=self.store.library.find(identity,canonical_url(raw.get('_url')))
                links=self.store.library.references(found['id']) if found else []
            else:links=[(i,'own' if identity in self.entries[i]['sourceProblemIds'] else 'explicit') for i in self.references.get(identity,[])]
            result=[];seen=set()
            for lecture,kind in links:
                entry=self.entries.get(lecture)
                if not entry:continue
                digest=hashlib.sha256(entry['markdown'].encode()).hexdigest()
                if digest in seen:continue
                seen.add(digest)
                result.append(dict(copy.deepcopy(summary(entry)),referenceKind=kind))
            return result

    def export(self):
        """Portable corpus without personal progress, keys, or absolute source paths."""
        self._refresh()
        with self.lock:
            entries=[copy.deepcopy(e) for e in self.entries.values()];redactions=0
            for e in entries:
                e['originalSourceHash']=e['sourceHash']
                for field in ('sourceMarkdown','markdown'):
                    e[field],count=portable_markdown(e[field]);redactions+=count
                e['sourceHash']=hashlib.sha256(e['sourceMarkdown'].encode()).hexdigest()
            audit=copy.deepcopy(self.audit);audit['portablePathReferenceCount']=redactions
            return {'curationVersion':C.VERSION,'knowledgeVersion':KNOWLEDGE_VERSION,
                    'lectures':entries,'audit':audit}

    def export_problem_knowledge(self):
        """A bounded correction set from explicitly taught archived techniques."""
        self._refresh()
        with self.lock:
            selected=[e for e in self.entries.values() if e['quality']['catalogClassificationChanged']
                      or e['knowledgeName']=='虚树']
            problems={};aliases={};urls={}
            for e in selected:
                identity=e['sourceContest']+'::'+e['sourceProblem']
                record=problems.setdefault(identity,{'id':identity,'addTags':[],'removeTags':[],
                    'sourcePath':e['sourcePath'],'lessonIds':[],'sourceHashes':[]})
                record['addTags'].append(e['knowledgeName']);record['lessonIds'].append(e['id'])
                record['sourceHashes'].append(e['sourceHash'])
                removed={'Z 函数':['KMP'],'后缀自动机':['字典树'],'虚树':['字典树']}.get(e['knowledgeName'],[])
                record['removeTags']+=removed
                source=self.root/e['sourcePath']
                if not source.is_file():continue
                header='\n'.join(source.read_text(encoding='utf-8-sig').splitlines()[:20])
                homepage=re.search(r'(https?://(?:codeforces\.com|atcoder\.jp|ac\.nowcoder\.com|www\.luogu\.com\.cn)/(?:acm/)?contests?/([a-zA-Z0-9_-]+))',header)
                if not homepage:continue
                parsed=urlsplit(homepage[1]);cid=homepage[2];letter=e['sourceProblem'];url=None;remote=None
                if parsed.hostname=='codeforces.com':
                    remote=f'remote:codeforces:{cid}::{letter}'
                    url=f'https://codeforces.com/contest/{cid}/problem/{letter}'
                    urls[f'codeforces.com/problemset/problem/{cid}/{letter}']=identity
                elif parsed.hostname=='ac.nowcoder.com':
                    remote=f'remote:nowcoder:{cid}::{letter}'
                    url=f'https://ac.nowcoder.com/acm/contest/{cid}/{letter}'
                elif parsed.hostname=='atcoder.jp':
                    remote=f'remote:atcoder:{cid}::{letter}'
                    url=f'https://atcoder.jp/contests/{cid}/tasks/{cid}_{letter.lower()}'
                elif parsed.hostname=='www.luogu.com.cn':
                    problem_list=source.parent/'_work'/'题单.md'
                    for line in problem_list.read_text(encoding='utf-8-sig').splitlines() if problem_list.is_file() else []:
                        cells=toolutil.split_cells(line)
                        if cells and len(cells)>2 and cells[0]==letter and re.fullmatch(r'[PBTU]\d+',cells[2]):
                            remote=f'remote:luogu:{cid}::{letter}'
                            url='https://www.luogu.com.cn/problem/'+cells[2];break
                if remote:aliases[remote]=identity
                if url:
                    parsed=urlsplit(url);urls[parsed.hostname+parsed.path]=identity
            for record in problems.values():
                for field in ('addTags','removeTags','lessonIds','sourceHashes'):
                    record[field]=list(dict.fromkeys(record[field]))
            return {'version':KNOWLEDGE_VERSION,'curationVersion':C.VERSION,
                    'problems':problems,'aliases':aliases,'urls':urls}
