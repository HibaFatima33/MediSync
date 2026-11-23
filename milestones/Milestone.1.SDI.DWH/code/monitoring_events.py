"""Record real observed attempts. History starts when this logging is installed."""
import json
from datetime import datetime, timezone

def record_event(cfg, kind, success, seconds, **fields):
    folder=cfg["results_folder"]; folder.mkdir(parents=True, exist_ok=True)
    event=dict(at=datetime.now(timezone.utc).isoformat(), kind=kind, success=bool(success), seconds=round(seconds,6), **fields)
    with (folder/"monitoring_events.jsonl").open("a",encoding="utf-8") as f:
        f.write(json.dumps(event)+"\n")

def summaries(cfg):
    path=cfg["results_folder"]/"monitoring_events.jsonl"
    events=[]
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip(): events.append(json.loads(line))
    batch=[e for e in events if e["kind"]=="ingestion" and e.get("mode")=="postgres"]
    query=[e for e in events if e["kind"]=="query"]
    def stats(rows):
        n=len(rows); good=sum(e["success"] for e in rows)
        return n,good,n-good,round(100*good/n,2) if n else None,round(100*(n-good)/n,2) if n else None
    return batch,query,stats(batch),stats(query)
