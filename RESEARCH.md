# Research and guidance boundary

The design uses a shared HTTP handler/transport instrumentation point, then checks whether fixed success/error requests remain linked across processes. Runtime behavior comes from the copied OpenTelemetry source and observed contract, not from a research citation.

## Peer-reviewed research: X-Trace

Rodrigo Fonseca, George Porter, Randy H. Katz, Scott Shenker and Ion Stoica, *X-Trace: A Pervasive Network Tracing Framework*, NSDI 2007, pp. 271–284: [USENIX proceedings entry](https://www.usenix.org/conference/nsdi-07/x-trace-pervasive-network-tracing-framework) and [original paper](https://static.usenix.org/event/nsdi07/tech/full_papers/fonseca/fonseca_html/index.html).

The original paper's introduction and Section 2 explain propagating a common task identifier along the actual request path and retaining causal links for later reconstruction. Its acknowledgments identify the NSDI reviewers. This is the reviewed research background for checking the operation → HTTP client → HTTP server links in this example. The missing-extraction control tests a specific broken link; the empty-export control prevents missing observations from being accepted as successful correlation.

X-Trace modifies multiple protocols and uses its own metadata/reporting architecture. This repository uses OpenTelemetry TraceContext at one HTTP boundary; it does not implement X-Trace, reproduce its deployments or demonstrate automatic fault diagnosis. The paper does not validate the synthetic baggage privacy contract. That contract is supported by the observed local tests and the official guidance below.

## Supplementary technical report: Dapper

Sigelman et al., *Dapper, a Large-Scale Distributed Systems Tracing Infrastructure*, Google, Inc. (2010): [official publication page](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/).

The inspected official abstract describes instrumentation at a small number of common libraries, sampling and tools used by developer/operations teams. It is background for choosing shared handler/transport instrumentation points. It does not establish this example's deployment scale, overhead, privacy protection, incident repair or customer outcomes.

The official page identifies Google, Inc. (2010), without a peer-reviewed venue. Dapper is therefore supplementary technical-report background here, not peer-reviewed research evidence. Read boundary: the official title, authors, year and abstract were read. The full linked PDF was not read; no paper-body-specific claim is adopted.

## Propagation and collection guidance

Official [OpenTelemetry baggage guidance](https://opentelemetry.io/docs/concepts/signals/baggage/) explains header propagation and explicit promotion into telemetry. Official [sensitive-data guidance](https://opentelemetry.io/docs/security/handling-sensitive-data/) supports reviewing emitted data and minimizing collection. These sources support the specific propagation/collection boundary exercised here; they do not turn its synthetic sentinel checks into general PII protection.

See [PROVENANCE.md](PROVENANCE.md) for the actual source and [VERIFICATION.md](VERIFICATION.md) for measured local outcomes and limits.
