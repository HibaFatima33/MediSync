"""M1 polling watcher: stable changed contents trigger pharma_phase1 via Airflow CLI.
No startup load is requested unless --initial-load is supplied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import time

FILES=("01_master_data.csv","05_pharmacy_sales_data.csv","06_hospital_demand_data.csv")

def ubuntu_path(value,base):
    win=PureWindowsPath(str(value))
    if len(win.drive)==2 and win.drive[1]==":":
        return Path('/mnt')/win.drive[0].lower()/Path(*win.parts[1:])
    p=Path(value).expanduser()
    return p if p.is_absolute() else base/p

def file_details(folder):
    return tuple((name,(folder/name).stat().st_size,(folder/name).stat().st_mtime_ns) for name in FILES)

def stable_hashes(folder,settle_seconds=5):
    before=file_details(folder)
    time.sleep(settle_seconds)
    if file_details(folder)!=before:return None
    hashes=[]
    for name in FILES:
        with (folder/name).open('rb') as f:
            hashes.append(hashlib.file_digest(f,'sha256').hexdigest())
    return tuple(hashes) if file_details(folder)==before else None

def watch(config_path,dag_id='pharma_phase1',once=False,initial_load=False,poll_seconds=5):
    config=json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
    source=ubuntu_path(config['source_folder'],Path(__file__).resolve().parents[3])
    command=Path(sys.executable).parent/'airflow'
    if not command.exists():raise RuntimeError("Use Ubuntu's Airflow Python environment.")
    env=os.environ.copy();env.setdefault('AIRFLOW_HOME',str(Path.home()/'airflow'))
    previous=None;baseline_ready=False
    print('Watching',source,'DAG:',dag_id,'Initial load:',initial_load,flush=True)
    while True:
        try:
            current=stable_hashes(source,poll_seconds)
            if current is None:continue
            if not baseline_ready:
                baseline_ready=True
                if not initial_load:
                    previous=current
                    print('Baseline recorded; waiting for changed contents.',flush=True)
                    continue
            if current==previous:continue
            result=subprocess.run([str(command),'dags','trigger',dag_id],env=env,capture_output=True,text=True,timeout=120)
            if result.returncode:
                print('Trigger not accepted; will retry:',result.stderr,flush=True)
                continue
            previous=current
            print('Airflow accepted changed contents:',result.stdout,flush=True)
            if once:return
        except (OSError,subprocess.SubprocessError) as exc:
            print('Waiting or retrying:',type(exc).__name__,flush=True)
        finally:
            time.sleep(poll_seconds)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--dag',default='pharma_phase1')
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--initial-load',action='store_true')
    args=parser.parse_args()
    try:watch(args.config,args.dag,args.once,args.initial_load)
    except KeyboardInterrupt:print('Watcher stopped.')
