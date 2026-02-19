## 2026-02-17 - IDOR in Ticket Attachment Download
**Vulnerability:** Authenticated users could download attachments from any ticket by guessing the `ticket_id` and `attachment_id`, bypassing authorization checks.
**Learning:** The `download_attachment` endpoint relied solely on `get_current_active_user` for authentication but lacked a specific authorization check for the requested ticket resource.
**Prevention:** Always verify resource ownership or specific permissions (using `AuthorizationService`) after retrieving an object by ID before returning sensitive data.

## 2026-02-19 - Critical IDOR in Ticket Management
**Vulnerability:** Authenticated users could access (GET) and modify (PATCH, DELETE, transition) tickets belonging to other users by guessing the `ticket_id`.
**Learning:** The endpoints relied on `get_current_active_user` but the Use Cases (e.g., `GetTicketWithRepliesUseCase`, `UpdateTicketUseCase`) did not implement any ownership or role-based checks. They merely checked if the ticket existed.
**Prevention:** Enforce authorization checks *inside* the Use Cases (Domain Service invocation) to ensure that the actor has the right permissions (Creator, Assigned Agent, or Admin) before returning or modifying data.
