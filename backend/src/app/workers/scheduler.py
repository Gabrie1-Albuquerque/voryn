"""Entry point for the `scheduler` Compose service: registers the recurring
reminder-scan tick with rq-scheduler, then blocks forever running its loop
(this is what the `rqscheduler` CLI does too, just with our own job
registered first). Runs as its own container/process, separate from the
`worker` service's plain `rq worker` -- rq-scheduler's loop and RQ's job
consumption are two different responsibilities that don't share a process.

Uses a fixed job id ("reminder-scan") so re-running this on every container
restart replaces the existing scheduled job instead of accumulating a new
recurring registration each time, which would send every reminder multiple
times over.
"""

from datetime import datetime, timezone

from redis import Redis
from rq_scheduler import Scheduler

from app.core.config import get_settings
from app.workers.reminders import scan_and_enqueue_reminders

settings = get_settings()

REMINDER_SCAN_JOB_ID = "reminder-scan"


def main() -> None:
    redis_conn = Redis.from_url(settings.redis_url)
    scheduler = Scheduler(connection=redis_conn)

    # Idempotent re-registration: cancel() on an id that isn't currently
    # scheduled is a safe no-op, so this doesn't need to check existence
    # first -- simpler and avoids depending on a narrower API surface.
    scheduler.cancel(REMINDER_SCAN_JOB_ID)

    scheduler.schedule(
        scheduled_time=datetime.now(timezone.utc),
        func=scan_and_enqueue_reminders,
        interval=settings.reminder_scan_interval_minutes * 60,
        repeat=None,
        id=REMINDER_SCAN_JOB_ID,
    )
    scheduler.run()


if __name__ == "__main__":
    main()
