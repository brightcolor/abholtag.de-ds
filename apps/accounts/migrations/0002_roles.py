"""Creates the role groups (§29). Permissions are assigned per group."""

from django.db import migrations


ROLES = {
    "Administrator": "__all__",
    "Datenmanager": [
        ("waste_types", ["wastetype"]),
        ("addresses", ["city", "district", "street", "streetalias", "streetassignment", "addresskey"]),
        ("schedules", ["collectionzone", "scheduleyear", "collectiondate"]),
        ("data_sources", ["datasource", "sourcedocument"]),
        ("imports", ["importrun"]),
    ],
    "Moderator": [
        ("community", [
            "errorreport", "correctionproposal", "proposalvote",
            "communitycontribution",
        ]),
        ("moderation", ["moderationcomment"]),
    ],
    "Analyst": [
        ("analytics", ["analyticsevent", "analyticsaggregate"]),
    ],
    "Auditor": [
        ("audit", ["auditlog", "changeset"]),
    ],
}

READ_ONLY_ROLES = {"Analyst", "Auditor"}


def create_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for role, spec in ROLES.items():
        group, _ = Group.objects.get_or_create(name=role)
        if spec == "__all__":
            continue  # administrators use is_superuser
        permissions = []
        for app_label, models in spec:
            for model in models:
                lookups = ["view"] if role in READ_ONLY_ROLES else ["view", "add", "change"]
                for action in lookups:
                    permission = Permission.objects.filter(
                        content_type__app_label=app_label, codename=f"{action}_{model}"
                    ).first()
                    if permission:
                        permissions.append(permission)
        group.permissions.set(permissions)


def drop_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("community", "0001_initial"),
        ("moderation", "0001_initial"),
        ("analytics", "0001_initial"),
        ("audit", "0001_initial"),
        ("imports", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(create_roles, drop_roles)]
