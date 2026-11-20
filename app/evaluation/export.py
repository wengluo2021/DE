"""Exports are pure reads of persisted snapshots; no QA or retrieval imports."""
import csv
import io
import json


def export_json(run):
    return json.dumps(run,ensure_ascii=False,indent=2,allow_nan=False)+"\n"


def export_csv(run):
    columns=("run_id","case_id","condition","corpus_version","gold_version","index_version","synthetic",
             "question","answerable","state","ask_id","conversation_id","gold","retrieval","result",
             "metrics","review","error","trace","review_history","configuration")
    output=io.StringIO(newline="")
    writer=csv.DictWriter(output,fieldnames=columns,lineterminator="\n")
    writer.writeheader()
    for case in run["cases"]:
        row={key:run[key] for key in ("run_id","corpus_version","gold_version","index_version","synthetic")}
        row.update({key:case[key] for key in ("case_id","condition","state","ask_id","conversation_id")})
        row.update(question=case["gold"]["question"],answerable=case["gold"]["answerable"],gold=case["gold"],
                   retrieval=(case["trace"] or {}).get("retrieval"),configuration=run["config"],
                   review_history=[r for r in run["review_history"] if (r["condition"],r["case_id"])==(case["condition"],case["case_id"])])
        row.update({key:case[key] for key in ("result","metrics","review","error","trace")})
        for key in row:
            if row[key] is None or isinstance(row[key],(dict,list,bool)):
                row[key]=json.dumps(row[key],ensure_ascii=False,allow_nan=False)
            elif isinstance(row[key],str) and row[key].lstrip().startswith(("=","+","-","@")):
                # Spreadsheet-safe text; exact original text remains in JSON columns/export.
                row[key]="'"+row[key]
        writer.writerow(row)
    return output.getvalue()
