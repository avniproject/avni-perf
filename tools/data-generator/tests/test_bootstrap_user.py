import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bootstrap_user as boot
import catchments as cat


def sql(**kw):
    return "\n".join(boot.statements(kw.pop("organisation", 1),
                                     kw.pop("username", "loadtest@openchs"), **kw))


def test_it_needs_nothing_the_environment_cannot_already_provide():
    """The whole point: no bundle, no columns.json, no refs.json, no dataset.

    Those are what make the generator's normal path depend on a loaded database, which is the
    thing this check is supposed to run before.
    """
    s = sql()
    # It owns its own address_level_type rather than looking one up from refs.json.
    assert "insert into address_level_type" in s
    assert s.index("address_level_type") < s.index("insert into address_level ")


def test_every_table_the_user_depends_on_is_created_in_order():
    s = sql()
    order = [s.index(f"insert into {t} ") for t in
             ("address_level_type", "address_level", "catchment",
              "catchment_address_mapping", "groups", "users", "user_group")]
    assert order == sorted(order), "a child row inserted before its parent fails on the spot"


def test_the_user_can_actually_resolve_privileges():
    """A user without group membership syncs none of the entities carrying field data, and the
    run still reports success. That is the defect this bootstrap exists not to reproduce."""
    s = sql()
    assert "insert into groups" in s and "has_all_privileges" in s
    assert "insert into user_group" in s


def test_it_is_re_runnable():
    for line in sql().splitlines():
        if line.startswith("insert into"):
            assert line.rstrip().endswith("on conflict do nothing;"), line
            # Naming a conflict target breaks on catchment_address_mapping, which has no id.
            assert "on conflict (" not in line, line


def test_every_row_carries_a_version_and_its_audit_columns():
    """version is a primitive int on CHSEntity: NULL makes the row unreadable and syncDetails
    500s. That is the first failure the first live run produced."""
    for line in sql().splitlines():
        if line.startswith("insert into") and "catchment_address_mapping" not in line:
            assert "version" in line, line
            assert "created_by_id" in line and "last_modified_by_id" in line, line


def test_ids_cannot_collide_with_a_generated_dataset():
    """A bootstrap user may sit beside a dataset if someone loads one without restoring first.

    Measured against the real upper bound rather than a guess: `plan_ids` gives each tenant
    `i * ID_STRIDE`, and the committed co-tenant deployment has 513 of them, so generated ids
    already reach 51.3 billion. The first constant chosen here was two billion — below the range
    in use — and this assertion is what caught it.
    """
    import recipe as recipe_mod
    import deployment as dep
    from pathlib import Path as P
    datasets = P(__file__).resolve().parents[1] / "datasets"
    highest = 0
    for f in datasets.glob("*.json"):
        d = recipe_mod.Recipe.load(f).to_deployment()
        highest = max(highest, max(dep.plan_ids(d).values()) + dep.ID_STRIDE)
    assert highest > 0, "no committed recipes to measure against"
    assert boot.BOOTSTRAP_ID_BASE > highest, (
        f"bootstrap ids start at {boot.BOOTSTRAP_ID_BASE:,} but generated ids reach {highest:,}")


def test_the_username_reaches_the_users_row_and_is_escaped():
    assert "'o''brien@org'" in sql(username="o'brien@org"), "a quote must not break the SQL"


def test_the_audit_user_is_configurable():
    """created_by_id points at a user that must already exist; it is not always 1."""
    assert ", 42, 42)" in sql(audit_user_id=42)
