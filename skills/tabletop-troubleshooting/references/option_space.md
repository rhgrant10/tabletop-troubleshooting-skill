# Troubleshooting Scenario Option Space

Nov 8, 2026 · @Robert

## How to use

A scenario is one value per axis, written as a coordinate string. Example: `D2 · R2 W1 S1 G3 E3 F3 · L12 M9 T5 N7 C3 I1 · Y14 B8 O4 A1 X6` is an auth service whose token-signing cert expired during a change freeze, seen as permission errors everywhere except in auth itself.

1. **Pin the domain (D)** in the session config. It decides the toolkit, so it is not rolled. Any other axis can also be pinned.
2. **Roll the rest in a fixed order**: A first, then Tier 1 (R W S G E F), Tier 2 (L M T N C I) and Tier 3 (Y B O X). Each roll is conditioned on the ones before it.
3. **Use a real random source**: code execution or numbers the user supplies. Model-chosen "random" picks drift back to the canonical incident.
4. **Coverage mode**: weight each value inversely to how often it appears in the scenario log. Never reuse a layer + mechanism pair (L + M) already in the log.
5. **Apply the coherence rules** below. The roller enforces them: Hard rules filter the candidates, Prefer and Avoid rules set the weights, so no rerolls are needed. If the writer finds a combination impossible that no rule caught, it rerolls that one axis and proposes a new Hard rule for this doc.
6. **Record the coordinates** in the debrief, and append a row to the scenario log.

Difficulty levers, if you want to steer rather than roll: degraded evidence (O2–O9), multiple causes (C2–C6), a foundational dependency (G3), or a fault far from the symptom (F2, F5–F8).

## Tier 0 — Domain (D), set in session config

The domain picks the investigator's toolkit and mental model, not where the root cause lives. Drill format says how evidence is handed over: **commands** (you query, I return output), **snippets** (code or config is part of the evidence), or **interviews** (you question stakeholders).

| Code | Domain | Examples | Drill format |
| --- | --- | --- | --- |
| D1 | Linux host / OS internals | scheduler, memory reclaim, fds, cgroups, filesystems | commands |
| D2 | Distributed systems / services | dependencies, retries, pools, consistency, cascades | commands |
| D3 | Networking | BGP, routing, L2/VLANs, MTU, load balancers, NAT, CDNs, Wi-Fi | commands |
| D4 | Storage and filesystems | RAID, NFS/GPFS, block devices, SSD wear, quotas | commands |
| D5 | Databases | query plans, locks, replication lag, vacuum/compaction, connection limits | commands |
| D6 | Performance engineering | profiling, flame graphs, nothing broken but slow | commands |
| D7 | GPU / HPC / ML infrastructure | NCCL hangs, stragglers, InfiniBand, GPU Xid errors, data loaders | commands |
| D8 | Single-process debugging | leaks, deadlocks, races, crashes and core dumps | snippets + commands |
| D9 | Language runtimes | Python GIL, JVM GC, Go scheduler, Node event loop | snippets + commands |
| D10 | Build systems, toolchains, CI | dependency resolution, linkers, reproducibility, flaky tests | snippets + commands |
| D11 | Security incidents | intrusion forensics, leaked credentials, lateral movement | commands |
| D12 | Data correctness and pipelines | wrong dashboard numbers, schema drift, duplicates, late data | commands + snippets |
| D13 | Cloud control plane and IaC | IAM, Terraform drift, quotas, managed-service limits | commands |
| D14 | Clients (frontend, mobile) | browser and app crashes, version skew, CDN caching | snippets + commands |
| D15 | Hardware, firmware, embedded | device fleets, firmware bugs, thermal, power, sensors | commands |
| D16 | Cost / FinOps | bill spikes, egress, idle capacity, runaway jobs | commands |
| D17 | Sociotechnical | flaky-CI trust erosion, alert fatigue, ownership gaps | interviews |

## Tier 1 — System context

These axes fix what the system is and where it runs, before anything breaks. R, W, S, G and E describe the component where the fault lives; F says where that component sits relative to the symptom.

### R — Functional role (what it does for others)

| Code | Role | Notes |
| --- | --- | --- |
| R1 | Business API / backend service | the default; under-weight it |
| R2 | Auth / identity | token issuing, LDAP, Kerberos, mTLS cert issuing |
| R3 | CI/CD and build | runners, build caches, deploy orchestration |
| R4 | Artifact / package repository | Artifactory, mirrors, container registries |
| R5 | DNS | resolvers, authoritative servers, caching |
| R6 | Service discovery / registry | Consul, k8s endpoints, sidecar config |
| R7 | Config, feature flags, secrets distribution | Vault, flag services, config push |
| R8 | Scheduler / orchestrator | k8s control plane, Slurm, GPU schedulers |
| R9 | Load balancer / proxy / API gateway | L4 and L7 balancing, TLS termination |
| R10 | Rate limiter / quota service | shared counters, token buckets |
| R11 | Queue / broker | Kafka, RabbitMQ, SQS, MQTT |
| R12 | Cache | Redis, memcached, CDN-style caches |
| R13 | Primary datastore | relational or NoSQL system of record |
| R14 | Object storage | S3-style blob stores |
| R15 | Shared / parallel filesystem | NFS, GPFS, Lustre |
| R16 | Time sync | NTP, PTP |
| R17 | CDN / edge | edge caches, edge compute |
| R18 | Observability pipeline | log shipping, metrics, tracing collectors |
| R19 | Data pipeline / ETL | batch transforms, warehouse loads |
| R20 | ML training | distributed training jobs, checkpointing |
| R21 | ML inference / serving | model servers, GPU batching |
| R22 | Device-fleet backend | telemetry ingest, command and control |
| R23 | External / third-party dependency | you are the client of someone else's system |
| R24 | Network fabric / transit | routers, switches, interconnects, VPNs, carrier links |

### W — Workload profile (what the SLO is measured on)

| Code | Profile | What "broken" looks like |
| --- | --- | --- |
| W1 | Latency-sensitive interactive | p99 up |
| W2 | Hard real-time / low jitter | microsecond budgets missed; jitter is the bug |
| W3 | Throughput / bulk transfer | bytes per second down |
| W4 | Batch with deadline | job misses its window |
| W5 | Nearline / streaming | consumer lag grows |
| W6 | Offline / analytics | wrong or late results, cost |
| W7 | Fan-out / scatter-gather | slowest backend sets the tail |
| W8 | Long-lived connections | websockets, gRPC streams; rebalancing pain |
| W9 | Spiky / bursty | flash crowds, top-of-hour cron load |
| W10 | Write-heavy ingest | backpressure, write amplification |
| W11 | Human-interactive tooling | developer shells, IDEs, CLIs feel slow |

### S — State model

| Code | Model | Effect on mitigation |
| --- | --- | --- |
| S1 | Stateless | restart and roll back freely |
| S2 | Rebuildable cache / derived state | restart costs a cold-cache period |
| S3 | Single stateful primary | restart is an outage |
| S4 | Primary + replicas | failover available, may lose writes |
| S5 | Sharded / partitioned | hot shards, rebalancing |
| S6 | Consensus / quorum | losing quorum stops writes |
| S7 | Multi-region active-active | conflicts, divergence |
| S8 | State held at the edge | devices or browsers hold state you can't reach |

### G — Position in the dependency graph

| Code | Position | Investigation effect |
| --- | --- | --- |
| G1 | Leaf | symptom sits on the broken thing |
| G2 | Mid-tier | symptom one or two hops away |
| G3 | Foundational | everything except the broken thing looks broken |
| G4 | External | you can't inspect it, only probe it |
| G5 | Debugging infrastructure itself | the tools you'd use are the broken thing |

### E — Environment

| Code | Environment | Notes |
| --- | --- | --- |
| E1 | Bare metal | full access, real hardware faults |
| E2 | VMs | steal time, hypervisor, live migration |
| E3 | Containers on Kubernetes | cgroups, rescheduling, overlay networking |
| E4 | Managed cloud service | no host access; provider metrics only |
| E5 | Serverless | cold starts, concurrency limits, no host |
| E6 | HPC / GPU cluster | InfiniBand, parallel FS, batch scheduler |
| E7 | Remote device fleet | embedded Linux on drones, POS, vehicles, edge boxes |
| E8 | Hybrid / multi-cloud | interconnects, split control planes |
| E9 | Developer machines / CI runners | heterogeneous, ephemeral |

### F — Fault location (relative to where the symptom shows)

| Code | Location |
| --- | --- |
| F1 | The service under suspicion |
| F2 | An upstream caller or client |
| F3 | A downstream dependency |
| F4 | The path between (network, proxy, carrier, broker) |
| F5 | The host or platform underneath (kernel, hypervisor, node) |
| F6 | The control or management plane (orchestrator, config, deploy tool) |
| F7 | The observer (monitoring, health checks, the tool itself) |
| F8 | An external party |

## Tier 2 — The fault

These axes define what is actually true about the incident. The scenario writer keeps this hidden and keeps every output consistent with it.

### L — Root-cause layer

| Code | Layer | Examples |
| --- | --- | --- |
| L1 | Hardware | failing disk, ECC memory errors, NIC faults, thermal throttling, power |
| L2 | Firmware / drivers | NIC offload bugs, RAID controller cache, GPU driver |
| L3 | Kernel | memory reclaim, writeback, scheduler, net stack, fd/PID/inode limits |
| L4 | Virtualization / container runtime | cgroup throttling, overlayfs, steal time, live migration |
| L5 | Network infrastructure | routing, MTU, load balancer, NAT, firewall, conntrack |
| L6 | Language runtime | GC pauses, thread pools, event loop blocking, GIL, CPU-count detection |
| L7 | Library / SDK | client pools, retry logic, TLS libraries, serializers |
| L8 | Application logic | the team's own code |
| L9 | Configuration | timeouts, limits, flags, routing rules |
| L10 | Data | poison message, hot key, skew, schema change, size growth |
| L11 | External service behavior | provider change, partner rate limits, upstream API semantics |
| L12 | Process / human | manual change, cron, expired credential, incident leftovers |

### M — Mechanism (failure dynamics)

| Code | Mechanism | Examples |
| --- | --- | --- |
| M1 | Resource leak | memory, fds, goroutines, connections; gradual |
| M2 | Hard-limit exhaustion | ports, conntrack, inodes, PIDs, quotas; a cliff |
| M3 | Saturation / queueing | capacity exceeded, queues grow |
| M4 | Contention | locks, hot partitions, noisy neighbors |
| M5 | Metastable feedback loop | retry storms, GC death spirals; persists after the trigger is gone |
| M6 | Thundering herd / synchronization | aligned crons, reconnect storms, synchronized retries |
| M7 | Stale state | stale connections, cached DNS, old config or routes |
| M8 | Consistency / split-brain / ordering | divergent replicas, out-of-order events |
| M9 | Time and expiry | clock skew, cert or token expiry, TTLs, timeout mismatches, DST |
| M10 | Race / concurrency bug | rare interleavings, double-processing |
| M11 | Cascading failure | overload spreading across services |
| M12 | Silent corruption | bit flips, torn writes, encoding bugs |
| M13 | Misdirection | traffic, jobs or writes sent to the wrong target |
| M14 | Gray failure | degraded but passing health checks: slow disk, lossy link |
| M15 | Deliberate throttling | cgroup CPU quota, API rate limits, IOPS caps |

### T — Temporal shape

| Code | Shape |
| --- | --- |
| T1 | Sudden step |
| T2 | Gradual drift (hours to weeks) |
| T3 | Periodic |
| T4 | Intermittent / random |
| T5 | Latent bomb (threshold, date, counter) |
| T6 | Flapping / oscillating |
| T7 | Conditional (only under a specific load, input or path) |
| T8 | Post-recovery (appears when things come back) |

### N — Trigger

| Code | Trigger |
| --- | --- |
| N1 | Code deploy |
| N2 | Config or feature-flag change |
| N3 | Infra event (failover, reschedule, node replacement, maintenance) |
| N4 | Traffic change (growth, spike, new client) |
| N5 | Dependency change (upgrade, provider-side change) |
| N6 | Data change (growth past a threshold, new shape) |
| N7 | Passage of time |
| N8 | Physical environment (temperature, power, RF) |
| N9 | Human one-off action |
| N10 | Adversarial action |
| N11 | None identifiable (always broken, newly noticed) |

### C — Cause structure

| Code | Structure |
| --- | --- |
| C1 | Single cause |
| C2 | Two interacting causes, both required |
| C3 | Single cause plus a coincident red-herring change |
| C4 | Two independent concurrent incidents |
| C5 | The mitigation sets off a second failure |
| C6 | Cause already gone; only effects remain |

### I — Impact type

| Code | Impact |
| --- | --- |
| I1 | Availability (errors, down) |
| I2 | Performance (slow) |
| I3 | Correctness (wrong answers) |
| I4 | Durability (data lost) |
| I5 | Freshness (stale data) |
| I6 | Duplication / idempotency |
| I7 | Security / confidentiality |
| I8 | Cost / efficiency |

## Tier 3 — Presentation and investigation

These axes decide what the investigator sees first, what evidence they can trust, and what they are allowed to do. A rolls first, right after the domain, because the assignment shapes everything else.

### Y — First symptom

| Code | Symptom |
| --- | --- |
| Y1 | Latency up |
| Y2 | Error rate up |
| Y3 | Can't connect / timeouts |
| Y4 | Hang: no errors, no progress |
| Y5 | Crash loop, restarts, OOM kills |
| Y6 | Throughput drop |
| Y7 | Lag or backlog growing |
| Y8 | Job late, stuck or missed its deadline |
| Y9 | Wrong or missing data, reported by someone |
| Y10 | Resource alert, no user impact yet |
| Y11 | Cost spike |
| Y12 | Dashboards green, customer says broken |
| Y13 | Flaky tests or build failures |
| Y14 | Auth failures / permission denied |
| Y15 | Devices go quiet (telemetry gap) |
| Y16 | Security alert / anomalous activity |

### B — Blast-radius shape

| Code | Shape |
| --- | --- |
| B1 | One host or instance |
| B2 | A handful of hosts, no obvious pattern |
| B3 | Subset sharing a hidden attribute (kernel, hardware SKU, rack, image) |
| B4 | Subset of requests (key, tenant, hash, endpoint, payload size) |
| B5 | One customer or tenant |
| B6 | One region or AZ |
| B7 | Whole fleet or service |
| B8 | Everyone except the broken thing |
| B9 | One client type or version |

### O — Evidence quality

| Code | Evidence |
| --- | --- |
| O1 | Rich and trustworthy |
| O2 | Aggregates hide it (averages, p50 only) |
| O3 | A key metric is missing |
| O4 | A signal lies (health check passes, monitoring broken) |
| O5 | Logs only, no shell |
| O6 | Ephemeral evidence (rotation, restarts, rescheduling) |
| O7 | Delayed or sampled telemetry |
| O8 | Conflicting human reports |
| O9 | Tampered evidence |

### A — Assignment (the investigator's job)

| Code | Assignment |
| --- | --- |
| A1 | Live incident response |
| A2 | Performance investigation, no incident |
| A3 | Post-incident forensics |
| A4 | Recurrence: "it came back" |
| A5 | Pre-mortem / design review: "how does this break?" |
| A6 | Capacity or limits investigation |
| A7 | Mid-incident handoff; the previous responder's changes muddy the evidence |
| A8 | Customer escalation / support ticket |

### X — Mitigation constraints

| Code | Constraint |
| --- | --- |
| X1 | Unconstrained |
| X2 | No rollback (migration, irreversible writes) |
| X3 | Restart loses state or warm caches |
| X4 | Failover riskier than waiting |
| X5 | Safety or physical constraint |
| X6 | Change freeze or approval gate |
| X7 | Limited access (vendor-owned, managed service) |
| X8 | Mitigation needs capacity you don't have |
| X9 | Evidence must be preserved (legal, security) |

## Coherence rules

Hard rules rule out impossible combinations; Prefer and Avoid rules only shift odds, because improbable incidents are real and often the most instructive. Writer rules constrain how the scenario is written, not what is rolled.

The roller reads this table, so the If and Then columns use a fixed syntax:

- **If**: one or more clauses `AXIS in {values}`, joined by `and` or `or`.
- **Then, Hard**: `AXIS in {values}` restricts that axis; `skip AXES` leaves those axes unrolled and overrides other rules on them; `extra AXES` rolls one more distinct value on each.
- **Then, Prefer / Avoid**: `{values}` multiplies their weights by 3 or 0.25.
- **Then, Writer**: prose, an obligation on the scenario text.

Axes roll in the order A, then R W S G E F, then L M T N C I, then Y B O X, so a rule may only constrain an axis that rolls after its If clauses. If Hard rules leave an axis with no candidates, the roller backtracks one axis and rerolls it.

| If | Then | Type |
| --- | --- | --- |
| `W in {W4}` | `Y in {Y6,Y8,Y9,Y11}` | Hard |
| `I in {I3,I4,I5,I6}` | `Y in {Y9,Y10,Y12}` | Hard |
| `G in {G3}` | `B in {B8}` | Hard |
| `G in {G3}` | `F in {F3}` | Hard |
| `G in {G4} or F in {F8}` | `X in {X7}` | Hard |
| `G in {G5} or F in {F7} or R in {R18}` | `O in {O4}` | Hard |
| `A in {A5}` | `skip Y,B,O` | Hard |
| `A in {A3}` | `X in {X1,X7,X9}` | Hard |
| `C in {C4}` | `extra L,M` | Hard |
| `C in {C5}` | `extra M` | Hard |
| `R in {R23}` | `G in {G4}` | Hard |
| `G in {G1}` | `F in {F1}` | Hard |
| `G in {G4}` | `F in {F4,F8}` | Hard |
| `G in {G1,G2,G4,G5}` | `B in {B1,B2,B3,B4,B5,B6,B7,B9}` | Hard |
| `S in {S1}` | `{X2}` | Avoid |
| `S in {S3,S6}` | `{X1}` | Avoid |
| `E in {E4,E5}` | `{L1,L2,L3,L4}` | Avoid |
| `A in {A1}` | `{N11}` | Avoid |
| `W in {W5}` | `{Y7}` | Prefer |
| `I in {I8}` | `{Y11}` | Prefer |
| `E in {E7}` | `{O7,X2,X5,B3,N8}` | Prefer |
| `R in {R16}` | `{M9}` | Prefer |
| `M in {M5}` | `{C6}` | Prefer |
| `M in {M6}` | `{T3,T8}` | Prefer |
| `M in {M9}` | `{N7,T5}` | Prefer |
| `M in {M14}` | `{O2,O4,B1,B2,B3}` | Prefer |
| `T in {T5}` | `{N6,N7,B7}` | Prefer |
| `A in {A3}` | `{C6,O6}` | Prefer |
| `D in {D11}` | `{N10,I7,O9,X9}` | Prefer |
| `S in {S1} and X in {X2}` | Give a reason outside the code: bad data already written, or an external contract changed. | Writer |
| `E in {E4,E5}` | No host shell; evidence is provider metrics and logs. | Writer |
| `M in {M5}` | Mitigation must shed load, not just remove the trigger. | Writer |
| `A in {A5}` | Hand over a design; the rolled fault is what the investigator should find in it. | Writer |
| `D in {D17}` | Read Tier 2 as organizational dynamics; interviews replace commands. | Writer |

## Interview subset

Interview mode rolls uniformly over these values instead of using coverage weights; the domain still comes from config. Hard rules still apply and can force a value outside the subset. The subset is a judgment about typical SRE and Linux troubleshooting loops, not measured data, so edit it as you learn what your interviews actually ask.

| Axis | Interview values |
| --- | --- |
| A | `{A1,A2}` |
| R | `{R1,R5,R9,R11,R12,R13,R15}` |
| W | `{W1,W3,W4,W5}` |
| S | `{S1,S2,S3,S4}` |
| G | `{G1,G2,G3}` |
| E | `{E1,E2,E3}` |
| F | `{F1,F3,F4,F5}` |
| L | `{L3,L5,L6,L7,L8,L9,L10}` |
| M | `{M1,M2,M3,M4,M7,M9,M11}` |
| T | `{T1,T2,T3,T4}` |
| N | `{N1,N2,N3,N4,N6}` |
| C | `{C1,C3}` |
| I | `{I1,I2}` |
| Y | `{Y1,Y2,Y3,Y4,Y5,Y6,Y7,Y8,Y10}` |
| B | `{B1,B3,B4,B6,B7,B8}` |
| O | `{O1,O2,O3}` |
| X | `{X1,X3}` |

## Scenario log

Past scenarios and their coordinates live in Troubleshooting Scenario Log, which the roller reads for coverage weighting.
