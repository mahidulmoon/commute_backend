from sqlalchemy.orm import Session

from app.models.groups import Group
from app.models.grouprule import GroupRule
from app.models.usergroupmembership import UserGroupMembership
from app.models.wo_user import User
from app.logging_config import logger


# ============================================================
# Fields that participate in automatic group allocation
# ============================================================
# Add/remove fields here whenever the business requirement changes.
#
# Postcode is given first priority when present in the user data.
# ============================================================

GROUPING_FIELDS = [
    "postcode",
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
            "postcode": "1212",
            "local_area": "block d",
            "current_city": "dhaka",
            "interest": "cricket",
            "university": "daffodil international university",
            "course": "software engineering",
            "level": "undergrad"
        }

    becomes something like:

        Postcode 1212 - Block D - Dhaka - Cricket Community
    """

    name_parts = []

    # Postcode is top priority for community naming when present.
    name_fields = [
        "postcode",
        "local_area",
        "current_city",
        "interest",
        "course",
    ]

    for field in name_fields:
        value = grouping_data.get(field)

        if value:
            if field == "postcode":
                name_parts.append(f"Postcode {value.upper()}")
            else:
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

    0. Look up user's postcode from User record if not in profile.
       - If postcode is present, it is given FIRST PRIORITY:
         - Match only groups that have a rule for 'postcode'.
         - If no existing postcode group matches, create a new
           group prioritized with postcode in its rules and name.
       - If postcode is not present, perform standard grouping as-is.
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
    # 0. Check postcode priority
    # --------------------------------------------------------

    # The worker reuses a single long-lived DB session. Expire all cached
    # objects so we always read the freshest data (including postcode that
    # was just saved by the auth service before publishing this message).
    db.expire_all()

    user_id_int = int(user_id) if user_id else 0
    user = (
        db.query(User).filter(User.user_id == user_id_int).first()
        if user_id_int
        else None
    )

    # Use postcode from profile (raw_data) first — it's guaranteed to be
    # present because CompleteProfileSchema now makes it required.
    # Fall back to users.postcode from DB in case of older messages.
    raw_postcode = profile.get("postcode") or (user.postcode if user else None)
    if raw_postcode:
        profile["postcode"] = raw_postcode

    user_postcode = normalize(profile.get("postcode"))
    has_postcode = bool(user_postcode)

    logger.info(
        f"User {user_id} | profile keys received: {list(profile.keys())}"
    )
    logger.info(
        f"User {user_id} | raw_postcode resolved to: '{raw_postcode}'"
    )

    if has_postcode:
        logger.info(
            f"User {user_id} has postcode '{user_postcode}'. Prioritizing postcode in group allocation."
        )
    else:
        logger.info(
            f"User {user_id} has no postcode. Performing standard group allocation."
        )

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
        # First priority for postcode:
        # If user has a postcode, only match groups that have
        # an active rule for 'postcode'.
        # ----------------------------------------------------
        if has_postcode:
            group_has_postcode_rule = any(
                rule.field == "postcode" for rule in relevant_rules
            )
            if not group_has_postcode_rule:
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
                    UserGroupMembership.user_id == user_id_int,
                    UserGroupMembership.group_id == group.id,
                )
                .first()
            )

            if existing_membership:
                continue

            membership = UserGroupMembership(
                user_id=user_id_int,
                group_id=group.id,
                allocation_type="automatic",
            )

            db.add(membership)

        db.commit()

        logger.info(
            f"User {user_id} assigned to existing matched groups: {[g.name for g in matched_groups]}"
        )
        return matched_groups

    # ========================================================
    # 5. NO MATCHING GROUP -> CREATE NEW GROUP
    # ========================================================

    logger.info(
        f"User {user_id} | No matching group found. "
        f"Creating new group from grouping_data: {grouping_data}"
    )

    group_name = create_group_name(grouping_data)

    # --------------------------------------------------------
    # 6. Check whether this generated group already exists
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
                "Automatically created based on user postcode and profile attributes."
                if has_postcode
                else "Automatically created based on user profile attributes."
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
            UserGroupMembership.user_id == user_id_int,
            UserGroupMembership.group_id == new_group.id,
        )
        .first()
    )

    if not existing_membership:

        membership = UserGroupMembership(
            user_id=user_id_int,
            group_id=new_group.id,
            allocation_type="automatic",
        )

        db.add(membership)

    # --------------------------------------------------------
    # 8. Commit
    # --------------------------------------------------------

    db.commit()

    logger.info(
        f"User {user_id} assigned to newly created/found group: {new_group.name}"
    )
    return [new_group]