## 2026-02-17 - IDOR in Ticket Attachment Download
**Vulnerability:** Authenticated users could download attachments from any ticket by guessing the `ticket_id` and `attachment_id`, bypassing authorization checks.
**Learning:** The `download_attachment` endpoint relied solely on `get_current_active_user` for authentication but lacked a specific authorization check for the requested ticket resource.
**Prevention:** Always verify resource ownership or specific permissions (using `AuthorizationService`) after retrieving an object by ID before returning sensitive data.
