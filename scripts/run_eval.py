"""HTTP-only evaluation client; the running server owns the single worker."""
import argparse
import math
from pathlib import Path
import sys
import time
from uuid import uuid4

import httpx

from app.config import load_settings
from app.qa.errors import QAError


def _json(response,expected=200):
    if response.status_code!=expected:
        raise QAError("EVALUATION_HTTP_ERROR",f"Evaluation server returned HTTP {response.status_code}",503)
    try:
        return response.json()
    except ValueError:
        raise QAError("EVALUATION_HTTP_ERROR","Evaluation server returned invalid JSON",502) from None


def run_eval(settings,client,output_dir,*,run_id=None,timeout=7200,poll_seconds=1,sleeper=time.sleep,monotonic=time.monotonic,on_plan=None):
    cfg=settings.experiment
    if not cfg.gold_version:
        raise QAError("GOLD_NOT_CONFIGURED","Configure A's frozen gold version before evaluation",409)
    # Compare parsed parameters, not personal file paths or API-key availability.
    expected=settings.experiment_fingerprint()
    health=_json(client.get("/api/health"))
    if health.get("experiment_fingerprint")!=expected:
        raise QAError("CONFIGURATION_MISMATCH","Local and running-server experiment configurations differ",409)
    if not run_id and not health.get("ready"):
        raise QAError("SERVICE_NOT_READY","Running server is not ready for evaluation",409)
    output_dir=Path(output_dir)
    if output_dir.exists():
        raise QAError("OUTPUT_EXISTS","Choose a new output directory; saved results are not overwritten",409)
    if run_id:
        previous=_json(client.get("/api/evaluations/"+run_id))
        if (previous.get("corpus_version"),previous.get("gold_version"),previous.get("config",{}).get("experiment_fingerprint"))!=(cfg.corpus_version,cfg.gold_version,expected):
            raise QAError("CONFIGURATION_MISMATCH","Saved evaluation differs from the local configuration",409)
        planned={"run_id":run_id,"task_id":previous["task_id"],"state":previous["state"]}
    else:
        planned=_json(client.post("/api/evaluations/run",json={"corpus_version":cfg.corpus_version,"gold_version":cfg.gold_version}),202)
    if on_plan:
        on_plan(planned)
    deadline=monotonic()+timeout
    while True:
        task=_json(client.get("/api/tasks/"+planned["task_id"]))
        if task["state"] in {"completed","failed"}:
            break
        if monotonic()>=deadline:
            raise QAError("EVALUATION_WAIT_TIMEOUT",f'Polling timed out; resume reading with --run-id {planned["run_id"]}',503)
        sleeper(poll_seconds)
    run=_json(client.get("/api/evaluations/"+planned["run_id"]))
    if (run.get("corpus_version"),run.get("gold_version"),run.get("config",{}).get("experiment_fingerprint"))!=(cfg.corpus_version,cfg.gold_version,expected):
        raise QAError("CONFIGURATION_MISMATCH","Saved evaluation differs from the requested frozen configuration",409)
    exports={}
    for extension in ("json","csv"):
        response=client.get("/api/evaluations/"+planned["run_id"]+"/export",params={"format":extension})
        if response.status_code!=200:
            raise QAError("EXPORT_FAILED","Saved evaluation export failed",503)
        exports[extension]=response.content
    output_dir.mkdir(parents=True,exist_ok=False)
    for extension,content in exports.items():
        (output_dir/f"evaluation.{extension}").write_bytes(content)
    return {"run_id":planned["run_id"],"task_id":planned["task_id"],"state":run["state"],
            "synthetic":run["synthetic"],"review_complete":run["review_complete"],"output_dir":str(output_dir)}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",help="Explicit configuration overrides DERAG_CONFIG")
    parser.add_argument("--env-file")
    parser.add_argument("--base-url",default="http://127.0.0.1:8000")
    parser.add_argument("--output-dir")
    parser.add_argument("--run-id",help="Read an existing run without submitting or regenerating")
    parser.add_argument("--timeout",type=float,default=7200)
    args=parser.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout<=0:
        parser.error("--timeout must be positive")
    try:
        settings=load_settings(args.config,env_file=args.env_file)
        output=args.output_dir or settings.experiment.data_dir/("runs/client-"+uuid4().hex)
        with httpx.Client(base_url=args.base_url,timeout=30,follow_redirects=False,trust_env=False) as client:
            import json
            result=run_eval(settings,client,output,run_id=args.run_id,timeout=args.timeout,
                            on_plan=lambda plan:print(json.dumps(plan,ensure_ascii=False),file=sys.stderr))
        import json
        print(json.dumps(result,ensure_ascii=False))
        return 0 if result["state"]=="completed" else 1
    except QAError as exc:
        print(f"{exc.code}: {exc.message}",file=sys.stderr)
    except (httpx.HTTPError,OSError,ValueError,KeyError,TypeError):
        print("EVALUATION_CLIENT_ERROR: Check server address, configuration and output directory",file=sys.stderr)
    return 1


if __name__=="__main__":
    raise SystemExit(main())
