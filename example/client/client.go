// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
// Modified by OTel Incident Sandbox contributors: synthetic support-request cases,
// TraceContext-only baggage boundary, header evidence, and bounded loopback lifecycle.
// Derived from the pinned OpenTelemetry example; see ../../NOTICE.

// Client exemplifies the otelhttp instrumentation for a client.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/baggage"
	stdout "go.opentelemetry.io/otel/exporters/stdout/stdouttrace"
	"go.opentelemetry.io/otel/propagation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.43.0"
	"go.opentelemetry.io/otel/trace"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

func initTracer() (*sdktrace.TracerProvider, error) {
	// Create stdout exporter to be able to retrieve
	// the collected spans.
	exporter, err := stdout.New()
	if err != nil {
		return nil, err
	}

	// For the demonstration, use sdktrace.AlwaysSample sampler to sample all traces.
	// In a production application, use sdktrace.ProbabilitySampler with a desired probability.
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
		sdktrace.WithBatcher(exporter),
	)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	return tp, err
}

type recordingTransport struct{ file *os.File }

func (t recordingTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	if err := json.NewEncoder(t.file).Encode(map[string]any{"url": req.URL.String(), "headers": req.Header}); err != nil {
		return nil, err
	}
	return http.DefaultTransport.RoundTrip(req)
}

func main() {
	tp, err := initTracer()
	if err != nil {
		log.Fatal(err)
	}
	defer func() {
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		if err := tp.Shutdown(ctx); err != nil {
			log.Printf("Error shutting down tracer provider: %v", err)
		}
	}()
	endpoint := flag.String("server", "http://127.0.0.1:7777/support", "loopback server URL")
	headers := flag.String("headers", "", "outbound-header evidence file")
	flag.Parse()
	u, err := url.Parse(*endpoint)
	if err != nil || u.Scheme != "http" || u.Hostname() != "127.0.0.1" || u.User != nil || u.Port() == "" || u.Path != "/support" || u.RawQuery != "" {
		log.Fatal("expected a loopback support endpoint")
	}
	if *headers == "" {
		log.Fatal("headers evidence file is required")
	}
	headerFile, err := os.Create(*headers)
	if err != nil {
		log.Fatal(err)
	}
	defer headerFile.Close()
	client := http.Client{Timeout: 3 * time.Second, Transport: otelhttp.NewTransport(recordingTransport{headerFile})}
	bag, err := baggage.Parse("username=customer.synthetic@example.test,api_token=synthetic-token-DO-NOT-USE-5f7d")
	if err != nil {
		log.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancel()
	ctx = baggage.ContextWithBaggage(ctx, bag)
	tr := otel.Tracer("example/client")
	for _, want := range []int{http.StatusOK, http.StatusServiceUnavailable} {
		requestURL := *endpoint
		if want == http.StatusServiceUnavailable {
			requestURL += "?failure=503"
		}
		err := func(ctx context.Context) error {
			ctx, span := tr.Start(ctx, "support.request", trace.WithAttributes(semconv.ServicePeerName("SupportSandboxServer")))
			defer span.End()
			req, err := http.NewRequestWithContext(ctx, http.MethodGet, requestURL, http.NoBody)
			if err != nil {
				return err
			}
			res, err := client.Do(req)
			if err != nil {
				return err
			}
			defer res.Body.Close()
			if _, err := io.ReadAll(res.Body); err != nil {
				return err
			}
			if res.StatusCode != want {
				return fmt.Errorf("status %d, expected %d", res.StatusCode, want)
			}
			fmt.Printf("STATUS %d\n", res.StatusCode)
			return nil
		}(ctx)
		if err != nil {
			log.Fatal(err)
		}
	}
}
