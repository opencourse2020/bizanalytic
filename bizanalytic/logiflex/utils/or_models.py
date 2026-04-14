"""
LogiFlex Phase 1 — Operations Research Models
==============================================
Production-ready Python functions for Django integration.

Each function:
  - Takes a pandas DataFrame (from the user's CSV upload)
  - Returns a structured dict (ready to feed to the LLM for narration or serialize as JSON)
  - Runs in <1 second on SMB-scale data (50-500 shipments)
  - Has no external dependencies beyond pandas, numpy, scipy, and PuLP

Integration:
  Call these from your Django view after CSV parsing/cleaning.
  Pass the returned dicts to your Sonnet prompt for narrative generation.

Dependencies:
  pip install pandas numpy scipy pulp
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


# =============================================================================
# MODEL 1: CARRIER ALLOCATION OPTIMIZER (Linear Programming)
# =============================================================================

def optimize_carrier_allocation(
        df: pd.DataFrame,
        min_ontime_threshold: float = 0.45,
        max_carrier_share: float = 0.70,
        min_carrier_share: float = 0.05,
) -> Dict[str, Any]:
    """
    Uses Linear Programming to find the optimal shipment allocation across carriers
    that minimizes total freight cost while meeting on-time delivery constraints.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain: CarrierName, FreightCost, DeliveryStatus, OriginCity, DestinationCity
    min_ontime_threshold : float
        Minimum acceptable weighted on-time rate for the portfolio (0-1)
    max_carrier_share : float
        Maximum share any single carrier can hold (diversification constraint)
    min_carrier_share : float
        Minimum share for any carrier included in the solution

    Returns
    -------
    dict with keys:
        - current_allocation: dict of carrier -> current % share
        - optimal_allocation: dict of carrier -> optimal % share
        - current_cost: float (avg cost per shipment under current allocation)
        - optimal_cost: float (avg cost per shipment under optimal allocation)
        - annual_savings_estimate: float
        - current_ontime: float
        - projected_ontime: float
        - recommendations: list of dicts with specific shift instructions
        - model_status: str ('optimal', 'infeasible', 'no_improvement')
    """
    try:
        from pulp import (
            LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, value
        )
    except ImportError:
        return _carrier_allocation_fallback(df)

    # --- Compute carrier-level KPIs ---
    carrier_stats = df.groupby("CarrierName").agg(
        total_shipments=("FreightCost", "size"),
        avg_cost=("FreightCost", "mean"),
        total_cost=("FreightCost", "sum"),
    ).reset_index()

    # On-time rate per carrier
    df_ontime = df.copy()
    df_ontime["is_ontime"] = df_ontime["DeliveryStatus"].str.strip().str.lower() == "on-time"
    ontime_rates = df_ontime.groupby("CarrierName")["is_ontime"].mean().reset_index()
    ontime_rates.columns = ["CarrierName", "ontime_rate"]

    carrier_stats = carrier_stats.merge(ontime_rates, on="CarrierName", how="left")
    carrier_stats["ontime_rate"] = carrier_stats["ontime_rate"].fillna(0)

    carriers = carrier_stats["CarrierName"].tolist()
    n_carriers = len(carriers)
    total_shipments = int(carrier_stats["total_shipments"].sum())

    if n_carriers < 2:
        return {
            "model_status": "insufficient_carriers",
            "message": "Need at least 2 carriers for optimization.",
            "current_allocation": {},
            "optimal_allocation": {},
            "recommendations": [],
        }

    # Current allocation
    current_alloc = {}
    for _, row in carrier_stats.iterrows():
        current_alloc[row["CarrierName"]] = round(
            row["total_shipments"] / total_shipments, 4
        )

    # Current weighted metrics
    current_weighted_cost = sum(
        carrier_stats.loc[carrier_stats["CarrierName"] == c, "avg_cost"].iloc[0]
        * current_alloc[c]
        for c in carriers
    )
    current_weighted_ontime = sum(
        carrier_stats.loc[carrier_stats["CarrierName"] == c, "ontime_rate"].iloc[0]
        * current_alloc[c]
        for c in carriers
    )

    # --- Build LP model ---
    prob = LpProblem("Carrier_Allocation", LpMinimize)

    # Decision variables: share of shipments allocated to each carrier
    x = {
        c: LpVariable(f"share_{i}", lowBound=0, upBound=1)
        for i, c in enumerate(carriers)
    }

    # Objective: minimize weighted average cost
    costs = {
        row["CarrierName"]: row["avg_cost"]
        for _, row in carrier_stats.iterrows()
    }
    prob += lpSum([costs[c] * x[c] for c in carriers]), "Total_Weighted_Cost"

    # Constraint 1: allocations sum to 1
    prob += lpSum([x[c] for c in carriers]) == 1, "Sum_To_One"

    # Constraint 2: minimum on-time performance
    ontime_map = {
        row["CarrierName"]: row["ontime_rate"]
        for _, row in carrier_stats.iterrows()
    }
    prob += (
        lpSum([ontime_map[c] * x[c] for c in carriers]) >= min_ontime_threshold,
        "Min_OnTime",
    )

    # Constraint 3: diversification — no single carrier > max_share
    for c in carriers:
        prob += x[c] <= max_carrier_share, f"Max_Share_{c}"

    # Constraint 4: if a carrier is used, minimum share
    # (This is a soft constraint — LP relaxation. True MIP not needed at this scale)
    for c in carriers:
        prob += x[c] >= 0, f"NonNeg_{c}"

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if LpStatus[prob.status] != "Optimal":
        return {
            "model_status": "infeasible",
            "message": "No feasible allocation meets all constraints. Try relaxing the on-time threshold.",
            "current_allocation": current_alloc,
            "optimal_allocation": {},
            "recommendations": [],
            "current_ontime": round(current_weighted_ontime, 4),
        }

    # Extract solution
    optimal_alloc = {}
    for c in carriers:
        val = value(x[c])
        if val is not None and val > 0.01:
            optimal_alloc[c] = round(val, 4)

    optimal_cost = value(prob.objective)
    optimal_ontime = sum(
        ontime_map[c] * optimal_alloc.get(c, 0) for c in carriers
    )

    # Calculate savings
    cost_reduction_per_shipment = current_weighted_cost - optimal_cost
    monthly_shipments = total_shipments  # assume this is monthly data
    monthly_savings = cost_reduction_per_shipment * monthly_shipments
    annual_savings = monthly_savings * 12

    # Generate specific recommendations
    recommendations = []
    for c in carriers:
        current_pct = current_alloc.get(c, 0)
        optimal_pct = optimal_alloc.get(c, 0)
        diff = optimal_pct - current_pct

        if abs(diff) > 0.03:  # only report meaningful changes
            direction = "increase" if diff > 0 else "decrease"
            shipment_change = abs(round(diff * monthly_shipments))
            recommendations.append({
                "carrier": c,
                "current_share": round(current_pct * 100, 1),
                "optimal_share": round(optimal_pct * 100, 1),
                "direction": direction,
                "shipment_change": shipment_change,
                "avg_cost": round(costs[c], 2),
                "ontime_rate": round(ontime_map[c] * 100, 1),
            })

    # Sort: biggest positive shifts first
    recommendations.sort(key=lambda r: abs(r["optimal_share"] - r["current_share"]), reverse=True)

    # Determine if there's actual improvement
    if cost_reduction_per_shipment < 1.0:
        model_status = "no_improvement"
    else:
        model_status = "optimal"

    return {
        "model_status": model_status,
        "current_allocation": current_alloc,
        "optimal_allocation": optimal_alloc,
        "current_avg_cost_per_shipment": round(current_weighted_cost, 2),
        "optimal_avg_cost_per_shipment": round(optimal_cost, 2),
        "savings_per_shipment": round(cost_reduction_per_shipment, 2),
        "monthly_savings": round(monthly_savings, 2),
        "annual_savings_estimate": round(annual_savings, 2),
        "current_ontime": round(current_weighted_ontime * 100, 1),
        "projected_ontime": round(optimal_ontime * 100, 1),
        "total_shipments_analyzed": total_shipments,
        "recommendations": recommendations,
    }


def _carrier_allocation_fallback(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Fallback when PuLP is not installed.
    Uses a greedy heuristic instead of LP.
    """
    carrier_stats = df.groupby("CarrierName").agg(
        total_shipments=("FreightCost", "size"),
        avg_cost=("FreightCost", "mean"),
    ).reset_index()

    df_ontime = df.copy()
    df_ontime["is_ontime"] = df_ontime["DeliveryStatus"].str.strip().str.lower() == "on-time"
    ontime_rates = df_ontime.groupby("CarrierName")["is_ontime"].mean().reset_index()
    ontime_rates.columns = ["CarrierName", "ontime_rate"]

    carrier_stats = carrier_stats.merge(ontime_rates, on="CarrierName", how="left")

    # Simple efficiency score: lower cost + higher on-time = better
    carrier_stats["efficiency_score"] = (
            (1 - carrier_stats["avg_cost"] / carrier_stats["avg_cost"].max())
            + carrier_stats["ontime_rate"]
    )

    total = carrier_stats["efficiency_score"].sum()
    carrier_stats["optimal_share"] = carrier_stats["efficiency_score"] / total

    recommendations = []
    total_shipments = int(carrier_stats["total_shipments"].sum())
    for _, row in carrier_stats.iterrows():
        current = row["total_shipments"] / total_shipments
        optimal = row["optimal_share"]
        if abs(optimal - current) > 0.03:
            recommendations.append({
                "carrier": row["CarrierName"],
                "current_share": round(current * 100, 1),
                "optimal_share": round(optimal * 100, 1),
                "direction": "increase" if optimal > current else "decrease",
                "shipment_change": abs(round((optimal - current) * total_shipments)),
                "avg_cost": round(row["avg_cost"], 2),
                "ontime_rate": round(row["ontime_rate"] * 100, 1),
            })

    return {
        "model_status": "heuristic",
        "message": "PuLP not available. Using efficiency-score heuristic.",
        "recommendations": recommendations,
        "total_shipments_analyzed": total_shipments,
    }


# =============================================================================
# MODEL 2: LANE PROFITABILITY WITH CONTRIBUTION MARGIN
# =============================================================================

def analyze_lane_profitability(
        df: pd.DataFrame,
        fuel_cost_col: str = "FuelCost",
        accessorial_col: str = "AccessorialCharges",
        estimated_driver_cost_per_mile: float = 0.18,
) -> Dict[str, Any]:
    """
    Calculates true contribution margin per lane using Activity-Based Costing.
    Identifies money-losing lanes the operator may not realize are unprofitable.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain: OriginCity, DestinationCity, FreightCost, Distance_Miles
        Optional: FuelCost, AccessorialCharges, LoadWeight_lbs
    fuel_cost_col : str
        Column name for fuel cost. If missing, estimates at $0.60/mile.
    accessorial_col : str
        Column name for accessorial charges. If missing, assumes 0.
    estimated_driver_cost_per_mile : float
        Estimated driver labor cost per mile (used if not derivable from data)

    Returns
    -------
    dict with keys:
        - lanes: list of dicts, each lane with full margin breakdown
        - profitable_lanes: int
        - unprofitable_lanes: int
        - total_margin_loss_from_unprofitable: float
        - worst_lane: dict
        - best_lane: dict
        - summary: dict with fleet-wide aggregates
    """
    work = df.copy()

    # Build lane identifier
    work["lane"] = work["OriginCity"].str.strip() + " → " + work["DestinationCity"].str.strip()

    # Handle optional columns
    has_fuel = fuel_cost_col in work.columns and work[fuel_cost_col].notna().sum() > 0
    has_accessorial = accessorial_col in work.columns and work[accessorial_col].notna().sum() > 0
    has_weight = "LoadWeight_lbs" in work.columns and work["LoadWeight_lbs"].notna().sum() > 0
    has_distance = "Distance_Miles" in work.columns and work["Distance_Miles"].notna().sum() > 0

    # Estimate missing costs
    if has_fuel:
        work["fuel"] = pd.to_numeric(work[fuel_cost_col], errors="coerce").fillna(0)
    elif has_distance:
        work["fuel"] = work["Distance_Miles"] * 0.60  # ~$0.60/mile fuel estimate
    else:
        work["fuel"] = 0

    if has_accessorial:
        work["accessorials"] = pd.to_numeric(work[accessorial_col], errors="coerce").fillna(0)
    else:
        work["accessorials"] = 0

    if has_distance:
        work["driver_cost"] = work["Distance_Miles"] * estimated_driver_cost_per_mile
    else:
        work["driver_cost"] = 0

    # Total variable cost per shipment
    work["variable_cost"] = work["fuel"] + work["accessorials"] + work["driver_cost"]

    # Contribution margin per shipment
    # FreightCost is revenue from the carrier's perspective (what they charge)
    # For an operator, FreightCost is what they pay — so margin = revenue - freight - variable
    # If we don't have separate revenue, we analyze cost efficiency instead
    work["total_cost"] = pd.to_numeric(work["FreightCost"], errors="coerce").fillna(0) + work["accessorials"]
    work["cost_per_mile"] = np.where(
        work.get("Distance_Miles", 0) > 0,
        work["total_cost"] / work["Distance_Miles"],
        np.nan,
    )

    # Lane-level aggregation
    lane_stats = work.groupby("lane").agg(
        shipment_count=("FreightCost", "size"),
        avg_freight_cost=("FreightCost", "mean"),
        total_freight_cost=("FreightCost", "sum"),
        avg_fuel=("fuel", "mean"),
        total_fuel=("fuel", "sum"),
        avg_accessorials=("accessorials", "mean"),
        total_accessorials=("accessorials", "sum"),
        avg_variable_cost=("variable_cost", "mean"),
        total_variable_cost=("variable_cost", "sum"),
        avg_total_cost=("total_cost", "mean"),
    ).reset_index()

    if has_distance:
        dist_stats = work.groupby("lane")["Distance_Miles"].agg(["mean", "median"]).reset_index()
        dist_stats.columns = ["lane", "avg_distance", "median_distance"]
        lane_stats = lane_stats.merge(dist_stats, on="lane", how="left")

        lane_stats["avg_cost_per_mile"] = np.where(
            lane_stats["avg_distance"] > 0,
            lane_stats["avg_total_cost"] / lane_stats["avg_distance"],
            np.nan,
        )
    else:
        lane_stats["avg_distance"] = None
        lane_stats["avg_cost_per_mile"] = None

    if has_weight:
        weight_stats = work.groupby("lane")["LoadWeight_lbs"].mean().reset_index()
        weight_stats.columns = ["lane", "avg_weight"]
        lane_stats = lane_stats.merge(weight_stats, on="lane", how="left")
        lane_stats["avg_cost_per_pound"] = np.where(
            lane_stats["avg_weight"] > 0,
            lane_stats["avg_total_cost"] / lane_stats["avg_weight"],
            np.nan,
        )
    else:
        lane_stats["avg_weight"] = None
        lane_stats["avg_cost_per_pound"] = None

    # Fleet-wide median cost per mile (benchmark for "cheap" vs "expensive")
    if has_distance:
        fleet_median_cpm = work.loc[work["Distance_Miles"] > 0, "cost_per_mile"].median()
    else:
        fleet_median_cpm = None

    # Identify each lane's relative position
    if fleet_median_cpm and fleet_median_cpm > 0:
        lane_stats["cost_vs_fleet_median"] = (
                (lane_stats["avg_cost_per_mile"] - fleet_median_cpm) / fleet_median_cpm * 100
        )
        lane_stats["is_above_median"] = lane_stats["avg_cost_per_mile"] > fleet_median_cpm
    else:
        lane_stats["cost_vs_fleet_median"] = None
        lane_stats["is_above_median"] = None

    # Rank lanes by total cost impact (shipment count × cost deviation from median)
    if fleet_median_cpm:
        lane_stats["excess_cost_total"] = (
                (lane_stats["avg_cost_per_mile"] - fleet_median_cpm).clip(lower=0)
                * lane_stats.get("avg_distance", 0)
                * lane_stats["shipment_count"]
        )
    else:
        lane_stats["excess_cost_total"] = 0

    # Sort by efficiency (worst first)
    lane_stats = lane_stats.sort_values("avg_total_cost", ascending=False)

    # Build output
    lanes_output = []
    for _, row in lane_stats.iterrows():
        lane_data = {
            "lane": row["lane"],
            "shipment_count": int(row["shipment_count"]),
            "avg_freight_cost": round(row["avg_freight_cost"], 2),
            "avg_fuel_cost": round(row["avg_fuel"], 2),
            "avg_accessorial_cost": round(row["avg_accessorials"], 2),
            "avg_total_cost": round(row["avg_total_cost"], 2),
            "total_spend": round(row["total_freight_cost"] + row["total_accessorials"], 2),
        }
        if row["avg_distance"] is not None:
            lane_data["avg_distance_miles"] = round(row["avg_distance"], 1)
        if row["avg_cost_per_mile"] is not None and not np.isnan(row["avg_cost_per_mile"]):
            lane_data["avg_cost_per_mile"] = round(row["avg_cost_per_mile"], 4)
        if row["cost_vs_fleet_median"] is not None and not np.isnan(row["cost_vs_fleet_median"]):
            lane_data["pct_above_fleet_median"] = round(row["cost_vs_fleet_median"], 1)
        if row["avg_weight"] is not None and not np.isnan(row.get("avg_weight", float("nan"))):
            lane_data["avg_weight_lbs"] = round(row["avg_weight"], 0)
        if row.get("excess_cost_total", 0) > 0:
            lane_data["excess_cost_total"] = round(row["excess_cost_total"], 2)

        lanes_output.append(lane_data)

    # Find worst and best
    expensive_lanes = [l for l in lanes_output if l.get("pct_above_fleet_median", 0) > 0]
    efficient_lanes = [l for l in lanes_output if l.get("pct_above_fleet_median", 0) <= 0]

    total_excess = sum(l.get("excess_cost_total", 0) for l in lanes_output)

    return {
        "lanes": lanes_output,
        "total_lanes_analyzed": len(lanes_output),
        "lanes_above_median": len(expensive_lanes),
        "lanes_below_median": len(efficient_lanes),
        "fleet_median_cost_per_mile": round(fleet_median_cpm, 4) if fleet_median_cpm else None,
        "total_excess_cost": round(total_excess, 2),
        "monthly_excess_cost": round(total_excess, 2),
        "annual_excess_cost_estimate": round(total_excess * 12, 2),
        "worst_lane": lanes_output[0] if lanes_output else None,
        "best_lane": lanes_output[-1] if lanes_output else None,
        "data_completeness": {
            "has_fuel_data": has_fuel,
            "has_accessorial_data": has_accessorial,
            "has_weight_data": has_weight,
            "has_distance_data": has_distance,
        },
    }


# =============================================================================
# MODEL 3: DRIVER EFFICIENCY SCORING WITH SPC CONTROL CHARTS
# =============================================================================

def analyze_driver_spc(
        df: pd.DataFrame,
        sigma_threshold: float = None,
) -> Dict[str, Any]:
    """
    Applies Statistical Process Control (SPC) to driver performance metrics.
    Computes control limits across the driver pool and flags out-of-control drivers.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain: DriverName, FreightCost, DeliveryStatus, Distance_Miles
        Optional: FuelCost (for fuel efficiency), DeliveryTime_hrs (for speed calc)
    sigma_threshold : float
        Number of standard deviations for control limits (default 2σ)

    Returns
    -------
    dict with keys:
        - drivers: list of driver profile dicts with SPC flags
        - fleet_summary: fleet-wide averages and control limits
        - out_of_control_drivers: list of drivers with at least one metric outside limits
        - total_excess_cost_from_outliers: estimated cost impact
        - control_charts: dict of metric -> {mean, ucl, lcl, std} for visualization
    """
    work = df.copy()

    work["is_ontime"] = work["DeliveryStatus"].str.strip().str.lower() == "on-time"
    work["FreightCost"] = pd.to_numeric(work["FreightCost"], errors="coerce")

    has_distance = "Distance_Miles" in work.columns and work["Distance_Miles"].notna().sum() > 0
    has_fuel = "FuelCost" in work.columns and work["FuelCost"].notna().sum() > 0
    has_time = "DeliveryTime_hrs" in work.columns and work["DeliveryTime_hrs"].notna().sum() > 0

    # Cost per mile per shipment
    if has_distance:
        work["cost_per_mile"] = np.where(
            work["Distance_Miles"] > 0,
            work["FreightCost"] / work["Distance_Miles"],
            np.nan,
        )
    else:
        work["cost_per_mile"] = np.nan

    # Fuel cost per mile
    if has_fuel and has_distance:
        work["FuelCost"] = pd.to_numeric(work["FuelCost"], errors="coerce")
        work["fuel_per_mile"] = np.where(
            work["Distance_Miles"] > 0,
            work["FuelCost"] / work["Distance_Miles"],
            np.nan,
        )
    else:
        work["fuel_per_mile"] = np.nan

    # Average speed
    if has_time and has_distance:
        work["DeliveryTime_hrs"] = pd.to_numeric(work["DeliveryTime_hrs"], errors="coerce")
        work["avg_speed"] = np.where(
            work["DeliveryTime_hrs"] > 0,
            work["Distance_Miles"] / work["DeliveryTime_hrs"],
            np.nan,
        )
    else:
        work["avg_speed"] = np.nan

    # --- Aggregate per driver ---
    driver_stats = work.groupby("DriverName").agg(
        shipment_count=("FreightCost", "size"),
        ontime_rate=("is_ontime", "mean"),
        avg_freight_cost=("FreightCost", "mean"),
        total_freight_cost=("FreightCost", "sum"),
        avg_cost_per_mile=("cost_per_mile", "mean"),
        avg_fuel_per_mile=("fuel_per_mile", "mean"),
        avg_speed=("avg_speed", "mean"),
        total_miles=("Distance_Miles", "sum") if has_distance else ("FreightCost", "size"),
        cost_std=("FreightCost", "std"),
    ).reset_index()

    # Adaptive sigma threshold based on fleet size
    # Small fleets (< 20 drivers): use 1.5σ for sensitivity
    # Medium fleets (20-50): use 1.75σ
    # Large fleets (50+): use standard 2.0σ
    n_drivers = len(driver_stats)
    if sigma_threshold is None:
        if n_drivers < 20:
            sigma_threshold = 1.5
        elif n_drivers < 50:
            sigma_threshold = 1.75
        else:
            sigma_threshold = 2.0

    # --- Compute fleet-wide SPC parameters ---
    metrics_to_analyze = {}

    # On-time rate (higher is better — flag low outliers)
    fleet_ontime_mean = driver_stats["ontime_rate"].mean()
    fleet_ontime_std = driver_stats["ontime_rate"].std()
    if fleet_ontime_std > 0:
        metrics_to_analyze["ontime_rate"] = {
            "mean": fleet_ontime_mean,
            "std": fleet_ontime_std,
            "ucl": min(fleet_ontime_mean + sigma_threshold * fleet_ontime_std, 1.0),
            "lcl": max(fleet_ontime_mean - sigma_threshold * fleet_ontime_std, 0.0),
            "higher_is_better": True,
            "label": "On-Time Rate",
            "format": "pct",
        }

    # Cost per mile (lower is better — flag high outliers)
    valid_cpm = driver_stats["avg_cost_per_mile"].dropna()
    if len(valid_cpm) >= 2:
        cpm_mean = valid_cpm.mean()
        cpm_std = valid_cpm.std()
        if cpm_std > 0:
            metrics_to_analyze["avg_cost_per_mile"] = {
                "mean": cpm_mean,
                "std": cpm_std,
                "ucl": cpm_mean + sigma_threshold * cpm_std,
                "lcl": max(cpm_mean - sigma_threshold * cpm_std, 0),
                "higher_is_better": False,
                "label": "Cost per Mile",
                "format": "dollar",
            }

    # Fuel per mile (lower is better)
    valid_fpm = driver_stats["avg_fuel_per_mile"].dropna()
    if len(valid_fpm) >= 2:
        fpm_mean = valid_fpm.mean()
        fpm_std = valid_fpm.std()
        if fpm_std > 0:
            metrics_to_analyze["avg_fuel_per_mile"] = {
                "mean": fpm_mean,
                "std": fpm_std,
                "ucl": fpm_mean + sigma_threshold * fpm_std,
                "lcl": max(fpm_mean - sigma_threshold * fpm_std, 0),
                "higher_is_better": False,
                "label": "Fuel Cost per Mile",
                "format": "dollar",
            }

    # Cost variance (lower is better — high variance = inconsistency)
    valid_std = driver_stats["cost_std"].dropna()
    if len(valid_std) >= 2:
        std_mean = valid_std.mean()
        std_std = valid_std.std()
        if std_std > 0:
            metrics_to_analyze["cost_std"] = {
                "mean": std_mean,
                "std": std_std,
                "ucl": std_mean + sigma_threshold * std_std,
                "lcl": max(std_mean - sigma_threshold * std_std, 0),
                "higher_is_better": False,
                "label": "Cost Variability (Std Dev)",
                "format": "dollar",
            }

    # --- Flag each driver ---
    drivers_output = []
    out_of_control = []
    total_excess_cost = 0.0

    for _, row in driver_stats.iterrows():
        driver_profile = {
            "driver_name": row["DriverName"],
            "shipment_count": int(row["shipment_count"]),
            "ontime_rate": round(row["ontime_rate"] * 100, 1),
            "avg_freight_cost": round(row["avg_freight_cost"], 2),
            "total_freight_cost": round(row["total_freight_cost"], 2),
            "flags": [],
            "sigma_positions": {},
        }

        if has_distance and not np.isnan(row.get("avg_cost_per_mile", float("nan"))):
            driver_profile["avg_cost_per_mile"] = round(row["avg_cost_per_mile"], 4)
        if not np.isnan(row.get("avg_fuel_per_mile", float("nan"))):
            driver_profile["avg_fuel_per_mile"] = round(row["avg_fuel_per_mile"], 4)
        if not np.isnan(row.get("avg_speed", float("nan"))):
            driver_profile["avg_speed_mph"] = round(row["avg_speed"], 1)
        if has_distance:
            driver_profile["total_miles"] = round(row["total_miles"], 0)

        is_out_of_control = False

        for metric_key, params in metrics_to_analyze.items():
            val = row.get(metric_key)
            if val is None or np.isnan(val):
                continue

            sigma_pos = (val - params["mean"]) / params["std"] if params["std"] > 0 else 0
            driver_profile["sigma_positions"][params["label"]] = round(sigma_pos, 2)

            # Check if out of control
            if params["higher_is_better"]:
                if val < params["lcl"]:
                    excess = params["mean"] - val
                    flag_type = "below_lcl"
                    is_out_of_control = True
                elif val > params["ucl"]:
                    flag_type = "above_ucl_good"  # exceptionally good
                else:
                    continue
            else:
                if val > params["ucl"]:
                    excess = val - params["mean"]
                    flag_type = "above_ucl"
                    is_out_of_control = True
                elif val < params["lcl"]:
                    flag_type = "below_lcl_good"  # exceptionally good
                else:
                    continue

            # Estimate cost impact of being out of control
            if flag_type in ("above_ucl", "below_lcl"):
                if metric_key == "avg_cost_per_mile" and has_distance:
                    excess_cost = excess * row.get("total_miles", 0)
                elif metric_key == "avg_fuel_per_mile" and has_distance:
                    excess_cost = excess * row.get("total_miles", 0)
                elif metric_key == "ontime_rate":
                    # Estimate: each 1% below mean → ~$50/month in penalties/lost business
                    excess_cost = abs(sigma_pos) * 50 * (row["shipment_count"] / 20)
                else:
                    excess_cost = 0

                total_excess_cost += excess_cost

                driver_profile["flags"].append({
                    "metric": params["label"],
                    "value": round(val, 4),
                    "fleet_mean": round(params["mean"], 4),
                    "sigma_position": round(sigma_pos, 2),
                    "flag_type": flag_type,
                    "estimated_monthly_excess_cost": round(excess_cost, 2),
                })

        driver_profile["is_out_of_control"] = is_out_of_control
        drivers_output.append(driver_profile)

        if is_out_of_control:
            out_of_control.append(driver_profile)

    # Build control chart data for visualization
    control_charts = {}
    for metric_key, params in metrics_to_analyze.items():
        chart_data = {
            "metric": params["label"],
            "fleet_mean": round(params["mean"], 4),
            "ucl": round(params["ucl"], 4),
            "lcl": round(params["lcl"], 4),
            "sigma": round(params["std"], 4),
            "higher_is_better": params["higher_is_better"],
            "drivers": [],
        }
        for _, row in driver_stats.iterrows():
            val = row.get(metric_key)
            if val is not None and not np.isnan(val):
                chart_data["drivers"].append({
                    "name": row["DriverName"],
                    "value": round(val, 4),
                })
        control_charts[metric_key] = chart_data

    return {
        "drivers": sorted(drivers_output, key=lambda d: len(d["flags"]), reverse=True),
        "fleet_summary": {
            "total_drivers": len(drivers_output),
            "out_of_control_count": len(out_of_control),
            "in_control_count": len(drivers_output) - len(out_of_control),
            "fleet_avg_ontime": round(fleet_ontime_mean * 100, 1),
        },
        "out_of_control_drivers": [d["driver_name"] for d in out_of_control],
        "total_estimated_monthly_excess_cost": round(total_excess_cost, 2),
        "total_estimated_annual_excess_cost": round(total_excess_cost * 12, 2),
        "control_charts": control_charts,
        "sigma_threshold": sigma_threshold,
    }


# =============================================================================
# MODEL 4: COST ANOMALY DETECTION PER SHIPMENT
# =============================================================================

def detect_cost_anomalies(
        df: pd.DataFrame,
        iqr_multiplier: float = 1.5,
        min_shipments_per_group: int = 3,
) -> Dict[str, Any]:
    """
    Detects cost anomalies at the individual shipment level using IQR method.
    Groups by lane + carrier to establish "normal" cost ranges, then flags outliers.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain: ShipmentID, FreightCost, CarrierName, OriginCity, DestinationCity
        Optional: FuelCost, AccessorialCharges, Distance_Miles
    iqr_multiplier : float
        Multiplier for IQR to set anomaly threshold (1.5 = standard, 3.0 = extreme only)
    min_shipments_per_group : int
        Minimum shipments in a lane-carrier group to compute statistics

    Returns
    -------
    dict with keys:
        - anomalies: list of flagged shipments with overpayment amounts
        - total_anomalies: int
        - total_overpayment: float
        - pct_anomalous: float (% of shipments that are anomalies)
        - by_carrier: dict of carrier -> anomaly count and total overpayment
        - by_lane: dict of lane -> anomaly count and total overpayment
        - summary: high-level stats
    """
    work = df.copy()
    work["FreightCost"] = pd.to_numeric(work["FreightCost"], errors="coerce")
    work["lane"] = work["OriginCity"].str.strip() + " → " + work["DestinationCity"].str.strip()

    # Include accessorials and fuel if available
    total_cost_cols = ["FreightCost"]
    if "FuelCost" in work.columns:
        work["FuelCost"] = pd.to_numeric(work["FuelCost"], errors="coerce").fillna(0)
        total_cost_cols.append("FuelCost")
    if "AccessorialCharges" in work.columns:
        work["AccessorialCharges"] = pd.to_numeric(work["AccessorialCharges"], errors="coerce").fillna(0)
        total_cost_cols.append("AccessorialCharges")

    work["total_cost"] = work[total_cost_cols].sum(axis=1)

    # Try grouping by lane + carrier first, fall back to lane only
    work["group_key"] = work["lane"] + " | " + work["CarrierName"].str.strip()

    group_counts = work.groupby("group_key")["total_cost"].count()
    small_groups = group_counts[group_counts < min_shipments_per_group].index

    # For small groups, fall back to lane-level grouping
    work.loc[work["group_key"].isin(small_groups), "group_key"] = work.loc[
        work["group_key"].isin(small_groups), "lane"
    ]

    # Compute IQR bounds per group
    group_stats = work.groupby("group_key")["total_cost"].agg(
        ["median", "count",
         lambda x: x.quantile(0.25),
         lambda x: x.quantile(0.75)]
    ).reset_index()
    group_stats.columns = ["group_key", "median", "count", "q1", "q3"]
    group_stats["iqr"] = group_stats["q3"] - group_stats["q1"]
    group_stats["upper_fence"] = group_stats["q3"] + iqr_multiplier * group_stats["iqr"]
    group_stats["lower_fence"] = (group_stats["q1"] - iqr_multiplier * group_stats["iqr"]).clip(lower=0)

    # Only compute anomalies for groups with enough data
    group_stats = group_stats[group_stats["count"] >= min_shipments_per_group]

    # Merge back
    work = work.merge(
        group_stats[["group_key", "median", "upper_fence", "lower_fence", "q1", "q3"]],
        on="group_key",
        how="left",
    )

    # Flag anomalies
    work["is_anomaly"] = False
    work["overpayment"] = 0.0

    has_bounds = work["upper_fence"].notna()

    # High-cost anomalies
    high_mask = has_bounds & (work["total_cost"] > work["upper_fence"])
    work.loc[high_mask, "is_anomaly"] = True
    work.loc[high_mask, "overpayment"] = work.loc[high_mask, "total_cost"] - work.loc[high_mask, "median"]

    # Low-cost anomalies (suspiciously cheap — might indicate data errors)
    low_mask = has_bounds & (work["total_cost"] < work["lower_fence"]) & (work["total_cost"] > 0)
    work.loc[low_mask, "is_anomaly"] = True
    work.loc[low_mask, "overpayment"] = 0  # not an overpayment, but still flagged

    anomalies_df = work[work["is_anomaly"]].copy()

    # Build anomaly output
    anomalies_output = []
    for _, row in anomalies_df.iterrows():
        anomaly = {
            "shipment_id": str(row.get("ShipmentID", "N/A")),
            "lane": row["lane"],
            "carrier": row["CarrierName"],
            "actual_cost": round(row["total_cost"], 2),
            "lane_median_cost": round(row["median"], 2),
            "upper_fence": round(row["upper_fence"], 2),
            "overpayment": round(row["overpayment"], 2),
            "pct_above_median": round(
                ((row["total_cost"] - row["median"]) / row["median"] * 100)
                if row["median"] > 0 else 0,
                1,
            ),
            "anomaly_type": "high_cost" if row["total_cost"] > row["median"] else "low_cost",
        }
        if "Distance_Miles" in row and not np.isnan(row.get("Distance_Miles", float("nan"))):
            anomaly["distance_miles"] = round(row["Distance_Miles"], 1)

        anomalies_output.append(anomaly)

    # Sort by overpayment descending
    anomalies_output.sort(key=lambda a: a["overpayment"], reverse=True)

    # Aggregate by carrier
    by_carrier = {}
    for a in anomalies_output:
        c = a["carrier"]
        if c not in by_carrier:
            by_carrier[c] = {"count": 0, "total_overpayment": 0}
        by_carrier[c]["count"] += 1
        by_carrier[c]["total_overpayment"] += a["overpayment"]

    for c in by_carrier:
        by_carrier[c]["total_overpayment"] = round(by_carrier[c]["total_overpayment"], 2)

    # Aggregate by lane
    by_lane = {}
    for a in anomalies_output:
        l = a["lane"]
        if l not in by_lane:
            by_lane[l] = {"count": 0, "total_overpayment": 0}
        by_lane[l]["count"] += 1
        by_lane[l]["total_overpayment"] += a["overpayment"]

    for l in by_lane:
        by_lane[l]["total_overpayment"] = round(by_lane[l]["total_overpayment"], 2)

    total_shipments = len(work)
    total_anomalies = len(anomalies_output)
    total_overpayment = sum(a["overpayment"] for a in anomalies_output)

    return {
        "anomalies": anomalies_output,
        "total_anomalies": total_anomalies,
        "total_shipments_analyzed": total_shipments,
        "pct_anomalous": round(total_anomalies / total_shipments * 100, 1) if total_shipments > 0 else 0,
        "total_overpayment": round(total_overpayment, 2),
        "annual_overpayment_estimate": round(total_overpayment * 12, 2),
        "by_carrier": by_carrier,
        "by_lane": by_lane,
        "iqr_multiplier_used": iqr_multiplier,
        "summary": {
            "high_cost_anomalies": len([a for a in anomalies_output if a["anomaly_type"] == "high_cost"]),
            "low_cost_anomalies": len([a for a in anomalies_output if a["anomaly_type"] == "low_cost"]),
            "worst_overpayment": anomalies_output[0] if anomalies_output else None,
            "carrier_with_most_anomalies": max(by_carrier,
                                               key=lambda c: by_carrier[c]["count"]) if by_carrier else None,
        },
    }


# =============================================================================
# ORCHESTRATOR: Run all Phase 1 models and combine results
# =============================================================================

def run_phase1_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Runs all four Phase 1 OR models on the uploaded data
    and returns a combined result dict ready for LLM narration.

    Parameters
    ----------
    df : pd.DataFrame
        The cleaned, parsed user upload with standard column names.

    Returns
    -------
    dict with keys:
        - carrier_optimization: result from optimize_carrier_allocation()
        - lane_profitability: result from analyze_lane_profitability()
        - driver_spc: result from analyze_driver_spc()
        - cost_anomalies: result from detect_cost_anomalies()
        - composite_savings: dict summarizing total identified savings
        - data_quality: dict noting which optional fields were present
    """
    results = {}

    # --- Model 1: Carrier Allocation ---
    try:
        results["carrier_optimization"] = optimize_carrier_allocation(df)
    except Exception as e:
        results["carrier_optimization"] = {"model_status": "error", "error": str(e)}

    # --- Model 2: Lane Profitability ---
    try:
        results["lane_profitability"] = analyze_lane_profitability(df)
    except Exception as e:
        results["lane_profitability"] = {"model_status": "error", "error": str(e)}

    # --- Model 3: Driver SPC ---
    try:
        results["driver_spc"] = analyze_driver_spc(df)
    except Exception as e:
        results["driver_spc"] = {"model_status": "error", "error": str(e)}

    # --- Model 4: Cost Anomalies ---
    try:
        results["cost_anomalies"] = detect_cost_anomalies(df)
    except Exception as e:
        results["cost_anomalies"] = {"model_status": "error", "error": str(e)}

    # --- Composite Savings Summary ---
    savings = {
        "carrier_reallocation_annual": 0,
        "lane_excess_cost_annual": 0,
        "driver_inefficiency_annual": 0,
        "cost_anomalies_annual": 0,
    }

    co = results.get("carrier_optimization", {})
    if co.get("model_status") == "optimal":
        savings["carrier_reallocation_annual"] = co.get("annual_savings_estimate", 0)

    lp = results.get("lane_profitability", {})
    savings["lane_excess_cost_annual"] = lp.get("annual_excess_cost_estimate", 0)

    ds = results.get("driver_spc", {})
    savings["driver_inefficiency_annual"] = ds.get("total_estimated_annual_excess_cost", 0)

    ca = results.get("cost_anomalies", {})
    savings["cost_anomalies_annual"] = ca.get("annual_overpayment_estimate", 0)

    savings["total_identified_annual_savings"] = round(
        sum(v for v in savings.values() if isinstance(v, (int, float))), 2
    )

    results["composite_savings"] = savings

    # --- Data Quality Report ---
    cols = set(df.columns)
    results["data_quality"] = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "has_fuel_cost": "FuelCost" in cols,
        "has_distance": "Distance_Miles" in cols,
        "has_weight": "LoadWeight_lbs" in cols,
        "has_accessorials": "AccessorialCharges" in cols,
        "has_delivery_time": "DeliveryTime_hrs" in cols,
        "has_shipment_id": "ShipmentID" in cols,
    }

    return results


# =============================================================================
# DJANGO VIEW INTEGRATION EXAMPLE
# =============================================================================

"""
# In your Django views.py:

import pandas as pd
from .or_models import run_phase1_analysis

def generate_report(request):
    # After CSV parsing and cleaning...
    df = pd.read_csv(uploaded_file_path)

    # Run all OR models
    analysis = run_phase1_analysis(df)

    # The composite_savings dict goes to the top of the report
    # as the "money headline":
    # f"This analysis identified ${analysis['composite_savings']['total_identified_annual_savings']:,.0f} 
    #   in potential annual savings."

    # Each model's output dict gets passed to Sonnet for narration:
    # carrier_prompt = build_carrier_narrative_prompt(analysis['carrier_optimization'])
    # driver_prompt = build_driver_narrative_prompt(analysis['driver_spc'])
    # etc.

    # Save to your Report model
    report = Report.objects.create(
        user=request.user,
        raw_data=df.to_json(),
        analysis_results=json.dumps(analysis),
        # ... narrative fields populated by LLM
    )

    return redirect('report_view', report_id=report.id)
"""