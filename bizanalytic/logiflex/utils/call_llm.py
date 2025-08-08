import json
import re
import os, shutil
import glob
from contextlib import contextmanager
from pathlib import Path
from django.conf import settings
import google.generativeai as genai
from .prompts import gemini_report_elite1, gemini_report_professional1, chatgpt_prompt1
from django.contrib.staticfiles.storage import staticfiles_storage
import pandas as pd
from openai import OpenAI
from .decorators import print_progress, log_exceptions, sleep_and_retry, limits, token_bucket

# DATABASE_URL = 'sqlite:///id_cards.db'
# Base = declarative_base()
# engine = create_engine(DATABASE_URL)
# Session = sessionmaker(bind=engine)
GOOGLE_API_KEY = settings.GEMINIAPI_KEY
genai.configure(api_key=GOOGLE_API_KEY)

media_folder = settings.MEDIA_ROOT
client = OpenAI(
    # This is the default and can be omitted
    api_key=settings.OPENAI_KEY,
)

class GenerativeAI:
    def __init__(self, model_name):
        self.model = genai.GenerativeModel(model_name)

    @staticmethod
    def upload_file(file_path):
        return genai.upload_file(file_path)

    def generate_content(self, file, prompt):
        return self.model.generate_content([file, "\n\n", prompt])


def clean_result_text(result_text):
    cleaned_text = re.sub(r'```json|```', '', result_text).strip()
    try:
        json.loads(cleaned_text)
    except json.JSONDecodeError:
        cleaned_text = re.sub(r'\\n', ' ', cleaned_text)
        cleaned_text = re.sub(r'\\', '', cleaned_text)
    return cleaned_text


@log_exceptions
@sleep_and_retry
@limits(calls=2000, period=60)
@token_bucket(rate=10, capacity=100)
def process_id_card(file_path, generative_ai, prompt):
    uploaded_file = generative_ai.upload_file(file_path)
    result = generative_ai.generate_content(uploaded_file, prompt)

    if result.text:
        result_text = clean_result_text(result.text)
        try:
            result_json = json.loads(result_text)
            print(json.dumps(result_json, indent=4))
            data = result_json
            name = data.get("Name")
            address = data.get("Address")
            dob = data.get("Date of Birth (DOB)")
            expiry_date = data.get("Expiration Date (EXP)")
            license_number = data.get("Driver's License Number")
            license_class = data.get("Class")
            sex = data.get("Sex")
            height = data.get("Height")
            weight = data.get("Weight")
            eyes = data.get("Eyes")
            restrictions = data.get("Restrictions")
            endorsements = data.get("Endorsements")
            issue_date = data.get("Issue Date")
            donor = data.get("Donor")

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print(f"Result text: {result_text}")
    else:
        print(f"No content generated for {file_path}")


@log_exceptions
@sleep_and_retry
@limits(calls=2000, period=60)
@token_bucket(rate=10, capacity=100)
def call_llm_ai(file_path, generative_ai, prompt):

    uploaded_file = generative_ai.upload_file(file_path)
    # logo_file = generative_ai.upload_file(logo)
    print("File uploaded successfully")
    result = generative_ai.generate_content(uploaded_file, prompt)
    print("result:", result)
    if result.text:
        result_text = clean_result_text(result.text)
        print("result_text:", result_text)
        try:
            result_json = json.loads(result_text)
            return result_json
        except json.JSONDecodeError as e:
            return result_text


# @print_progress
def generate_analysis(report):
    # media_path = Path(media_folder + "/data_files/route_files/company_id_" + str(report.client.id) + "/report_" + str(report.id))
    file = report.routefile.name
    media_path = (media_folder, file)
    filepath = "/".join(media_path)
    # 'data_files/report_files/company_id_{0}'.format(client.id)
    result = None
    # print("mediaPath:", media_path)

    # Load CSV with Pandas
    df = pd.read_csv(filepath)

    data = df.to_dict(orient='records')
    summary = df.describe(include='all').to_string()
    customer = report.client.company
    prompt = f"""
Persona & Context:
Act as my strategic thinking partner, a world-class operations consultant with strong business intelligence and data storytelling capabilities. We are conducting a Q3 performance review for our logistics operations with the goal of presenting a comprehensive report to executives and operations managers.

Strategic Priority:
Our company's strategic priority this quarter is improving operational margin while maintaining our reputation for reliability. The report must balance strategic insight with operational detail.

Core Problem Statement:
Our freight operations are experiencing significant hidden costs due to persistent delivery delays. We believe these delays are eroding both profit margins and customer trust. We need to quantify this impact and develop a BI-rich, data-backed action plan.

--- Client ---
{customer}

Deliverables (Output Format: JSON-structured response):

1. **Executive Summary**
   - Total estimated quarterly cost of delivery delays.
   - One key recommendation with the highest ROI.
   - Summary chart showing delay trends over time.

2. **Analytics Section**
   - Summary Metrics: Total shipments, on-time %, average cost per mile, average delay per route, delay causes.
   - Visuals:
     - Delay heatmap (by route or region).
     - Weekly trend chart: delays vs. on-time deliveries.
     - Histogram of delay durations.
     - 2x2 Matrix: Carriers plotted by Cost per Mile (X-axis) vs. On-Time Delivery % (Y-axis).

3. **Diagnostic Insights**
   - Root-cause analysis of the "Texas Triangle" bottleneck.
     - Segment by carrier, time-of-day, day-of-week.
     - Highlight top 3 operational risks.
   - Highlight underperforming carriers and routes with thresholds.

4. **Prescriptive Recommendations**
   - Prioritized action plan. For each:
     - Action name
     - Description
     - Expected Outcome (e.g., "Reduce SA->DAL delay rate by 25%")
     - Estimated Impact ($/quarter)
     - Level of Effort (Low/Medium/High)
   - Suggested KPI to track each action.

5. **Predictive Modeling**
   - Model the impact of shifting 50% of ABC Carriers’ volume to GHI Transport:
     - New delay rate
     - Cost differential
   - Risk scenario if fuel prices increase by 10%:
     - Which routes or carriers are most sensitive
     - Mitigation strategies

6. **Recommendations Dashboard Schema**
   - Output a JSON-ready structure to feed a BI dashboard or Django frontend.
   - Include labels, chart types, data points, and metric definitions.

---

Input:
You will receive a CSV file with shipment-level data including: Origin, Destination, Carrier, Cost per Mile, On-Time status, Delay Duration (minutes), Date, and Fuel Cost Index at time of shipment.
--- DATA ---
{data}

Assume clean data and summarize patterns at both shipment and route levels.
--- SUMMARY STATISTICS ---
{summary}

Output format: JSON. Keep visuals as chart spec suggestions (e.g., matplotlib, seaborn, or Vega-Lite).
"""


    # prompt = gemini_report_professional1.format(report.client.company)
    print("prompt:", prompt)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,

    )
    # logo = staticfiles_storage.path("assets/logo/logo1-1.png")

    # generative_ai = GenerativeAI("gemini-1.5-flash")
    # generative_ai = GenerativeAI("gemini-2.5-flash")
    results = response.choices[0].message.content
    # for file_path in media_path.glob("*.*"):
    #     print("file path:", file_path)
        # result = call_llm_ai(file_path, generative_ai, prompt)
        # results = {**results, **result}
        # deletefile(file_path)
    return results


def deletefile(file_path):
  try:
    if os.path.isfile(file_path) or os.path.islink(file_path):
      os.unlink(file_path)
    elif os.path.isdir(file_path):
      shutil.rmtree(file_path)
  except Exception as e:
    print('Failed to delete %s. Reason: %s' % (file_path, e))