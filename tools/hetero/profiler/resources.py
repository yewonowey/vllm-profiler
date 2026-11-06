# SPDX-License-Identifier: Apache-2.0
import json
from itertools import pairwise
from statistics import mean

from tools.hetero.profiler import expected, server
from tools.hetero.profiler.server import metric

DEVICES = ("gpu", "npu0", "npu1")
DEVICE_METRICS = dict(
    utilization="gpu_utilization",
    memory="gpu_memory_used_bytes",
    power="gpu_power_consumption_watts",
)
ROLE_DEVICE = dict(prefill="gpu", decode0="npu0", decode1="npu1")


def union(intervals):
    result = []
    for a, b in sorted(intervals):
        if b > a:
            if result and a <= result[-1][1]:
                result[-1] = (result[-1][0], max(b, result[-1][1]))
            else:
                result.append((a, b))
    return result


def active_ratio(intervals, window):
    clipped = [(max(a, window[0]), min(b, window[1])) for a, b in intervals]
    return sum(b - a for a, b in union(clipped)) / (window[1] - window[0])


def device_states(phases, window):
    edges = [t for group in phases.values() for ab in group for t in ab]
    points = {max(window[0], min(t, window[1])) for t in edges}
    result = {}
    for a, b in pairwise(sorted(points | set(window))):
        active = {
            p for p, spans in phases.items() if any(x < b and y > a for x, y in spans)
        }
        state = "mixed" if len(active) > 1 else next(iter(active), "idle")
        result.setdefault(state, []).append((a, b))
    return result


def attribute_samples(points, intervals, linear=False):
    """Integrate adjacent samples without extrapolation or bridging missing values."""
    intervals = union(intervals)
    total, covered, maxima = 0, 0, []
    for (a, va), (b, vb) in pairwise(sorted(points)):
        # At 1 Hz, a gap beyond 1.5 periods is uncovered, not interpolated.
        if None in (va, vb) or not 0 < b - a <= 1.5:
            continue
        for start, end in intervals:
            lo, hi = max(start, a), min(end, b)
            if hi > lo:
                left = va + (vb - va) * (lo - a) / (b - a) if linear else va
                right = va + (vb - va) * (hi - a) / (b - a) if linear else va
                total += (left + right) / 2 * (hi - lo)
                covered += hi - lo
                maxima.extend((left, right))
    for t, v in points:
        if v is not None and any(a <= t <= b for a, b in intervals):
            maxima.append(v)
    duration = sum(b - a for a, b in intervals)
    avg = total / covered if covered else None
    coverage = covered / duration if duration else 0
    return avg, max(maxima, default=None), coverage, total


def classify_devices(text, links):
    gpu_uuid = links["nvidia_smi"].split(",")[0].strip()
    devices = json.loads(links["rbln_smi"])["devices"]
    pci = {d["pci"]["bus_id"].lower(): f"npu{d['npu']}" for d in devices}
    result = {}
    for sample in server.samples(text):
        labels = sample.labels
        if sample.name == "all_smi_gpu_info":
            uuid = labels["gpu_uuid"]
            role = pci.get(labels.get("pci_bus_id", "").lower())
            role = "gpu" if uuid == gpu_uuid else role
            if role:
                result[uuid] = role
    return result


def read_samples(collected, links, window):
    series = {(d, k): [] for d in DEVICES for k in DEVICE_METRICS}
    series.update({("system", k): [] for k in ("cpu", "memory")})
    names = {"all_smi_" + v: k for k, v in DEVICE_METRICS.items()}
    names.update(all_smi_cpu_utilization="cpu", all_smi_memory_used_bytes="memory")
    for row in collected:
        t = row["mono_ns"] / 1e9
        if row["endpoint"] != "all-smi" or not window[0] <= t <= window[1]:
            continue
        values = {}
        if row["status"] == 200:
            roles = {None: "system", **classify_devices(row["text"], links)}
            for sample in server.samples(row["text"]):
                role = roles.get(sample.labels.get("gpu_uuid"))
                key = role, names.get(sample.name)
                if key in series:
                    values[key] = sample.value
        for key, points in series.items():
            points.append((t, values.get(key)))
    return series


def phase_intervals(rows, ids, spans, events, anchors, trace):
    phases = {d: {} for d in DEVICES}

    def add(role, phase, a, b):
        phases[ROLE_DEVICE.get(role, role)].setdefault(phase, []).append((a, b))

    def mono(ns):
        anchor = min(anchors, key=lambda x: abs(x["time_ns"] - ns))
        return (ns - anchor["time_ns"] + anchor["monotonic_ns"]) / 1e9

    for role, names in ids.items():
        for row in rows:
            if row["request_id"] not in names:
                continue
            rid = expected.server_request_id(row["request_id"])
            send, first, end = (
                row[k + "_monotonic"]
                for k in ("actual_send", "first_output", "completed")
            )
            if trace:
                span = spans.get(role, {}).get(rid)
                if span is None:
                    continue
                # vLLM 0.22 output_processor.py:730-747: span arrival + TTFT.
                first = mono(span["start"]) + span["gen_ai.latency.time_to_first_token"]
                send = first - span["gen_ai.latency.time_in_model_prefill"]
                end = first + span["gen_ai.latency.time_in_model_decode"]
            if not role.startswith("decode"):
                add(role, "prefill", send, first)
            if role != "prefill":
                add(role, "decode", first, end)
        starts = {
            e["req_id"]: e["monotonic_ns"]
            for e in events.get(role, [])
            if e["kind"] == "kv_xfer_start"
        }
        for event in events.get(role, []):
            if event["kind"] == "kv_xfer_done" and event["req_id"] in starts:
                begin = starts[event["req_id"]] / 1e9
                add(role, "kv_transfer", begin, event["monotonic_ns"] / 1e9)
            if event["kind"] == "kv_h2d":
                add(role, "layout", event["start_ns"] / 1e9, event["end_ns"] / 1e9)
    return phases


def request_phase_share(rows, ids, spans, transfers, trace):
    requests = {}
    source = "spans+events" if trace else "requests.jsonl"
    status = "measured" if trace else "estimated"
    for row in filter(expected.request_succeeded, rows):
        rid = expected.server_request_id(row["request_id"])
        duration = row["completed_monotonic"] - row["actual_send_monotonic"]
        first = row["first_output_monotonic"] - row["actual_send_monotonic"]
        parts = dict(first_token=first, after_first_token=duration - first)
        roles = [r for r, names in ids.items() if row["request_id"] in names]
        if trace:
            parts = {k: [] for k in server.LATENCIES}
            for role in roles:
                span = spans.get(role, {}).get(rid, {})
                for key, attr in server.LATENCIES.items():
                    excluded = {
                        "prefill": ("decode0", "decode1"),
                        "decode": ("prefill",),
                    }
                    if role not in excluded.get(key, ()):
                        parts[key].append(span.get("gen_ai.latency." + attr))
            parts = {k: sum(v) if None not in v else None for k, v in parts.items()}
            for role in (r for r in roles if r.startswith("decode")):
                event = transfers[role]["requests"].get(rid, {})
                for key in ("kv", "h2d", "reorder"):
                    parts[key] = event.get(key, {}).get("value")
            parts["other"] = (
                duration - sum(parts.values()) if None not in parts.values() else None
            )
        ratios = None
        if None not in parts.values():
            ratios = {k: v / duration for k, v in parts.items()}
        requests[row["request_id"]] = metric(ratios, "ratio", source, status=status)
    values = [node["value"] for node in requests.values()]
    summary = None
    if values and None not in values:
        summary = {k: mean(v[k] for v in values) for k in values[0]}
    return dict(
        requests=requests, summary=metric(summary, "ratio", source, status=status)
    )


def phase_resources(series, phases, window, trace):
    system, ratios, rows = {}, {}, []
    status = "measured" if trace else "estimated"
    source = "spans+events" if trace else "requests.jsonl"
    for device, parts in phases.items():
        ratios[device] = {}
        for phase, intervals in parts.items():
            system.setdefault(phase, []).extend(intervals)
            ratios[device][phase] = metric(
                active_ratio(intervals, window), "ratio", source, status=status
            )
    states = {
        d: device_states(p, window) for d, p in dict(phases, system=system).items()
    }
    for (device, name), points in series.items():
        unit = "W" if name == "power" else "bytes" if name == "memory" else "%"
        for state, intervals in dict(states[device], all=[window]).items():
            avg, maximum, coverage, _ = attribute_samples(points, intervals)
            value = dict(mean=avg, max=maximum) if avg is not None else None
            node = metric(
                value, unit, server.SERIES, status="estimated", coverage=coverage
            )
            rows.append(dict(device=device, state=state, metric=name, **node))
    return dict(samples=rows, device_phase_active_ratio=ratios)


def energy_efficiency(power, window, tokens):
    result, valid = {}, []
    for device in (*DEVICES, "total"):
        coverage, reason = 0, "missing_device"
        if device != "total":
            points = [
                (t, v) for t, v in power.get(device, []) if window[0] <= t <= window[1]
            ]
            _, _, coverage, energy = attribute_samples(points, [window], linear=True)
            reason = "coverage_below_80_percent"
            if sum(v is not None for _, v in points) < 2:
                reason = "insufficient_power_samples"
            energy = energy if coverage >= 0.8 and len(points) >= 2 else None
            if energy is not None:
                valid.append((energy, coverage))
        else:
            energy = sum(e for e, _ in valid) if len(valid) == 3 else None
            coverage = min((c for _, c in valid), default=0)
        per_token = energy / tokens if energy is not None and tokens else None
        efficiency = tokens / energy if energy else None
        values = dict(
            energy_j=(energy, "J"),
            energy_per_output_token_j_est=(per_token, "J/token"),
            tok_per_s_per_w_est=(efficiency, "tokens/s/W"),
        )
        result[device] = {
            k: metric(v, u, server.SERIES, reason, "estimated", coverage=coverage)
            for k, (v, u) in values.items()
        }
    return result
