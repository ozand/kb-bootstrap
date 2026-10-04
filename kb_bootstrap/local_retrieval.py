"""Bounded local retrieval (ADR-017)."""
from __future__ import annotations
import json, os, stat, ntpath, unicodedata
from pathlib import Path, PurePosixPath
import yaml
MAX_ENTRIES=10000
MAX_FILES=1000
MAX_FILE=1024*1024
MAX_SCAN=16*1024*1024
MAX_RESULTS=100
MAX_OUTPUT=256*1024
MAX_TEXT=512
MAX_QUERY=512
MAX_READ=64*1024
DEFAULT_READ=16*1024
SKIP_DIRS={"raw","research","lessons"}
RESERVED={"index.md","log.md"}
REPARSE=getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0x400)


def json_bytes(value): return json.dumps(value,ensure_ascii=False,separators=(",",":")).encode("utf-8")

def bounded_text(value):
    raw=value.encode("utf-8")[:MAX_TEXT]
    while raw:
        try: return raw.decode("utf-8")
        except UnicodeDecodeError: raw=raw[:-1]
    return ""

def bounded_relative(path):
    value=path.as_posix()
    return value if len(value.encode("utf-8"))<=MAX_TEXT else None

def safe_components(path):
    if ".." in path.parts: return False
    current=Path(path.anchor)
    for part in path.parts[1:]:
        current/=part
        try: info=os.lstat(current)
        except OSError: return False
        if stat.S_ISLNK(info.st_mode) or getattr(info,"st_file_attributes",0)&REPARSE: return False
    return True

def checked_root(directory):
    root=Path(directory)
    if ".." in root.parts: return None,"root_unsafe"
    if not root.is_absolute(): root=Path.cwd()/root
    if root.name.casefold() in SKIP_DIRS or not safe_components(root): return None,"root_unsafe"
    try:
        if not stat.S_ISDIR(os.lstat(root).st_mode): return None,"root_invalid"
    except OSError: return None,"root_unavailable"
    return root,""

def relative_markdown(value):
    if not isinstance(value,str) or "\\" in value or "\x00" in value or ntpath.splitdrive(value)[0]: return None
    path=PurePosixPath(value)
    if path.is_absolute() or path.as_posix()!=value or not path.parts: return None
    if len(path.as_posix().encode("utf-8"))>MAX_TEXT: return None
    if any(x in ("",".","..") or x.startswith(".") or ":" in x for x in path.parts): return None
    if any(x.split(".",1)[0].upper() in {"CON","PRN","AUX","NUL"} or
           (len(x.split(".",1)[0]) == 4 and x.split(".",1)[0][:3].upper() in ("COM","LPT") and x.split(".",1)[0][3] in "123456789")
           for x in path.parts): return None
    if any(x.casefold() in SKIP_DIRS for x in path.parts[:-1]): return None
    if path.name.casefold() in RESERVED or path.suffix.casefold()!=".md": return None
    return path

class _BoundedFrontmatterLoader(yaml.SafeLoader):
    def __init__(self, stream):
        super().__init__(stream)
        self._node_count = 0
        self._compose_depth = 0

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise yaml.YAMLError("aliases are not used for authored context")
        self._node_count += 1
        self._compose_depth += 1
        try:
            if self._node_count > 512 or self._compose_depth > 32:
                raise yaml.YAMLError("frontmatter resource bound")
            return super().compose_node(parent, index)
        finally:
            self._compose_depth -= 1


def parse_frontmatter(data):
    try:
        lines=data.decode("utf-8").splitlines()
        if not lines or lines[0]!="---": return {}
        end=lines.index("---",1)
        if end > 256 or sum(len(line.encode("utf-8")) for line in lines[:end]) > 8192: return {}
        value=yaml.load(chr(10).join(lines[1:end]), Loader=_BoundedFrontmatterLoader)
    except (UnicodeError,ValueError,RecursionError,yaml.YAMLError): return {}
    return value if isinstance(value,dict) else {}

def authored_context(data):
    values=parse_frontmatter(data)
    return {k:bounded_text(values[k]) if isinstance(values.get(k),str) else "unknown" for k in ("revision","review","freshness")}

def authored_title(data):
    try:
        for line in data.decode("utf-8").splitlines():
            title=line.lstrip("#").strip() if line.startswith("#") else ""
            if title: return bounded_text(title)
    except UnicodeError: pass
    return "unknown"

def blocked_search(reason,path=None):
    result={"status":"BLOCKED","complete":False,"results":[],"limiting_budget":None,"reason":reason}
    if path and len(path.encode("utf-8"))<=MAX_TEXT: result["path"]=path
    return result,1

def blocked_read(reason,path=""):
    return {"status":"BLOCKED","path":path,"content":"","truncated":False,"reason":reason},1

def walk_search(root):
    stack=[("directory",root,"")]; entries_seen=file_count=byte_count=0
    while stack:
        kind,path,relative=stack.pop()
        if kind=="directory":
            try:
                with os.scandir(path) as scan:
                    names=[]; remaining=MAX_ENTRIES-entries_seen; overflow=False
                    for index,entry in enumerate(scan):
                        if index>=remaining: overflow=True; break
                        names.append((entry.name,entry.path))
                    if overflow: return entries_seen,file_count,byte_count,"directory_entries",None
                    entries_seen+=len(names)
            except OSError: return entries_seen,file_count,byte_count,"directory_unavailable",relative or None
            typed=[]
            for name,raw in names:
                try: info=os.lstat(raw)
                except OSError: return entries_seen,file_count,byte_count,"path_unavailable",name
                if stat.S_ISLNK(info.st_mode) or getattr(info,"st_file_attributes",0)&REPARSE:
                    return entries_seen,file_count,byte_count,"unsafe_path",name
                typed.append((name+("/" if stat.S_ISDIR(info.st_mode) else ""),name,Path(raw),info))
            typed.sort(key=lambda row:row[0])
            actions=[]
            for _,name,child,info in typed:
                rel=relative+"/"+name if relative else name
                if name.startswith("."): continue
                if stat.S_ISDIR(info.st_mode):
                    if name.casefold() not in SKIP_DIRS: actions.append(("directory",child,rel))
                    continue
                if not stat.S_ISREG(info.st_mode) or child.suffix.casefold()!=".md" or name.casefold() in RESERVED: continue
                if len(rel.encode("utf-8"))>MAX_TEXT: return entries_seen,file_count,byte_count,"path_too_long",None
                actions.append(("file",child,rel))
            stack.extend(reversed(actions))
            continue
        file_count+=1
        if file_count>MAX_FILES: return entries_seen,file_count,byte_count,"files",None
        try: details=os.lstat(path)
        except OSError: return entries_seen,file_count,byte_count,"file_unavailable",relative
        if not stat.S_ISREG(details.st_mode) or getattr(details,"st_file_attributes",0)&REPARSE:
            return entries_seen,file_count,byte_count,"unsafe_path",relative
        if details.st_size>MAX_FILE: return entries_seen,file_count,byte_count,"file_bytes",None
        if byte_count+details.st_size>MAX_SCAN: return entries_seen,file_count,byte_count,"scan_bytes",None
        try:
            with open(path,"rb") as stream: data=stream.read(min(MAX_FILE,MAX_SCAN-byte_count)+1)
        except OSError: return entries_seen,file_count,byte_count,"file_unavailable",relative
        if len(data)>MAX_FILE: return entries_seen,file_count,byte_count,"file_bytes",None
        if byte_count+len(data)>MAX_SCAN: return entries_seen,file_count,byte_count,"scan_bytes",None
        byte_count+=len(data)
        try: text=data.decode("utf-8")
        except UnicodeError: return entries_seen,file_count,byte_count,"invalid_utf8",relative
        yield relative,data,text
    return entries_seen,file_count,byte_count,"",None

def search_local(query,directory,limit=10):
    if not isinstance(query,str) or not query or any(unicodedata.category(c)=="Cc" for c in query): return blocked_search("query_invalid")
    if len(query.encode("utf-8"))>MAX_QUERY: return blocked_search("query_too_long")
    if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=MAX_RESULTS: return blocked_search("limit_invalid")
    root,error=checked_root(directory)
    if error: return blocked_search(error)
    results=[]; folded=query.casefold(); iterator=walk_search(root)
    while True:
        try: rel,data,text=next(iterator)
        except StopIteration as stop:
            summary=stop.value or (0,0,0,"",None); reason,path=summary[-2:]; break
        hit=None
        for number,line in enumerate(text.splitlines(),1):
            if folded not in line.casefold(): continue
            context=authored_context(data)
            hit={"kb":bounded_text(root.name),"layer":"canonical-selection","path":rel,
              "title":authored_title(data),"match_line":number,"snippet":bounded_text(line),
              "snippet_truncated":len(line.encode("utf-8"))>MAX_TEXT,"revision":context["revision"],
              "review":context["review"],"freshness":context["freshness"]}
            break
        if hit and len(results)>=limit:
            reason,path="result_limit",None
            break
        if hit: results.append(hit)
    if reason in ("path_unavailable","unsafe_path","invalid_utf8"): return blocked_search(reason,path)
    if reason in ("directory_unavailable","file_unavailable","path_too_long"): return blocked_search(reason,path)
    result={"status":"PARTIAL" if reason else "COMPLETE","complete":not bool(reason),"results":results,"limiting_budget":reason or None}
    code=3 if reason else 0
    while len(json_bytes(result))+1>MAX_OUTPUT and results:
        results.pop(); result.update(status="PARTIAL",complete=False,limiting_budget="output_bytes"); code=3
    if len(json_bytes(result))+1>MAX_OUTPUT: return blocked_search("output_unavailable")
    return result,code

def read_local(value,directory,max_bytes=DEFAULT_READ):
    if not isinstance(max_bytes,int) or isinstance(max_bytes,bool) or not 0<=max_bytes<=MAX_READ: return blocked_read("read_limit_invalid")
    relative=relative_markdown(value)
    if relative is None: return blocked_read("path_invalid")
    rel=relative.as_posix()
    if len(rel.encode("utf-8"))>MAX_TEXT: return blocked_read("path_too_long")
    root,error=checked_root(directory)
    if error: return blocked_read(error)
    target=root.joinpath(*relative.parts)
    if not safe_components(target): return blocked_read("unsafe_path",rel)
    try:
        info=os.lstat(target)
        if not stat.S_ISREG(info.st_mode) or getattr(info,"st_file_attributes",0)&REPARSE: return blocked_read("file_unavailable",rel)
        with open(target,"rb") as stream: raw=stream.read(max_bytes+3)
    except OSError: return blocked_read("file_unavailable",rel)
    truncated=len(raw)>max_bytes; prefix=raw[:max_bytes]
    try: content=prefix.decode("utf-8")
    except UnicodeDecodeError as exc:
        if not truncated and exc.reason=="unexpected end of data":
            return blocked_read("invalid_utf8",rel)
        if exc.reason=="unexpected end of data" and exc.end==len(prefix) and len(prefix)-exc.start<=3:
            lead = prefix[exc.start]
            total = 2 if lead < 0xE0 else 3 if lead < 0xF0 else 4
            needed = total - (len(prefix) - exc.start)
            try:
                (prefix[exc.start:] + raw[max_bytes:max_bytes + needed]).decode("utf-8")
            except UnicodeError:
                return blocked_read("invalid_utf8",rel)
            prefix=prefix[:exc.start]
            try: content=prefix.decode("utf-8")
            except UnicodeError: return blocked_read("invalid_utf8",rel)
        else: return blocked_read("invalid_utf8",rel)
    result={"status":"TRUNCATED" if truncated else "COMPLETE","path":rel,"content":content,"truncated":truncated}
    code=3 if truncated else 0
    while len(json_bytes(result))+1>MAX_OUTPUT and content:
        content=content[:-1]
        truncated=True; code=3
        result.update(status="TRUNCATED",content=content,truncated=True)
    if len(json_bytes(result))+1>MAX_OUTPUT: return blocked_read("output_unavailable")
    return result,code
