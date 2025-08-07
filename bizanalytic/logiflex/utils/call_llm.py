import json
import re
import os, shutil
import glob
from contextlib import contextmanager
from pathlib import Path
from django.conf import settings
import google.generativeai as genai
from .prompts import gemini_report_elite, gemini_report_professional
from django.contrib.staticfiles.storage import staticfiles_storage
from .decorators import print_progress, log_exceptions, sleep_and_retry, limits, token_bucket

# DATABASE_URL = 'sqlite:///id_cards.db'
# Base = declarative_base()
# engine = create_engine(DATABASE_URL)
# Session = sessionmaker(bind=engine)
GOOGLE_API_KEY = settings.GEMINIAPI_KEY
genai.configure(api_key=GOOGLE_API_KEY)

media_folder = settings.MEDIA_ROOT


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
def call_llm_ai(file_path, generative_ai, prompt, logo):

    uploaded_file = generative_ai.upload_file(file_path)
    logo_file = generative_ai.upload_file(logo)

    result = generative_ai.generate_content(uploaded_file, logo, prompt)
    if result.text:
        result_text = clean_result_text(result.text)
        print(result_text)
        try:
            result_json = json.loads(result_text)
            return result_json
        except json.JSONDecodeError as e:
            return result_text


# @print_progress
def generate_analysis(report):
    media_path = Path(media_folder + "data_files/route_files/company_id_" + report.client.id + "/report_" + report.id)
    # 'data_files/report_files/company_id_{0}'.format(client.id)
    result = None

    prompt = gemini_report_professional.format(report.client.company)

    logo = staticfiles_storage.path("assets/logo/logo1-1.png")
    # prompt = (
    #     "Please extract and parse the text from the ID card image. "
    #     "Ensure the extracted information is formatted for database entry with the following fields: "
    #     "Name, City of Birth, Date of Birth (DOB), Expiration Date (EXP) "
    #     "Provide the output in a structured JSON format without any backticks. "
    #     "Example format: "
    #     "{"
    #     "\"Identity\": \"C356899\", "
    #     "\"Name\": \"John Doe\", "
    #     "\"City of Birth\": \"Casablanca\", "
    #     "\"Date of Birth (DOB)\": \"01/01/1970\", "
    #     "\"Expiration Date (EXP)\": \"01/01/2030\", "
    #     "\"Driver's License Number\": \"D1234567\", "
    #     "\"Address\": \"123 Main St, Any town, USA\", "
    #     "\"Gender\": \"M\""
    #
    #     "}"
    # )


    # generative_ai = GenerativeAI("gemini-1.5-flash")
    generative_ai = GenerativeAI("gemini-1.5-flash-8b")
    results = {}
    for file_path in media_path.glob("*.*"):
        result = call_llm_ai(file_path, generative_ai, prompt, logo)
        results = {**results, **result}
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