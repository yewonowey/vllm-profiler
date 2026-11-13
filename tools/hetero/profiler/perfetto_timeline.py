# SPDX-License-Identifier: Apache-2.0
"""Convert existing observations to a deterministic MONOTONIC Perfetto trace."""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

if __package__ is None:
    sys.path[0] = str(Path(__file__).resolve().parents[3])

from tools.hetero.profiler import analysis, expected, resources, server
from tools.hetero.profiler.common import live_rows

ROOT = "Heterogeneous LLM Processing"
ORDER = ["Request", "Prefill", "KV Transfer", "KV Layout (H2D+reorder)", "Decode"]
ROLES = dict(
    gpu="GPU",
    npu0="NPU0",
    npu1="NPU1",
    prefill="Prefill(GPU)",
    decode0="Decode(NPU0)",
    decode1="Decode(NPU1)",
)


def slices(rows, ids, spans, events, anchors, trace):
    """Return observed slices/instants in ns; never infer idle or missing stages."""
    result = []

    def add(track, name, a, b, rid="", **args):
        if a is not None and b is not None:
            a, b = round(a * 1e9), round(b * 1e9)
            result.append(
                dict(track=track, name=name, start=a, end=b, rid=rid, args=args)
            )

    for row in sorted(rows, key=lambda r: r["request_id"]):
        rid = row["request_id"]
        slot = str(row["assigned_slot"])
        send, first, end = (
            row[k + "_monotonic"] for k in ("actual_send", "first_output", "completed")
        )
        add(("Client", "Slot " + slot), "Request", send, end, rid)
        add(("Client", "Slot " + slot), "First Token", first, first, rid)
        arrival, assigned = (
            row[k + "_monotonic"] for k in ("scheduled_arrival", "assigned")
        )
        add(("Client", "Queue " + slot, rid), "Queue", arrival, assigned, rid)
        for role, names in sorted(ids.items()):
            if rid not in names:
                continue
            base = (ROLES[role], rid)
            if trace:
                span = spans.get(role, {}).get(expected.server_request_id(rid))
                if not span:
                    continue
                start = resources.mono(span["start"], anchors)
                queue = span.get("gen_ai.latency.time_in_queue")
                if queue is not None:
                    add(
                        base + ("Server Queue",),
                        "Server Queue",
                        start,
                        start + queue,
                        rid,
                    )
                ttft = span.get("gen_ai.latency.time_to_first_token")
                if ttft is None:
                    continue
                first = start + ttft
                prefill = span.get("gen_ai.latency.time_in_model_prefill")
                if not role.startswith("decode") and prefill is not None:
                    add(base + ("Prefill",), "Prefill", first - prefill, first, rid)
                decode = span.get("gen_ai.latency.time_in_model_decode")
                if role != "prefill" and decode is not None:
                    add(base + ("Decode",), "Decode", first, first + decode, rid)
            else:
                first = row["first_output_monotonic"]
                if not role.startswith("decode"):
                    add(base, "Prefill", send, first, rid, status="추정")
                if role != "prefill":
                    add(base, "Decode", first, end, rid, status="추정")
    for role, items in sorted(events.items()):
        starts = {
            e["req_id"]: e["monotonic_ns"]
            for e in items
            if e["kind"] == "kv_xfer_start"
        }
        reverse = {expected.server_request_id(r): r for r in ids.get(role, [])}
        for e in items:
            rid = reverse.get(expected.engine_request_base(e.get("req_id")), "")
            name = {
                "kv_xfer_done": "KV Transfer",
                "kv_h2d": "KV Layout (H2D+reorder)",
                "step": "Decode Step",
            }.get(e["kind"])
            if not name or (e["kind"] == "step" and e.get("phase") != "decode"):
                continue
            if name == "KV Transfer":
                a, b = starts.get(e["req_id"]), e["monotonic_ns"]
            else:
                keys = (
                    ("span_start_ns", "span_end_ns")
                    if name == "Decode Step"
                    else ("start_ns", "end_ns")
                )
                a, b = (e.get(k) for k in keys)
            if a is not None and b is not None:
                fields = ("h2d_ns", "reorder_ns", "num_blocks", "bytes_est", "rank")
                track = (ROLES[role], name, rid or str(e.get("rank", 0)))
                add(
                    track,
                    name,
                    a / 1e9,
                    b / 1e9,
                    rid,
                    **{k: e[k] for k in fields if k in e},
                )

    def ordering(x):
        phase = ORDER.index(x["name"]) if x["name"] in ORDER else len(ORDER)
        return x["start"], phase, x["end"], x["track"], x["name"]

    return sorted(result, key=ordering)


def assign_lanes(entries):
    """Pack intervals by start time, preferring a request's last available lane."""
    ends, previous = {}, {}
    for item in sorted(entries, key=lambda x: (x["start"], x["end"], x["rid"])):
        group = item["track"]
        lanes = ends.setdefault(group, [])
        key = group, item["rid"]
        preferred = previous.get(key)
        free = [i for i, end in enumerate(lanes) if end <= item["start"]]
        lane = preferred if preferred in free else next(iter(free), len(lanes))
        if lane == len(lanes):
            lanes.append(item["end"])
        else:
            lanes[lane] = item["end"]
        previous[key] = lane
        item["track"] = group + (f"Lane {lane}",)
    return ends


def convert(root, workload, out=None, flows="sample", per_request_tracks=False):
    """Write one trace and its SQL validation; return validation metadata."""
    from perfetto.trace_builder.proto_builder import TraceProtoBuilder
    from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

    folder, repo = root / workload, Path(__file__).resolve().parents[3]
    if any(p.resolve().is_relative_to(repo) for p in (folder, out or folder)):
        raise ValueError("timeline output must be outside repository")
    rows = list(live_rows(folder / "requests.jsonl"))
    config = expected.service_config(root)
    ids = expected.expected_ids(rows, config)
    window = (
        min(r["scheduled_arrival_monotonic"] for r in rows),
        max(r["completed_monotonic"] for r in rows),
    )
    trace = json.loads((root / "run.json").read_text())["mode"] in ("trace", "deep")
    spans, events = {}, {}
    if trace:
        analysis.join_requests(root, rows, config, spans, events, window)
    anchors = [
        v
        for k, v in json.loads((folder / "loadgen_run.json").read_text()).items()
        if k.startswith("clock_anchor_")
    ]
    entries = slices(rows, ids, spans, events, anchors, trace)
    bad = [x for x in entries if x["start"] < 0 or x["end"] < x["start"]]
    if bad:
        (folder / "timeline_validation.json").write_text(
            json.dumps(dict(status="FAIL", invalid_input=bad))
        )
        raise ValueError(f"{folder.name}: negative/reversed timestamps ({len(bad)})")
    collected = list(live_rows(folder / "monitor/metrics.jsonl"))
    counters = []
    links = root / "links.json"
    if links.exists():
        for (device, metric), points in resources.read_samples(
            collected, json.loads(links.read_text()), window
        ).items():
            for t, value in points:
                if value is not None:
                    counters.append(
                        (("Resources", device, metric), round(t * 1e9), value)
                    )
    for r in collected:
        if (
            r["endpoint"] in ids
            and r["status"] == 200
            and window[0] <= r["mono_ns"] / 1e9 <= window[1]
        ):
            for sample in server.samples(r["text"]):
                if sample.name in ["vllm:" + n for n in server.GAUGES.values()]:
                    label = json.dumps(sample.labels, sort_keys=True)
                    counters.append(
                        (
                            (ROLES[r["endpoint"]], sample.name, label),
                            r["mono_ns"],
                            sample.value,
                        )
                    )
    by_id = {r["request_id"]: r for r in rows}
    for x in entries:
        r = by_id.get(x["rid"], {})
        x["args"].update(start_ns=x["start"], end_ns=x["end"])
        x["args"].update(
            {k: v for k, v in r.items() if "tokens" in k and isinstance(v, int)}
        )
        if x["name"] == "Request":
            x["args"].update(
                arrival=r["scheduled_arrival_monotonic"],
                queue_wait_s=r["assigned_monotonic"] - r["scheduled_arrival_monotonic"],
            )
    if not per_request_tracks:
        entries = [x for x in entries if x["name"] != "Queue"]
        packed = [x for x in entries if x["track"][0] != "Client"]
        for x in packed:
            x["track"] = (
                (x["track"][0], x["name"])
                if x["name"] in ORDER[2:4] + ["Decode Step", "Server Queue"]
                else x["track"][:1]
            )
        assign_lanes(packed)
        for x in packed:
            if x["name"] in ("Prefill", "Decode"):
                x["track"] = x["track"][:-1] + (
                    x["track"][-1].replace("Lane", "Batch slot"),
                )
    for name, begin, end in (
        ("Queued requests", "scheduled_arrival", "assigned"),
        ("In-flight requests", "actual_send", "completed"),
    ):
        changes = Counter()
        for r in rows:
            changes[round(r[begin + "_monotonic"] * 1e9)] += 1
            changes[round(r[end + "_monotonic"] * 1e9)] -= 1
        value = 0
        for t, delta in sorted(changes.items()):
            value += delta
            counters.append((("Client", name), t, value))
    labels, renamed = {}, []
    names = dict(
        utilization="utilization (%)",
        cpu="CPU utilization (%)",
        power="power (W)",
        memory="memory (bytes)",
    )
    for path, t, value in counters:
        if path[0] == "Resources":
            metric = path[-1]
            path = ("Resources", path[1].upper() + " " + names[metric])
        elif path[0] != "Client":
            raw, label = path[-2:]
            name = (
                "KV cache usage (%)"
                if "cache" in raw
                else "Running requests"
                if "running" in raw
                else "Waiting requests"
            )
            path = (path[0], name)
            labels[path] = label
            value *= 100 if "cache" in raw else 1
        renamed.append((path, t, value))
    counters = renamed

    def grouped(path):
        return path if path[0] in ("Client", "Resources") else (ROOT,) + path

    for x in entries:
        x["track"] = grouped(x["track"])
    counters = [(grouped(p), t, v) for p, t, v in counters]
    labels = {grouped(p): v for p, v in labels.items()}
    paths = {x["track"] for x in entries} | {p for p, _, _ in counters}
    paths = {p[:i] for p in paths for i in range(1, len(p) + 1)}
    uuids = {p: i + 1 for i, p in enumerate(sorted(paths))}
    builder = TraceProtoBuilder()
    snapshot = builder.add_packet().clock_snapshot
    snapshot.primary_trace_clock = 3
    # This synthetic trace's BOOTTIME alias is MONOTONIC, not host BOOTTIME.
    # Perfetto v58 bridges its implicit BOOTTIME domain even without such events.
    for clock_id in (3, 6):
        clock = snapshot.clocks.add()
        clock.clock_id, clock.timestamp = clock_id, 0
    counter_paths = {p for p, _, _ in counters}
    for p, uuid in uuids.items():
        desc = builder.add_packet().track_descriptor
        desc.uuid, desc.name = uuid, p[-1] if p else ROOT
        desc.child_ordering = 3
        rank = [
            "Client",
            ROOT,
            "GPU",
            "Prefill(GPU)",
            "NPU0",
            "Decode(NPU0)",
            "NPU1",
            "Decode(NPU1)",
            "Resources",
        ]
        desc.sibling_order_rank = rank.index(p[-1]) if p[-1] in rank else uuid
        if len(p) > 1:
            desc.parent_uuid = uuids[p[:-1]]
        if p in counter_paths:
            if "memory" in p[-1]:
                desc.counter.unit = desc.counter.UNIT_SIZE_BYTES
            elif p[-1].endswith("requests"):
                desc.counter.unit = desc.counter.UNIT_COUNT
            else:
                desc.counter.unit_name = p[-1].partition("(")[2].rstrip(")")
    flow_ids, next_id = {}, 1
    chosen = sorted(by_id)
    if flows == "sample" and len(chosen) > 64:
        chosen = [chosen[i * (len(chosen) - 1) // 15] for i in range(16)]
    for rid in chosen if flows != "none" else []:
        chain = [
            i
            for name in ORDER
            for i, x in enumerate(entries)
            if x["rid"] == rid and x["name"] == name
        ]
        for a, b in zip(chain, chain[1:]):
            flow_ids.setdefault(a, []).append((next_id, False))
            flow_ids.setdefault(b, []).append((next_id, True))
            next_id += 1
    packets = []
    for i, x in enumerate(entries):
        packets.append((x["start"], 1, i, x, 3 if x["start"] == x["end"] else 1))
        if x["end"] != x["start"]:
            packets.append((x["end"], 0, i, x, 2))
    for t, _, i, x, kind in sorted(packets):
        packet = builder.add_packet()
        packet.timestamp = t
        packet.timestamp_clock_id, packet.trusted_packet_sequence_id = 3, 1
        event = packet.track_event
        event.track_uuid, event.type = uuids[x["track"]], kind
        if kind != 2:
            event.name = x["name"]
            for key, value in dict(request_id=x["rid"], **x["args"]).items():
                arg = event.debug_annotations.add()
                arg.name, arg.string_value = key, str(value)
            for fid, terminal in flow_ids.get(i, []):
                (event.terminating_flow_ids if terminal else event.flow_ids).append(fid)
    for path, t, value in sorted(counters, key=lambda x: (x[1], x[0], x[2])):
        packet = builder.add_packet()
        packet.timestamp = t
        packet.timestamp_clock_id, packet.trusted_packet_sequence_id = 3, 1
        event = packet.track_event
        event.track_uuid, event.type, event.double_counter_value = uuids[path], 4, value
        if path in labels:
            arg = event.debug_annotations.add()
            arg.name, arg.string_value = "prometheus_labels", labels[path]
    out = out or folder / "timeline.pftrace"
    out.write_bytes(builder.serialize())
    with TraceProcessor(
        trace=str(out),
        config=TraceProcessorConfig(bin_path=os.environ["PERFETTO_TP_BIN"]),
    ) as tp:
        query = lambda sql: [vars(r) for r in tp.query(sql)]
        errors = query(
            "select name,value from stats where value != 0 "
            "and severity in ('error','data_loss')"
        )
        actual = query(
            "select track.name, "
            "extract_arg(track.source_arg_set_id, 'trace_id') as uuid, "
            "count(*) as n from slice join track on track.id=slice.track_id "
            "group by track.id order by track.name"
        )
        track_count = query("select count(*) as n from track")[0]["n"]
        counter_count = query("select count(*) as n from counter")[0]["n"]
        total = query("select count(*) as n from slice")[0]["n"]
        flows = query("select count(*) as n from flow")[0]["n"]
        invalid = query("select count(*) as n from slice where dur < 0 or ts < 0")[0][
            "n"
        ]
    wanted = Counter(uuids[x["track"]] for x in entries)
    found = {r["uuid"]: r["n"] for r in actual}
    for row in actual:
        row["expected"] = wanted[row["uuid"]]
    result = dict(
        status="PASS"
        if not errors
        and not invalid
        and dict(wanted) == found
        and counter_count == len(counters)
        and total == len(entries)
        and flows == next_id - 1
        else "FAIL",
        errors=errors,
        invalid_slices=invalid,
        invalid_input=0,
        expected_counters=len(counters),
        actual_counters=counter_count,
        expected_slices=len(entries),
        actual_slices=total,
        expected_flows=next_id - 1,
        actual_flows=flows,
        tracks=actual,
        bytes=out.stat().st_size,
        track_count=track_count,
        lanes=sum(p[-1].startswith(("Lane ", "Batch slot ")) for p in paths if p),
        request_count=len(rows),
    )
    (folder / "timeline_validation.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-dir", type=Path)
    group.add_argument("--sweep-dir", type=Path)
    parser.add_argument("--workload")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--flows", choices=("all", "sample", "none"), default="sample")
    parser.add_argument("--per-request-tracks", action="store_true")
    args = parser.parse_args()
    jobs = []
    if args.sweep_dir:
        spec = json.loads((args.sweep_dir / "scenarios.json").read_text())
        latest = {}
        for scenario in spec["scenarios"]:
            for attempt in scenario.get("attempts") or [
                dict(path="runs/" + scenario["name"])
            ]:
                for work in scenario["workloads"]:
                    root = args.sweep_dir / attempt["path"]
                    p = root / work["name"] / "profile/summary.json"
                    s = json.loads(p.read_text()) if p.exists() else {}
                    if (
                        attempt.get("returncode", 0 if s else None) == 0
                        and s.get("run_status") == s.get("analysis_status") == "PASS"
                    ):
                        latest[scenario["name"], work["name"]] = (root, work["name"])
        jobs = list(latest.values())
    else:
        jobs = (
            [(args.run_dir, args.workload)]
            if args.workload
            else [
                (args.run_dir, p.parent.name)
                for p in sorted(args.run_dir.glob("*/requests.jsonl"))
            ]
        )
    if args.out and len(jobs) != 1:
        parser.error("--out requires exactly one workload")
    results = [
        convert(root, name, args.out, args.flows, args.per_request_tracks)
        for root, name in jobs
    ]
    failed = [
        str(root / name)
        for (root, name), r in zip(jobs, results)
        if r["status"] != "PASS"
    ]
    if failed:
        print(
            f"perfetto_timeline: validation failed: {failed}; "
            "see timeline_validation.json",
            file=sys.stderr,
        )
    return int(bool(failed))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"perfetto_timeline: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
