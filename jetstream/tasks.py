import logging
import collections

from django.conf import settings
from django.utils import timezone
from dateutil.parser import parse


from celery.decorators import task
from core.models.allocation_source import total_usage
from core.models.allocation_source import (
    UserAllocationSource, AllocationSourceSnapshot,
    AllocationSource, UserAllocationSnapshot
)

from core.models import EventTableUpdated
from service.allocation_logic import create_report, get_instance_burn_rate_from_row
from core.models.user import AtmosphereUser

from .models import TASAllocationReport
from .allocation import (TASAPIDriver, fill_user_allocation_sources)

from .exceptions import TASPluginException


logger = logging.getLogger(__name__)


@task(name="monitor_jetstream_allocation_sources")
def monitor_jetstream_allocation_sources():
    """
    Queries the TACC API for Jetstream allocation sources
    Adds each new source (And user association) to the DB.
    """
    resources = fill_user_allocation_sources()
    return resources


def create_reports():
    """
    GO through the list of all users or all providers
    For each username, get an XSede API map to the 'TACC username'
    if 'TACC username' includes a jetstream resource, create a report
    """
    user_allocation_list = UserAllocationSource.objects.all()
    all_reports = []
    driver = TASAPIDriver()
    end_date = timezone.now()
    for item in user_allocation_list:
        allocation_id = item.allocation_source.source_id
        tacc_username = driver.get_tacc_username(item.user)
        if not tacc_username:
            logger.error("No TACC username for user: '{}' which came from allocation id: {}".format(item.user,
                                                                                                    allocation_id))
            continue
        project_name = driver.get_allocation_project_name(allocation_id)
        try:
            project_report = _create_tas_report_for(
                item.user,
                tacc_username,
                project_name,
                end_date)
        except TASPluginException:
            logger.exception(
                "Could not create the report because of the error below"
            )
            continue
        all_reports.append(project_report)
    return all_reports


def _create_tas_report_for(user, tacc_username, tacc_project_name, end_date):
    """
    Create a new report
    """
    if not end_date:
        raise TASPluginException("Explicit end date required")
    if not user:
        raise TASPluginException("User missing")
    if not tacc_username:
        raise TASPluginException("TACC Username missing")
    if not tacc_project_name:
        raise TASPluginException("OpenStack/TACC Project missing")

    last_report = TASAllocationReport.objects.filter(
        project_name=tacc_project_name,
        user=user
        ).order_by('end_date').last()
    if not last_report:
        start_date = user.date_joined
    else:
        start_date = last_report.end_date

    compute_used = total_usage(
        user.username, start_date,
        allocation_source_name=tacc_project_name,
        end_date=end_date)

    if compute_used < 0:
        raise TASPluginException(
            "Compute usage was not accurately calculated for user:%s"
            % user)

    new_report = TASAllocationReport.objects.create(
        user=user,
        username=tacc_username,
        project_name=tacc_project_name,
        compute_used=compute_used,
        start_date=start_date,
        end_date=end_date,
        tacc_api=settings.TACC_API_URL)
    logger.info("Created New Report:%s" % new_report)
    return new_report


@task(name="report_allocations_to_tas")
def report_allocations_to_tas():
    if 'jetstream' not in settings.INSTALLED_APPS:
        return
    logger.info("Reporting: Begin creating reports")
    create_reports()
    logger.info("Reporting: Completed, begin sending reports")
    send_reports()
    logger.info("Reporting: Reports sent")


def send_reports():
    failed_reports = 0
    reports_to_send = TASAllocationReport.objects.filter(success=False).order_by('user__username', 'start_date')
    count = reports_to_send.count()
    for tas_report in reports_to_send:
        try:
            tas_report.send()
        except TASPluginException:
            logger.exception(
                "Could not send the report because of the error below"
            )
            failed_reports += 1
            continue
    if failed_reports != 0:
        raise Exception("%s/%s reports failed to send to TAS" % (failed_reports, count))

@task(name="update_snapshot")
def update_snapshot(start_date=None, end_date=None):
    if not settings.USE_ALLOCATION_SOURCE:
        return False
    end_date = end_date or timezone.now()
    # TODO: Read this start_date from last 'reset event' for each allocation source
    start_date = start_date or '2016-09-01 00:00:00.0-05'

    allocation_sources_renewed_dict = {e.payload['allocation_source_name']: e.payload['start_date'] for e in
                                       EventTableUpdated.objects.filter(name='allocation_source_renewed').order_by(
                                           'timestamp')}

    tas_api_obj = TASAPIDriver()
    allocation_source_usage_from_tas = tas_api_obj.get_all_projects()


    for project in allocation_source_usage_from_tas:
        total_burn_rate = 0
        allocation_source_name = project['chargeCode']
        try:
            allocation_source = AllocationSource.objects.filter(name=allocation_source_name).order_by('id').last()

            if allocation_source.name in allocation_sources_renewed_dict:
                #if renewed, change ignore old allocation usage
                start_date = allocation_sources_renewed_dict[allocation_source.name]

            for user in allocation_source.all_users:
                compute_used, burn_rate = total_usage(user.username, start_date, allocation_source_name=allocation_source.name ,end_date=end_date,burn_rate=True)

                total_burn_rate +=burn_rate
                snapshot, created = UserAllocationSnapshot.objects.update_or_create(
                    allocation_source_id=allocation_source.id,
                    user_id=user.id,
                    defaults={
                        'compute_used': compute_used,
                        'burn_rate': burn_rate
                    }
                )

        except KeyError:
            # This allocation source does not exist in our database yet. Create it? Skip for now.
            continue
        # MAKE SURE THAT WE ARE ONLY LOOKING AT MOST RECENT ACTIVE ALLOCATION SOURCES
        compute_used = project['allocations'][-1]['computeUsed']
        snapshot, created = AllocationSourceSnapshot.objects.update_or_create(
            allocation_source_id=allocation_source.id,
            defaults={
                'compute_used': compute_used,
                'global_burn_rate': total_burn_rate
            }
        )
    return True

