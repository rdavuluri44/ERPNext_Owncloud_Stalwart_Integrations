"""Framework-independent parts of the face capture queue (P95), shared by the service and its tests."""

RETENTION_DAYS = 30  # a rejected capture keeps its photograph this long (owner, 26 November 2026)
STATES = ('Needs review', 'Matched', 'Resolved', 'Rejected')


def roster_note(rostered, not_enrolled, needs_re_enrolment):
    """What the project manager should know about the team behind a capture that was not recognised."""
    if not rostered:
        return 'No workers are rostered to this supervisor for the shift.'
    parts = []
    if not_enrolled:
        parts.append(f'{not_enrolled} of {rostered} rostered workers have no face enrolled')
    if needs_re_enrolment:
        parts.append(f'{needs_re_enrolment} need to enrol again (the face model changed)')
    return '; '.join(parts) + '.' if parts else ''


def join_notes(*notes):
    return ' '.join(n.strip() for n in notes if n and n.strip())[:1000]
