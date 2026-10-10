# OTel Incident Sandbox

A local Go example for engineers who want to keep a support request traceable while excluding customer baggage at the HTTP propagation boundary. It exercises one successful request and one injected HTTP 503 in separate client/server processes, using a copied OpenTelemetry HTTP handler and transport.

The recorded positive contract has **four client spans and two server spans**, with matching trace and parent links. HTTP 200 leaves HTTP span status Unset; HTTP 503 records Error. Synthetic customer email/token baggage is absent from post-injection outbound headers and exported spans/logs. The three deliberately broken variants must be rejected.

The [run procedure](#try-the-example) exercises the copied instrumentation through the adapted client and server. Read the [verification contract](VERIFICATION.md) for each positive and negative case, then use the [repository map](#repository-map) to inspect the source and its derivation.

## Try the example

The observed environment is Linux, Go 1.27.2 and Python 3.12.3. Python needs only its standard library. Put an existing Go executable on PATH, or supply `--go /path/to/go`. Go fetches the exact dependencies pinned in [example/go.mod](example/go.mod) and [example/go.sum](example/go.sum); no Docker or external telemetry backend is required. The normal GOPROXY environment setting is honored.

From the repository root, choose a new directory outside the repository:

```sh
python3 verification/run.py --work-dir ../otel-incident-sandbox-run
```

The entry point refuses an existing work directory. It creates a fresh module/build cache, builds the copied example, runs the positive contract and three negative controls, verifies modules and checks teardown. Results stay in that work directory. A successful overall run exits 0; the three negative checker exits of 1 are expected. The server binds only `127.0.0.1`, and all listeners/processes have bounded lifetimes.

## Repository map

| Path | Start here for |
| --- | --- |
| [example/client/client.go](example/client/client.go), [example/server/server.go](example/server/server.go) | The adapted support-request example and loopback lifecycle |
| [upstream/instrumentation/net/http/otelhttp](upstream/instrumentation/net/http/otelhttp) | Complete, unchanged 46-file HTTP instrumentation module, including its original example/tests |
| [verification/run.py](verification/run.py), [verification/verifier.py](verification/verifier.py) | Linux portability adapter and retained acceptance/negative-control verifier |
| [VERIFICATION.md](VERIFICATION.md), [verification/evidence](verification/evidence) | Observed results and sanitized source-only receipts |
| [PROVENANCE.md](PROVENANCE.md), [source-manifest.json](source-manifest.json) | Immutable source version, hashes, derivation and license boundaries |
| [RESEARCH.md](RESEARCH.md) | Narrow research/guidance mapping and read boundary |

## Scope

This is a synthetic loopback demonstration of one baggage collection/propagation boundary. It does not establish general PII protection, incident repair, production readiness, full upstream regression coverage, remote CI, customer use or revenue. Sampling is fixed for deterministic demonstration rather than production policy.

The unchanged implementation and modified Go derivatives keep their original licenses/notices. MIT applies only to task-authored glue and documentation; see [NOTICE](NOTICE), [LICENSE](LICENSE) and the complete [upstream/LICENSE](upstream/LICENSE).
