"""
LogiFlex Fleet Health Score
============================
Composite 0-100 operational health index.

Takes a pandas DataFrame (the user's upload) and optionally the output
from run_phase1_analysis() to avoid recomputing metrics.

Returns a structured dict ready for the report template and LLM narration.

Dependencies: pandas, numpy (already required by or_models.py)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


def sigmoid_score(value: float, midpoint: float, steepness: float = 0.1) -> float:
    """
    Maps a raw metric to 0-100 using a sigmoid curve.

    Steep in the operational range (where small changes matter most),
    flat at extremes (where the operation is either broken or excellent).

    Parameters
    ----------
    value : float
        The raw metric (e.g., on-time rate as 0-100)
    midpoint : float
        The value that maps to score 50 (the inflection point)
    steepness : float
        How sharp the transition is (higher = steeper curve)
    """
    try:
        return 100.0 / (1.0 + np.exp(-steepness * (value - midpoint)))
    except (OverflowError, FloatingPointError):
        return 0.0 if value < midpoint else 100.0


def percentile_score(value: float, values_array: np.ndarray, invert: bool = False) -> float:
    """
    Scores a value based on its percentile position within a distribution.

    Parameters
    ----------
    value : float
        The value to score
    values_array : np.ndarray
        The distribution to compare against
    invert : bool
        If True, lower values get higher scores (for cost metrics)
    """
    if len(values_array) < 2:
        return 50.0

    from scipy.stats import percentileofscore
    pct = percentileofscore(values_array, value, kind='rank')

    if invert:
        pct = 100.0 - pct

    return np.clip(pct, 0, 100)


def compute_fleet_score(
    df: pd.DataFrame,
    phase1_results: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Computes the LogiFlex Fleet Health Score (0-100).

    Parameters
    ----------
    df : pd.DataFrame
        The cleaned user upload with standard column names.
    phase1_results : dict, optional
        Output from run_phase1_analysis(). If provided, reuses computed
        metrics instead of recalculating. Pass this when you've already
        run the OR models.

    Returns
    -------
    dict with keys:
        - score: int (0-100 composite)
        - grade: str ('Critical', 'Needs work', 'Competent', 'Strong', 'Elite')
        - dimensions: list of dicts, each with name, score, weight, contribution
        - biggest_drag: dict with dimension name and point impact
        - biggest_strength: dict with dimension name and point impact
        - improvement_scenario: dict showing what score would be if drag improved
        - data_completeness: dict of which dimensions were computable
    """
    work = df.copy()

    # Standardize delivery status
    if "DeliveryStatus" in work.columns:
        work["is_ontime"] = work["DeliveryStatus"].str.strip().str.lower() == "on-time"
    else:
        work["is_ontime"] = np.nan

    work["FreightCost"] = pd.to_numeric(work.get("FreightCost"), errors="coerce")

    has_distance = "Distance_Miles" in work.columns and work["Distance_Miles"].notna().sum() > 0
    has_fuel = "FuelCost" in work.columns and work["FuelCost"].notna().sum() > 0
    has_delivery = "DeliveryStatus" in work.columns and work["DeliveryStatus"].notna().sum() > 0
    has_carriers = "CarrierName" in work.columns
    has_origins = "OriginCity" in work.columns and "DestinationCity" in work.columns

    dimensions = []
    weights_used = {}

    # Default weights
    default_weights = {
        "on_time_delivery": 0.30,
        "cost_efficiency": 0.25,
        "fuel_efficiency": 0.20,
        "route_utilization": 0.15,
        "cost_predictability": 0.10,
    }

    # =====================================================================
    # DIMENSION 1: ON-TIME DELIVERY (weight: 30%)
    # =====================================================================
    if has_delivery:
        fleet_otd = work["is_ontime"].mean() * 100  # as percentage

        # Sigmoid centered at 75% (industry midpoint for SMB)
        # Steepness 0.1: score ~20 at 50%, ~50 at 75%, ~88 at 90%
        otd_score = sigmoid_score(fleet_otd, midpoint=75, steepness=0.1)

        # Per-carrier breakdown for detail
        carrier_otd = {}
        if has_carriers:
            for c, grp in work.groupby("CarrierName"):
                carrier_otd[c] = round(grp["is_ontime"].mean() * 100, 1)

        dimensions.append({
            "id": "on_time_delivery",
            "name": "On-time delivery",
            "score": round(otd_score, 1),
            "weight": default_weights["on_time_delivery"],
            "raw_value": round(fleet_otd, 1),
            "raw_unit": "%",
            "benchmark": "Industry median: 85%",
            "detail": carrier_otd,
        })
        weights_used["on_time_delivery"] = default_weights["on_time_delivery"]

    # =====================================================================
    # DIMENSION 2: COST EFFICIENCY (weight: 25%)
    # =====================================================================
    if has_distance and has_origins:
        work["cost_per_mile"] = np.where(
            work["Distance_Miles"] > 0,
            work["FreightCost"] / work["Distance_Miles"],
            np.nan,
        )

        work["lane"] = work["OriginCity"].str.strip() + " → " + work["DestinationCity"].str.strip()
        fleet_median_cpm = work["cost_per_mile"].dropna().median()

        lane_cpms = work.groupby("lane")["cost_per_mile"].median().dropna()
        if len(lane_cpms) > 0 and fleet_median_cpm > 0:
            pct_above = (lane_cpms > fleet_median_cpm).mean()

            # Score component 1: how good is the fleet median vs. a reference range
            # For SMB trucking, $0.35-0.50/mile is typical
            cpm_score = sigmoid_score(
                100 - (fleet_median_cpm / 0.50 * 100),  # invert: lower cost = higher input
                midpoint=50,
                steepness=0.08,
            )

            # Score component 2: what percentage of lanes are efficient
            lane_eff_score = (1 - pct_above) * 100

            cost_eff_score = 0.6 * cpm_score + 0.4 * lane_eff_score

            dimensions.append({
                "id": "cost_efficiency",
                "name": "Cost efficiency",
                "score": round(np.clip(cost_eff_score, 0, 100), 1),
                "weight": default_weights["cost_efficiency"],
                "raw_value": round(fleet_median_cpm, 4),
                "raw_unit": "$/mile",
                "benchmark": f"{len(lane_cpms)} lanes analyzed, {round(pct_above*100)}% above median",
                "detail": {
                    "fleet_median_cpm": round(fleet_median_cpm, 4),
                    "pct_lanes_above_median": round(pct_above * 100, 1),
                    "total_lanes": len(lane_cpms),
                },
            })
            weights_used["cost_efficiency"] = default_weights["cost_efficiency"]

    # =====================================================================
    # DIMENSION 3: FUEL EFFICIENCY (weight: 20%)
    # =====================================================================
    if has_fuel and has_distance:
        work["FuelCost"] = pd.to_numeric(work["FuelCost"], errors="coerce")
        work["fuel_per_mile"] = np.where(
            work["Distance_Miles"] > 0,
            work["FuelCost"] / work["Distance_Miles"],
            np.nan,
        )

        fleet_fuel_mean = work["fuel_per_mile"].dropna().mean()

        if "DriverName" in work.columns:
            driver_fuel = work.groupby("DriverName")["fuel_per_mile"].mean().dropna()
            if len(driver_fuel) >= 2:
                fuel_cv = driver_fuel.std() / driver_fuel.mean() if driver_fuel.mean() > 0 else 1.0
            else:
                fuel_cv = 0.5
        else:
            fuel_cv = 0.5

        # Lower fuel cost = better. Score against typical range $0.15-$0.40/mile
        fuel_pct_score = sigmoid_score(
            100 - (fleet_fuel_mean / 0.40 * 100),
            midpoint=40,
            steepness=0.08,
        )

        # Penalize high variance across drivers (inconsistency)
        consistency_score = (1 - np.clip(fuel_cv, 0, 1)) * 100

        fuel_score = 0.7 * fuel_pct_score + 0.3 * consistency_score

        dimensions.append({
            "id": "fuel_efficiency",
            "name": "Fuel efficiency",
            "score": round(np.clip(fuel_score, 0, 100), 1),
            "weight": default_weights["fuel_efficiency"],
            "raw_value": round(fleet_fuel_mean, 4),
            "raw_unit": "$/mile fuel",
            "benchmark": f"Driver CV: {round(fuel_cv, 3)} (lower = more consistent)",
            "detail": {
                "fleet_avg_fuel_per_mile": round(fleet_fuel_mean, 4),
                "driver_fuel_cv": round(fuel_cv, 3),
            },
        })
        weights_used["fuel_efficiency"] = default_weights["fuel_efficiency"]

    # =====================================================================
    # DIMENSION 4: ROUTE UTILIZATION (weight: 15%)
    # =====================================================================
    if has_origins:
        work["lane"] = work["OriginCity"].str.strip() + " → " + work["DestinationCity"].str.strip()
        lane_counts = work.groupby("lane").size()
        total_lanes = len(lane_counts)

        if total_lanes > 0:
            avg_shipments_per_lane = lane_counts.mean()
            pct_underused = (lane_counts <= 2).mean()

            # Utilization score: higher avg shipments/lane = better
            util_score = sigmoid_score(avg_shipments_per_lane, midpoint=5, steepness=0.5)

            # Underused lanes penalty
            underused_score = (1 - pct_underused) * 100

            # Network balance: check inbound vs outbound per city
            city_out = work.groupby("OriginCity").size()
            city_in = work.groupby("DestinationCity").size()
            all_cities = set(city_out.index) | set(city_in.index)

            imbalance_ratios = []
            for city in all_cities:
                out_vol = city_out.get(city, 0)
                in_vol = city_in.get(city, 0)
                total = out_vol + in_vol
                if total > 0:
                    imbalance = abs(out_vol - in_vol) / total
                    imbalance_ratios.append(imbalance)

            avg_imbalance = np.mean(imbalance_ratios) if imbalance_ratios else 0.5
            balance_score = (1 - avg_imbalance) * 100

            route_score = (
                0.4 * util_score
                + 0.3 * underused_score
                + 0.3 * balance_score
            )

            dimensions.append({
                "id": "route_utilization",
                "name": "Route utilization",
                "score": round(np.clip(route_score, 0, 100), 1),
                "weight": default_weights["route_utilization"],
                "raw_value": round(avg_shipments_per_lane, 1),
                "raw_unit": "shipments/lane avg",
                "benchmark": f"{total_lanes} lanes, {round(pct_underused*100)}% underused, {round(avg_imbalance*100)}% network imbalance",
                "detail": {
                    "total_lanes": total_lanes,
                    "avg_shipments_per_lane": round(avg_shipments_per_lane, 1),
                    "pct_underused_lanes": round(pct_underused * 100, 1),
                    "network_imbalance": round(avg_imbalance * 100, 1),
                },
            })
            weights_used["route_utilization"] = default_weights["route_utilization"]

    # =====================================================================
    # DIMENSION 5: COST PREDICTABILITY (weight: 10%)
    # =====================================================================
    if has_carriers and has_origins:
        work["lane"] = work["OriginCity"].str.strip() + " → " + work["DestinationCity"].str.strip()
        work["lane_carrier"] = work["lane"] + " | " + work["CarrierName"].str.strip()

        lc_stats = work.groupby("lane_carrier")["FreightCost"].agg(["mean", "std", "count"])
        lc_stats = lc_stats[lc_stats["count"] >= 3]  # only groups with enough data

        if len(lc_stats) > 0:
            # CV per lane-carrier pair (lower = more predictable)
            lc_stats["cv"] = np.where(
                lc_stats["mean"] > 0,
                lc_stats["std"] / lc_stats["mean"],
                1.0,
            )
            lc_stats["cv"] = lc_stats["cv"].fillna(1.0)

            avg_cv = np.average(lc_stats["cv"], weights=lc_stats["count"])

            # Anomaly rate (from Phase 1 results if available)
            anomaly_pct = 0.0
            if phase1_results and "cost_anomalies" in phase1_results:
                ca = phase1_results["cost_anomalies"]
                if ca.get("total_shipments_analyzed", 0) > 0:
                    anomaly_pct = ca.get("pct_anomalous", 0)

            # Score: lower CV = higher score
            cv_score = (1 - np.clip(avg_cv, 0, 1)) * 100

            # Anomaly penalty: cap at 10% anomaly rate
            anomaly_score = (1 - np.clip(anomaly_pct / 10, 0, 1)) * 100

            pred_score = 0.7 * cv_score + 0.3 * anomaly_score

            dimensions.append({
                "id": "cost_predictability",
                "name": "Cost predictability",
                "score": round(np.clip(pred_score, 0, 100), 1),
                "weight": default_weights["cost_predictability"],
                "raw_value": round(avg_cv, 4),
                "raw_unit": "avg CV",
                "benchmark": f"Anomaly rate: {round(anomaly_pct, 1)}%",
                "detail": {
                    "avg_cost_cv": round(avg_cv, 4),
                    "anomaly_pct": round(anomaly_pct, 1),
                    "lane_carrier_groups_analyzed": len(lc_stats),
                },
            })
            weights_used["cost_predictability"] = default_weights["cost_predictability"]

    # =====================================================================
    # COMPOSITE SCORE
    # =====================================================================
    if not dimensions:
        return {
            "score": 0,
            "grade": "Insufficient data",
            "dimensions": [],
            "biggest_drag": None,
            "biggest_strength": None,
            "improvement_scenario": None,
            "data_completeness": {
                "has_delivery_status": has_delivery,
                "has_distance": has_distance,
                "has_fuel": has_fuel,
                "has_carriers": has_carriers,
                "has_origins": has_origins,
                "dimensions_computed": 0,
            },
        }

    # Redistribute weights proportionally among computable dimensions
    total_weight = sum(d["weight"] for d in dimensions)
    for d in dimensions:
        d["effective_weight"] = d["weight"] / total_weight
        d["contribution"] = d["score"] * d["effective_weight"]

    composite = sum(d["contribution"] for d in dimensions)
    composite = int(round(np.clip(composite, 0, 100)))

    # Grade assignment
    if composite >= 90:
        grade = "Elite"
    elif composite >= 75:
        grade = "Strong"
    elif composite >= 60:
        grade = "Competent"
    elif composite >= 40:
        grade = "Needs work"
    else:
        grade = "Critical"

    # Biggest drag and strength
    for d in dimensions:
        d["gap"] = d["effective_weight"] * (100 - d["score"])
        d["surplus"] = d["effective_weight"] * d["score"]

    sorted_by_gap = sorted(dimensions, key=lambda x: x["gap"], reverse=True)
    biggest_drag = {
        "dimension": sorted_by_gap[0]["name"],
        "dimension_score": sorted_by_gap[0]["score"],
        "point_impact": round(sorted_by_gap[0]["gap"], 1),
    }

    sorted_by_surplus = sorted(dimensions, key=lambda x: x["surplus"], reverse=True)
    biggest_strength = {
        "dimension": sorted_by_surplus[0]["name"],
        "dimension_score": sorted_by_surplus[0]["score"],
        "point_impact": round(sorted_by_surplus[0]["surplus"], 1),
    }

    # Improvement scenario: what if biggest drag improved to 75?
    drag_dim = sorted_by_gap[0]
    hypothetical_score = composite + drag_dim["effective_weight"] * (75 - drag_dim["score"])
    hypothetical_score = int(round(np.clip(hypothetical_score, 0, 100)))

    improvement_scenario = {
        "dimension": drag_dim["name"],
        "current_score": drag_dim["score"],
        "improved_to": 75,
        "current_fleet_score": composite,
        "projected_fleet_score": hypothetical_score,
        "point_gain": hypothetical_score - composite,
    }

    # Clean output
    output_dimensions = []
    for d in dimensions:
        output_dimensions.append({
            "name": d["name"],
            "score": d["score"],
            "weight": round(d["effective_weight"] * 100),
            "raw_value": d.get("raw_value"),
            "raw_unit": d.get("raw_unit"),
            "benchmark": d.get("benchmark"),
        })

    return {
        "score": composite,
        "grade": grade,
        "dimensions": output_dimensions,
        "biggest_drag": biggest_drag,
        "biggest_strength": biggest_strength,
        "improvement_scenario": improvement_scenario,
        "data_completeness": {
            "has_delivery_status": has_delivery,
            "has_distance": has_distance,
            "has_fuel": has_fuel,
            "has_carriers": has_carriers,
            "has_origins": has_origins,
            "dimensions_computed": len(dimensions),
            "dimensions_possible": 5,
        },
    }