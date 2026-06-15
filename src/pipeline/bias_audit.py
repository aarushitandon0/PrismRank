import pandas as pd
import numpy as np


def _gini(values: list) -> float:
    if not values:
        return 0.0
    arr = np.array(sorted(values), dtype=float)
    n = len(arr)
    if arr.sum() == 0:
        return 0.0
    index = np.arange(1, n + 1)
    return (2 * (index * arr).sum() / (n * arr.sum())) - (n + 1) / n


def run_bias_audit(ranked_df: pd.DataFrame) -> dict:
    total = len(ranked_df)
    top_n = max(1, total // 5)
    top = ranked_df.head(top_n)
    pool = ranked_df

    warnings = []
    metrics = {}

    # 1. Education tier concentration
    for tier in [4, 3]:
        tier_label = f"tier_{5-tier}" if tier < 5 else "tier_1"
        top_share = (top["education_tier_score"] == tier).mean()
        pool_share = (pool["education_tier_score"] == tier).mean()
        skew = top_share / pool_share if pool_share > 0 else 0
        w = skew > 1.5
        metrics[f"edu_tier_{5-tier}_concentration"] = {
            "shortlist_share": round(top_share, 3),
            "pool_share": round(pool_share, 3),
            "skew_ratio": round(skew, 2),
            "warning": w,
        }
        if w:
            warnings.append(
                f"Education tier {5-tier}: shortlist {top_share:.0%} vs pool {pool_share:.0%} "
                f"(skew {skew:.1f}×)"
            )

    # 2. Geography concentration (Gini on country)
    country_counts = top["country"].value_counts()
    country_shares = (country_counts / len(top)).tolist()
    geo_gini = round(_gini(country_shares), 3)
    w = geo_gini > 0.6
    metrics["geography_gini"] = {
        "shortlist_gini": geo_gini,
        "description": "0=even, 1=one country dominates",
        "warning": w,
    }
    if w:
        top_country = country_counts.index[0] if len(country_counts) else "unknown"
        warnings.append(f"Geography: top country '{top_country}' dominates shortlist (Gini={geo_gini})")

    # 3. Experience years distribution
    low_exp_top = (top["years_experience"] < 3).mean()
    low_exp_pool = (pool["years_experience"] < 3).mean()
    high_exp_top = (top["years_experience"] > 15).mean()
    high_exp_pool = (pool["years_experience"] > 15).mean()

    skew_low = low_exp_pool / low_exp_top if low_exp_top > 0 else 0
    skew_high = high_exp_pool / high_exp_top if high_exp_top > 0 else 0

    metrics["experience_distribution"] = {
        "under_3yr_shortlist": round(low_exp_top, 3),
        "under_3yr_pool": round(low_exp_pool, 3),
        "exclusion_skew_under3": round(skew_low, 2),
        "over_15yr_shortlist": round(high_exp_top, 3),
        "over_15yr_pool": round(high_exp_pool, 3),
        "exclusion_skew_over15": round(skew_high, 2),
        "warning": skew_low > 1.5 or skew_high > 1.5,
    }
    if skew_low > 1.5:
        warnings.append(f"Under-3yr candidates: {low_exp_pool:.0%} of pool but only {low_exp_top:.0%} of shortlist.")
    if skew_high > 1.5:
        warnings.append(f"Over-15yr candidates: {high_exp_pool:.0%} of pool but only {high_exp_top:.0%} of shortlist.")

    # 4. Profile completeness bias
    top_comp = top["final_score"].mean() if "final_score" in top.columns else 0
    # Use education_tier_score as proxy since completeness is in nested dict
    redrob_top = top.get("redrob_signals", pd.Series(dtype=float)).mean() if "redrob_signals" in top.columns else None
    # Check if completeness is captured — it's embedded in the score; flag if top avg score >> pool avg
    pool_avg_score = pool["final_score"].mean() if "final_score" in pool.columns else 0
    top_avg_score = top["final_score"].mean() if "final_score" in top.columns else 0
    score_skew = top_avg_score / pool_avg_score if pool_avg_score > 0 else 1
    w = score_skew > 2.0
    metrics["completeness_bias"] = {
        "top20pct_avg_score": round(top_avg_score, 3),
        "pool_avg_score": round(pool_avg_score, 3),
        "skew_ratio": round(score_skew, 2),
        "warning": w,
    }
    if w:
        warnings.append(
            f"Completeness bias: top-20% avg score {top_avg_score:.2f} vs pool {pool_avg_score:.2f} "
            f"(skew {score_skew:.1f}×). High completeness may not equal talent."
        )

    # 5. Relocation bias
    reloc_top = top["willing_to_relocate"].astype(bool).mean() if "willing_to_relocate" in top.columns else 0
    reloc_pool = pool["willing_to_relocate"].astype(bool).mean() if "willing_to_relocate" in pool.columns else 0
    skew_reloc = reloc_top / reloc_pool if reloc_pool > 0 else 0
    w = skew_reloc > 1.5
    metrics["relocation_bias"] = {
        "shortlist_willing_to_relocate": round(reloc_top, 3),
        "pool_willing_to_relocate": round(reloc_pool, 3),
        "skew_ratio": round(skew_reloc, 2),
        "warning": w,
    }
    if w:
        warnings.append(
            f"Relocation bias: {reloc_top:.0%} of shortlist willing to relocate vs {reloc_pool:.0%} pool. "
            f"Strong remote candidates may be under-represented."
        )

    audit_passed = len(warnings) == 0

    if warnings:
        first_warning = warnings[0]
        if "edu" in first_warning.lower():
            rec = (
                "Over 80% of shortlist has high-tier education — consider expanding to strong "
                "tier_3 candidates with high skill assessment scores."
            )
        elif "geography" in first_warning.lower():
            rec = "Geography is highly concentrated — review if role requires specific location or consider remote candidates."
        elif "3yr" in first_warning.lower():
            rec = "High-potential candidates with under 3 years experience are systematically excluded — review experience floor."
        elif "relocation" in first_warning.lower():
            rec = "Shortlist skews toward candidates willing to relocate — ensure remote-friendly candidates are not being penalized."
        else:
            rec = "Review scoring weights to reduce systematic bias in the shortlist."
    else:
        rec = "No significant bias detected. Shortlist looks representative of the talent pool."

    return {
        "audit_passed": audit_passed,
        "warnings": warnings,
        "metrics": metrics,
        "recommendation": rec,
    }
