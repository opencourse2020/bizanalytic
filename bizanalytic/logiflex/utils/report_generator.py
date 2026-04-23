"""
LogiFlex Report Generator — Claude Sonnet 4.6 Integration
==========================================================
Generates the FreightOps Performance Report narrative from structured
analysis data (output of run_phase1_analysis + compute_fleet_score).

Architecture:
  1. Your Python OR models compute all numbers (deterministic)
  2. This module sends the structured results to Sonnet
  3. Sonnet generates ONLY the narrative text (executive + detailed)
  4. Your Django template assembles the final report

The LLM never sees raw CSV data. It receives pre-computed JSON
and writes prose. All numbers in the output come from your models,
not from the LLM's reasoning.

Dependencies:
  pip install anthropic
"""

import json
import numpy as np
import anthropic
from typing import Dict, Any


class NumpyEncoder(json.JSONEncoder):
    """Handles numpy types that default json.dumps can't serialize."""

    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


# =============================================================================
# SYSTEM PROMPT — The "personality" of every report
# =============================================================================

SYSTEM_PROMPT = """You are a senior logistics performance analyst writing a FreightOps 
Performance Report for an SMB fleet operator. Your reader is a fleet manager or 
owner-operator with 5-50 trucks who has no analytics background. They need to 
understand what's happening and what to do about it — in plain language.

WRITING RULES:
- Write like a professor explaining results to a business owner, not like software 
  generating output. Warm, direct, authoritative.
- Every insight must include a specific dollar amount, percentage, or comparison.
  Never say "significant" without a number. Never say "consider" without a reason.
- Use carrier names, driver names, lane names, and shipment IDs from the data.
  Generic advice is worthless — specific advice is what they pay for.
- When recommending an action, state: what to do, who it involves, and the 
  estimated financial impact.
- Use short paragraphs (2-3 sentences max). Use plain English, not logistics jargon.
- Never invent numbers. Use ONLY the values provided in the analysis data.
  If a metric is missing, skip it — do not estimate or hallucinate.

OUTPUT FORMAT:
Return a JSON object (no markdown, no backticks, no preamble) with the exact 
structure specified in the user message. Every field must be a string containing 
the narrative text for that section."""


# =============================================================================
# BUILD THE USER PROMPT — Structured data + output instructions
# =============================================================================

def build_report_prompt(
        fleet_score: Dict[str, Any],
        carrier_optimization: Dict[str, Any],
        lane_profitability: Dict[str, Any],
        driver_spc: Dict[str, Any],
        cost_anomalies: Dict[str, Any],
        composite_savings: Dict[str, Any],
        carrier_stats: Dict[str, Any],
        driver_stats: Dict[str, Any],
        route_stats: Dict[str, Any],
        sample_data: Dict[str, Any],
) -> str:
    """
    Constructs the user prompt with all analysis data and output format spec.
    """

    prompt = f"""Generate the FreightOps Performance Report narrative from the following 
analysis data. Return ONLY a valid JSON object with the structure defined below.

============================
FLEET HEALTH SCORE
============================
{json.dumps(fleet_score, indent=2, cls=NumpyEncoder)}

============================
COMPOSITE SAVINGS SUMMARY
============================
{json.dumps(composite_savings, indent=2, cls=NumpyEncoder)}

============================
CARRIER STATISTICS SUMMARY
============================
{json.dumps(carrier_stats, indent=2, cls=NumpyEncoder)}

============================
CARRIER OPTIMIZATION (LP MODEL)
============================
{json.dumps(carrier_optimization, indent=2, cls=NumpyEncoder)}

============================
DRIVER STATISTICS SUMMARY
============================
{json.dumps(driver_stats, indent=2, cls=NumpyEncoder)}

============================
DRIVER SPC ANALYSIS
============================
{json.dumps(driver_spc, indent=2, cls=NumpyEncoder)}

============================
ROUTE STATISTICS SUMMARY
============================
{json.dumps(route_stats, indent=2, cls=NumpyEncoder)}

============================
LANE PROFITABILITY ANALYSIS
============================
{json.dumps(lane_profitability, indent=2, cls=NumpyEncoder)}

============================
COST ANOMALY DETECTION
============================
{json.dumps(cost_anomalies, indent=2, cls=NumpyEncoder)}

============================
SAMPLE RAW DATA (first 5 rows for context)
============================
{json.dumps(sample_data, indent=2, cls=NumpyEncoder)}

============================
REQUIRED OUTPUT FORMAT
============================
Return a JSON object with EXACTLY these keys. Each value is a string of narrative text.

{{
  "money_headline_sub": "One sentence summarizing where the savings come from (under 20 words)",

  "top_actions": [
    {{
      "title": "Specific action instruction (e.g., 'Shift 35% of ABC Carriers volume to XYZ Freight on Dallas → Houston')",
      "detail": "2-3 sentence explanation with numbers from the data. Why this matters, what changes.",
      "value": "Dollar amount per year (e.g., '$18,240/yr')"
    }},
    {{
      "title": "Second action",
      "detail": "Explanation",
      "value": "Dollar amount"
    }},
    {{
      "title": "Third action",
      "detail": "Explanation",
      "value": "Dollar amount"
    }}
  ],

  "carriers_summary": "3-5 sentence executive analysis of carrier performance. Name specific carriers. Include the key comparison (best vs worst on-time, cost gap). End with the single most important carrier decision.",

  "carriers_insights": [
    {{
      "type": "finding|warning|opportunity",
      "text": "One specific insight with numbers. Bold the carrier name and key metric."
    }}
  ],

  "carriers_detailed": "Full carrier analysis: 3-4 paragraphs covering performance ranking, cost variance analysis, contingency/reliability analysis (which carrier is Nx more likely to deliver on-time than which), allocation optimization results from the LP model (current vs optimal split with shipment counts), and specific negotiation recommendations. Use all carrier stats and optimization results provided. This is the expanded view — be thorough.",

  "drivers_summary": "3-5 sentence executive analysis of driver performance. Name specific drivers. Include fleet average on-time vs industry benchmark. Highlight the best and worst performers with their personality archetypes.",

  "drivers_detailed": "Full driver analysis: 3-4 paragraphs covering SPC control chart findings (who is out of control, on which metrics, by how many sigma), driver personality profiles with behavioral descriptions, specific coaching recommendations per flagged driver with dollar impact, and fleet-wide improvement projections. Use all driver SPC data provided. This is the expanded view — be thorough.",

  "routes_summary": "3-5 sentence executive analysis of route performance. Name specific lanes. Include the network imbalance finding (deadhead/empty miles). Highlight the worst and best performing lanes with cost data.",

  "routes_insights": [
    {{
      "type": "finding|warning|opportunity",
      "text": "One specific insight about a lane or route pattern."
    }}
  ],

  "routes_detailed": "Full route analysis: 3-4 paragraphs covering lane profitability rankings (contribution margin analysis), underutilized lanes, network balance analysis (inbound vs outbound by city), the 5 worst routes with specific reasons (heavy load vs light load distinction), and consolidation/repricing recommendations with dollar impact. Use all lane profitability data provided. This is the expanded view — be thorough.",

  "financial_impact": [
    {{
      "value": "Dollar amount",
      "description": "One sentence explaining what this saving comes from and how it's achieved"
    }}
  ],

  "week_actions": [
    {{
      "text": "Specific Monday-morning action. Include names, shipment IDs, dollar amounts. Must be executable within 48 hours."
    }}
  ],

  "improvement_scenario": "One sentence: 'Improving [biggest drag dimension] to [target] would raise your Fleet Score from [current] to [projected] (+[delta] points).' Use the fleet score improvement_scenario data."
}}

CRITICAL: Return ONLY the JSON object. No markdown formatting, no ```json blocks, 
no explanatory text before or after. Just the raw JSON."""

    return prompt


# =============================================================================
# API CALL — Generate the report narrative
# =============================================================================

def generate_report_narrative(
        fleet_score: Dict[str, Any],
        carrier_optimization: Dict[str, Any],
        lane_profitability: Dict[str, Any],
        driver_spc: Dict[str, Any],
        cost_anomalies: Dict[str, Any],
        composite_savings: Dict[str, Any],
        carrier_stats: Dict[str, Any],
        driver_stats: Dict[str, Any],
        route_stats: Dict[str, Any],
        sample_data: Dict[str, Any],
        api_key: str = None,
) -> Dict[str, Any]:
    """
    Calls Claude Sonnet 4.6 to generate all report narrative sections.

    Parameters
    ----------
    fleet_score : dict
        Output from compute_fleet_score()
    carrier_optimization : dict
        Output from optimize_carrier_allocation()
    lane_profitability : dict
        Output from analyze_lane_profitability()
    driver_spc : dict
        Output from analyze_driver_spc()
    cost_anomalies : dict
        Output from detect_cost_anomalies()
    composite_savings : dict
        The composite_savings key from run_phase1_analysis()
    carrier_stats : dict
        Pre-computed carrier-level statistics (see build_carrier_stats)
    driver_stats : dict
        Pre-computed driver-level statistics (see build_driver_stats)
    route_stats : dict
        Pre-computed route-level statistics (see build_route_stats)
    sample_data : dict
        First 5 rows of the uploaded CSV as a list of dicts
    api_key : str, optional
        Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.

    Returns
    -------
    dict : The parsed JSON narrative sections, ready for the Django template.
    """

    client = anthropic.Anthropic(api_key=api_key)

    user_prompt = build_report_prompt(
        fleet_score=fleet_score,
        carrier_optimization=carrier_optimization,
        lane_profitability=lane_profitability,
        driver_spc=driver_spc,
        cost_anomalies=cost_anomalies,
        composite_savings=composite_savings,
        carrier_stats=carrier_stats,
        driver_stats=driver_stats,
        route_stats=route_stats,
        sample_data=sample_data,
    )

    message = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
    )

    raw_text = message.content[0].text

    # Clean potential markdown fencing
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        narrative = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse LLM response as JSON: {str(e)}",
            "raw_response": raw_text,
        }

    # Add usage metadata
    narrative["_meta"] = {
        "model": "claude-sonnet-4-6-20250514",
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
        "estimated_cost_usd": round(
            (message.usage.input_tokens / 1_000_000 * 3)
            + (message.usage.output_tokens / 1_000_000 * 15),
            4,
        ),
    }

    return narrative


# =============================================================================
# HELPER: Build statistics summaries from raw DataFrame
# =============================================================================

def build_carrier_stats(df) -> Dict[str, Any]:
    """Pre-computes carrier statistics for the prompt."""
    import pandas as pd
    import numpy as np

    work = df.copy()
    work["FreightCost_USD"] = pd.to_numeric(work["FreightCost_USD"], errors="coerce")
    work["is_ontime"] = work["DeliveryStatus"].str.strip().str.lower() == "on-time"

    has_distance = "Distance_Miles" in work.columns
    has_fuel = "FuelCost_USD" in work.columns
    has_weight = "LoadWeight_lbs" in work.columns

    carriers = []
    for carrier, grp in work.groupby("CarrierName"):
        stats = {
            "carrier_name": carrier,
            "total_shipments": int(len(grp)),
            "pct_of_total": round(len(grp) / len(work) * 100, 1),
            "avg_freight_cost": round(grp["FreightCost_USD"].mean(), 2),
            "total_freight_cost": round(grp["FreightCost_USD"].sum(), 2),
            "cost_std_dev": round(grp["FreightCost"].std(), 2),
            "cost_cv": round(
                grp["FreightCost_USD"].std() / grp["FreightCost_USD"].mean(), 3
            ) if grp["FreightCost_USD"].mean() > 0 else 0,
            "ontime_rate": round(grp["is_ontime"].mean() * 100, 1),
            "late_rate": round((1 - grp["is_ontime"].mean()) * 100, 1),
            "ontime_shipments": int(grp["is_ontime"].sum()),
            "late_shipments": int((~grp["is_ontime"]).sum()),
        }
        if has_distance:
            valid = grp[grp["Distance_Miles"] > 0]
            if len(valid) > 0:
                stats["avg_cost_per_mile"] = round(
                    (valid["FreightCost_USD"] / valid["Distance_Miles"]).mean(), 4
                )
                stats["avg_distance"] = round(valid["Distance_Miles"].mean(), 1)
        if has_fuel:
            fuel = pd.to_numeric(grp["FuelCost_USD"], errors="coerce")
            stats["avg_fuel_cost"] = round(fuel.mean(), 2)
        if has_weight:
            weight = pd.to_numeric(grp["LoadWeight_lbs"], errors="coerce")
            if weight.mean() > 0:
                stats["avg_cost_per_pound"] = round(
                    grp["FreightCost_USD"].mean() / weight.mean(), 4
                )

        carriers.append(stats)

    # Reliability contingency analysis
    sorted_by_otd = sorted(carriers, key=lambda c: c["ontime_rate"])
    worst = sorted_by_otd[0]
    contingency = []
    for c in sorted_by_otd[1:]:
        if worst["ontime_rate"] > 0:
            ratio = round(c["ontime_rate"] / worst["ontime_rate"], 2)
        else:
            ratio = float("inf")
        contingency.append({
            "better_carrier": c["carrier_name"],
            "worse_carrier": worst["carrier_name"],
            "ontime_ratio": ratio,
            "better_otd": c["ontime_rate"],
            "worse_otd": worst["ontime_rate"],
        })

    return {
        "carriers": sorted(carriers, key=lambda c: c["ontime_rate"], reverse=True),
        "total_carriers": len(carriers),
        "fleet_avg_ontime": round(work["is_ontime"].mean() * 100, 1),
        "fleet_avg_cost": round(work["FreightCost_USD"].mean(), 2),
        "contingency_analysis": contingency,
    }


def build_driver_stats(df) -> Dict[str, Any]:
    """Pre-computes driver statistics for the prompt."""
    import pandas as pd
    import numpy as np

    work = df.copy()
    work["FreightCost_USD"] = pd.to_numeric(work["FreightCost_USD"], errors="coerce")
    work["is_ontime"] = work["DeliveryStatus"].str.strip().str.lower() == "on-time"

    has_distance = "Distance_Miles" in work.columns
    has_fuel = "FuelCost_USD" in work.columns
    has_time = "DeliveryTime_hrs" in work.columns

    if has_distance:
        work["cost_per_mile"] = np.where(
            work["Distance_Miles"] > 0,
            work["FreightCost_USD"] / work["Distance_Miles"],
            np.nan,
        )

    if has_fuel and has_distance:
        work["FuelCost_USD"] = pd.to_numeric(work["FuelCost_USD"], errors="coerce")
        work["fuel_per_mile"] = np.where(
            work["Distance_Miles"] > 0,
            work["FuelCost_USD"] / work["Distance_Miles"],
            np.nan,
        )

    if has_time and has_distance:
        work["DeliveryTime_hrs"] = pd.to_numeric(work["DeliveryTime_hrs"], errors="coerce")
        work["avg_speed"] = np.where(
            work["DeliveryTime_hrs"] > 0,
            work["Distance_Miles"] / work["DeliveryTime_hrs"],
            np.nan,
        )

    drivers = []
    for driver, grp in work.groupby("DriverName"):
        stats = {
            "driver_name": driver,
            "total_shipments": int(len(grp)),
            "ontime_rate": round(grp["is_ontime"].mean() * 100, 1),
            "avg_freight_cost": round(grp["FreightCost_USD"].mean(), 2),
            "total_freight_cost": round(grp["FreightCost_USD"].sum(), 2),
        }
        if has_distance:
            stats["total_miles"] = round(grp["Distance_Miles"].sum(), 0)
            valid_cpm = grp["cost_per_mile"].dropna()
            if len(valid_cpm) > 0:
                stats["avg_cost_per_mile"] = round(valid_cpm.mean(), 4)
        if has_fuel and has_distance:
            valid_fpm = grp["fuel_per_mile"].dropna()
            if len(valid_fpm) > 0:
                stats["avg_fuel_per_mile"] = round(valid_fpm.mean(), 4)
        if has_time and has_distance:
            valid_speed = grp["avg_speed"].dropna()
            if len(valid_speed) > 0:
                stats["avg_speed_mph"] = round(valid_speed.mean(), 1)

        drivers.append(stats)

    return {
        "drivers": sorted(drivers, key=lambda d: d["ontime_rate"], reverse=True),
        "total_drivers": len(drivers),
        "fleet_avg_ontime": round(work["is_ontime"].mean() * 100, 1),
        "fleet_total_miles": round(work["Distance_Miles"].sum(), 0) if has_distance else None,
        "fleet_avg_trip_length": round(work["Distance_Miles"].mean(), 1) if has_distance else None,
        "fleet_total_shipments": len(work),
    }


def build_route_stats(df) -> Dict[str, Any]:
    """Pre-computes route statistics for the prompt."""
    import pandas as pd
    import numpy as np

    work = df.copy()
    work["FreightCost_USD"] = pd.to_numeric(work["FreightCost_USD"], errors="coerce")
    work["lane"] = work["OriginCity"].str.strip() + " → " + work["DestinationCity"].str.strip()
    work["is_ontime"] = work["DeliveryStatus"].str.strip().str.lower() == "on-time"

    has_distance = "Distance_Miles" in work.columns

    if has_distance:
        work["cost_per_mile"] = np.where(
            work["Distance_Miles"] > 0,
            work["FreightCost_USD"] / work["Distance_Miles"],
            np.nan,
        )

    lanes = []
    for lane, grp in work.groupby("lane"):
        stats = {
            "lane": lane,
            "shipment_count": int(len(grp)),
            "avg_freight_cost": round(grp["FreightCost_USD"].mean(), 2),
            "total_freight_cost": round(grp["FreightCost_USD"].sum(), 2),
            "ontime_rate": round(grp["is_ontime"].mean() * 100, 1),
        }
        if has_distance:
            valid = grp[grp["Distance_Miles"] > 0]
            if len(valid) > 0:
                stats["avg_distance"] = round(valid["Distance_Miles"].mean(), 1)
                stats["avg_cost_per_mile"] = round(valid["cost_per_mile"].mean(), 4)
        lanes.append(stats)

    # Network balance analysis
    city_out = work.groupby("OriginCity").size().to_dict()
    city_in = work.groupby("DestinationCity").size().to_dict()
    all_cities = set(city_out.keys()) | set(city_in.keys())

    network_balance = []
    for city in all_cities:
        out_vol = city_out.get(city, 0)
        in_vol = city_in.get(city, 0)
        network_balance.append({
            "city": city,
            "outbound": out_vol,
            "inbound": in_vol,
            "imbalance": out_vol - in_vol,
            "likely_deadhead_trips": max(0, out_vol - in_vol),
        })

    return {
        "lanes": sorted(lanes, key=lambda l: l["avg_freight_cost"], reverse=True),
        "total_lanes": len(lanes),
        "fleet_avg_cost_per_mile": round(
            work["cost_per_mile"].dropna().mean(), 4
        ) if has_distance else None,
        "fleet_median_cost_per_mile": round(
            work["cost_per_mile"].dropna().median(), 4
        ) if has_distance else None,
        "fleet_avg_distance": round(work["Distance_Miles"].mean(), 1) if has_distance else None,
        "network_balance": network_balance,
    }


def build_sample_data(df, n_rows: int = 5) -> Dict[str, Any]:
    """Extracts the first N rows as a list of dicts for the prompt."""
    sample = df.head(n_rows).copy()
    # Convert to serializable types
    for col in sample.columns:
        if sample[col].dtype in ["float64", "float32"]:
            sample[col] = sample[col].round(2)
    return sample.to_dict(orient="records")


# =============================================================================
# FULL PIPELINE: DataFrame → Report Narrative
# =============================================================================

def generate_full_report(df, api_key: str = None) -> Dict[str, Any]:
    """
    End-to-end: takes a cleaned DataFrame, runs all models,
    and generates the complete report narrative.

    This is the function you call from your Django view.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned user upload with standard column names.
    api_key : str, optional
        Anthropic API key.

    Returns
    -------
    dict with keys:
        - narrative: the LLM-generated text sections
        - analysis: the structured model outputs (for charts/tables)
        - fleet_score: the composite score
        - meta: token usage and cost
    """
    # Import the OR models
    from .or_models import run_phase1_analysis
    from .fleet_score import compute_fleet_score

    # Step 1: Run all OR models
    analysis = run_phase1_analysis(df)

    # Step 2: Compute Fleet Health Score
    score = compute_fleet_score(df, phase1_results=analysis)

    # Step 3: Build statistics summaries
    carrier_stats = build_carrier_stats(df)
    driver_stats = build_driver_stats(df)
    route_stats = build_route_stats(df)
    sample_data = build_sample_data(df)

    # Step 4: Generate narrative via Sonnet
    narrative = generate_report_narrative(
        fleet_score=score,
        carrier_optimization=analysis["carrier_optimization"],
        lane_profitability=analysis["lane_profitability"],
        driver_spc=analysis["driver_spc"],
        cost_anomalies=analysis["cost_anomalies"],
        composite_savings=analysis["composite_savings"],
        carrier_stats=carrier_stats,
        driver_stats=driver_stats,
        route_stats=route_stats,
        sample_data=sample_data,
        api_key=api_key,
    )

    return {
        "narrative": narrative,
        "analysis": analysis,
        "fleet_score": score,
        "carrier_stats": carrier_stats,
        "driver_stats": driver_stats,
        "route_stats": route_stats,
    }


# =============================================================================
# DJANGO VIEW INTEGRATION
# =============================================================================

"""
# In your Django views.py:

import pandas as pd
import json
from django.shortcuts import redirect
from django.conf import settings
from .report_generator import generate_full_report

def create_report(request):
    # After CSV upload and cleaning...
    df = pd.read_csv(uploaded_file_path)

    # Generate everything in one call
    result = generate_full_report(df, api_key=settings.ANTHROPIC_API_KEY)

    # Save to your Report model
    report = Report.objects.create(
        user=request.user,

        # Structured data (for charts, tables, KPI cards)
        fleet_score=result["fleet_score"]["score"],
        fleet_grade=result["fleet_score"]["grade"],
        analysis_json=json.dumps(result["analysis"]),
        carrier_stats_json=json.dumps(result["carrier_stats"]),
        driver_stats_json=json.dumps(result["driver_stats"]),
        route_stats_json=json.dumps(result["route_stats"]),

        # LLM-generated narrative (for text sections)
        narrative_json=json.dumps(result["narrative"]),

        # Cost tracking
        llm_input_tokens=result["narrative"].get("_meta", {}).get("input_tokens", 0),
        llm_output_tokens=result["narrative"].get("_meta", {}).get("output_tokens", 0),
        llm_cost_usd=result["narrative"].get("_meta", {}).get("estimated_cost_usd", 0),
    )

    return redirect('report_view', report_id=report.id)


# In your Django template (report_view.html):
# 
# The template receives both structured data and narrative text.
# Charts render from analysis_json (Chart.js / Plotly).
# Text sections render from narrative_json.
# The "Show detailed analysis" toggle shows/hides the *_detailed fields.
#
# Example:
#
#   <div class="analysis-summary">
#     {{ narrative.carriers_summary }}
#   </div>
#   
#   <ul class="insight-list">
#     {% for insight in narrative.carriers_insights %}
#       <li class="insight-item">
#         <div class="insight-marker {{ insight.type }}"></div>
#         <div class="insight-text">{{ insight.text|safe }}</div>
#       </li>
#     {% endfor %}
#   </ul>
#   
#   <button onclick="toggleDetail('carriers')">Show detailed analysis</button>
#   <div id="carriers-detail" style="display:none">
#     {{ narrative.carriers_detailed|linebreaksbr }}
#   </div>
"""