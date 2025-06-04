import asyncio
import random
import logging
from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from utils.json_storage import load_scenarios
from utils.monitoring_utils import launch_monitoring_from_dict

tz = pytz.timezone("Europe/Kiev")
scheduler = AsyncIOScheduler(timezone=tz)

recently_run = {}  # {scenario_name: datetime}
bot_instance = None  # глобальна змінна для доступу до бота

def set_scheduler_bot(bot):
    global bot_instance
    bot_instance = bot

def init_scenarios_cron_jobs():
    scenarios = load_scenarios()
    for name, sc in scenarios.items():
        if not sc.get("active"):
            continue

        schedules = sc.get("schedules", [])
        for sch in schedules:
            if sch["type"] == "fixed_times":
                for t in sch.get("times", []):
                    hour, minute = map(int, t.split(":"))
                    scheduler.add_job(
                        _run_named_scenario, 
                        CronTrigger(hour=hour, minute=minute, timezone=tz), 
                        args=[name]
                    )
                    logging.info(f"[Scheduler] ⏰ Fixed time: {name} @ {t}")

            elif sch["type"] == "random_in_intervals":
                for interval in sch.get("intervals", []):
                    start = _parse_time(interval["start"])
                    end = _parse_time(interval["end"])
                    delay = _random_time_between(start, end)
                    scheduler.add_job(_run_named_scenario, "date", run_date=delay, args=[name])
                    logging.info(f"[Scheduler] 🎲 Random run {name} @ {delay}")

    # запускаємо фоновий цикл для loop-сценаріїв
    asyncio.create_task(_loop_interval_checker())

def _parse_time(t: str) -> datetime:
    now = datetime.now(tz)
    hour, minute = map(int, t.split(":"))
    run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_time < now:
        run_time += timedelta(days=1)
    return run_time

def _random_time_between(start: datetime, end: datetime) -> datetime:
    delta = (end - start).total_seconds()
    return start + timedelta(seconds=random.randint(0, int(delta)))

async def _run_named_scenario(name: str):
    scenarios = load_scenarios()
    sc = scenarios.get(name)
    if not sc or not sc.get("active"):
        logging.info(f"[Scheduler] ⛔️ Scenario {name} is not active or not found")
        return

    last_run = recently_run.get(name)
    now = datetime.now(tz)
    if last_run and (now - last_run).total_seconds() < 60:
        logging.info(f"[Scheduler] ⏳ Skipping duplicate run for {name}")
        return

    logging.info(f"[Scheduler] ▶️ Running scenario: {name}")
    recently_run[name] = now

    try:
        await launch_monitoring_from_dict(sc, callback=None, bot=bot_instance)
    except Exception as e:
        logging.error(f"[Scheduler] ❌ Failed to run scenario {name}: {e}")

async def _loop_interval_checker():
    while True:
        scenarios = load_scenarios()
        now = datetime.now(tz)
        now_time = now.time()

        for name, sc in scenarios.items():
            if not sc.get("active"):
                continue

            for sch in sc.get("schedules", []):
                if sch["type"] != "loop_in_intervals":
                    continue

                interval_min = sch.get("interval_min", 2)
                interval_max = sch.get("interval_max", 5)

                for interval in sch.get("intervals", []):
                    start = datetime.strptime(interval["start"], "%H:%M").time()
                    end = datetime.strptime(interval["end"], "%H:%M").time()

                    if start <= now_time <= end:
                        last_run = recently_run.get(name)
                        if last_run and (now - last_run).total_seconds() < interval_min * 60:
                            continue

                        logging.info(f"[Scheduler] 🔁 Loop run for {name} at {now_time}")
                        recently_run[name] = now
                        asyncio.create_task(
                            launch_monitoring_from_dict(sc, callback=None, bot=bot_instance)
                        )
        await asyncio.sleep(60)

def reload_scheduler():
    if not scheduler.running:
        try:
            scheduler.start()
        except Exception as e:
            logging.warning(f"[Scheduler] ⚠️ Scheduler not running and cannot start: {e}")
            return
    logging.info("[Scheduler] 🔄 Reloading all scheduled jobs...")
    scheduler.remove_all_jobs()
    init_scenarios_cron_jobs()
