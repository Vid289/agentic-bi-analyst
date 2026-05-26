"""
Synthetic SaaS data generator for the Agentic BI Analyst.

Generates 2 years (Jan 2024 - Dec 2025) of realistic SaaS data for the
fictional company "Nimbus Analytics", with intentional patterns embedded
so the agent has interesting things to discover during investigations.

Embedded patterns (the agent should be able to surface these):
  1. Q3 2025 EMEA enterprise churn cluster — failed regional pricing experiment
     caused ~23 enterprise EMEA cancellations in Jul-Sep 2025.
  2. First-30-day usage predicts churn (low-onboarder cohort churns ~2x more —
     44% vs 24% — a strong, clean signal for a retention recommendation).
  3. Enterprise tier paradox: highest CSAT (~4.4) but most tickets per account
     (~10 per customer vs ~2 for starter).
  4. June 2025 Pro plan price increase ($199 -> $249) caused ~100 churns over
     Jun-Aug 2025, all citing "price".
  5. Outbound-acquired customers have ~1.6x baseline churn vs referral-acquired.

Run:  python database/generate_data.py
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

# ============================================================
# Configuration
# ============================================================

START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)
TODAY = END_DATE  # treat end-of-2025 as "now" for the demo

NUM_CUSTOMERS = 2000

INDUSTRIES = [
    "Software", "Financial Services", "Healthcare", "Retail",
    "Manufacturing", "Education", "Media", "Real Estate",
    "Logistics", "Professional Services",
]

REGIONS_COUNTRIES = {
    "NAM":   ["United States", "Canada", "Mexico"],
    "EMEA":  ["United Kingdom", "Germany", "France", "Netherlands", "Spain", "Italy", "Sweden"],
    "APAC":  ["Japan", "Australia", "Singapore", "India", "South Korea"],
    "LATAM": ["Brazil", "Argentina", "Chile", "Colombia"],
}
REGION_WEIGHTS = [0.45, 0.30, 0.18, 0.07]  # NAM is biggest, LATAM smallest

ACQUISITION_CHANNELS = ["organic", "paid_search", "content", "referral", "outbound"]
ACQUISITION_WEIGHTS = [0.30, 0.25, 0.15, 0.15, 0.15]

# Plans — note the June 2025 Pro price increase is handled separately
PLANS = [
    {"plan_id": 1, "plan_name": "Free",       "tier": "free",       "monthly_price": 0,    "seat_limit": 3},
    {"plan_id": 2, "plan_name": "Starter",    "tier": "starter",    "monthly_price": 49,   "seat_limit": 10},
    {"plan_id": 3, "plan_name": "Pro",        "tier": "pro",        "monthly_price": 199,  "seat_limit": 50},
    {"plan_id": 4, "plan_name": "Enterprise", "tier": "enterprise", "monthly_price": 999,  "seat_limit": None},
]
PLAN_BY_ID = {p["plan_id"]: p for p in PLANS}
INITIAL_PLAN_WEIGHTS = [0.40, 0.30, 0.20, 0.10]  # most start on Free

USAGE_EVENT_TYPES = [
    "login", "dashboard_view", "report_export", "api_call", "integration_used",
]

TICKET_CATEGORIES = ["billing", "bug", "feature_request", "onboarding", "integration", "other"]
TICKET_PRIORITIES = ["low", "medium", "high", "critical"]
TICKET_PRIORITY_WEIGHTS = [0.45, 0.35, 0.15, 0.05]

CHURN_REASONS = [
    "price", "missing_features", "competitor",
    "low_usage", "bad_support", "business_closure", "other",
]


# ============================================================
# Helpers
# ============================================================

def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def random_date_between(start: date, end: date) -> date:
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))


def weighted_choice(options, weights):
    return random.choices(options, weights=weights, k=1)[0]


@dataclass
class CustomerProfile:
    """Internal representation while generating; flattened to a DataFrame later."""
    customer_id: int
    company_name: str
    industry: str
    employee_count: int
    country: str
    region: str
    signup_date: date
    acquisition_channel: str
    initial_plan_id: int
    # Behavioral params (drive downstream generation)
    engagement_level: float        # 0-1, drives usage volume
    churn_propensity: float        # 0-1, baseline churn risk
    is_low_onboarder: bool          # ~20% — barely engages first 30 days
    is_low_first_30_day_user: bool  # percentile-flagged after usage generation


# ============================================================
# Step 1: Generate customers
# ============================================================

def generate_customers() -> list[CustomerProfile]:
    customers: list[CustomerProfile] = []
    # Signups grow over time (gentle growth curve)
    signup_dates = []
    for d in daterange(START_DATE, END_DATE):
        # Growth: ~2 signups/day at start, ~5/day by end
        days_elapsed = (d - START_DATE).days
        total_days = (END_DATE - START_DATE).days
        growth_factor = 1 + (days_elapsed / total_days) * 1.5
        # Mild seasonality: Q4 dip, Q1 bump
        month = d.month
        seasonal = 0.85 if month in (11, 12) else (1.15 if month in (1, 2) else 1.0)
        daily_signups = np.random.poisson(2.5 * growth_factor * seasonal)
        for _ in range(daily_signups):
            signup_dates.append(d)

    # Trim or pad to NUM_CUSTOMERS
    if len(signup_dates) > NUM_CUSTOMERS:
        signup_dates = random.sample(signup_dates, NUM_CUSTOMERS)
    while len(signup_dates) < NUM_CUSTOMERS:
        signup_dates.append(random_date_between(START_DATE, END_DATE))
    signup_dates.sort()

    for i, signup in enumerate(signup_dates, start=1):
        region = weighted_choice(list(REGIONS_COUNTRIES.keys()), REGION_WEIGHTS)
        country = random.choice(REGIONS_COUNTRIES[region])
        industry = random.choice(INDUSTRIES)
        # Realistic employee_count distribution (lognormal-ish)
        employee_count = int(np.clip(np.random.lognormal(mean=4.0, sigma=1.4), 5, 50000))
        channel = weighted_choice(ACQUISITION_CHANNELS, ACQUISITION_WEIGHTS)

        # Plan tier correlates with company size
        if employee_count < 25:
            plan_weights = [0.55, 0.30, 0.13, 0.02]
        elif employee_count < 200:
            plan_weights = [0.20, 0.40, 0.30, 0.10]
        elif employee_count < 1000:
            plan_weights = [0.05, 0.25, 0.45, 0.25]
        else:
            plan_weights = [0.02, 0.10, 0.30, 0.58]
        initial_plan_id = weighted_choice([1, 2, 3, 4], plan_weights)

        # Engagement level: most users are moderate, some are power users, some are dabblers
        engagement_level = float(np.clip(np.random.beta(2, 2), 0.05, 0.99))

        # Churn propensity baseline — boosted for outbound, dampened for referral
        base_churn = np.random.beta(2, 5)  # most customers low-churn, long tail
        if channel == "outbound":
            base_churn *= 1.6
        elif channel == "referral":
            base_churn *= 0.6
        base_churn = float(np.clip(base_churn, 0.02, 0.95))

        customers.append(CustomerProfile(
            customer_id=i,
            company_name=fake.company(),
            industry=industry,
            employee_count=employee_count,
            country=country,
            region=region,
            signup_date=signup,
            acquisition_channel=channel,
            initial_plan_id=initial_plan_id,
            engagement_level=engagement_level,
            churn_propensity=base_churn,
            is_low_onboarder=(random.random() < 0.20),  # 20% never properly onboard
            is_low_first_30_day_user=False,  # set later via percentile
        ))

    return customers


# ============================================================
# Step 2: Generate usage events
# ============================================================

def generate_usage_events(customers: list[CustomerProfile]) -> pd.DataFrame:
    """
    For each customer, generate daily usage events from signup to either
    churn or END_DATE. Also flag low-first-30-day customers so churn
    generation can use that signal.
    """
    rows = []
    event_id = 1
    first_30_counts: dict[int, int] = {}  # customer_id -> total first 30-day event_count

    for c in customers:
        first_30_count = 0
        days_active = (END_DATE - c.signup_date).days
        if days_active <= 0:
            first_30_counts[c.customer_id] = 0
            continue

        for offset in range(days_active + 1):
            d = c.signup_date + timedelta(days=offset)
            # Daily event probability scales with engagement
            # Free tier engagement is lower on average
            plan_engagement_multiplier = {1: 0.4, 2: 0.7, 3: 1.0, 4: 1.3}[c.initial_plan_id]
            # Weekday vs weekend (B2B — lower on weekends)
            dow_multiplier = 0.3 if d.weekday() >= 5 else 1.0
            # Low-onboarder dampening: first 30 days drastically suppressed
            onboarder_multiplier = 0.05 if (c.is_low_onboarder and offset < 30) else 1.0

            lam = (c.engagement_level * plan_engagement_multiplier
                   * dow_multiplier * onboarder_multiplier * 5)
            if lam < 0.05:
                continue
            num_events_today = np.random.poisson(lam)
            if num_events_today == 0:
                continue

            # Distribute across event types
            for _ in range(num_events_today):
                event_type = random.choice(USAGE_EVENT_TYPES)
                count = max(1, int(np.random.exponential(2)))
                rows.append({
                    "event_id": event_id,
                    "customer_id": c.customer_id,
                    "event_date": d,
                    "event_type": event_type,
                    "event_count": count,
                })
                event_id += 1
                if offset < 30:
                    first_30_count += count

        first_30_counts[c.customer_id] = first_30_count

    # Flag bottom-20% of first-30-day usage as "low first-30-day users"
    # This guarantees a meaningful cohort for the churn pattern.
    counts_array = np.array(list(first_30_counts.values()))
    threshold = float(np.percentile(counts_array, 20))
    for c in customers:
        c.is_low_first_30_day_user = first_30_counts[c.customer_id] <= threshold

    return pd.DataFrame(rows)


# ============================================================
# Step 3: Generate subscriptions, churn events, invoices
# ============================================================

def generate_subscriptions_churn_invoices(customers: list[CustomerProfile]):
    """
    Walks each customer's lifecycle: subscription periods, possible
    upgrades/downgrades, eventual churn, and monthly invoices.

    Embedded patterns:
      - Low-first-30-day users have 5x churn propensity
      - June 2025: Pro plan price increase causes churn spike on Pro
      - Q3 2025 EMEA: failed regional pricing experiment causes enterprise churn
    """
    sub_rows = []
    churn_rows = []
    invoice_rows = []
    sub_id = 1
    churn_id = 1
    invoice_id = 1

    PRO_PRICE_INCREASE_DATE = date(2025, 6, 1)
    EMEA_PRICING_EXPERIMENT_START = date(2025, 7, 1)
    EMEA_PRICING_EXPERIMENT_END = date(2025, 9, 30)

    for c in customers:
        current_plan_id = c.initial_plan_id
        current_start = c.signup_date
        seats = max(1, min(
            c.employee_count // 5,
            PLAN_BY_ID[current_plan_id]["seat_limit"] or c.employee_count,
        ))

        # Effective churn propensity with pattern adjustments
        churn_p = c.churn_propensity
        if c.is_low_first_30_day_user:
            churn_p = min(0.95, churn_p * 5.0)

        # Step through each month from signup until churn or END_DATE
        current_date = c.signup_date
        churned = False

        while current_date <= END_DATE and not churned:
            month_end = min(
                date(current_date.year + (1 if current_date.month == 12 else 0),
                     (current_date.month % 12) + 1, 1) - timedelta(days=1),
                END_DATE,
            )

            # ----- Pattern: June 2025 Pro plan price increase -----
            # Boost churn for Pro plan customers in June-Aug 2025
            month_churn_boost = 1.0
            if current_plan_id == 3 and date(2025, 6, 1) <= current_date <= date(2025, 8, 31):
                month_churn_boost *= 3.5

            # ----- Pattern: Q3 2025 EMEA enterprise churn -----
            # Failed regional pricing experiment causes enterprise EMEA churn
            if (c.region == "EMEA"
                    and current_plan_id == 4
                    and EMEA_PRICING_EXPERIMENT_START <= current_date <= EMEA_PRICING_EXPERIMENT_END):
                month_churn_boost *= 6.0

            # Monthly churn probability (converted from annualized propensity)
            monthly_churn_prob = 1 - (1 - churn_p) ** (1 / 12)
            monthly_churn_prob *= month_churn_boost

            # Free tier has much higher passive churn
            if current_plan_id == 1:
                monthly_churn_prob *= 2.5

            if random.random() < monthly_churn_prob:
                # Churn this month
                churn_date = random_date_between(current_date, month_end)
                # Determine reason
                if (current_plan_id == 3
                        and date(2025, 6, 1) <= churn_date <= date(2025, 8, 31)):
                    reason = "price"  # Pro increase
                elif (c.region == "EMEA"
                      and current_plan_id == 4
                      and EMEA_PRICING_EXPERIMENT_START <= churn_date <= EMEA_PRICING_EXPERIMENT_END):
                    reason = "price"  # EMEA experiment
                elif c.is_low_first_30_day_user:
                    reason = "low_usage"
                else:
                    reason = weighted_choice(
                        CHURN_REASONS,
                        [0.20, 0.18, 0.18, 0.15, 0.12, 0.07, 0.10],
                    )

                # MRR at churn
                price = PLAN_BY_ID[current_plan_id]["monthly_price"]
                if current_plan_id == 3 and churn_date >= PRO_PRICE_INCREASE_DATE:
                    price = 249  # increased price
                mrr = price * (seats if current_plan_id != 1 else 1)

                # Close current subscription as churned
                sub_rows.append({
                    "subscription_id": sub_id,
                    "customer_id": c.customer_id,
                    "plan_id": current_plan_id,
                    "start_date": current_start,
                    "end_date": churn_date,
                    "seats": seats,
                    "mrr": mrr,
                    "status": "churned",
                })
                sub_id += 1

                # Churn event (skip for free tier — they "churn" silently)
                if current_plan_id != 1:
                    churn_rows.append({
                        "churn_id": churn_id,
                        "customer_id": c.customer_id,
                        "churn_date": churn_date,
                        "reason_category": reason,
                        "mrr_lost": mrr,
                    })
                    churn_id += 1

                churned = True
                break

            # Possible upgrade/downgrade (small probability per month)
            if random.random() < 0.015 and current_plan_id < 4:
                # Upgrade
                new_plan = current_plan_id + 1
                sub_rows.append({
                    "subscription_id": sub_id,
                    "customer_id": c.customer_id,
                    "plan_id": current_plan_id,
                    "start_date": current_start,
                    "end_date": month_end,
                    "seats": seats,
                    "mrr": _compute_mrr(current_plan_id, seats, current_date),
                    "status": "upgraded",
                })
                sub_id += 1
                current_plan_id = new_plan
                current_start = month_end + timedelta(days=1)
                seats = max(seats, max(1, c.employee_count // 5))
                if PLAN_BY_ID[current_plan_id]["seat_limit"]:
                    seats = min(seats, PLAN_BY_ID[current_plan_id]["seat_limit"])

            current_date = month_end + timedelta(days=1)

        # If never churned, close out as active
        if not churned:
            sub_rows.append({
                "subscription_id": sub_id,
                "customer_id": c.customer_id,
                "plan_id": current_plan_id,
                "start_date": current_start,
                "end_date": None,
                "seats": seats,
                "mrr": _compute_mrr(current_plan_id, seats, END_DATE),
                "status": "active",
            })
            sub_id += 1

    # ----- Generate invoices from subscriptions -----
    subs_df = pd.DataFrame(sub_rows)
    for _, sub in subs_df.iterrows():
        if sub["plan_id"] == 1:
            continue  # free plan, no invoices
        start = sub["start_date"]
        end = sub["end_date"] if sub["end_date"] is not None else END_DATE
        # Monthly invoice on the start-day-of-month
        current = date(start.year, start.month, 1)
        while current <= end:
            # Payment status — mostly paid, sometimes failed/pending
            r = random.random()
            if r < 0.93:
                status = "paid"
                paid = current + timedelta(days=random.randint(0, 5))
            elif r < 0.98:
                status = "pending"
                paid = None
            else:
                status = "failed"
                paid = None

            invoice_rows.append({
                "invoice_id": invoice_id,
                "customer_id": sub["customer_id"],
                "subscription_id": sub["subscription_id"],
                "invoice_date": current,
                "amount": float(sub["mrr"]),
                "status": status,
                "paid_date": paid,
            })
            invoice_id += 1

            # Next month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

    return (
        pd.DataFrame(sub_rows),
        pd.DataFrame(churn_rows),
        pd.DataFrame(invoice_rows),
    )


def _compute_mrr(plan_id: int, seats: int, on_date: date) -> float:
    """Compute MRR for a given plan / seats / point in time (handles Pro price bump)."""
    if plan_id == 1:
        return 0.0
    price = PLAN_BY_ID[plan_id]["monthly_price"]
    if plan_id == 3 and on_date >= date(2025, 6, 1):
        price = 249  # Pro price increase
    return float(price * seats)


# ============================================================
# Step 4: Generate support tickets
# ============================================================

def generate_support_tickets(customers: list[CustomerProfile],
                             subs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enterprise tier generates more tickets per customer (more complex usage)
    but reports higher CSAT (white-glove support).
    """
    rows = []
    ticket_id = 1

    # Customer -> latest plan tier mapping (rough)
    last_plan_per_customer = (
        subs_df.sort_values("start_date").groupby("customer_id")["plan_id"].last()
    )

    for c in customers:
        last_plan = last_plan_per_customer.get(c.customer_id, c.initial_plan_id)
        # Tickets per year by tier
        tickets_per_year_by_tier = {1: 0.5, 2: 2, 3: 5, 4: 12}
        rate = tickets_per_year_by_tier.get(int(last_plan), 2)
        # Time active in years
        active_end = END_DATE
        sub_for_customer = subs_df[subs_df["customer_id"] == c.customer_id]
        churned = sub_for_customer[sub_for_customer["status"] == "churned"]
        if len(churned) > 0:
            active_end = churned["end_date"].max()
        years_active = max(0.05, (active_end - c.signup_date).days / 365.0)
        expected_tickets = rate * years_active
        num_tickets = np.random.poisson(expected_tickets)

        for _ in range(num_tickets):
            created = random_date_between(c.signup_date, active_end)
            priority = weighted_choice(TICKET_PRIORITIES, TICKET_PRIORITY_WEIGHTS)
            category = random.choice(TICKET_CATEGORIES)

            # Resolution time depends on priority
            resolve_days_by_priority = {"critical": 1, "high": 2, "medium": 4, "low": 7}
            base_resolve = resolve_days_by_priority[priority]
            resolve_days = max(0, int(np.random.exponential(base_resolve)))
            resolved = created + timedelta(days=resolve_days)
            if resolved > END_DATE:
                resolved = None
                csat = None
            else:
                # CSAT by tier (enterprise gets better)
                csat_means_by_tier = {1: 3.0, 2: 3.5, 3: 4.0, 4: 4.5}
                mean = csat_means_by_tier.get(int(last_plan), 3.5)
                csat = int(np.clip(round(np.random.normal(mean, 0.8)), 1, 5))

            rows.append({
                "ticket_id": ticket_id,
                "customer_id": c.customer_id,
                "created_date": created,
                "resolved_date": resolved,
                "priority": priority,
                "category": category,
                "csat_score": csat,
            })
            ticket_id += 1

    return pd.DataFrame(rows)


# ============================================================
# Step 5: Orchestrate
# ============================================================

def generate_all():
    print("⏳ Generating customers...")
    customers = generate_customers()
    print(f"   ✓ {len(customers)} customers")

    print("⏳ Generating usage events (this is the slow one)...")
    usage_df = generate_usage_events(customers)
    print(f"   ✓ {len(usage_df):,} usage events")

    print("⏳ Generating subscriptions, churn events, invoices...")
    subs_df, churn_df, invoices_df = generate_subscriptions_churn_invoices(customers)
    print(f"   ✓ {len(subs_df):,} subscriptions")
    print(f"   ✓ {len(churn_df):,} churn events")
    print(f"   ✓ {len(invoices_df):,} invoices")

    print("⏳ Generating support tickets...")
    tickets_df = generate_support_tickets(customers, subs_df)
    print(f"   ✓ {len(tickets_df):,} support tickets")

    # Flatten customers to DataFrame
    customers_df = pd.DataFrame([{
        "customer_id": c.customer_id,
        "company_name": c.company_name,
        "industry": c.industry,
        "employee_count": c.employee_count,
        "country": c.country,
        "region": c.region,
        "signup_date": c.signup_date,
        "acquisition_channel": c.acquisition_channel,
    } for c in customers])

    plans_df = pd.DataFrame(PLANS)

    return {
        "customers": customers_df,
        "plans": plans_df,
        "subscriptions": subs_df,
        "usage_events": usage_df,
        "support_tickets": tickets_df,
        "churn_events": churn_df,
        "invoices": invoices_df,
    }


if __name__ == "__main__":
    # Test run (writes nothing — that's init_db.py's job)
    print("Test generation (not persisting — use init_db.py to write to DuckDB):\n")
    tables = generate_all()
    print("\n📊 Summary:")
    for name, df in tables.items():
        print(f"   {name:20s} {len(df):>8,} rows")
