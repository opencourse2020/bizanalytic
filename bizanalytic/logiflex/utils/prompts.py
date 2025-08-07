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

use the attached logo for branding
"""
