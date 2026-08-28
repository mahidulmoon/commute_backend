from sqlalchemy.orm import Session
from app.logging_config import setup_logging, logger
from app.models.groups import Group
from app.models.grouprule import GroupRule
from app.models.usergroupmembership import UserGroupMembership

def normalize(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def evaluate_rule(profile: dict, rule):
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


def allocate_user_to_groups(
    db: Session,
    user_id: int,
    profile: dict,
):
    # ---------------------------------------------------------
    # 1. Find all active groups
    # ---------------------------------------------------------
    groups = (
        db.query(Group)
        .filter(Group.is_active.is_(True))
        .all()
    )

    matched_groups = []

    # ---------------------------------------------------------
    # 2. Check which groups match this user's profile
    # ---------------------------------------------------------
    for group in groups:

        rules = (
            db.query(GroupRule)
            .filter(
                GroupRule.group_id == group.id,
                GroupRule.is_active.is_(True),
            )
            .all()
        )

        # Group without rules cannot be automatically matched
        if not rules:
            continue

        # All rules of the group must match
        if all(
            evaluate_rule(profile, rule)
            for rule in rules
        ):
            matched_groups.append(group)

    # ---------------------------------------------------------
    # 3. If groups matched, assign user to them
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # 4. No matching group found
    # ---------------------------------------------------------

    # Pick meaningful information from profile
    city = normalize(profile.get("current_city"))
    country = normalize(profile.get("current_country_name"))
    interest = normalize(profile.get("interest"))
    course = normalize(profile.get("course"))
    level = normalize(profile.get("level"))
    position = normalize(profile.get("position"))

    # ---------------------------------------------------------
    # 5. Generate a group name based on available data
    # ---------------------------------------------------------

    if city and interest:
        group_name = (
            f"{city.title()} - "
            f"{interest.title()} Community"
        )

    elif city and course:
        group_name = (
            f"{city.title()} - "
            f"{course.title()} Community"
        )

    elif city and position:
        group_name = (
            f"{city.title()} - "
            f"{position.title()} Community"
        )

    elif city:
        group_name = f"{city.title()} Community"

    elif country and interest:
        group_name = (
            f"{country.title()} - "
            f"{interest.title()} Community"
        )

    elif interest:
        group_name = f"{interest.title()} Community"

    elif course:
        group_name = f"{course.title()} Community"

    elif position:
        group_name = f"{position.title()} Community"

    elif level:
        group_name = f"{level.title()} Community"

    else:
        group_name = "General Community"

    # ---------------------------------------------------------
    # 6. Check if generated group already exists
    # ---------------------------------------------------------

    new_group = (
        db.query(Group)
        .filter(Group.name == group_name)
        .first()
    )

    # If it already exists, use it
    if not new_group:

        new_group = Group(
            name=group_name,
            description=(
                "Automatically created group "
                "based on user profile."
            ),
            is_active=True,
        )

        db.add(new_group)

        # Flush so new_group.id becomes available
        db.flush()

    # ---------------------------------------------------------
    # 7. Assign user to the newly selected group
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 8. Commit everything
    # ---------------------------------------------------------

    db.commit()

    return [new_group]