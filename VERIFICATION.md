# Run and inspect the contract

Run the [Linux entry point](verification/run.py) as shown in [README.md](README.md). It executes two separate Go processes for each case and retains commands, process exits, outbound-header captures, exported spans/logs, module mapping, mutation diffs and teardown receipts outside the repository.

## Observed contract

| Case | Client/server spans | Checker exit | Observed checks |
| --- | ---: | ---: | --- |
| Positive | 4 / 2 | 0 | Both HTTP 200/503 cases, counts/kinds, status, root/client/server/wire joins and privacy pass |
| Baggage propagation plus attribute promotion | 4 / 2 | 1 | Header, received-baggage and exported-data privacy fail; status/counts/joins remain intact |
| Disabled server extraction | 4 / 2 | 1 | Correlation fails; privacy, counts and status remain intact |
| NeverSample empty export | 0 / 0 | 1 | Completeness, status and correlation fail; privacy alone still passes |

Two operation roots are named support.request. Each HTTP client span must join its root and exactly one remote-parent server span by trace/span IDs; the injected trace header must identify that client span. Both HTTP sides report Unset for 200 and Error for 503. Counts/status are mandatory, so discarding all spans cannot pass the full contract. The third control is NeverSample, not a wrapper-bypass experiment.

Privacy checks require no baggage key in post-injection outbound captures, false received-baggage flags at the server, and no synthetic email/token sentinel in exported spans or stdout/stderr logs. This is a fixed sentinel/propagation contract; it does not establish arbitrary PII handling in attributes, URLs, bodies or encodings.

## Portability and teardown

The fresh-cache entry point was executed on Linux with Go 1.27.2 and Python 3.12.3. Exact dependency versions/checksums come from the copied example module; go mod verify passed. The first fresh attempt stopped before application cases on WSL DNS/TLS errors. The corrected run used a newly acquired file proxy populated from the official Go module proxy; its module/build caches were fresh. The functional contract ran once. A later module-list query was completed after six pinned transitive metadata records were fetched, without rerunning the application cases. Direct HTTPS dependency fetching was not a successful observed route in this environment. Module inspection and both executed binary metadata records identify the local copied source. Original/copy source hashes are checked again by the retained verifier.

Every application process exited 0. Final owned-PID probes found no remaining application processes; all four recorded loopback listener ports returned connection refused. New disposable control source/binary directories were removed within the newly owned run directory. Their mutation diffs/hashes and run receipts remain retained. No existing artifact is deleted. No external collector, paid provider, global installation or AOE test is involved.

## Source-only evidence

[verification/evidence/index.json](verification/evidence/index.json) binds raw artifact hashes to sanitized files, including exact redaction positions/encoding forms. Host-specific path prefixes are replaced with named tokens; counts, IDs, statuses, exits, timestamps and hashes are preserved. Private prefix values are held separately so the original bytes can be reconstructed and checked. Binaries and caches are not distributed.

The prior original/copy baseline, private adapted result and independent retained-artifact review are preserved. The independent review verdict was PASS_WITH_SCOPE_LIMITS; it did not rerun the suite. Full upstream regression coverage, remote CI, production readiness and customer outcomes remain unverified.
