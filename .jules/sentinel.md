## 2026-02-17 - IDOR in Ticket Attachment Download
**Vulnerability:** Authenticated users could download attachments from any ticket by guessing the `ticket_id` and `attachment_id`, bypassing authorization checks.
**Learning:** The `download_attachment` endpoint relied solely on `get_current_active_user` for authentication but lacked a specific authorization check for the requested ticket resource.
**Prevention:** Always verify resource ownership or specific permissions (using `AuthorizationService`) after retrieving an object by ID before returning sensitive data.

## 2025-02-18 - [Insecure File Upload]
**Vulnerability:** File extension validation was missing. Attackers could upload malicious scripts (e.g., .php) by faking the Content-Type header to match allowed types (e.g., image/jpeg).
**Learning:** Relying on 'Content-Type' header alone is insecure as it's user-controlled. Also, file name extensions from user input should be strictly validated against an allowlist.
**Prevention:** Use a strict allowlist mapping MIME types to allowed extensions. Validate both the MIME type and the extension. Consider checking file signatures (magic bytes) for deeper validation.
