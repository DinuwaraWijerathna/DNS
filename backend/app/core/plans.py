from __future__ import annotations

# ─── SERVER-SIDE SOURCE OF TRUTH FOR PLAN LIMITS ─────────────────────────
# The frontend pricing page only displays these numbers for marketing
# purposes - it never enforces them. Enforcement happens here, on the
# backend, using the plan stored on the user's row in Supabase (set when
# their PayPal payment is captured - see payments.py).
#
# "None" as a limit means unlimited domains.
PLAN_DOMAIN_LIMITS: dict[str, int | None] = {
    "individual": 5,
    "smallbusiness": 25,
    "business": 250,
    "enterprise": None,
}

# Anyone who has registered an account but hasn't purchased a plan yet
# (users.plan is NULL) still gets to try the platform, but only with a
# single domain, so the product is usable in a demo without a plan while
# still making it obvious that an upgrade is needed for more.
TRIAL_DOMAIN_LIMIT = 1


def get_domain_limit(plan: str | None) -> int | None:
    """Return the max number of domains allowed for a plan (None = unlimited)."""
    if not plan:
        return TRIAL_DOMAIN_LIMIT
    return PLAN_DOMAIN_LIMITS.get(plan, TRIAL_DOMAIN_LIMIT)
