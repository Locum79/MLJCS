# EDGES_LOG.md (Certifystack)

## Initial Edge Cases (2026-05-09)

1. **Railway Ephemeral Filesystem**: Certificates uploaded to `uploads/` are lost on every deployment because the filesystem is wiped. **Mitigation**: Added `[[mounts]]` to `railway.toml`.
2. **Missing Master Template**: If a `CertificateType` exists in the DB but its PDF/PNG master file is missing from disk (e.g., failed mount or manual deletion), the PDF generator crashes with `FileNotFoundError`. **Mitigation**: Added existence check and graceful error response in `preview_certificate` route.
3. **Ambiguous Name Splitting**: Webhooks/Imports splitting `full_name` by space fail for multi-part names (e.g., "Van der Woodsen"). **Mitigation**: Updated logic to treat the first word as `first_name` and all subsequent words as `surname`.
4. **Parameter Mismatch**: Engine function `generate_personalized_pdf` expects `issuance_date`, but route was calling it with `issue_date` (or intended to). **Fixed**.

## Future Considerations
- **Railway Volume Persistence**: If the volume is detached or renamed, the app will fail to find existing files. Added early check in `preview_certificate`.
- **Large Import Memory usage**: `openpyxl` loads the entire workbook into memory. For >10k participants, this may OOM on small Railway plans.
