"""Seed the database with a demo driver + 8 days of history,
plus an admin user and a driver login.

Idempotent: re-running upserts the same records so the demo is
always deterministic.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from trip.models import Driver, DayHistory

User = get_user_model()


class Command(BaseCommand):
    help = "Create a demo driver, 8 days of on-duty history, an admin, and a driver login."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=8)
        parser.add_argument("--on-duty", type=float, default=9.5,
                            help="Hours on-duty for the seeded days")
        parser.add_argument("--admin-username", default="admin")
        parser.add_argument("--admin-password", default="admin")
        parser.add_argument("--driver-username", default="tino")
        parser.add_argument("--driver-password", default="12345")

    def _ensure_user(self, username, password, is_staff=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_staff": is_staff},
        )
        user.set_password(password)
        if is_staff:
            user.is_staff = True
        user.save()
        return user

    def handle(self, *args, **opts):
        admin = self._ensure_user(opts["admin_username"], opts["admin_password"], is_staff=True)
        driver_user = self._ensure_user(opts["driver_username"], opts["driver_password"], is_staff=False)

        driver, _ = Driver.objects.update_or_create(
            name="Tinotenda Duma",
            defaults=dict(
                user=driver_user,
                carrier="John Doe's Transportation",
                default_truck_number="123, 20544",
                home_terminal="Washington, D.C.",
                main_office="Washington, D.C.",
                current_cycle_used_hrs=opts["on_duty"] * opts["days"],
            ),
        )
        today = date.today()
        for i in range(1, opts["days"] + 1):
            DayHistory.objects.update_or_create(
                driver=driver,
                date=today - timedelta(days=i),
                source=DayHistory.SOURCE_MANUAL,
                defaults={
                    "on_duty_hrs": opts["on_duty"],
                    "driving_hrs": opts["on_duty"] - 1.5,
                },
            )
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {driver} with {opts['days']} days of {opts['on_duty']:.1f}-hr history "
            f"(id={driver.id}); admin={admin.username}, driver login={driver_user.username}"
        ))
