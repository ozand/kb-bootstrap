"""Bounded read-only search of explicitly configured lesson Markdown."""
import json, os, re, stat, unicodedata
from pathlib import Path, PurePosixPath
import yaml
REPARSE=getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0x400)
PROJECT=re.compile(r"^([A-Za-z][A-Za-z0-9_-]*-\d{4})-[A-Za-z0-9._-]+\.md$")
SHARED=re.compile(r"^(KB-\d{4})-[A-Za-z0-9._-]+\.md$")
class Loader(yaml.SafeLoader):
 def __init__(self,s): super().__init__(s); self.n=0; self.d=0
 def compose_node(self,p,i):
  if self.check_event(yaml.AliasEvent): raise yaml.YAMLError()
  self.n+=1; self.d+=1
  try:
   if self.n>10000 or self.d>32: raise yaml.YAMLError()
   return super().compose_node(p,i)
  finally: self.d-=1
 def construct_mapping(self,node,deep=False):
  d={}
  for k,v in node.value:
   key=self.construct_object(k,deep=deep)
   if key in d: raise yaml.YAMLError()
   d[key]=self.construct_object(v,deep=deep)
  return d
def _pairs(items):
 d={}
 for k,v in items:
  if k in d: raise ValueError()
  d[k]=v
 return d
def _safe(p):
 p=Path(p)
 if ".." in p.parts: return False
 if not p.is_absolute(): p=Path.cwd()/p
 cur=Path(p.anchor)
 for part in p.parts[1:]:
  cur/=part
  try: s=os.lstat(cur)
  except OSError: return False
  if stat.S_ISLNK(s.st_mode) or getattr(s,"st_file_attributes",0)&REPARSE: return False
 return True
def _read(p,cap,b,markdown=False):
 if not _safe(p): raise ValueError()
 s=os.lstat(p)
 if s.st_size>cap:
  if markdown: raise OverflowError("file_bytes")
  raise ValueError()
 if not stat.S_ISREG(s.st_mode) or b[0]+s.st_size>16*1024*1024: raise OverflowError()
 with open(p,"rb") as f: raw=f.read(cap+1)
 b[0]+=len(raw)
 if len(raw)>cap or b[0]>16*1024*1024: raise OverflowError()
 return raw
def _bad(): return {"status":"UNAVAILABLE","complete":False,"results":[],"limiting_budget":None,"reason":"unavailable"}
def search_lessons(query,project_root,store,limit=10):
 try: query_bytes=len(query.encode("utf-8")) if isinstance(query,str) else 0
 except UnicodeEncodeError: return _bad(),1
 if not isinstance(query,str) or not query or query_bytes>512 or any(unicodedata.category(c)=="Cc" for c in query) or not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=100 or store not in ("local","shared"): return _bad(),1
 raw_root=Path(project_root)
 if ".." in raw_root.parts: return _bad(),1
 root=raw_root if raw_root.is_absolute() else Path.cwd()/raw_root
 cfg=root/"lesson-stores.json"; budget=[0]
 try:
  if not _safe(root) or not stat.S_ISDIR(os.lstat(root).st_mode): raise ValueError()
  conf=json.loads(_read(cfg,65536,budget).decode(),object_pairs_hook=_pairs)
  if not isinstance(conf,dict) or conf.get("version")!=1: raise ValueError()
  entry=conf.get(store)
  if store=="local" and store not in conf:
   return {"status":"BLOCKED","complete":False,"results":[],"limiting_budget":None,"reason":"store_not_configured"},1
  if not isinstance(entry,dict) or not isinstance(entry.get("path"),str): raise ValueError()
  raw=entry["path"]
  if "\\" in raw or "\x00" in raw: raise ValueError()
  raw_path=Path(raw)
  if ".." in raw_path.parts: raise ValueError()
  if store=="local" and raw_path.is_absolute(): raise ValueError()
  base=raw_path if raw_path.is_absolute() else cfg.parent/raw_path
  if not _safe(base) or not stat.S_ISDIR(os.lstat(base).st_mode): raise ValueError()
  base=Path(os.path.abspath(base))
  try: base.relative_to(root)
  except ValueError:
   if store!="shared": raise ValueError()
  if store=="shared" and entry.get("read_only") is not True: raise ValueError()
  if store=="local":
   lessons=base; result_prefix=base.relative_to(root).as_posix()+"/"; _read(base/"SCHEMA.md",65536,budget).decode(); index=base/"index.yaml"; pattern=PROJECT
  else: lessons=base/"lessons"; result_prefix="lessons/"; index=base/"index.yaml"; pattern=SHARED
  if not _safe(lessons) or not stat.S_ISDIR(os.lstat(lessons).st_mode): raise ValueError()
  idx=yaml.load(_read(index,1048576,budget).decode(),Loader=Loader)
  if not isinstance(idx,dict) or not isinstance(idx.get("lessons"),list): raise ValueError()
  if len(idx["lessons"])>1000: raise OverflowError("index_entries")
  with os.scandir(lessons) as it:
   names=[]; directory_entries=0
   for e in it:
    directory_entries+=1
    if directory_entries>10000: raise OverflowError("directory_entries")
    if e.name.lower().endswith(".md") and not (store=="local" and e.name=="SCHEMA.md"): names.append(e.name)
  names.sort()
  if len(names)>1000: raise OverflowError("eligible_files")
  mapped={}; indexed_ids=set()
  if store=="local":
   if idx.get("version")!=1 or idx.get("scope")!="project": raise ValueError()
   prefix=idx.get("id_prefix")
   if not isinstance(prefix,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*-",prefix): raise ValueError()
   for row in idx["lessons"]:
    if not isinstance(row,dict): raise ValueError()
    lid,path=row.get("id"),row.get("path"); p=PurePosixPath(path) if isinstance(path,str) else None
    if not isinstance(lid,str) or not re.fullmatch(re.escape(prefix)+r"\d{4}",lid) or p is None or p.is_absolute() or ".." in p.parts or "\\" in path: raise ValueError()
    name=p.name; m=pattern.fullmatch(name)
    if not m or m.group(1)!=lid or name not in names: raise ValueError()
    if base.relative_to(root).as_posix()+"/"+name!=p.as_posix(): raise ValueError()
    if name in mapped or lid in indexed_ids: raise ValueError()
    mapped[name]=lid; indexed_ids.add(lid)
  else:
   for row in idx["lessons"]:
    if not isinstance(row,dict): raise ValueError()
    lid,path=row.get("id"),row.get("file")
    if not isinstance(path,str) or not path.startswith("lessons/") or path.count("/")!=1: raise ValueError()
    name=path[8:]; m=pattern.fullmatch(name)
    if not isinstance(lid,str) or not re.fullmatch(r"KB-\d{4}",lid) or not m or m.group(1)!=lid or name not in names or name in mapped or lid in indexed_ids: raise ValueError()
    mapped[name]=lid; indexed_ids.add(lid)
   count=idx.get("count")
   if not isinstance(count,int) or isinstance(count,bool) or count!=len(idx["lessons"]): raise ValueError()
  if len(mapped)!=len(names) or set(mapped)!=set(names): raise ValueError()
  for name in names:
   m=pattern.fullmatch(name)
   if not m or m.group(1)!=mapped[name]: raise ValueError()
  results=[]; folded=query.casefold(); partial=None
  for i,name in enumerate(names):
   try: data=_read(lessons/name,1048576,budget,markdown=True)
   except OverflowError as exc: partial=str(exc) or "source_bytes"; break
   chunks=data.split(b"\n")
   if not chunks or chunks[0].removesuffix(b"\r")!=b"---": raise ValueError()
   header_parts=[]; header_bytes=0; end=None
   for n,part in enumerate(chunks,1):
    line=part+b"\n" if n<len(chunks) else part
    if line.endswith(b"\r\n"): content=line[:-2]
    elif line.endswith(b"\n"): content=line[:-1]
    else: content=line
    if n>256 or header_bytes+len(line)>8192: raise ValueError()
    header_bytes+=len(line)
    if n==1: continue
    if content==b"---": end=n; break
    header_parts.append(content)
   if end is None: raise ValueError()
   header=b"\n".join(header_parts).decode("utf-8")
   meta=yaml.load(header,Loader=Loader)
   if not isinstance(meta,dict) or meta.get("id")!=mapped[name]: raise ValueError()
   body=b"\n".join(chunks[end:]).decode("utf-8")
   if body.startswith("\r"): body=body[1:]
   body_lines=body.splitlines()
   hit=next((line for line in body_lines if folded in line.casefold()),None)
   if hit is not None:
    raw=hit.encode("utf-8")[:512]
    while raw:
     try: excerpt=raw.decode("utf-8"); break
     except UnicodeDecodeError: raw=raw[:-1]
    results.append({"store":store,"id":mapped[name],"path":result_prefix+name,"excerpt":excerpt})
    if len(results)>=limit and i+1<len(names): partial="results"; break
  report={"status":"PARTIAL" if partial else "COMPLETE","complete":not bool(partial),"results":results,"limiting_budget":partial,"reason":None}
  output_bytes=len(json.dumps(report,ensure_ascii=False,separators=(",",":")).encode())+1
  if output_bytes>262144:
   partial="output_bytes"
   while output_bytes>262144 and results:
    results.pop(); report.update(status="PARTIAL",complete=False,limiting_budget=partial)
    output_bytes=len(json.dumps(report,ensure_ascii=False,separators=(",",":")).encode())+1
  return report,3 if partial else 0
 except OverflowError as exc: return {"status":"PARTIAL","complete":False,"results":[],"limiting_budget":str(exc) or "source_bytes","reason":None},3
 except (OSError,UnicodeError,ValueError,TypeError,yaml.YAMLError,RecursionError): return _bad(),1
