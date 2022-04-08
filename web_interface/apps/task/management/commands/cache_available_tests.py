from framework.test_system import get_available_tests
from django.core.management.base import BaseCommand

from framework.xlsdata import cached_test_groups
from web_interface.apps.framework_data.models import AvailableTest, AvailableTestGroup

# from web_interface.apps.task.task_functional.estimate_time import update_test_time_data


class Command(BaseCommand):
    help = "Loads available tests and updates the DB cache"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Loading available test groups"))
        AvailableTestGroup.objects.all().delete()
        available_test_groups = {}
        for cached_test in cached_test_groups:
            if cached_test["status"] != "disabled":
                available_test_group = AvailableTestGroup.objects.create(name=cached_test["name"])
                available_test_groups[available_test_group.name] = available_test_group

        self.stdout.write(self.style.NOTICE("Loading available tests"))
        tests = get_available_tests(include_axe_tests=True)
        AvailableTest.objects.all().delete()

        for test in tests:
            test_name = test["name"]
            test_human_name = test["human_name"]
            if not test_name:
                self.stdout.write(self.style.WARNING("Skip test with empty name"))
                continue
            elif not test_human_name:
                self.stdout.write(self.style.WARNING("Skip test with empty human name"))
                continue
            available_test = AvailableTest.objects.create(name=test_name, human_name=test_human_name)
            for group_name in test["groups"]:
                available_test_group = available_test_groups.get(group_name)
                if available_test_group is None:
                    self.stdout.write(
                        self.style.WARNING('Test group with name "%s" is not present in metadata' % group_name)
                    )
                else:
                    available_test.groups.add(available_test_group)

        # * deprecated
        # update_test_time_data()

        self.stdout.write(self.style.SUCCESS("DB cache of available tests updated"))
