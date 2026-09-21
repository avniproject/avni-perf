"""Production's own organisations, as co-tenants beside the customer's.

Test cases 6 and 7 put the customer's ten tenants on a database that also holds everyone else's
data, and the delta against case 5 is the shared-versus-separate hosting decision. **Without this
the comparison has no second half**, and the decision stays an opinion.

The shape is Q12's, not an invention: **986 organisations, 473 of them holding nothing**, the
largest holding 21% of all subjects, the top ten 63% and the top fifty over 90%. That skew is the
point — multi-tenancy costs scale with what is in the tables rather than with who is querying, so a
co-tenant set of 986 equal organisations would misrepresent production as badly as no co-tenants at
all.

**Sizes are interpolated through the measured ranks rather than fitted.** A power law does not hold
across the range: the exponent between ranks 1 and 10 is 0.84 and between 1 and 156 it is 1.57, so
any single curve is wrong somewhere. Interpolating in log-log space through the points Q12 actually
returned reproduces every share within two points and assumes nothing between them.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import deployment as dep

# Q12: rank against subjects held. The curve passes through each of these exactly.
MEASURED_RANKS: tuple[tuple[int, int], ...] = (
    (1, 570_805), (2, 188_330), (5, 127_289), (10, 81_837), (20, 22_681),
    (50, 5_471), (100, 1_212), (156, 205), (300, 11), (513, 1),
)

TOTAL_ORGANISATIONS = 986
ORGANISATIONS_WITH_SUBJECTS = 513

# Q7: 6,860,430 program encounters against 2,751,205 subjects across production.
ENCOUNTERS_PER_SUBJECT = 2.49


def subjects_at_rank(rank: int) -> int:
    """How many subjects the organisation at this rank holds."""
    if rank < 1:
        raise ValueError("rank starts at 1")
    if rank > ORGANISATIONS_WITH_SUBJECTS:
        return 0
    pts = MEASURED_RANKS
    if rank <= pts[0][0]:
        return pts[0][1]
    for (r0, s0), (r1, s1) in zip(pts, pts[1:]):
        if r0 <= rank <= r1:
            f = (math.log(rank) - math.log(r0)) / (math.log(r1) - math.log(r0))
            return max(1, round(math.exp(math.log(s0) + f * (math.log(s1) - math.log(s0)))))
    return pts[-1][1]


@dataclass(frozen=True)
class CoTenant:
    rank: int
    organisation_id: int
    subjects: int
    encounters: int

    @property
    def empty(self) -> bool:
        return self.subjects == 0


def plan(*, first_organisation_id: int = 1000,
         total: int = TOTAL_ORGANISATIONS,
         with_subjects: int = ORGANISATIONS_WITH_SUBJECTS,
         days: int = 180,
         encounters_per_subject: float = ENCOUNTERS_PER_SUBJECT) -> list[CoTenant]:
    """The co-tenant set, ranked largest first.

    `days` scales the encounter count. Production's ratio is a standing figure rather than a rate,
    so a shorter dataset holds proportionally fewer — the co-tenants are background, and the point
    is their weight in the tables, not their history.
    """
    scale = days / 365
    out = []
    for rank in range(1, total + 1):
        subjects = subjects_at_rank(rank) if rank <= with_subjects else 0
        out.append(CoTenant(
            rank=rank,
            organisation_id=first_organisation_id + rank,
            subjects=subjects,
            encounters=round(subjects * encounters_per_subject * scale),
        ))
    return out


def as_tenant_specs(co_tenants: list[CoTenant], *,
                    beneficiaries_per_village: int = 3000,
                    field_workers_per_village: int = 3) -> list[dep.TenantSpec]:
    """Turn them into something the generator already knows how to build.

    **Empty organisations are dropped.** They exist in production as a row in `organisation` and
    nothing else, so generating a hierarchy, a catchment and a user for each would add 473 tenants'
    worth of work to model rows that carry no data. They still matter — planner statistics and RLS
    span them — so they are created directly as rows rather than generated (see `empty_rows`).
    """
    specs = []
    for c in co_tenants:
        if c.empty:
            continue
        villages = max(1, round(c.subjects / beneficiaries_per_village))
        # Divide the org's actual subjects across its villages rather than assuming every village
        # is full. The tail is where this matters: production's 513th organisation holds a single
        # subject, and a full village would inflate it three thousandfold. Across ranks 156 to 513
        # that alone would add a million subjects the co-tenant set does not have.
        per_village = max(1, round(c.subjects / villages))
        specs.append(dep.TenantSpec(
            name=f"co-{c.rank:03d}",
            organisation_id=c.organisation_id,
            field_workers=max(1, villages * field_workers_per_village),
            field_workers_per_village=field_workers_per_village,
            beneficiaries_per_village=per_village,
            total_encounters=c.encounters,
        ))
    return specs


def empty_rows(co_tenants: list[CoTenant], *, audit_user_id: int = 1) -> list[dict]:
    """The organisations that hold nothing — a row each, and nothing else.

    Half of production's tenants are in this state, and they are not free: RLS predicates evaluate
    against the full organisation set, `rls_visible_org_ids_with_ancestors()` walks it, and the
    planner's statistics span it. Leaving them out would make the co-tenant set look more uniform
    than production is.
    """
    return [{"id": c.organisation_id,
             "uuid": f"org-co-{c.rank:03d}",
             "name": f"Co-tenant {c.rank}",
             "db_user": f"co_tenant_{c.rank}",
             "is_voided": False,
             "version": 0,
             "created_by_id": audit_user_id,
             "last_modified_by_id": audit_user_id}
            for c in co_tenants if c.empty]


def summarise(co_tenants: list[CoTenant]) -> str:
    total_s = sum(c.subjects for c in co_tenants)
    total_e = sum(c.encounters for c in co_tenants)
    empty = sum(1 for c in co_tenants if c.empty)
    lines = [f"co-tenants: {len(co_tenants)} organisations, {empty} of them empty "
             f"({100 * empty / len(co_tenants):.0f}%)", "",
             f"  subjects   {total_s:>12,}", f"  encounters {total_e:>12,}", ""]
    for k in (1, 5, 10, 50, 100):
        share = sum(c.subjects for c in co_tenants[:k]) / total_s
        lines.append(f"  top {k:<4} holds {share:>5.0%} of subjects")
    return "\n".join(lines)
