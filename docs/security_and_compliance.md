# Security, Compliance & Ethical Guidelines

## 1. Threat Model & Mitigations

| Threat Vector | Potential Impact | Implemented Mitigation |
|---|---|---|
| **Server-Side Request Forgery (SSRF)** | Attacker forces crawler to probe internal cloud metadata (`169.254.169.254`), localhost, or private VPC assets. | `validate_url_security()` validates scheme (`http`/`https`), checks allowed domains, and performs DNS resolution checking against `is_private_ip()` to block loopback, link-local, and private subnets. |
| **Path Traversal / Arbitrary File Overwrite** | Malformed URL or listing ID containing `../` attempts to write files outside archive destination. | `safe_join_path()` resolves real paths and checks `relative_to(base)`. `sanitize_filename()` strips all path separators, null bytes, and Windows reserved device names. |
| **Denial of Service / Memory Exhaustion** | Target server serves multi-gigabyte files or decompression bombs. | `max_response_size_bytes` limits response sizes (50MB default). Pillow verifies image headers and dimensions before reading full bitmap into memory. |
| **Archive Corruption from Crashes** | Network drops or process termination mid-crawl leaves corrupt/partial archives. | Staging directory pattern (`.staging_<id>_<timestamp>`) commits atomically only upon complete write and hash calculation. |
| **Credential / Secret Leakage** | Authorization headers, session tokens, or API keys exposed in output logs. | No secrets or authentication headers are used or logged; all metadata captures only public status codes and response headers. |

---

## 2. Legal & Ethical Considerations

- **Public Data Access**: Only publicly exposed information is collected. No private accounts, paywalls, or restricted endpoints are accessed.
- **Respect for Technical Restrictions**: The system does not attempt to bypass CAPTCHAs, bot protections, or access control mechanisms. If automated access is blocked, users can supply offline HTML snapshots using `--file` or local paths.
- **Polite Crawling**: Always maintain `rate_limit_delay_sec >= 1.0` and avoid aggressive concurrency.
- **Privacy Minimization**: The extractor avoids collecting unnecessary personal contact details beyond publicly visible agency names.
