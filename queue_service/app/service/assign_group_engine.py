from sqlalchemy.orm import Session

from app.models.groups import Group
from app.models.grouprule import GroupRule
from app.models.usergroupmembership import UserGroupMembership


# ============================================================
# Fields that participate in automatic group allocation
# ============================================================
# Add/remove fields here whenever the business requirement changes.
#
# Example:
#     "company",
#     "position",
#     "hobbies",
#
# can simply be added later.
# ============================================================

GROUPING_FIELDS = [
    "local_area",
    "current_city",
    "interest",
    "university",
    "course",
    "level",
]


# ============================================================
# Helpers
# ============================================================

def normalize(value):
    """
    Normalize profile/rule values before comparison.

    Example:
        " Dhaka " -> "dhaka"
        None      -> ""
    """
    if value is None:
        return ""

    return str(value).strip().lower()


def get_grouping_data(profile: dict) -> dict:
    """
    Extract only the fields that are configured for grouping.

    Empty values are ignored.
    """

    return {
        field: normalize(profile.get(field))
        for field in GROUPING_FIELDS
        if normalize(profile.get(field))
    }


def evaluate_rule(profile: dict, rule: GroupRule) -> bool:
    """
    Check whether a profile satisfies a group rule.
    """

    profile_value = normalize(profile.get(rule.field))
    expected_value = normalize(rule.value)

    if rule.operator == "equals":
        return profile_value == expected_value

    if rule.operator == "contains":
        return expected_value in profile_value

    if rule.operator == "starts_with":
        return profile_value.startswith(expected_value)

    if rule.operator == "ends_with":
        return profile_value.endswith(expected_value)

    raise ValueError(
        f"Unsupported rule operator: {rule.operator}"
    )


def create_group_name(grouping_data: dict) -> str:
    """
    Generate a readable group name from the profile data.

    Example:

        {
            "local_area": "block d",
            "current_city": "dhaka",
            "interest": "cricket",
            "university": "daffodil international university",
            "course": "software engineering",
            "level": "undergrad"
        }

    becomes something like:

        Block D - Dhaka - Cricket Community
    """

    name_parts = []

    # Only use the most useful fields for the human-readable name.
    # All configured fields can still participate in the rules.
    name_fields = [
        "local_area",
        "current_city",
        "interest",
        "course",
    ]

    for field in name_fields:
        value = grouping_data.get(field)

        if value:
            name_parts.append(value.title())

    if name_parts:
        return " - ".join(name_parts) + " Community"

    return "General Community"


# ============================================================
# Main allocation function
# ============================================================

def allocate_user_to_groups(
    db: Session,
    user_id: int,
    profile: dict,
):
    """
    Automatically allocate a user to matching groups.

    Logic:

    1. Extract configured grouping fields.
    2. Check all active groups.
    3. Match user's profile against group rules.
    4. Assign user to every matching group.
    5. If nothing matches:
         - create a new group
         - create rules based on profile
         - assign user to the new group
    """

    # --------------------------------------------------------
    # 1. Extract only fields configured for grouping
    # --------------------------------------------------------

    grouping_data = get_grouping_data(profile)

    if not grouping_data:
        raise ValueError(
            "No valid grouping information found in profile."
        )

    # --------------------------------------------------------
    # 2. Find all active groups
    # --------------------------------------------------------

    groups = (
        db.query(Group)
        .filter(Group.is_active.is_(True))
        .all()
    )

    matched_groups = []

    # --------------------------------------------------------
    # 3. Check every group
    # --------------------------------------------------------

    for group in groups:

        rules = (
            db.query(GroupRule)
            .filter(
                GroupRule.group_id == group.id,
                GroupRule.is_active.is_(True),
            )
            .all()
        )

        # A group without rules cannot be automatically matched.
        if not rules:
            continue

        # ----------------------------------------------------
        # Only consider rules for configured grouping fields.
        # ----------------------------------------------------

        relevant_rules = [
            rule
            for rule in rules
            if rule.field in GROUPING_FIELDS
        ]

        if not relevant_rules:
            continue

        # ----------------------------------------------------
        # Every rule must match
        # ----------------------------------------------------

        if all(
            evaluate_rule(profile, rule)
            for rule in relevant_rules
        ):
            matched_groups.append(group)

    # --------------------------------------------------------
    # 4. Assign user to existing matching groups
    # --------------------------------------------------------

    if matched_groups:

        for group in matched_groups:

            existing_membership = (
                db.query(UserGroupMembership)
                .filter(
                    UserGroupMembership.user_id == user_id,
                    UserGroupMembership.group_id == group.id,
                )
                .first()
            )

            if existing_membership:
                continue

            membership = UserGroupMembership(
                user_id=user_id,
                group_id=group.id,
                allocation_type="automatic",
            )

            db.add(membership)

        db.commit()

        return matched_groups

    # ========================================================
    # 5. NO MATCHING GROUP
    # ========================================================

    group_name = create_group_name(grouping_data)

    # --------------------------------------------------------
    # 6. Check whether this generated group already exists
    # --------------------------------------------------------
    #
    # The name is NOT enough to determine an exact match.
    # We therefore first try the generated name.
    # --------------------------------------------------------

    new_group = (
        db.query(Group)
        .filter(
            Group.name == group_name,
            Group.is_active.is_(True),
        )
        .first()
    )

    if not new_group:

        # ----------------------------------------------------
        # Create group
        # ----------------------------------------------------

        new_group = Group(
            name=group_name,
            description=(
                "Automatically created based "
                "on user profile attributes."
            ),
            is_active=True,
        )

        db.add(new_group)

        # Get generated ID without committing yet.
        db.flush()

        # ----------------------------------------------------
        # Create rules for the new group
        # ----------------------------------------------------

        for field, value in grouping_data.items():

            rule = GroupRule(
                group_id=new_group.id,
                field=field,
                operator="equals",
                value=value,
                is_active=True,
            )

            db.add(rule)

    # --------------------------------------------------------
    # 7. Assign user to newly created/found group
    # --------------------------------------------------------

    existing_membership = (
        db.query(UserGroupMembership)
        .filter(
            UserGroupMembership.user_id == user_id,
            UserGroupMembership.group_id == new_group.id,
        )
        .first()
    )

    if not existing_membership:

        membership = UserGroupMembership(
            user_id=user_id,
            group_id=new_group.id,
            allocation_type="automatic",
        )

        db.add(membership)

    # --------------------------------------------------------
    # 8. Commit
    # --------------------------------------------------------

    db.commit()

    return [new_group]