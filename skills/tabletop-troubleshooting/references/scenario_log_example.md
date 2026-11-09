# Troubleshooting Scenario Log

One row per completed scenario, newest first, coded against the Troubleshooting Scenario Option Space. The roller parses the Coordinates column, so keep its format exact: `D · R W S G E F · L M T N C I · Y B O A X`, with `?` for an unspecified value and `+` joining two values on one axis.

| Date | Scenario | Coordinates | Root cause |
| --- | --- | --- | --- |
| 2026/11/05 | payments paging gap | `D17 · R18 W? S? G5 E? F7 · L12 M14 T2 N11 C1 I1 · Y12 B? O4 A8 X1` | Paging threshold raised during a noisy week and never restored; real outages stopped paging anyone |
| 2026/11/02 | session-cache restart herd | `D2 · R12 W1 S2 G2 E3 F3 · L9 M3+M6 T8 N3 C5 I2 · Y1 B7 O1 A7 X3` | Redis maxmemory set too low; restarting it emptied the cache and the reconnect herd flattened the primary database |
| 2026/10/27 | ci-runner pool stalls | `D10 · R3 W4 S2 G2 E9 F5 · L3+L12 M2+M9 T5 N7 C4 I1 · Y8 B3 O6 A1 X1` | Two separate faults at once: old-image runners ran out of inodes in /tmp, and an expired registry token failed every fetch |
| 2026/10/21 | catalog-api latency | `D2 · R13 W1 S4 G2 E? F3 · L12 M4 T1 N9 C1 I2 · Y1 B1 O1 A1 X1` | Analytics ETL pointed at a production Postgres replica; disk saturation and page-cache churn |
| 2026/10/14 | ingest-worker Kafka lag | `D1 · R19 W5 S1 G2 E? F1 · L9+L12 M2 T2 N9 C2 I5 · Y7 B2 O1 A1 X1` | Debug logging left on, plus logrotate unlinking the live log without a reopen signal; disk full |
| 2026/10/06 | orders-api canary 5xx | `D2 · R1 W1 S1 G2 E? F1 · L7 M2 T1 N1 C1 I1 · Y2 B3 O1 A1 X1` | New SDK built an HTTP client per request; ephemeral port exhaustion |
| 2026/09/18 | checkout-api via payments-gw | `D2 · R1 W1 S1 G2 E? F3 · L7 M2 T1 N1 C1 I1 · Y1 B4 O1 A1 X1` | Per-request HTTP client flooded the conntrack table; silent SYN drops |
| 2026/09/11 | feed-ingest us-west-2 | `D3 · R24 W3 S1 G4 E2 F4 · L5 M14 T7 N5 C3 I1 · Y2 B6 O1 A1 X7` | Path MTU black hole: low-MTU hop plus filtered ICMP fragmentation-needed |
| 2026/09/11 | checkout-api payments | `D2 · R1 W1 S1 G2 E3 F3 · L7 M7 T1 N3 C1 I1 · Y1 B4 O1 A1 X1` | Redis client kept a pooled connection to a rescheduled pod's dead IP |
| 2026/09/09 | api-07 health checks | `D2 · R1 W1 S1 G2 E? F1 · L7 M1 T4 N3 C1 I1 · Y2 B1 O1 A1 X1` | CLOSE\_WAIT leak poisoned the pool after a database failover |
