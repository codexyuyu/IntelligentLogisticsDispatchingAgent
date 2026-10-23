"""One isolated child process per claimed job; no FastAPI BackgroundTasks."""
import multiprocessing
import time
from datetime import datetime, timezone
from uuid import uuid4

from logistics_backend.application.jobs import Deadline, WorkIdle, WorkLeaseLost
from logistics_contracts.runtime import JobResultRef
from logistics_contracts.common import ErrorEnvelope
from logistics_domain.errors import DomainError
from logistics_domain.states import ErrorCode


def _execute(handler, content, deadline, sender):
    try:
        handler.validate(content)
        result = handler.execute(content, Deadline(deadline))
        sender.send(("result", JobResultRef.model_validate(result).model_dump_json()))
    except DomainError as exc:
        # A handler must expose only typed, safe business failures.
        sender.send(("failure", exc.code.value))
    except Exception:
        sender.send(("failure", ErrorCode.INTERNAL_ERROR.value))
    finally:
        sender.close()


class Worker:
    def __init__(self, repository, registry, owner_id=None):
        self.repository = repository
        self.registry = registry
        self.owner_id = owner_id or uuid4()
        self.context = multiprocessing.get_context("spawn")

    def run_once(self):
        claimed = self.repository.claim(self.owner_id)
        if claimed is None:
            return WorkIdle()
        token, command, scope_id, trace_id = claimed
        try:
            handler = self.registry.require(command)
            content = self.repository.load_request(command.payload.request_ref, scope_id)
        except DomainError as exc:
            return self.repository.finish(token, failure=ErrorEnvelope(code=exc.code,
                message="job capability or immutable input unavailable", trace_id=trace_id, retryable=False))
        receiver, sender = self.context.Pipe(duplex=False)
        process = self.context.Process(target=_execute, args=(handler, content, command.deadline_utc, sender))
        try:
            process.start()
            sender.close()
            while True:
                now = datetime.now(timezone.utc)
                if now >= command.deadline_utc:
                    # Expired leases cannot commit. The queue reaper records the terminal timeout.
                    return WorkLeaseLost(token.job_id)
                cancelled = self.repository.heartbeat(token)
                if cancelled is None:
                    return WorkLeaseLost(token.job_id)
                if cancelled:
                    return self.repository.finish(token)
                if receiver.poll(min(1.0, (command.deadline_utc - now).total_seconds())):
                    try:
                        kind, payload = receiver.recv()
                    except EOFError:
                        kind, payload = "failure", ErrorCode.DEPENDENCY_UNAVAILABLE.value
                    if kind == "result":
                        return self.repository.finish(token, result=JobResultRef.model_validate_json(payload))
                    code = ErrorCode(payload)
                    return self.repository.finish(token, failure=ErrorEnvelope(code=code,
                        message="job handler failed", trace_id=trace_id,
                        retryable=code in (ErrorCode.DEPENDENCY_UNAVAILABLE, ErrorCode.PROVIDER_UNAVAILABLE)))
                if not process.is_alive():
                    return self.repository.finish(token, failure=ErrorEnvelope(code=ErrorCode.DEPENDENCY_UNAVAILABLE,
                        message="job process exited without a result", trace_id=trace_id, retryable=True))
        finally:
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=2)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=2)
                process.close()
            receiver.close()
            sender.close()

    def run(self, stop_event):
        while not stop_event.is_set():
            outcome = self.run_once()
            if isinstance(outcome, WorkIdle):
                stop_event.wait(0.5)


def main():
    from threading import Event
    from logistics_backend.bootstrap import Settings, compose
    engine, services = compose(Settings.from_env())
    try:
        Worker(services.jobs.repository, services.jobs.registry).run(Event())
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
