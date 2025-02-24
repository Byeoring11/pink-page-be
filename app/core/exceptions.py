class TaskAlreadyRunningError(Exception):
    """Raised when attempting to start a task while another is already running."""
    pass
