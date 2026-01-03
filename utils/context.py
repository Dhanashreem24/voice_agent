from contextvars import ContextVar
import threading

# ContextVar to store the current user_id (thread-safe and async-safe)
_current_user_id: ContextVar[str] = ContextVar("current_user_id", default=None)

def set_user_context(user_id: str):
    """Sets the user_id for the current context."""
    print(f"DEBUG: Setting context for {user_id} in Thread {threading.get_ident()}")
    _current_user_id.set(user_id)

def get_user_context() -> str:
    """Retrieves the user_id from the current context."""
    return _current_user_id.get()
