# SPDX-License-Identifier: Apache-2.0
import argparse
import json
import math
import statistics
import sys
from collections import Counter
from itertools import pairwise
from pathlib import Path

if __package__ is None:
    sys.path[0] = str(Path(__file__).resolve().parents[3])

from tools.hetero.profiler import expected, log
from tools.hetero.profiler.expected import request_succeeded

KV_KINDS = ("kv_xfer_start", "kv_xfer_done", "kv_h2d")


def metric(value, unit="s", reason="missing_raw"):
    status = "not_collected" if value is None else "measured"
    reason = reason if value is None else None
    return dict(
        value=value, status=status, reason=reason, source="requests.jsonl", unit=unit
    )


def validate_raw(folder, rows, config):
    failures = [
        f"{name}: missing file"
        for name in ("requests.jsonl", "loadgen_run.json")
        if not (folder / name).is_file()
    ]
    unique = len({r["request_id"] for r in rows})
    successes = sum(map(request_succeeded, rows))
    if not config["requests"] == unique == successes == len(rows):
        counts = config["requests"], unique, successes, len(rows)
        failures.append(f"requests.jsonl: planned/unique/success/raw mismatch {counts}")
    for row in rows:
        rid = row["request_id"]
        for kind in ("input", "output"):
            if row[f"actual_{kind}_tokens"] != row[f"requested_{kind}_tokens"]:
                failures.append(f"{rid}: {kind} token count mismatch")
        if not request_succeeded(row):
            failures.append(f"{rid}: HTTP {row['http_status']}, {row['error']}")
    return dict(run_status="FAILED" if failures else "PASS", failures=failures)


def client_metrics(rows):
    requests, samples = [], []
    fields = "scheduled_arrival assigned actual_send first_output last_output completed"
    for row in rows:
        arrival, assigned, send, first, last, end = (
            row[k + "_monotonic"] for k in fields.split()
        )
        count, chunks = row["actual_output_tokens"], row["chunk_timestamps"]
        tokens, chunk_times = [], []
        for chunk in chunks:
            timestamp = arrival + chunk["t_rel_arrival_seconds"]
            tokens.extend(
                timestamp for t in (chunk["token_ids"] or []) if type(t) is int
            )
            if chunk["text_chars"] or chunk["token_ids"]:
                chunk_times.append(timestamp)
        streamed = len(row["streamed_token_ids"] or [])
        exact = bool(tokens) and len(tokens) == streamed == count == len(set(tokens))
        itl = [b - a for a, b in pairwise(tokens)] if exact else None
        tpot = None
        if count and count > 1 and first is not None and last is not None:
            tpot = (last - first) / (count - 1)
        values = dict(queue_wait=assigned - arrival, client_send_delay=send - arrival)
        values.update(ttft=first - arrival if first is not None else None)
        values.update(service_ttft=first - send if first is not None else None)
        values.update(tpot=tpot, e2e=end - arrival, service=end - send)
        values.update(second_token_delay=itl[0] if itl else None)
        values.update(
            token_itl=itl, chunk_itl=[b - a for a, b in pairwise(chunk_times)]
        )
        wrapped = {}
        for key, value in values.items():
            undefined = count == 1 and key in ("tpot", "second_token_delay")
            reason = "not_applicable" if undefined else "missing_token_timing"
            wrapped[key + "_seconds"] = metric(value, reason=reason)
        requests.append(dict(request_id=row["request_id"], metrics=wrapped))
        samples.append((request_succeeded(row), values))
    good = [r for r in rows if request_succeeded(r)]
    start = min((r["scheduled_arrival_monotonic"] for r in rows), default=0)
    makespan = max((r["completed_monotonic"] for r in rows), default=start) - start
    exact_count = sum(ok and v["token_itl"] is not None for ok, v in samples)
    counts = dict(request_count=len(rows), success_count=len(good))
    counts.update(
        dict.fromkeys(("failure_count", "incomplete_count"), len(rows) - len(good))
    )
    counts.update(sample_size=len(rows), retry_count=0)
    counts["token_itl_request_count"] = exact_count
    counts.update(chunk_itl_only_request_count=len(good) - exact_count)
    counts["timeout_count"] = sum(
        "timed out" in str(r["error"]).lower() for r in rows if not request_succeeded(r)
    )
    counts["target_request_counts"] = dict(Counter(r["assigned_target"] for r in rows))
    summary = {k: metric(v, "requests") for k, v in counts.items()}
    summary["makespan_seconds"] = metric(makespan)
    totals = {
        k: sum(r[f"actual_{k}_tokens"] or 0 for r in good) for k in ("input", "output")
    }
    for kind, total in totals.items():
        summary[f"actual_{kind}_tokens_total"] = metric(total, "tokens")
    rates = {"completed_requests": len(good), "output_tokens": totals["output"]}
    for name, total in rates.items():
        unit = "requests/s" if name == "completed_requests" else "tokens/s"
        summary[name + "_per_second"] = metric(
            total / makespan if makespan else None, unit, "no_duration"
        )
    summary["tok_per_s_per_device"] = metric(
        totals["output"] / makespan / 3 if makespan else None, "tokens/s/device"
    )
    for key in samples[0][1] if samples else ():
        values = [v[key] for ok, v in samples if ok or key == "queue_wait"]
        # Preserve legacy zero exclusion for TTFT/TPOT and failed-request queues.
        values = [
            v for v in values if v is not None and (v or key not in ("ttft", "tpot"))
        ]
        values = sorted(x for v in values for x in (v if isinstance(v, list) else [v]))
        prefix = "queue" if key == "queue_wait" else key
        stats = {"mean": statistics.mean(values) if values else None}
        for q in (50, 90, 95, 99):
            stats[f"p{q}"] = (
                values[math.ceil(q / 100 * len(values)) - 1] if values else None
            )
        reasons = {r["metrics"][key + "_seconds"]["reason"] for r in requests}
        reason = "not_applicable" if reasons == {"not_applicable"} else "no_samples"
        for stat, value in stats.items():
            summary[f"{prefix}_{stat}_seconds"] = metric(value, reason=reason)
    return dict(requests=requests, summary=summary)


def join_requests(root, rows, config):
    ids = expected.expected_ids(rows, config)
    current = {expected.server_request_id(r["request_id"]) for r in rows}
    kinds, wanted = {}, set()
    for role, names in ids.items():
        kv = role.startswith("decode") and config["configuration"] == "pdd"
        kinds[role] = ("span",) + (KV_KINDS if kv else ())
        names = {expected.server_request_id(rid) for rid in names}
        wanted.update((role, rid, kind) for rid in names for kind in kinds[role])
    seen, unmatched = Counter(), Counter()
    for batch in expected.live_rows(root / "otel" / "traces.jsonl"):
        for resource in batch.get("resourceSpans", []):
            role = expected.attribute(resource.get("resource", {}), "service.name")
            for scope in resource.get("scopeSpans", []):
                for span in scope.get("spans", []):
                    rid = expected.attribute(span, "gen_ai.request.id")
                    if rid in current:
                        seen[role, rid, "span"] += 1
    for role in kinds:
        for path in (root / "rbln_metrics" / role).glob("events_*.jsonl"):
            for event in expected.live_rows(path):
                rid, kind = event.get("req_id"), event["kind"]
                base = expected.engine_request_base(rid)
                if kind in kinds[role] and (base is None or base in current):
                    target = unmatched if base is None else seen
                    target[role, base or rid, kind] += 1
    groups = dict(missing=wanted - seen.keys(), unexpected=seen.keys() - wanted)
    groups["unmatched"] = unmatched.keys()
    groups["duplicates"] = {k for k, v in seen.items() if v > 1}
    result = {}
    for key, items in groups.items():
        counts = unmatched if key == "unmatched" else seen
        result[key] = [
            dict(role=r, request_id=i, kind=k, count=counts[r, i, k])
            for r, i, k in sorted(items)
        ]
    result["complete"] = not any(result.values())
    counts = Counter((role, kind) for role, _, kind in wanted & seen.keys())
    result["matched"] = {r: {k: counts[r, k] for k in kinds[r]} for r in ids}
    return result


def analyze(service_run, workload):
    root, folder = Path(service_run), Path(service_run) / workload
    if folder.resolve().is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError(f"{folder}: analysis output must be outside repository")
    log.RUN_ID = root.name
    mode = json.loads((root / "run.json").read_text())["mode"]
    config = expected.service_config(root)
    rows = list(expected.live_rows(folder / "requests.jsonl"))
    workload_config = json.loads((folder / "config.json").read_text())
    result = validate_raw(folder, rows, workload_config)
    result.update(
        client=client_metrics(rows), per_device={}, analysis_status="NOT_COLLECTED"
    )
    result.update(configuration=config["configuration"], mode=mode, workload=workload)
    for role, ids in expected.expected_ids(rows, config).items():
        subset = [
            r for r in rows if r["request_id"] in ids or r["assigned_target"] == role
        ]
        result["per_device"][role] = client_metrics(subset)
    if mode in ("trace", "deep"):
        joined = result["request_join"] = join_requests(root, rows, config)
        result["analysis_status"] = "PASS" if joined["complete"] else "INCOMPLETE"
        for kind in ("missing", "unexpected", "duplicates", "unmatched"):
            for item in joined[kind]:
                result["failures"].append(
                    f"{kind}: {item} (otel/traces.jsonl or rbln_metrics)"
                )
    (folder / "profile").mkdir(exist_ok=True)
    (folder / "profile" / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    for failure in result["failures"]:
        log.log_line("analysis", f"{folder}: {failure}")
    return int(bool(result["failures"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    folder = parser.parse_args().run_dir
    try:
        code = analyze(folder.parent, folder.name)
    except Exception as exc:
        log.log_line("analysis", f"{folder}: {type(exc).__name__}: {exc}")
        code = 1
    raise SystemExit(code)
