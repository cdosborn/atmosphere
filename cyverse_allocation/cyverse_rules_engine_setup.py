from business_rules.variables import BaseVariables, boolean_rule_variable, numeric_rule_variable
from business_rules.actions import BaseActions, rule_action
from dateutil.parser import parse
from core.models.allocation_source import AllocationSource,AllocationSourceSnapshot


class CyverseTestRenewalVariables(BaseVariables):
    def __init__(self, allocation_source, supplement_requested, current_time):
        self.allocation_source = allocation_source
        self.supplement_requested = supplement_requested
        self.current_time = current_time

    @boolean_rule_variable
    def is_valid(self):
        if self.allocation_source.end_date > parse(self.current_time):
            return True
        return False
    #
    # @boolean_rule_variable
    # def is_at_full_capacity(self):
    #     if self.allocation_source.compute_allowed > AllocationSource.objects.get(allocation_source = self.allocation_source).compute_used:
    #         return True
    #     return False

    @boolean_rule_variable
    def is_pending_renewal(self):
        source_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=self.allocation_source)
        if not source_snapshot:
            return False
        if (source_snapshot.last().last_renewed - parse(self.current_time)).days >= 30:
            return True


class CyverseTestRenewalActions(BaseActions):
    def __init__(self, allocation_source):
        if not isinstance(allocation_source, AllocationSource):
            raise Exception('Please provide Allocation Source instance for renewal')
        self.allocation_source = allocation_source

    @rule_action()
    def renew_allocation_source(self):
        source_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=self.allocation_source)
        if not source_snapshot:
            raise Exception('Allocation Source %s cannot be renewed because no snapshot is available'%(self.allocation_source.name))
        source_snapshot.last().compute_used


cyverse_rules = [
    #  if isValid(allocation_source) && ( is_monthly_renewal(allocation_source) | is_weekly_renewal(allocation_source) | is_)
    {"conditions": {"all": [
        {"name": "is_valid",
         "operator": "equal_to",
         "value": True,
         },
        {"name": "is_pending_renewal",
         "operator": "equal_to",
         "value": True,
         },
    ]},
        "actions": [
            {"name": "renew_allocation_source",
             },
        ],
    },
]
