from pathlib import Path
import json,hashlib,os,shutil,datetime
w=Path(__file__).resolve().parent
rows=[]
for name in ["compile","reproduce","compile-check"]:
 p=w/(name+"-ownership.json");r=json.loads(p.read_text());assert r["ownedProcessGroupExited"] and r["exitCode"]==0
 pg=r["ownedProcessGroup"]
 try:os.killpg(pg,0)
 except ProcessLookupError:absent=True
 else:absent=False
 assert absent,(name,pg,"still exists")
 tmp=w/(name+"-tmp");files={str(x.relative_to(tmp)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(tmp.rglob("*")) if x.is_file()} if tmp.exists() else {}
 if tmp.exists():shutil.rmtree(tmp)
 assert not tmp.exists()
 rows.append({"name":name,"processGroup":pg,"processGroupAbsent":True,"tempDirectory":str(tmp),"tempDirectoryDeleted":True,"retainedTempFileHashes":files,"ownershipReportSHA256":hashlib.sha256(p.read_bytes()).hexdigest()})
report={"status":"pass","workspaceOwner":"placid-badger","completedUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"jobs":rows,"scope":"Only exact final-export owned process groups and directories; prior cleanup reports remain unchanged."}
(w/"final-export-cleanup.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
