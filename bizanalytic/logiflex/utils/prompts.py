client = ""
data = ""
summary = ""

gemini_report_elite = """"
client: {0}
Persona & Context: "Act as my strategic thinking partner, a world-class operations consultant. We are conducting a performance review for our client logistics operations with the goal of presenting a concrete action plan to the executive team. Our client's strategic priority is improving operational margin, but he cannot sacrifice his reputation for reliability."

Core Problem Statement: "Our client freight operations are experiencing significant hidden costs due to persistent delivery delays, which we believe are eroding his profit margins and customer trust. We need to quantify this impact and build a data-backed plan to address it."

Key Tasks & Hypotheses to Test:

Executive Summary: Write a concise, hard-hitting summary for the CEO that highlights the total estimated quarterly cost of delays and the single most impactful recommendation.

Diagnostic Analysis:

Instead of just listing problematic routes, perform a root-cause analysis on the operating area bottleneck. Is the issue carrier-specific, related to time-of-day, or something else?

Create a 2x2 matrix plotting all carriers based on Cost per Mile (X-axis) vs. On-Time Delivery % (Y-axis) to visually identify client's "Strategic Partners" (low cost, high reliability) and "High-Risk Partners" (high cost, low reliability).

Prescriptive Action Plan:

Don't just give recommendations. Frame them as a prioritized action plan. For each action, specify the:

Expected Outcome: (e.g., "Reduce delay rate on SA->DAL by 25%")

Estimated Impact: (e.g., "Projected savings of $15k/quarter")

Level of Effort: (Low/Medium/High)

Scenario Modeling & Future Outlook:

Model the financial and performance impact of shifting 50% of ABC Carriers' volume to GHI Transport. What would our client new average delay rate and total cost be?

What is our client risk exposure if fuel prices increase by 10% next quarter? Which routes or carriers would be most affected?
use the attached logo for branding
"""

gemini_report_professional = """
client = {0}
Role: "Act as a Senior Logistics Analyst."

Audience: "You are preparing a report for our client's Chief Operating Officer (COO)."

Goal: "The primary goal is to identify the top 3 actionable opportunities to reduce our overall freight costs by at least 5% in the next quarter."

Analysis Request: "Using the provided freight data, create an analysis that answers the following:

Which carrier offers the best true value when factoring in both freight cost and delay rates?

What is the total financial impact of delays on our client most problematic route (San Antonio → Dallas)?

Is there a correlation between LoadWeight_lbs and the likelihood of a shipment being delayed?"

Output: 'Present the findings in a report with an executive summary, detailed answers to each question, and a list of prioritized recommendations.'"""


gemini_report_elite1 = """"
client: {0}
Persona & Context: "Act as my strategic thinking partner, a world-class operations consultant. We are conducting a performance review for our client logistics operations with the goal of presenting a concrete action plan to the executive team. Our client's strategic priority is improving operational margin, but he cannot sacrifice his reputation for reliability."

Core Problem Statement: "Our client freight operations are experiencing significant hidden costs due to persistent delivery delays, which we believe are eroding his profit margins and customer trust. We need to quantify this impact and build a data-backed plan to address it."

Key Tasks & Hypotheses to Test:

Executive Summary: Write a concise, hard-hitting summary for the CEO that highlights the total estimated quarterly cost of delays and the single most impactful recommendation.

Diagnostic Analysis:

Instead of just listing problematic routes, perform a root-cause analysis on the operating area bottleneck. Is the issue carrier-specific, related to time-of-day, or something else?

Prescriptive Action Plan:

Don't just give recommendations. Frame them as a prioritized action plan. For each action, specify the:

Expected Outcome: (e.g., "Reduce delay rate on SA->DAL by 25%")

Estimated Impact: (e.g., "Projected savings of $15k/quarter")

Level of Effort: (Low/Medium/High)

Scenario Modeling & Future Outlook:

Model the financial and performance impact of shifting 50% of ABC Carriers' volume to GHI Transport. What would our client new average delay rate and total cost be?

What is our client risk exposure if fuel prices increase by 10% next quarter? Which routes or carriers would be most affected?

return the results in json format.

use the attached logo for branding
"""

gemini_report_professional1 = """
client = {0}
Role: "Act as a Senior Logistics Analyst."

Audience: "You are preparing a report for our client's Chief Operating Officer (COO)."

Goal: "The primary goal is to identify the top 3 actionable opportunities to reduce our overall freight costs by at least 5% in the next quarter."

Analysis Request: "Using the provided freight data, create an analysis that answers the following:

Which carrier offers the best true value when factoring in both freight cost and delay rates?

What is the total financial impact of delays on our client most problematic route (San Antonio → Dallas)?

Is there a correlation between LoadWeight_lbs and the likelihood of a shipment being delayed?"

Output: 'Present the findings in a report with an executive summary, detailed answers to each question, and a list of prioritized recommendations.'

return the results in json format.

"""


chatgpt_prompt = """
Persona & Context:
Act as my strategic thinking partner, a world-class operations and logistics consultant. We are conducting a performance review for our client's freight operations. You are analyzing a dataset of {0} freight deliveries (uploaded separately) with route, carrier, distance, fuel cost, delay status, and other variables.

Company Goal:
Our strategic goal is to increase operational margin without compromising reliability.

Objective:
Diagnose the financial and operational impact of delivery delays, then develop a concrete, data-driven action plan for the executive team.

Section 1: Executive Summary
- Write a 1-paragraph summary for the CEO.
- Include:
  • Total estimated quarterly cost of delivery delays (from dataset).
  • Most impactful action with projected impact (financial + delay reduction).

Section 2: Diagnostic Analysis
- Identify root cause of delay concentration in the "Texas Triangle" (Austin, Houston, Dallas/Fort Worth).
- Use the dataset to analyze:
  • Carrier reliability (e.g., ABC vs GHI)
  • Time-of-day or day-of-week patterns
  • Route distance vs. delay frequency correlation

Section 3: Carrier 2x2 Matrix
- Plot a 2x2 matrix:
  X-axis: Cost per Mile
  Y-axis: On-Time Delivery %
- Label quadrants:
  • Top-Left: Strategic Partners
  • Bottom-Right: High-Risk Carriers
  • Others: Monitor and Opportunity Carriers

Section 4: Prescriptive Action Plan
- For top 3 recommended actions, provide a table with:
  | Action | Expected Outcome | Estimated Impact | Level of Effort |
  |--------|------------------|------------------|------------------|

Section 5: Scenario Modeling
1. Carrier Swap Simulation:
   - What happens if 50% of ABC’s volume is shifted to GHI?
   - Recalculate average delay rate, cost per mile, and projected savings.

2. Fuel Price Sensitivity:
   - Model 10% increase in fuel prices.
   - Identify which routes or carriers are most exposed to margin erosion.

Constraints:
- Use uploaded data only — do not invent values.
- Prioritize concise, executive-ready insights.
- Output in structured HTML and optionally PDF.
- client : {1}
"""

chatgpt_prompt1 = f"""
Persona & Context: Act as my strategic thinking partner, a world-class operations consultant. 
We are conducting a performance review for our client's logistics operations with the goal of presenting a concrete action plan to the executive team. 
Our company's strategic priority for this half is improving operational margin, but we cannot sacrifice our reputation for reliability.

Core Problem Statement: Our client freight operations are experiencing significant hidden costs due to persistent delivery delays, which we believe are eroding our profit margins and customer trust. 
We need to quantify this impact and build a data-backed plan to address it.

--- Client ---
{client}
--- DATA ---
{data}

--- SUMMARY STATISTICS ---
{summary}

Key Tasks & Hypotheses to Test:

1. Executive Summary: Write a concise, hard-hitting summary for the CEO that highlights the total estimated quarterly cost of delays and the single most impactful recommendation.

2. Diagnostic Analysis:
   - Instead of just listing problematic routes, perform a root-cause analysis on the 'Texas Triangle' bottleneck. 
     Is the issue carrier-specific, related to time-of-day, or something else?
   - Create a 2x2 matrix plotting all carriers based on Cost per Mile (X-axis) vs. On-Time Delivery % (Y-axis) 
     to visually identify our 'Strategic Partners' (low cost, high reliability) and 'High-Risk Partners' (high cost, low reliability).

3. Prescriptive Action Plan:
   For each recommendation, specify:
   - Expected Outcome
   - Estimated Impact
   - Level of Effort

4. Scenario Modeling & Future Outlook:
   - Model the impact of shifting 50% of ABC Carriers' volume to GHI Transport.
   - Estimate our risk exposure if fuel prices increase by 10% next quarter.
"""

SYSTEM_PROMPT = """
You are FreightOps BI — a senior logistics and freight analytics consultant.
Produce an executive-ready, BI-rich report with clear sections, metrics, visuals, and actions.

Rules:
1) Return a single JSON object that validates the provided JSON schema. No extra text.
2) Include BOTH:
   - markdown_report: full report in Markdown with headings, bullet points, and tables.
   - summary_json: structured analytics for charts and KPIs (Chart.js-ready).
3) Flag any data-quality issues under summary_json.data_quality.flags.
4) Use 'City, ST' format for locations already cleaned.
5) Provide at least 3 chart specs in Chart.js format (labels, datasets).
6) Keep executive tone: concise, definitive, and actionable.
"""

# JSON Schema to force structure
JSON_SCHEMA = {
    "name": "freight_bi_dual_output",
    "schema": {
        "type": "object",
        "properties": {
            "markdown_report": {"type": "string"},
            "summary_json": {
                "type": "object",
                "properties": {
                    "client": {"type": "string"},
                    "kpis": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "metric": {"type": "string"},
                                "value": {"type": ["string","number"]},
                                "note": {"type": "string"}
                            },
                            "required": ["metric","value"]
                        }
                    },
                    "charts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "type": {"type": "string"},   # bar|line|pie|scatter
                                "config": {"type": "object"}  # Full Chart.js config: {type,data,options}
                            },
                            "required": ["title","type","config"]
                        }
                    },
                    "data_quality": {
                        "type": "object",
                        "properties": {
                            "flags": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["flags"]
                    },
                    "recommendations": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["client","kpis","charts","data_quality","recommendations"]
            }
        },
        "required": ["markdown_report","summary_json"]
    },
    "strict": True,
}

# text={"format": {"type": "json_schema",
#             "name": "freight_bi_dual_output",
#             "schema": {
#                 "type": "object",
#                 "properties": {
#                     "name": {"type": "string"},
#                     "date": {"type": "string"},
#                     "participants": {"type": "array", "items": {"type": "string"}},
#                 },
#                 "required": ["name", "date", "participants"],
#                 "additionalProperties": False,
#             },
#             "strict": True,
#         }
#     },