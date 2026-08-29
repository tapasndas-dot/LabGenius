from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestContext:
    request_id: str | None = None
    source_ip: str | None = None


_request_context: ContextVar[RequestContext] = ContextVar(
    "request_context", default=RequestContext()
)


def get_request_context() -> RequestContext:
    return _request_context.get()


def set_request_context(context: RequestContext):
    return _request_context.set(context)


def reset_request_context(token) -> None:
    _request_context.reset(token)
