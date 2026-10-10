# Source and derivation

Use this page to distinguish the copied implementation, adapted example and verification glue. The active example imports the local copied `otelhttp` module; a remote package with the same declared version is not the selected source.

## Immutable source

Source repository: [OpenTelemetry Go contrib](https://github.com/open-telemetry/opentelemetry-go-contrib). Immutable commit: [`33d034d81ab04b64c460717c5f42080324ca281f`](https://github.com/open-telemetry/opentelemetry-go-contrib/commit/33d034d81ab04b64c460717c5f42080324ca281f).

The entire `instrumentation/net/http/otelhttp/` subtree is retained under `upstream/`: 46 tracked files, plus the complete root LICENSE, for 47 entries. Internal helpers, filters, original examples and tests remain together. [source-manifest.json](source-manifest.json) records each original Git blob ID, Git mode, byte count, SHA-256 and pinned source URL. All recorded source modes are `100644`; filesystem permission presentation is separate from Git mode.

The full [upstream/LICENSE](upstream/LICENSE) is 12,892 bytes and has SHA-256 `1ae07514be1d7bb33f0698f8d91fb51b8b9fe1463157ec1c72081a49b9bc6f40`. It retains Apache-2.0 text and the Go Authors BSD notice. Upstream files are byte-identical; inherited upstream documentation retains its original monorepo context.

## Adapted example

The active `example/` was copied from the inspected upstream example through the accepted private adaptation. Client/server changes are limited to the fixed support-request cases, TraceContext-only propagation, header evidence and bounded loopback/process lifecycle. The source files retain OpenTelemetry copyright/SPDX headers and prominent modification notices. The module's only functional configuration change is a relative replacement of otelhttp with the staged copy; dependency versions and go.sum remain pinned.

[verification/derivation.json](verification/derivation.json) binds the accepted and curated source hashes. The retained verifier SHA-256 is `95c31b21c5a28ef030e7621a0417242c5c4a2859483e2dbe06c70e75cf17f951`; its checking and mutation semantics are unchanged.

## Portable verification layout

The adapter makes the verifier's compatibility layout in a fresh external work directory: an original snapshot, links to the repository's single copied module, the adapted example, fresh caches and build outputs. Both positive executables resolve the implementation back to this repository's `upstream/` tree. The compatibility file named baseline-runtime.json supplies environment metadata only; the entry point does not rerun the prior original/copy test suite.

The prior original and unchanged-copy module baselines passed five selected upstream tests with HTTP status subcases. The adapted two-process contract and the fresh portability execution are separate observed stages, described in [VERIFICATION.md](VERIFICATION.md).

## License boundaries

The copied implementation and modified example derivatives retain Apache-2.0 notices and the complete applicable upstream license, including its BSD notice. [LICENSE](LICENSE) covers task-authored portability/verification glue and documentation under MIT; it does not relicense the copied implementation or Go derivatives. [NOTICE](NOTICE) states attribution and modifications. SDK/exporter dependencies remain normal checksum-pinned Go dependencies and are not claimed as copied implementation.
