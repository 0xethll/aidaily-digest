"""
Scheduling utilities for periodic tasks
"""

import logging
from datetime import datetime, timezone
from typing import Callable, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class BotScheduler:
    """Handles scheduled tasks for the bot"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._started = False
    
    def schedule_daily_task(
        self,
        func: Callable,
        hour: int,
        minute: int = 0,
        timezone: str = 'UTC',
        job_id: str = 'daily_task'
    ):
        """
        Schedule a daily recurring task
        
        Args:
            func: Function to execute
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            timezone: Timezone for scheduling
            job_id: Unique identifier for the job
        """
        self.scheduler.add_job(
            func,
            CronTrigger(hour=hour, minute=minute, timezone=timezone),
            id=job_id,
            name=f'Daily task at {hour:02d}:{minute:02d} {timezone}',
            replace_existing=True
        )
        
        logger.info(f"Scheduled daily task '{job_id}' for {hour:02d}:{minute:02d} {timezone}")
    
    def schedule_interval_task(
        self,
        func: Callable,
        seconds: int,
        job_id: str = 'interval_task'
    ):
        """
        Schedule a task to run at regular intervals
        
        Args:
            func: Function to execute
            seconds: Interval in seconds
            job_id: Unique identifier for the job
        """
        self.scheduler.add_job(
            func,
            'interval',
            seconds=seconds,
            id=job_id,
            name=f'Interval task every {seconds}s',
            replace_existing=True
        )
        
        logger.info(f"Scheduled interval task '{job_id}' every {seconds} seconds")
    
    def start(self):
        """Start the scheduler"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self._started:
            self.scheduler.shutdown()
            self._started = False
            logger.info("Scheduler stopped")
    
    def list_jobs(self):
        """List all scheduled jobs"""
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            logger.info(f"Job: {job.id} - {job.name} - Next run: {job.next_run_time}")
        return jobs
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._started and self.scheduler.running