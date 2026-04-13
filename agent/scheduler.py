"""APScheduler setup for fetch/surface/silence/reflect."""
from __future__ import annotations

import logging
import signal

log = logging.getLogger(__name__)


def build_scheduler(jobs: dict):
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    sched = BlockingScheduler()
    if "fetch_and_score" in jobs:
        sched.add_job(jobs["fetch_and_score"], IntervalTrigger(hours=6), id="fetch", misfire_grace_time=3600)
    if "surface" in jobs:
        sched.add_job(jobs["surface"], CronTrigger(hour=7, minute=0), id="surface", misfire_grace_time=3600)
    if "silence" in jobs:
        sched.add_job(jobs["silence"], CronTrigger(hour=8, minute=0), id="silence", misfire_grace_time=3600)
    if "reflect" in jobs:
        sched.add_job(jobs["reflect"], CronTrigger(day_of_week="sun", hour=8, minute=0), id="reflect", misfire_grace_time=7200)

    def _shutdown(*_):
        log.info("shutting down scheduler")
        sched.shutdown(wait=False)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    return sched
