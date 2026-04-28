from django.shortcuts import render, redirect
from django.views.generic import (
    UpdateView,
    RedirectView,
    CreateView,
    View,
    TemplateView,
    DetailView,
    ListView,
    DeleteView,
)
from django.views.decorators.cache import cache_page
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import hashlib
import time
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.db import transaction
from django.utils.timezone import now
import json
import requests
import math
import pandas as pd
# Third party libraries
import stripe
from datetime import datetime, timedelta
from user_agents import parse
from openai import OpenAI
# from . import models, forms
from .forms import *
from .models import *
from bizanalytic.profiles.mixins import JsonFormMixin
from bizanalytic.profiles.models import User
from .utils.mail import *
from .utils.tools import *
from .utils.call_llm import generate_analysis
from .utils.pre_process_datafile import *
from .utils.local_analytics import *
from .utils.report_helpers import *
from .utils.prompts import SYSTEM_PROMPT, JSON_SCHEMA
from .utils.report_generator import generate_full_report, analyze_in_transit
# Create your views here.

# Initiate variables
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe_price_id = settings.STRIPE_PRICE_ID
stripe_publishable = settings.STRIPE_PUBLISHABLE_KEY
stripe_webhook = settings.STRIPE_WEBHOOK_SECRET
OPENAI_KEY = settings.OPENAI_KEY


# client = OpenAI(api_key=OPENAI_KEY)


def get_ip(request):
    try:
        x_forward = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forward:
            ip = x_forward.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
    except:
        ip = ""
    return ip


class LandingFreeView(TemplateView):
    template_name = "logiflex/landing_free.html"


class FreeFreightOpsView(TemplateView):
    template_name = "logiflex/freightops-report-template.html"

    def get_context_data(self, **kwargs):
        report = LogiflexReport.objects.filter(pk=190, download_code="mNUW9tzr").first()
        dff = pd.read_csv(report.routefile)
        validator = ColumnNameValidator()

        results = validator.validate_and_correct_columns(dff)
        df = clean_data(dff)
        df = calculate_kpis(df)

        # Carrier Analysis
        carrier_stats = prepare_carrier_stats(df)
        carrier_stats["AvgCostPerMile"] = carrier_stats["AvgCostPerMile"].round(3)
        carrier_stats["AvgFreightCost"] = carrier_stats["AvgFreightCost"].round(2)
        carrier_stats["AvgCostPerPound"] = carrier_stats["AvgCostPerPound"].round(3)
        carrier_stats = carrier_stats.reset_index()
        carrier_stats = json.loads(carrier_stats.to_json(orient='records'))
        kwargs["carrierstats"] = carrier_stats

        # Drivers Analysis
        driver_stats = prepare_driver_stats(df)
        driver_stats["OnTimeRate"] = driver_stats["OnTimeRate"] * 100
        driver_stats = driver_stats.reset_index()
        driver_stats = json.loads(driver_stats.to_json(orient='records'))
        kwargs["driverstats"] = driver_stats

        # Routes Analysis
        route_stats = prepare_route_stats(df)
        route_stats = route_stats.reset_index()

        # Pivot for heatmap
        heatmap_data = route_stats.pivot(
            index='OriginCity',
            columns='DestinationCity',
            values='AvgCostPerMile'
        )
        start = heatmap_data.min().min()
        end = heatmap_data.max().max()
        colors = ['#FCB79D', '#FB8464', '#F44F39', '#B81419', '#67000D', ]
        costintensity = ['Very Low', 'Low', 'Medium', 'High', 'Extreme']
        num_parts = 5
        division_points = np.linspace(start, end, num_parts + 1)
        division_points = [float(x) for x in division_points]
        range_values = []
        for i in range(int(len(division_points) - 1)):
            range_values.append({"from": division_points[i], "to": division_points[i + 1], "name": costintensity[i],
                                 "color": colors[i]})

        heatmap_data = heatmap_data.fillna(0)

        hm_dest = []

        for index, row in heatmap_data.iterrows():
            hm_dest.append({"name": index, "data": row.to_list()})
        heatmap_columns = heatmap_data.columns.to_list()
        print("range_values:", range_values)
        heatmap_values = {"range_values": range_values, "heatmapvalues": hm_dest, "heatmap_columns": heatmap_columns}
        # kwargs["rangevalues"] = range_values
        kwargs["heatmapvalues"] = heatmap_values
        # Carrier Cost Per Mile Analysis
        cost_mile = df[['CarrierName', 'CostPerMile']]
        cost_mile["CostPerMile"] = cost_mile["CostPerMile"].round(4)
        cost_mile = json.loads(cost_mile.to_json(orient='records'))
        kwargs["costmile"] = cost_mile

        # Driver Cost Per Mile Analysis
        cost_mile_driver = df[['DriverName', 'CostPerMile']]
        cost_mile_driver["CostPerMile"] = cost_mile_driver["CostPerMile"].round(4)
        cost_mile_driver = json.loads(cost_mile_driver.to_json(orient='records'))
        kwargs["costmiledriver"] = cost_mile_driver

        return super(FreeFreightOpsView, self).get_context_data(**kwargs)

class FreeFreightDiagnosticView(TemplateView):
    template_name = "logiflex/freight-health-check.html"


class IndexView(TemplateView):
    template_name = "logiflex/home.html"
    def get_context_data(self, **kwargs):
        ip = get_ip(self.request)
        user_browser = self.request.META.get("HTTP_USER_AGENT", "")
        user_language = self.request.META.get("HTTP_ACCEPT_LANGUAGE", "")
        user_page_referer = self.request.META.get("HTTP_REFERER", "")

        user_agent = parse(user_browser)
        device_type = user_agent.device  # e.g., 'mobile', 'tablet', 'pc'
        os_family = user_agent.os.family  # e.g., 'iOS', 'Android', 'Windows'
        browser_family = user_agent.browser.family  # e.g., 'Chrome', 'Firefox', 'Safari'

        return super(IndexView, self).get_context_data(**kwargs)

class RouteFileView(TemplateView):
    template_name = "logiflex/report_detail.html"
    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        report = LogiflexReport.objects.filter(pk=pu).first()


        # Check file extension
        extension_ok = True
        if report.routefile_ext == ".csv":
            df = pd.read_csv(report.routefile)
        elif report.routefile_ext == ".xlsx" or report.routefile_ext == ".xls":
            df = pd.read_excel(report.routefile)
        else:
            extension_ok = False

        if extension_ok:
            # Get route file information
            carriers = df['CarrierName'].unique()
            null_carriers = df['CarrierName'].isnull().sum()
            if null_carriers > 0:
                carriers_cleaned = df.dropna(subset=['CarrierName'])
                carriers = carriers_cleaned['CarrierName'].unique()

            drivers = df['DriverName'].unique()
            null_drivers = df['DriverName'].isnull().sum()
            if null_drivers > 0:
                drivers_cleaned = df.dropna(subset=['DriverName'])
                drivers = drivers_cleaned['DriverName'].unique()

            deliverystatus = df['DeliveryStatus'].unique()
            null_deliverystatus = df['DeliveryStatus'].isnull().sum()
            if null_deliverystatus > 0:
                deliverystatus_cleaned = df.dropna(subset=['DeliveryStatus'])
                deliverystatus = deliverystatus_cleaned['DeliveryStatus'].unique()

            distance_str, fuelcost_str, loadweight_str, deliveryhrs_str = process_route_info(df.describe())

            log_message = LogEntry.objects.filter(report=report).first()
            if log_message.column_report:
                logcol = log_message.column_report.split("@@#@@")
            if log_message.date_report:
                logdate = log_message.date_report.split("@@#@@")
            if log_message.citi_report:
                logcity = log_message.citi_report.split("@@#@@")

            # Report status percentage
            reportstatus = 50
            if report.report_text:
                reportstatus = 100
            elif report.report_status:
                reportstatus = 80

            if report:
                kwargs["report"] = report
                kwargs["reportstatus"] = reportstatus
                kwargs["logcolumn"] = logcol
                kwargs["logdate"] = logdate
                kwargs["logcity"] = logcity
                kwargs["carriers"] = carriers
                kwargs["null_carriers"] = null_carriers
                kwargs["drivers"] = drivers
                kwargs["null_drivers"] = null_drivers
                kwargs["deliverystatus"] = deliverystatus
                kwargs["null_deliverystatus"] = null_deliverystatus
                kwargs["distance_str"] = distance_str
                kwargs["fuelcost_str"] = fuelcost_str
                kwargs["loadweight_str"] = loadweight_str
                kwargs["deliveryhrs_str"] = deliveryhrs_str

            else:
                kwargs["report"] = ""
                kwargs["logcolumn"] = ""
                kwargs["logdate"] = ""
                kwargs["logcity"] = ""
        return super(RouteFileView, self).get_context_data(**kwargs)


class ReportView(TemplateView):
    template_name = "logiflex/report_view.html"

    def get(self, request, *args, **kwargs):

        pu = self.kwargs.get("pk")
        user = self.request.user
        query = self.request.GET.get("cat")
        if pu == 190 or pu == 195 or pu == 199:
            report = LogiflexReport.objects.filter(pk=pu, download_code=query).first()
        else:
            if user.is_authenticated:
                if user.is_staff:
                    report = LogiflexReport.objects.filter(pk=pu, download_code=query).first()
                else:
                    report = LogiflexReport.objects.filter(client__user=user, pk=pu, download_code=query, report_approved=True).first()
            else:
                report = LogiflexReport.objects.filter(pk=pu, download_code=query, report_approved=True).first()

        # Example: Redirect at the dispatch level
        if not report:
            return redirect('profiles:403')  # Redirect to login page by URL name
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        user = self.request.user
        query = self.request.GET.get("cat")
        # print("user1: ", user)
        # print("user1 name: ", user.username)
        # if not user.is_authenticated:
        #     print("user2: ", user)

        # else:
        if pu == 190 or pu == 195 or pu == 199:
            report = LogiflexReport.objects.filter(pk=pu, download_code=query).first()
        else:

            if user.is_authenticated:
                if user.is_staff:
                    report = LogiflexReport.objects.filter(pk=pu, download_code=query).first()
                else:
                    report = LogiflexReport.objects.filter(client__user=user, pk=pu, download_code=query,
                                                           report_approved=True).first()
            else:
                report = LogiflexReport.objects.filter(pk=pu, download_code=query, report_approved=True).first()

        print("report ID:", report)
        if report:
            if not report.viewed:
                report.viewed = True
                report.save()
            # Check file extension
            extension_ok = True
            if report.routefile_ext == ".csv":
                dff = pd.read_csv(report.routefile)
            elif report.routefile_ext == ".xlsx" or report.routefile_ext == ".xls":
                dff = pd.read_excel(report.routefile)
            else:
                extension_ok = False

            if extension_ok:
                df = clean_data(dff)
                df = calculate_kpis(df)
                print("report ID2:", report.id)
                # Carrier Analysis
                carrier_stats = prepare_carrier_stats(df)
                carrier_stats["AvgCostPerMile"] = carrier_stats["AvgCostPerMile"].round(3)
                carrier_stats["AvgFreightCost"] = carrier_stats["AvgFreightCost"].round(2)
                carrier_stats["AvgCostPerPound"] = carrier_stats["AvgCostPerPound"].round(3)
                carrier_ontime = carrier_stats["OnTimeRate"].max()
                carrier_ontime_name = carrier_stats["OnTimeRate"].idxmax()
                carrier_costpermile = carrier_stats["AvgCostPerMile"].min()
                carrier_costpermile_name = carrier_stats["AvgCostPerMile"].idxmin()
                carrier_freightcost = carrier_stats["AvgFreightCost"].min()
                carrier_freightcost_name = carrier_stats["AvgFreightCost"].idxmin()
                carrier_costpound = carrier_stats["AvgCostPerPound"].min()
                carrier_costpound_name = carrier_stats["AvgCostPerPound"].idxmin()

                carrier_stats = carrier_stats.reset_index()
                carrier_stats = json.loads(carrier_stats.to_json(orient='records'))
                # Carrier Contingency and Reliability Vs Cost Analysis
                if not report.contingency_result:
                    highcostvariance, lowcostvariance, costreliability_action, contingency_result, contingency_action = prepare_data_report(
                        df)
                    report.contingency_result = contingency_result
                    report.highvariance = highcostvariance
                    report.lowvariance = lowcostvariance
                    report.costreliability_action = costreliability_action
                    report.contingency_action = contingency_action
                    report.save()
                else:
                    contingency_result = report.contingency_result
                    highcostvariance = report.highvariance
                    lowcostvariance = report.lowvariance
                    costreliability_action = report.costreliability_action
                    contingency_action = report.contingency_action

                #

                # Drivers Analysis
                driver_stats = prepare_driver_stats(df)
                driver_messages, driver_actions, driver_extended_message = prepare_driver_analysis(driver_stats)
                driver_stats["OnTimeRate"] = driver_stats["OnTimeRate"]*100
                driver_totalmiles = driver_stats["TotalMiles"].max()
                driver_totalmiles_name = driver_stats["TotalMiles"].idxmax()
                driver_speed = driver_stats["MedianSpeed"].max()
                driver_speed_name = driver_stats["MedianSpeed"].idxmax()
                driver_medianmpg = driver_stats["MedianMPG"].max()
                driver_medianmpg_name = driver_stats["MedianMPG"].idxmax()
                driver_ontime = driver_stats["OnTimeRate"].max()
                driver_ontime_name = driver_stats["OnTimeRate"].idxmax()
                driver_stats = driver_stats.reset_index()
                driver_stats = json.loads(driver_stats.to_json(orient='records'))

                # Routes Analysis
                route_stats = prepare_route_stats(df)
                rs1 = route_stats.head(5)
                serrie1 = df[(df['OriginCity'] == rs1.index[0][0]) & (df['DestinationCity'] == rs1.index[0][1])]
                serie1 = []
                for index, row in serrie1.iterrows():
                    serie1.append(
                        [float(row['Speed']), float(row['CostPerMile']), float(row['LoadWeight_lbs']/2000)])
                serrie2 = df[(df['OriginCity'] == rs1.index[1][0]) & (df['DestinationCity'] == rs1.index[1][1])]
                serie2 = []
                for index, row in serrie2.iterrows():
                    serie2.append(
                        [float(row['Speed']), float(row['CostPerMile']), float(row['LoadWeight_lbs']/2000)])
                serrie3 = df[(df['OriginCity'] == rs1.index[2][0]) & (df['DestinationCity'] == rs1.index[2][1])]
                serie3 = []
                for index, row in serrie3.iterrows():
                    serie3.append(
                        [float(row['Speed']), float(row['CostPerMile']), float(row['LoadWeight_lbs']/2000)])
                serrie4 = df[(df['OriginCity'] == rs1.index[3][0]) & (df['DestinationCity'] == rs1.index[3][1])]
                serie4 = []
                for index, row in serrie4.iterrows():
                    serie4.append(
                        [float(row['Speed']), float(row['CostPerMile']), float(row['LoadWeight_lbs']/2000)])
                serrie5 = df[(df['OriginCity'] == rs1.index[4][0]) & (df['DestinationCity'] == rs1.index[4][1])]
                serie5 = []
                for index, row in serrie5.iterrows():
                    serie5.append(
                        [float(row['Speed']), float(row['CostPerMile']), float(row['LoadWeight_lbs']/2000)])
                route_stats = route_stats.reset_index()

                # Pivot for heatmap
                heatmap_data = route_stats.pivot(
                    index='OriginCity',
                    columns='DestinationCity',
                    values='AvgCostPerMile'
                )
                start = heatmap_data.min().min()
                end = heatmap_data.max().max()
                colors = ['#FCB79D', '#FB8464', '#F44F39', '#B81419', '#67000D', ]
                costintensity = ['Very Low', 'Low', 'Medium', 'High', 'Extreme']
                num_parts = 5
                division_points = np.linspace(start, end, num_parts + 1)
                division_points = [float(x) for x in division_points]
                range_values = []
                for i in range(int(len(division_points) - 1)):
                    range_values.append({"from": division_points[i], "to": division_points[i + 1], "name": costintensity[i], "color": colors[i]})

                heatmap_data = heatmap_data.fillna(0)

                hm_dest = []

                for index, row in heatmap_data.iterrows():
                    hm_dest.append({"name": index, "data": row.to_list()})
                heatmap_columns = heatmap_data.columns.to_list()
                print("range_values:", range_values)
                heatmap_values = {"range_values": range_values, "heatmapvalues": hm_dest, "heatmap_columns": heatmap_columns}
                # kwargs["rangevalues"] = range_values
                kwargs["heatmapvalues"] = heatmap_values
                kwargs["route_heatmap"] = route_heatmap
                kwargs["route_heatmap_plain"] = route_heatmap_plain
                kwargs["route_heatmap_short"] = route_heatmap_short

                # kwargs["heatmap_columns"] = heatmap_columns

                # Route Efficiency Speed Vs Cost
                data_series = []
                for index, row in route_stats.iterrows():
                    data_series.append(
                        [float(row['MedianSpeed']), float(row['AvgCostPerMile']), float(row['ShipmentCount'])])

                meanspeed = round(route_stats['MedianSpeed'].mean(), 2)
                minspeed = math.floor(route_stats['MedianSpeed'].min())
                maxspeed = math.ceil(route_stats['MedianSpeed'].max())

                if maxspeed < 55:
                    maxspeed = 55
                multiplier = 10
                meandistance = round(route_stats['AvgDistance'].mean(), 2)
                meanshipment = round(route_stats['ShipmentCount'].mean(), 2)
                meancost = round(route_stats['AvgCostPerMile'].mean(), 3)
                mincost = route_stats['AvgCostPerMile'].min()
                maxcost = route_stats['AvgCostPerMile'].max()
                mincost_tmp = math.floor(mincost * multiplier) / multiplier
                maxcost_tmp = math.floor(maxcost * multiplier) / multiplier
                if mincost < mincost_tmp + 0.05:
                    mincost = mincost_tmp
                else:
                    mincost = mincost_tmp + 0.05
                if maxcost < maxcost_tmp:
                    maxcost = maxcost_tmp
                else:
                    maxcost = maxcost_tmp + 0.05

                # serie1 = json.loads(serie1.to_json(orient='records'))
                # serie2 = json.loads(serie2.to_json(orient='records'))
                # serie3 = json.loads(serie3.to_json(orient='records'))
                # serie4 = json.loads(serie4.to_json(orient='records'))
                # serie5 = json.loads(serie5.to_json(orient='records'))
                serie1_name = rs1.index[0][0].split(",")[0].replace(" ", "")[:5] + "-" + rs1.index[0][1].split(",")[
                                                                                              0].replace(" ", "")[:5]
                serie2_name = rs1.index[1][0].split(",")[0].replace(" ", "")[:5] + "-" + rs1.index[1][1].split(",")[
                                                                                              0].replace(" ", "")[:5]
                serie3_name = rs1.index[2][0].split(",")[0].replace(" ", "")[:5] + "-" + rs1.index[2][1].split(",")[
                                                                                              0].replace(" ", "")[:5]
                serie4_name = rs1.index[3][0].split(",")[0].replace(" ", "")[:5] + "-" + rs1.index[3][1].split(",")[
                                                                                              0].replace(" ", "")[:5]
                serie5_name = rs1.index[4][0].split(",")[0].replace(" ", "")[:5] + "-" + rs1.index[4][1].split(",")[
                                                                                              0].replace(" ", "")[:5]
                # route_stats = json.loads(route_stats.to_json(orient='records'))
                # x_medianspeed = json.loads(route_stats["MedianSpeed"].to_json(orient='records'))
                # y_costpermile = json.loads(route_stats["AvgCostPerMile"].to_json(orient='records'))
                # size_shipmentcount = json.loads(route_stats["ShipmentCount"].to_json(orient='records'))
                # kwargs["x_medianspeed"] = x_medianspeed
                # kwargs["y_costpermile"] = y_costpermile
                worstrouteefficiency_data = {"serie1": serie1, "serie2": serie2, "serie3": serie3, "serie4": serie4,
                                             "serie5": serie5, "serie1_name": serie1_name, "serie2_name": serie2_name,
                                             "serie3_name": serie3_name, "serie4_name": serie4_name, "serie5_name": serie5_name}
                routeefficiency_data = {"routeefficiency": data_series, "maxspeed": maxspeed, "minspeed": minspeed, "maxcost": maxcost, "mincost": mincost, "meanspeed": meanspeed, "meancost": meancost}
                kwargs["routeefficiency_data"] = routeefficiency_data
                kwargs["worstrouteefficiency_data"] = worstrouteefficiency_data
                kwargs["routemessage"] = routes_message
                kwargs["meanspeed"] = meanspeed
                kwargs["meandistance"] = meandistance
                kwargs["meanshipment"] = meanshipment
                kwargs["meancost"] = meancost
                kwargs["currentyear"] = now().year
                kwargs["client"] = report.client.company
                kwargs["reportid"] = report.report_id
                kwargs["reporttype"] = report.report_type
                kwargs["carrier_ontime"] = carrier_ontime
                kwargs["carrier_costpermile"] = carrier_costpermile
                kwargs["carrier_freightcost"] = carrier_freightcost
                kwargs["carrier_costpound"] = carrier_costpound
                kwargs["carrier_ontime_name"] = carrier_ontime_name
                kwargs["carrier_costpermile_name"] = carrier_costpermile_name
                kwargs["carrier_freightcost_name"] = carrier_freightcost_name
                kwargs["carrier_costpound_name"] = carrier_costpound_name
                kwargs["driver_ontime"] = driver_ontime
                kwargs["driver_totalmiles"] = driver_totalmiles
                kwargs["driver_speed"] = driver_speed
                kwargs["driver_medianmpg"] = driver_medianmpg
                kwargs["driver_ontime_name"] = driver_ontime_name
                kwargs["driver_totalmiles_name"] = driver_totalmiles_name
                kwargs["driver_speed_name"] = driver_speed_name
                kwargs["driver_medianmpg_name"] = driver_medianmpg_name
                driver_hcarvar, driver_lcarvar, driver_costreliability_action = prepare_driver_costvariance(df)
                kwargs["driverhighcostvariance"] = driver_hcarvar
                kwargs["driverlowcostvariance"] = driver_lcarvar
                kwargs["driver_costreliability_action"] = driver_costreliability_action
                kwargs["reportdate"] = report.report_date

                if report.report_type == "lite":

                    # Carrier Cost Reliability Analysis
                    kwargs["carrierstats"] = carrier_stats
                    kwargs["contigency"] = contingency_result
                    kwargs["contingency_action"] = contingency_action
                    kwargs["highcostvariance"] = highcostvariance
                    kwargs["lowcostvariance"] = lowcostvariance
                    kwargs["costreliability_action"] = costreliability_action

                    # Driver On-time Rate Vs. MPG Analysis
                    kwargs["driverstats"] = driver_stats

                    # Driver Messages and Actions
                    kwargs["driver_messages"] = driver_messages
                    kwargs["driver_actions"] = driver_actions

                    cost_mile = '{"0":"0"}'
                    kwargs["costmile"] = json.loads(cost_mile)
                    kwargs["costmiledriver"] = json.loads(cost_mile)

                    if report.report_text:
                        raw = report.report_text
                        data = json.loads(raw)
                        # data = raw

                        # markdown_report = data.get("markdown_report", "")

                        kwargs["report_route"] = data.get("summary_json", {})
                        kwargs["report_carrier"] = ""
                        kwargs["report_driver"] = ""

                elif report.report_type == "advanced":

                    # Carrier Cost Reliability Analysis
                    print("carrier_stats:", carrier_stats)
                    kwargs["carrierstats"] = carrier_stats
                    kwargs["contigency"] = contingency_result
                    kwargs["contingency_action"] = contingency_action

                    # Driver On-time Rate Vs. MPG Analysis
                    kwargs["driverstats"] = driver_stats

                    # Driver Messages and Actions
                    kwargs["driver_messages"] = driver_extended_message
                    kwargs["driver_actions"] = driver_actions

                    # Carrier Cost Per Mile Analysis
                    cost_mile = df[['CarrierName', 'CostPerMile']]
                    cost_mile["CostPerMile"] = cost_mile["CostPerMile"].round(4)
                    cost_mile = json.loads(cost_mile.to_json(orient='records'))
                    kwargs["costmile"] = cost_mile

                    # Driver Cost Per Mile Analysis
                    cost_mile_driver = df[['DriverName', 'CostPerMile']]
                    cost_mile_driver["CostPerMile"] = cost_mile_driver["CostPerMile"].round(4)
                    cost_mile_driver = json.loads(cost_mile_driver.to_json(orient='records'))
                    kwargs["costmiledriver"] = cost_mile_driver
                    kwargs["driver_costreliability_action_ext"] = driver_cost_variance

                    # Carrier Messages and Actions
                    kwargs["highcostvariance"] = highcostvariance
                    kwargs["lowcostvariance"] = lowcostvariance
                    kwargs["costreliability_action"] = costreliability_action

                    # data = raw

                    if report.report_carrier:
                        rawc = report.report_carrier
                        datac = json.loads(rawc)
                        kwargs["report_carrier"] = datac.get("summary_json", {})
                    if report.report_driver:
                        rawd = report.report_driver
                        datad = json.loads(rawd)
                        kwargs["report_driver"] = datad.get("summary_json", {})
                    if report.report_route:
                        rawr = report.report_route
                        datar = json.loads(rawr)
                        kwargs["report_route"] = datar.get("summary_json", {})

                elif report.report_type == "free":
                    kwargs["carrierstats"] = carrier_stats
                    kwargs["driverstats"] = driver_stats
                    kwargs["costmile"] = 0
                    kwargs["costmiledriver"] = 0

        else:
            print("report none")

        return super(ReportView, self).get_context_data(**kwargs)


class ReportSummaryView(LoginRequiredMixin, TemplateView):
    template_name = "logiflex/report_template.html"

    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        user = self.request.user
        if user.is_staff:
            report = LogiflexReport.objects.filter(pk=pu).first()
        else:
            report = LogiflexReport.objects.filter(client__user=user, pk=pu).first()
            if not report.viewed:
                report.viewed = True
                report.save()

        if report:
            log = LogEntry.objects.filter(report=report).first()
            flags = json.dumps(log.flags, indent=2)
            if report.report_text:

                #
                # # run summary analysis
                # csv_text = read_csv_into_text_and_df(report.routefile)
                # # Compact summary for prompt to control tokens (use this instead of full CSV if large)
                # asynch_preprocess = run_LLM_analysis.delay(flags, pu)
                # raw = asynch_preprocess.get()
                #
                # # report.report_text = raw
                # # report.report_status = "download"
                # # report.save()

                raw = report.report_text
                data = json.loads(raw)
            # data = raw
            client_name = report.client.company
            markdown_report = data.get("markdown_report", "")
            summary_json = data.get("summary_json", {})
            print("client view", client_name)

        else:
            client_name = ""
            markdown_report = ""
            summary_json = ""

        kwargs["client_name"] = client_name
        kwargs["markdown_report"] = markdown_report
        kwargs["summary_json"] = summary_json
        return super(ReportSummaryView, self).get_context_data(**kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "logiflex/dashboard.html"

    def get_context_data(self, **kwargs):
        pu = self.request.user
        servicepayment = ServicePayment.objects.filter(client__user_id=pu).first()
        payments = PaymentsHistory.objects.filter(client__user_id=pu).order_by('-id')[:3]
        report_allowed = 0
        if servicepayment:
            if servicepayment.can_generate_report() or servicepayment.can_generate_advanced_report():
                report_allowed = 1
            kwargs["report_allowed"] = report_allowed

            kwargs["contact_name"] = servicepayment.client.contact_name
            kwargs["company"] = servicepayment.client.company
            kwargs["email"] = servicepayment.client.email
            kwargs["clientid"] = servicepayment.client.id
            kwargs["subscriptionstatus"] = servicepayment.status
            kwargs["isactive"] = servicepayment.is_active
            clienttype = 1
        else:
            kwargs["subscriptionstatus"] = "0"
            kwargs["isactive"] = False
        reports = LogiflexReport.objects.filter(client__user=pu)
        total_reports = reports.count()
        if total_reports == 0:
            total_reports = 1

        ontime_reports = reports.filter(report_status="download")
        num_ontime_reports = ontime_reports.count()
        ontime_reports = ontime_reports.order_by('report_number')[:3]
        processing_reports = reports.filter(report_status="processing")
        num_processing_reports = processing_reports.count()
        processing_reports = processing_reports.order_by('report_number')[:3]
        canceled_reports = reports.filter(report_status="canceled")
        num_canceled_reports = canceled_reports.count()
        canceled_reports = canceled_reports.order_by('report_number')[:3]
        num_late_reports = reports.filter(expected_delivery__lt=now(), report_status="processing").count() + \
                       reports.filter(report_status="late").count()
        finished_reports = num_ontime_reports + num_late_reports
        late_reports = reports.filter(expected_delivery__lt=now(), report_status="processing").order_by('report_number')[:3]
        new_reports = reports.filter(viewed=False, report_approved=True)
        if finished_reports == 0:
            finished_reports = 1
        kwargs["latest_ontime_reports"] = num_ontime_reports
        kwargs["latest_processing_reports"] = num_processing_reports
        kwargs["latest_canceled_reports"] = num_canceled_reports
        kwargs["latest_late_reports"] = num_late_reports
        kwargs["ontime_reports"] = math.ceil((num_ontime_reports/total_reports)*100)
        kwargs["processing_reports"] = math.ceil((num_processing_reports/total_reports)*100)
        kwargs["canceled_reports"] = math.ceil((num_canceled_reports/total_reports)*100)
        kwargs["late_reports"] = math.ceil((num_late_reports/finished_reports)*100)
        kwargs["newreports"] = new_reports

        kwargs["lreports"] = servicepayment.reports_allowed - servicepayment.reports_used
        kwargs["areports"] = servicepayment.advanced_reports_allowed - servicepayment.advanced_reports_used
        kwargs["acredits"] = servicepayment.advanced_credits
        kwargs["lcredits"] = servicepayment.lite_credits
        kwargs["subscrib_status"] = servicepayment.is_active
        if servicepayment.is_active:
            kwargs["enddate"] = servicepayment.reset_date
        else:
            kwargs["enddate"] = servicepayment.end_date
        kwargs["startdate"] = servicepayment.date_added
        kwargs["servicetype"] = servicepayment.service_type.name
        kwargs["payments"] = payments

        return super(DashboardView, self).get_context_data(**kwargs)


class ResumeSubscriptionView(LoginRequiredMixin, CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):
        logiclient = LogiFlexClient.objects.filter(user=self.request.user).first()
        subscription = ServicePayment.objects.filter(client=logiclient).first()
        changesubscription = ChangeSubscriptionRequest.objects.filter(client=logiclient, processed=False).first()
        message = "Your will receive an email once your request is been processed"
        if subscription:
            if subscription.status == "2" and subscription.is_active:
                if changesubscription and not changesubscription.request == "3":
                    changesubscription.request = "3"
                    changesubscription.save()
                elif not changesubscription:
                    ChangeSubscriptionRequest.objects.create(client=logiclient, subscription=subscription,
                                                             request="3")

        data = {"submessage": message}

        return JsonResponse(data)


class PauseSubscriptionView(LoginRequiredMixin, CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):
        logiclient = LogiFlexClient.objects.filter(user=self.request.user).first()
        subscription = ServicePayment.objects.filter(client=logiclient).first()
        changesubscription = ChangeSubscriptionRequest.objects.filter(client=logiclient, processed=False).first()
        message = "Your will receive an email once your request is been processed"
        if subscription:
            if (subscription.status == "1" or subscription.status == "4") and subscription.is_active:
                if changesubscription and not changesubscription.request == "1":
                    changesubscription.request = "1"
                    changesubscription.save()
                elif not changesubscription:
                    ChangeSubscriptionRequest.objects.create(client=logiclient, subscription=subscription, request="1")

        data = {"submessage": message}

        return JsonResponse(data)


class CancelSubscriptionView(LoginRequiredMixin, CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):
        logiclient = LogiFlexClient.objects.filter(user=self.request.user).first()
        subscription = ServicePayment.objects.filter(client=logiclient).first()
        changesubscription = ChangeSubscriptionRequest.objects.filter(client=logiclient, processed=False).first()
        message = "Your will receive an email once your request is been processed"
        if subscription:
            if (subscription.status == "1" or subscription.status == "4") and subscription.is_active:
                if changesubscription and not changesubscription.request == "2":
                    changesubscription.request = "2"
                    changesubscription.save()
                elif not changesubscription:
                    ChangeSubscriptionRequest.objects.create(client=logiclient, subscription=subscription, request="2")

        data = {"submessage": message}

        return JsonResponse(data)


class ReportHelpersView(CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):
        helper = request.POST.get("cixphoto")

        message = ""
        if helper == "hcv":
            message = reckless_rocket
        data = {"submessage": message}

        return JsonResponse(data)


class SampleAdvancedReportView(TemplateView):
    template_name = "logiflex/sample_report.html"


class AdvancedReportView(TemplateView):
    template_name = "logiflex/report.html"

    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        report = LogiflexReport.objects.filter(pk=pu).first()
        if report:
            kwargs["report"] = report.report_text
        return super(AdvancedReportView, self).get_context_data(**kwargs)


class NewsletterCreateView(UserPassesTestMixin, CreateView):
    model = NewsLetter_logiflex
    form_class = NewsLetter_logiflexForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:newsletters:list")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "Create NewsLetter"
        kwargs["title"] = "Newsletter"
        kwargs["pageheader1"] = "Edit a Newsletter"
        kwargs["pageheader2"] = "Add or Edit a New Logiflex Newsletter"
        kwargs["cardheader"] = "Newsletter Info"
        return super(NewsletterCreateView, self).get_context_data(**kwargs)


class NewsletterEditView(UserPassesTestMixin, UpdateView):
    model = NewsLetter_logiflex
    form_class = NewsLetter_logiflexForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:newsletters:list")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "Create NewsLetter"
        kwargs["title"] = "Newsletter"
        kwargs["pageheader1"] = "Edit a Newsletter"
        kwargs["pageheader2"] = "Add or Edit a New Logiflex Newsletter"
        kwargs["cardheader"] = "Newsletter Info"
        return super(NewsletterEditView, self).get_context_data(**kwargs)


class NewsletterListView(UserPassesTestMixin, ListView):
    model = NewsLetter_logiflex
    template_name = "logiflex/newsletter_logiflex_list.html"

    def test_func(self):
        return self.request.user.is_staff


class BlogCreateView(UserPassesTestMixin, CreateView):
    model = Blog_logiflex
    form_class = Blog_logiflexForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:blog:list")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "Create a Blog"
        kwargs["title"] = "Blog"
        kwargs["pageheader1"] = "Edit a Blog"
        kwargs["pageheader2"] = "Add or Edit a New Logiflex Blog"
        kwargs["cardheader"] = "Blog Info"
        return super(BlogCreateView, self).get_context_data(**kwargs)


class BlogEditView(UserPassesTestMixin, UpdateView):
    model = Blog_logiflex
    form_class = Blog_logiflexForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:blog:list")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "Create a Blog"
        kwargs["title"] = "Blog"
        kwargs["pageheader1"] = "Edit a Blog"
        kwargs["pageheader2"] = "Add or Edit a New Logiflex Blog"
        kwargs["cardheader"] = "Blog Info"
        return super(BlogEditView, self).get_context_data(**kwargs)


class BlogListView(UserPassesTestMixin, ListView):
    model = Blog_logiflex
    template_name = "logiflex/blogs_list.html"

    def test_func(self):
        return self.request.user.is_staff


class BlogDetailView(TemplateView):
    template_name = "logiflex/blog.html"

    def get_context_data(self, **kwargs):
        slug = self.kwargs.get("slug")
        blog = Blog_logiflex.objects.filter(slug=slug).first()

        # Retreive all blogs
        blogs = Blog_logiflex.objects.all()

        # Latest Blogs
        blogslatest = blogs.order_by('-date_created')[:3]
        categorytype = (
            ('logi_freight', "Logistics & Freight"),
            # ('optimize', _("Optimization")),
            ('warehouse', "Warehousing"),
            ('distribute', "Delivery & Distribution"),
            ('driver', "Drivers & Trucking"),
            ('cost', "Cost Optimization"),
            # ('ai_insight', _("AI-Powered Insights")),
            ('predict', "Forecasting & Predictions"),
        )
        # get the category title
        category_dict = dict(categorytype)
        search_term = blog.category
        result = (search_term, category_dict[search_term]) if search_term in category_dict else None

        # get the 3 related blogs
        relatedblog = blog.relatedblog.split("-")
        related_title1 = blogs.filter(pk=int(relatedblog[0])).first().anchor_title
        related_title2 = blogs.filter(pk=int(relatedblog[1])).first().anchor_title
        related_title3 = blogs.filter(pk=int(relatedblog[2])).first().anchor_title

        kwargs["title"] = blog.title
        kwargs["bodytop"] = blog.body
        kwargs["bodybottom"] = blog.body_bottom
        kwargs["datecreated"] = blog.date_created
        kwargs["picture"] = blog.picture
        kwargs["category"] = result[1] if result else None
        kwargs["meta_title"] = blog.meta_title
        kwargs["meta_description"] = blog.meta_description
        kwargs["insidepicture"] = blog.insidepicture
        kwargs["related1"] = blogs.filter(pk=int(relatedblog[0])).first().slug
        kwargs["related2"] = blogs.filter(pk=int(relatedblog[1])).first().slug
        kwargs["related3"] = blogs.filter(pk=int(relatedblog[2])).first().slug
        kwargs["related_title1"] = related_title1
        kwargs["related_title2"] = related_title2
        kwargs["related_title3"] = related_title3
        kwargs["blogs"] = blogslatest

        return super(BlogDetailView, self).get_context_data(**kwargs)


class BlogsView(TemplateView):
    template_name = "logiflex/blogs.html"

    def get_context_data(self, **kwargs):
        query = self.request.GET.get("cat")
        allblogs = Blog_logiflex.objects.all()

        if query:
            blogs = allblogs.filter(category=query)
        else:
            blogs = allblogs

        latestblogs = allblogs.order_by('-date_created')[:3]
        kwargs["blogs"] = blogs
        kwargs["latestblogs"] = latestblogs
        return super(BlogsView, self).get_context_data(**kwargs)


class NewsletterSubscriptionCreateView(CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):

        # load AJAX data from the template
        cp_name = request.POST.get("cp_name")
        if cp_name:
            cp_name = cp_name.lower()
        else:
            cp_name = "none"
        email_nl = request.POST.get("em_nl").lower()
        tp_area = int(request.POST.get("tp_area"))

        # Search the database for the email
        subs = NewsLetter_logiflex_subscription.objects.filter(email=email_nl).first()

        # Check if data exists or not in the database
        message = ""
        if subs:
            company = subs.company.lower()
            if company == "none":
                if cp_name == "none":
                    message = "Thank you for your request. This email is already registered with us"
                else:
                    message = "Thank you for your request. You have been registered Successfully"
                    area = ""
                    if tp_area == 1:
                        area = "lo"
                    elif tp_area == 2:
                        area = "ki"
                    subs.company = cp_name
                    subs.area = area
                    subs.save()
            else:
                if cp_name == "none" or not cp_name == company:
                    message = "Thank you for your request. This email is already registered under different company name"
                elif cp_name == company:
                    message = "Thank you for your request. This email is already registered with us"
        else:
            message = "Thank you for your request. You have been registered Successfully"
            area = ""
            if tp_area == 1:
                area = "lo"
            elif tp_area == 2:
                area = "ki"
            subscription = NewsLetter_logiflex_subscription(email=email_nl, company=cp_name, area=area)
            subscription.save()

        data = {"submessage": message}

        return JsonResponse(data)


class NewsletterSubscriptionEditView(UserPassesTestMixin, UpdateView):
    model = NewsLetter_logiflex_subscription
    form_class = NewsLetter_logiflex_subscriptionForm
    template_name = "logiflex/newslettersubscrib_logiflex_create.html"
    success_url = reverse_lazy("logiflex:newsletters:list")

    def test_func(self):
        return self.request.user.is_staff


class NewsletterSubscriptionListView(UserPassesTestMixin, ListView):
    model = NewsLetter_logiflex_subscription
    template_name = "logiflex/newslettersubscription_logiflex_list.html"

    def test_func(self):
        return self.request.user.is_staff


class RequestCallView(TemplateView):
    template_name = "logiflex/call.html"


class BookACallView(CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):
        message = ""
        cp_name = request.POST.get("cp_nm")
        client_name = request.POST.get("client_nm")
        email_name = request.POST.get("email_nm")
        email_name = email_name.lower()
        phone_nb = request.POST.get("phone_nb")

        client = LogiFlexClient.objects.filter(email=email_name).first()
        if client:
            if not client.contact_name:
                client.contact_name = client_name
            if not client.company:
                client.company = cp_name
            if not client.phone or not client.phone == phone_nb:
                client.phone = phone_nb
            client.save()
            call = RequestedCall(client=client)
            call.save()
            message = "Thank you for choosing BizAnalytic + LogiFlex to power your freight analytics. " \
                      "You will be contacted As Quick As Possible"

        data = {"submessage": message}

        return JsonResponse(data)


def create_checkout_sessions(request):

    if request.method == 'POST':
        try:

            # Create checkout session
            print("Start Stripe Session")
            print(settings.FRONTEND_SUCCESS_URL)
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': stripe_price_id,
                    'quantity': 1,
                }],
                mode='payment',
                success_url=settings.FRONTEND_SUCCESS_URL + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=settings.FRONTEND_CANCEL_URL,
                # customer_email=request.user.email if request.user.is_authenticated else None,
                # metadata={
                #     'user_id': request.user.id if request.user.is_authenticated else 'anonymous',
                #     'order_id': '141'
                # }
            )
            print("Session ID:", session.id)
            data = {"sessionId": session.id}
            return JsonResponse(data)

        except (ValueError, stripe.error.StripeError) as e:
            data = {'error': str(e)}
            return JsonResponse(data, status=400)


@login_required
def create_checkout_session(request, plan_id):
    plan = get_object_or_404(PricingPlan, id=plan_id)

    # Stripe Checkout Session
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='subscription' if plan.name in ['monthly', 'quarterly'] else 'payment',
        line_items=[{
            'price': plan.stripe_price_id,
            'quantity': 1,
        }],
        customer_email=request.user.email,
        success_url=settings.FRONTEND_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=settings.FRONTEND_CANCEL_URL,
    )

    # Save to DB
    subscription = ServicePayment.objects.create(
        client=request.user,
        plan=plan,
        stripe_checkout_id=session.id
    )

    return redirect(session.url)

class WebhookView(View):
    """Handles Stripe webhooks with signature verification"""

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']
        print("Payment Successful and WebHook initiated")
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                stripe_webhook
            )
        except ValueError as e:
            return HttpResponse(status=400)  # Invalid payload
        except stripe.error.SignatureVerificationError as e:
            return HttpResponse(status=401)  # Invalid signature

        # Handle specific events
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            self.handle_successful_payment(session)
        elif event['type'] == 'invoice.paid':
            session = event['data']['object']
            self.handle_invoice_paid(session)
        elif event['type'] == 'invoice.payment_failed':
            session = event['data']['object']
            self.handle_invoice_payment_failed(session)
        elif event['type'] == 'charge.refunded':
            self.handle_refund(event['data']['object'])
        # Add other event handlers as needed

        return HttpResponse(status=200)

    def handle_successful_payment(self, session):
        """Process completed payment"""
        try:
            # Retrieve and validate session data
            expanded_session = stripe.checkout.Session.retrieve(
                id=session.id,
                expand=['line_items', 'customer']
            )
            # print(expanded_session)
            company_names = expanded_session.custom_fields

            amount_paid = expanded_session.amount_total / 100  # Convert to currency

            # Get client reference ID if it exists
            client_reference_id = ""
            if expanded_session.client_reference_id:
                client_reference_id = expanded_session.client_reference_id

            # Get Subscription ID if it exists
            subscription_id = ""
            if expanded_session.subscription:
                subscription_id = expanded_session.subscription

            # Check if client is an existing Client
            client_reference_id_part1 = client_reference_id.split("-")[0]
            client_type = 1
            if client_reference_id_part1 == "CLTEST":
                client_type = 1                                       # New Client
            elif client_reference_id_part1 == "CL":
                client_type = 2                                       # Existing Client

            email = expanded_session.customer_details.email
            email = email.lower()
            customer_name = expanded_session.customer_details.name
            phone_nb = expanded_session.customer_details.phone
            address_line1 = expanded_session.customer_details.address.line1
            address_line2 = expanded_session.customer_details.address.line2
            city = expanded_session.customer_details.address.city
            postal_code = expanded_session.customer_details.address.postal_code
            state = expanded_session.customer_details.address.state
            country = expanded_session.customer_details.address.country
            company = ""
            if company_names[0].key == "companyname":
                company = company_names[0].text.value

            # print(f"Line items: {expanded_session.line_items}")
            # print("company_details:", expanded_session)
            # stripe_price_id = expanded_session.line_items.data[].price.id
            # print(f"Payment was successful for session: {session['id']}")
            # print(f"Name: {customer_name}")
            # print(f"Email: {email}")
            # print(f"Phone: {phone_nb}")
            # print(f"Payment Amount: {amount_paid}")
            strippriceid = expanded_session.line_items.data[0].price.id
            quantity = expanded_session.line_items.data[0].quantity

            # check if client exists. if not it will be added
            logiclient = None
            if client_type == 2:
                logiclient = LogiFlexClient.objects.filter(client_number=client_reference_id).first()
                print(logiclient)
            if not logiclient:
                logiclient = LogiFlexClient.objects.filter(email=email).first()
            # Check if Client email matches his client number

            if client_type == 1 and not logiclient:
                logiclient = LogiFlexClient.objects.create(email=email, phone=phone_nb, contact_name=customer_name,
                                                       address_line1=address_line1, address_line2=address_line2,
                                                       city=city, state=state, country=country, postal_code=postal_code,
                                                       company=company)
                logiclient.client_number = makeclientnumber(logiclient.id)
                logiclient.save()
                email_info = {
                    'subject': "Urgent: New Client",
                    'to_email': ["bizanalytics.us@gmail.com", ],
                    'client': logiclient.contact_name,
                    'company': logiclient.company,
                    'message': f"A new Client has been created with the following info: client company: {logiclient.company}, email: {email}",
                    'curentyear': datetime.now().year
                }
                sendnotificationemail.delay(email_info)
            elif logiclient:
                if not logiclient.company:
                    logiclient.company = company
                if not logiclient.state:
                    logiclient.state = state
                logiclient.save()

            if strippriceid:
                payment_plan = PricingPlan.objects.filter(stripe_price_id=strippriceid).first()
                if payment_plan:
                    # Save payment and Create report instance with empty data
                    servicepayment = ServicePayment.objects.filter(client=logiclient).first()
                    if servicepayment:
                        if payment_plan.name == "onetime_lite":
                            servicepayment.lite_credits += quantity
                        elif payment_plan.name == "onetime_advanced":
                            servicepayment.advanced_credits += quantity
                        else:
                            servicepayment.is_active = True
                            servicepayment.status = "1"
                            servicepayment.end_date = None
                            servicepayment.date_canceled = None
                        servicepayment.stripe_checkout_id = session['id']
                        servicepayment.service_type = payment_plan
                        servicepayment.subscription_id = subscription_id
                        servicepayment.save()
                        servicepayment.reset_quota_if_needed()

                    else:
                        # advancedcredits = 0
                        # if payment_plan.name == "starter":
                        #     advancedcredits = 1
                        servicepayment = ServicePayment.objects.create(
                            client=logiclient,
                            service_type=payment_plan,
                            stripe_checkout_id=session['id'],
                            subscription_id=subscription_id)
                        if payment_plan.name == "onetime_lite":
                            servicepayment.lite_credits += quantity
                        elif payment_plan.name == "onetime_advanced":
                            servicepayment.advanced_credits += quantity
                        else:
                            servicepayment.is_active = True
                            servicepayment.save()
                            servicepayment.set_quota()

                    # Get User Session Information
                    ip = get_ip(self.request)
                    user_browser = self.request.META.get("HTTP_USER_AGENT", "")
                    user_language = self.request.META.get("HTTP_ACCEPT_LANGUAGE")
                    user_page_referer = self.request.META.get("HTTP_REFERER")

                    user_agent = parse(user_browser)
                    device_type = user_agent.device  # e.g., 'mobile', 'tablet', 'pc'
                    os_family = user_agent.os.family  # e.g., 'iOS', 'Android', 'Windows'
                    browser_family = user_agent.browser.family  # e.g., 'Chrome', 'Firefox', 'Safari'
                    # print("device_type:", device_type)
                    # print("os_family:", os_family)
                    # print("browser_family:", browser_family)

                    paymenthistory = PaymentsHistory.objects.create(
                        client=logiclient, service_type=payment_plan, stripe_checkout_id=session['id'],
                        amount_paid=amount_paid, quantity=quantity, ipaddress=ip, user_referee=user_page_referer,
                        user_language=user_language, user_device=device_type, user_browser=browser_family,
                        user_os=os_family, address_line1=address_line1, address_line2=address_line2,
                        city=city, state=state, country=country, postal_code=postal_code, name_on_card=customer_name,
                        phone_number=phone_nb, company=company, subscription_id=subscription_id)

                    currentyear = now().strftime("%y")
                    currentmonth = now().strftime("%m")
                    receipt = f"RC{currentmonth}{currentyear}-{servicepayment.pk}{logiclient.id}-{paymenthistory.pk}"
                    paymenthistory.receipt_number = receipt
                    downloadcode = generatecode(8)
                    paymenthistory.download_code = downloadcode
                    paymenthistory.save()

                    email_info = {
                        'payment_link': "https://bizanalytic.com/logiflex/payments/receipt/?cat="+downloadcode,
                        'subject': "Urgent: New Payment",
                        'to_email': logiclient.email,
                        'client': logiclient.contact_name,
                        'company': logiclient.company,
                        'address_line1': logiclient.address_line1,
                        'address_line2': logiclient.address_line2,
                        'city': city,
                        'state': state,
                        'postal_code': postal_code,
                        'comuntry': country,
                        'receipt': paymenthistory.receipt_number,
                        'payment_date': paymenthistory.payment_date,
                        'amount_paid': paymenthistory.amount_paid,
                        'quantity': paymenthistory.quantity,
                        'unit_price': servicepayment.service_type.price,
                        'description': servicepayment.service_type.description,
                        'message': f"A new payment received from {logiclient.company}, email: {email}",
                        'curentyear': datetime.now().year
                    }
                    paymentconfirmationmail.delay(email_info)

                    # email_info = {
                    #     'subject': "Urgent: New Payment",
                    #     'to_email': ["bizanalytics.us@gmail.com", ],
                    #     'client': client.contact_name,
                    #     'company': client.company,
                    #     'message': f"A new payment received from {client.company}, email: {email}",
                    #     'curentyear': datetime.now().year
                    # }
                    # sendnotificationemail.delay(email_info)

                # downloadcode = generatecode(8)
                # report = LogiflexReport(client=client, payment=servicepayment, report_type='Paid',
                #                                download_code=downloadcode)
                # report.save()

            # print(session)


            # Implement your business logic:
            # - Update order status
            # - Grant access to service
            # - Send confirmation email

        except stripe.error.StripeError as e:
            # Handle error (log and retry mechanism)
            pass

    def handle_refund(self, charge):
        """Process refunds"""
        # Implement your refund logic
        pass

    def handle_invoice_paid(self, session):
        """Process Invoice Paid Successfully"""

        logpay = LogPayments.objects.create(session=session)
        email = session.get("customer_email")
        logiclient = LogiFlexClient.objects.filter(email=email).first()

        billing_reason = session.get("billing_reason")
        subscription_id = session.get('lines').data[0].parent.subscription_item_details.subscription
        price_id = session.get('lines').data[0].pricing.price_details.price
        amount_paid = session.get('lines').data[0].amount / 100  # Convert to currency
        quantity = session.get('lines').data[0].quantity
        payment_plan = PricingPlan.objects.filter(stripe_price_id=price_id).first()
        if payment_plan and (payment_plan.name == "starter" or payment_plan.name == "pro" or payment_plan.name == "quarterly" or payment_plan.name == "daily"):
            if billing_reason and not billing_reason == "subscription_create":
                if logiclient:
                    servicepayment = None
                    if subscription_id:
                        servicepayment = ServicePayment.objects.filter(client=logiclient, subscription_id=subscription_id).first()
                    if not servicepayment:
                        servicepayment = ServicePayment.objects.filter(client=logiclient).first()
                        if servicepayment:
                            servicepayment.is_active = True
                            servicepayment.subscription_id = subscription_id
                            servicepayment.save()
                            servicepayment.reset_quota_if_needed()
                    else:
                        servicepayment.is_active = True
                        servicepayment.save()
                        servicepayment.reset_quota_if_needed()
                        # Get User Session Information
                        ip = get_ip(self.request)
                        user_browser = self.request.META.get("HTTP_USER_AGENT", "")
                        user_language = self.request.META.get("HTTP_ACCEPT_LANGUAGE")
                        user_page_referer = self.request.META.get("HTTP_REFERER")

                        user_agent = parse(user_browser)
                        device_type = user_agent.device  # e.g., 'mobile', 'tablet', 'pc'
                        os_family = user_agent.os.family  # e.g., 'iOS', 'Android', 'Windows'
                        browser_family = user_agent.browser.family  # e.g., 'Chrome', 'Firefox', 'Safari'

                        paymenthistory = PaymentsHistory.objects.create(
                            client=logiclient, service_type=payment_plan, stripe_checkout_id=session['id'],
                            amount_paid=amount_paid, quantity=quantity, ipaddress=ip, user_referee=user_page_referer,
                            user_language=user_language, user_device=device_type, user_browser=browser_family,
                            user_os=os_family, subscription_id=subscription_id)

                        currentyear = now().strftime("%y")
                        currentmonth = now().strftime("%m")
                        receipt = f"RC{currentmonth}{currentyear}-{servicepayment.pk}{logiclient.id}-{paymenthistory.pk}"
                        paymenthistory.receipt_number = receipt
                        downloadcode = generatecode(8)
                        paymenthistory.download_code = downloadcode
                        paymenthistory.save()

                        email_info = {
                            'payment_link': "https://bizanalytic.com/logiflex/payments/receipt/?cat=" + downloadcode,
                            'subject': "Urgent: New Payment",
                            'to_email': logiclient.email,
                            'client': logiclient.contact_name,
                            'company': logiclient.company,
                            'address_line1': logiclient.address_line1,
                            'address_line2': logiclient.address_line2,
                            'city': logiclient.city,
                            'state': logiclient.state,
                            'postal_code': logiclient.postal_code,
                            'comuntry': logiclient.country,
                            'receipt': paymenthistory.receipt_number,
                            'payment_date': paymenthistory.payment_date,
                            'amount_paid': paymenthistory.amount_paid,
                            'quantity': paymenthistory.quantity,
                            'unit_price': servicepayment.service_type.price,
                            'description': servicepayment.service_type.description,
                            'message': f"A new payment received from {logiclient.company}, email: {email}",
                            'curentyear': datetime.now().year
                        }
                        paymentconfirmationmail.delay(email_info)
            else:
                print("SUBSCRIPTION ID:", subscription_id)
                print("STRIPE PRICE ID:", price_id)
                print("Billing Reason:", billing_reason)
        # print("Session_Invoice Paid", session)



    def handle_invoice_payment_failed(self, session):
        """Process refunds"""
        # Implement your refund logic
        pass


class Pricing_PageView(TemplateView):
    template_name = "logiflex/stripe_pay.html"

    def get_context_data(self, **kwargs):
        if self.request.user.is_authenticated:
            logedin = 1
        else:
            logedin = 2
        kwargs["logedin"] = logedin
        # kwargs["stripe_publishable_key"] = stripe_publishable
        return super(Pricing_PageView, self).get_context_data(**kwargs)


class Payments_ListView(LoginRequiredMixin, TemplateView):
    template_name = "logiflex/payments_list.html"

    def get_context_data(self, **kwargs):
        if self.request.user.is_authenticated:
            user = self.request.user
            if user:
                client = LogiFlexClient.objects.filter(user=user).first()
                service = ServicePayment.objects.filter(client=client).first()
                payments = PaymentsHistory.objects.filter(client=client)
                kwargs["payments"] = payments
                if service:
                    kwargs["lreports"] = service.reports_allowed - service.reports_used
                    kwargs["areports"] = service.advanced_reports_allowed - service.advanced_reports_used
                    kwargs["acredits"] = service.advanced_credits
                    kwargs["lcredits"] = service.lite_credits
                    kwargs["subscrib_status"] = service.is_active
                    kwargs["enddate"] = service.end_date
        # kwargs["stripe_publishable_key"] = stripe_publishable
        return super(Payments_ListView, self).get_context_data(**kwargs)


class OrderDetailsView(TemplateView):
    template_name = "logiflex/payments_verify.html"

    def get_context_data(self, **kwargs):
        query = self.request.GET.get("cat")
        query = query.lower()
        if self.request.user.is_authenticated:
            user = self.request.user
            if user:
                client = LogiFlexClient.objects.filter(user=user).first()
                kwargs["client"] = client
                kwargs["clientexist"] = 1
            else:
                kwargs["clientexist"] = 2
        payment = PricingPlan.objects.filter(name=query).first()
        kwargs["payment"] = payment
        return super(OrderDetailsView, self).get_context_data(**kwargs)



class PaymentView(LoginRequiredMixin, CreateView, JsonFormMixin):

    def post(self, request, *args, **kwargs):
        paymentid = int(request.POST.get("rx_cfr_ci"))
        print("Report ID: ", paymentid)

        message = "Payment doesn't exist"
        status = "fail"

        if self.request.user.is_authenticated:
            user = self.request.user
            if user:
                # client = LogiFlexClient.objects.filter(user=user).first()

                if paymentid:
                    payment = PaymentsHistory.objects.filter(pk=paymentid).select_related("client").first()

                    payment_info = {
                        'subject': "Urgent: New Payment",
                        'to_email': payment.client.email,
                        'client': payment.client.contact_name,
                        'company': payment.client.company,
                        'address_line1': payment.address_line1,
                        'address_line2': payment.address_line2,
                        'city': payment.city,
                        'state': payment.state,
                        'postal_code': payment.postal_code,
                        'comuntry': payment.country,
                        'receipt': payment.receipt_number,
                        'payment_date': payment.payment_date,
                        'amount_paid': payment.amount_paid,
                        'quantity': payment.quantity,
                        'unit_price': payment.service_type.price,
                        'description': payment.service_type.description,
                        'message': f"A new payment received from {payment.client.company}, email: {payment.client.email}",
                        'curentyear': datetime.now().year
                    }
                    message = paymentconfirmation(payment_info)

                    status = "success"
                    downloadcode = payment.download_code

        data = {"submessage": message, "rpstatus": status, 'downloadcode':downloadcode}

        return JsonResponse(data)


class PaymentDetailView(TemplateView):
    template_name = "logiflex/payment_receipt.html"

    def get_context_data(self, **kwargs):
        query = self.request.GET.get("cat")
        if query:
            payment = PaymentsHistory.objects.filter(download_code=query).select_related("client").first()
            if payment:
                kwargs["customer_number"] = payment.client.client_number
                kwargs['customer_name'] = payment.client.email
                kwargs['customer_company'] = payment.client.company
                kwargs['customer_email'] = payment.client.email
                kwargs['customer_address_line1'] = payment.address_line1
                kwargs['customer_address_line2'] = payment.address_line2
                kwargs['customer_city'] = payment.city
                kwargs['customer_state'] = payment.state
                kwargs['customer_zip'] = payment.postal_code
                kwargs['customer_country'] = payment.country
                kwargs['current_year'] = datetime.now().year
                kwargs['receipt_number'] = payment.receipt_number
                kwargs['receipt_date'] = payment.payment_date
                kwargs['grand_total'] = payment.amount_paid
                kwargs['company_name'] = "BizAnalytic"
                kwargs['operator_legal_name'] = "Adil Akaaboune"
                kwargs['company_address_line1'] = "The Woodlands"
                kwargs['company_address_line2'] = "Texas"
                kwargs['company_country'] = "United States of America"
                kwargs['support_email'] = "support@bizanalytic.com"
                kwargs['payment_brand'] = "Stripe"
                kwargs['refund_policy_url'] = "https://bizanalytic.com/refund-policy/"
                kwargs['desc'] = payment.service_type.name
                kwargs['quantity'] = payment.quantity
                kwargs['unit_price'] = payment.service_type.price
                kwargs['line_total'] = payment.amount_paid
                kwargs['subtotal'] = payment.amount_paid

        return super(PaymentDetailView, self).get_context_data(**kwargs)


class Payment_SuccessView(LoginRequiredMixin, TemplateView):
    template_name = "logiflex/payment_success.html"

    def get_context_data(self, **kwargs):
        query = self.request.GET.get("cat")

        user = self.request.user
        servicepayment = ServicePayment.objects.filter(client__user=user).first()
        if servicepayment:
            if query:
                query = query.lower()
                if query in ["processing", "download", "canceled", "late"]:
                    reports = LogiflexReport.objects.filter(client__user=user, report_status=query)
                else:
                    reports = LogiflexReport.objects.filter(client__user=user)
            else:
                reports = LogiflexReport.objects.filter(client__user=user)
            # reports = reports.filter(report_created=True)
            kwargs["reports"] = reports.order_by('-report_number')
            if servicepayment.can_generate_report():
                kwargs["payid"] = servicepayment.pk
            else:
                kwargs["payid"] = "none"
        else:
            kwargs["reports"] = "none"
            kwargs["payid"] = "none"
        return super(Payment_SuccessView, self).get_context_data(**kwargs)


class SampleReportCreateView(CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):

        # load AJAX data from the template
        client_nm = request.POST.get("client_nm")
        cp_name = request.POST.get("cp_nm")
        email_name = request.POST.get("email_nm")
        email_name = email_name.lower()
        route_file = request.FILES["route_file"]
        route_filename = route_file.name
        _, ext = os.path.splitext(route_filename)
        ext = ext.lower()  # Convert to lowercase for case-insensitive comparison
        report_type = "free"
        reportype = "0"
        # Save client and result data
        user = User.objects.filter(email=email_name).first()
        downloadcode = generatecode(8)
        client_exist = 1
        if user:
            client = LogiFlexClient.objects.filter(user=user).first()
            if client:
                latest_report = LogiflexReport.objects.filter(client=client).order_by('-report_number').first()
                latest_number = 1
                if latest_report:
                    latest_number = latest_report.report_number + 1
                report = LogiflexReport(client=client, report_type=report_type,
                                               report_number=latest_number)

            else:
                client, created = LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'user': user,
                                                                                        'contact_name': client_nm})
                client.client_number =makeclientnumber(client.id)
                client.save()
                report = LogiflexReport(client=client, report_type=report_type,
                                               report_number=1)
                client_exist = 2

        else:
            client = LogiFlexClient.objects.filter(email=email_name).first()
            if client:
                latest_report = LogiflexReport.objects.filter(client=client).order_by('-report_number').first()
                latest_number = 1
                if latest_report:
                    latest_number = latest_report.report_number + 1
                report = LogiflexReport(client=client, report_type=report_type,
                                        report_number=latest_number)

            else:
                client, created = LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'contact_name': client_nm})
                client.client_number = makeclientnumber(client.id)
                client.save()
                report = LogiflexReport(client=client, report_type=report_type, report_number=1)
                client_exist = 2

        report.save()

        # add route file
        report.routefile = route_file
        report.routefile_ext = ext

        # add report ID
        report.report_id = makereportnumber(report.pk, reportype)

        # add expected_delivery
        report.expected_delivery = now() + timedelta(days=1)
        report.download_code = downloadcode
        report.report_approved = True
        report.report_status = "download"
        report.save()

        if client_exist == 2:
            email_info = {
                'subject': "Urgent: New Client",
                'to_email': ["bizanalytics.us@gmail.com", ],
                'client': client.contact_name,
                'company': client.company,
                'message': f"A new Client has been created with the following info: client company: {client.company}, email: {email_name}",
                'curentyear': datetime.now().year
            }
            sendnotificationemail.delay(email_info)

        asynch_preprocess = test_validator.delay(report.pk, route_filename)
        if asynch_preprocess:
            flags = asynch_preprocess.get()

        # update route file
        # logireport.routefile = routefilename
        # logireport.save()

        # Send a confirmation Email to client
        email_info = {
            'subject': f"Your Fleet {report_type.capitalize()} Efficiency Report is in Progress 🚚📊",
            'to_email': [email_name, ],
            'client': client_nm,
            'report_list_link': f"https://bizanalytic.com/logiflex/reports/reportview/{report.id}/?cat={downloadcode}",
            'cuurentyear': now().year
        }
        senduploadmail.delay(email_info)

        message = "Report Uploaded Succssefully. Wait for a confirmation email from us."
        repstatus = "success"
        reportid = report.id

        data = {"submessage": message, "repstatus": repstatus, "repid": reportid, "repocode": downloadcode}

        return JsonResponse(data)


class FullReportView(LoginRequiredMixin, TemplateView):
    template_name = "logiflex/report_create.html"
    def get_context_data(self, **kwargs):
        # pu = self.kwargs.get("pk")
        client = LogiFlexClient.objects.filter(user=self.request.user).first()
        clienttype = 0
        servicepayment = ServicePayment.objects.filter(client=client).first()
        if servicepayment:
            if servicepayment.can_generate_report():
                kwargs["lite_allowed"] = 1
            else:
                kwargs["lite_allowed"] = 0
            if servicepayment.can_generate_advanced_report():
                kwargs["advanced_allowed"] = 1
            else:
                kwargs["advanced_allowed"] = 0

            kwargs["contact_name"] = servicepayment.client.contact_name
            kwargs["company"] = servicepayment.client.company
            kwargs["email"] = servicepayment.client.email
            kwargs["clientid"] = servicepayment.client.id
            clienttype = 1
        kwargs["clienttype"] = clienttype
        return super(FullReportView, self).get_context_data(**kwargs)


class FullReportCreateView(LoginRequiredMixin, CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):

        # load AJAX data from the template

        # clientid = request.POST.get("cixphoto")
        client_name = request.POST.get("client_nm")
        cp_name = request.POST.get("cp_nm")
        email_name = request.POST.get("email_nm")
        email_name = email_name.lower()
        reportype = request.POST.get("reptyp")
        route_file = request.FILES["route_file"]

        route_filename = route_file.name
        _, ext = os.path.splitext(route_filename)
        ext = ext.lower()  # Convert to lowercase for case-insensitive comparison

        reportid = None
        client = LogiFlexClient.objects.filter(user=self.request.user).first()
        servicepayment = ServicePayment.objects.filter(client=client).first()
        lite_report = 0
        advanced_report = 0
        print("Report Type:", reportype)
        report_type = ""
        # Check report type
        if reportype == "1":
            report_type = "lite"
            if servicepayment.can_generate_report():
                lite_report = 1
        elif reportype == "2":
            report_type = "advanced"
            if servicepayment.can_generate_advanced_report():
                advanced_report = 1

        # print("client: ", client.pk)
        # print("Service Payment:", servicepayment.pk)
        # print("lite_report:", lite_report, "advanced_report:", advanced_report)
        # print("report_type:", report_type)
        if lite_report or advanced_report:
            # print("you can generate reports")
            # Save client and result data
            user = self.request.user
            if not client.contact_name:
                client.contact_name = client_name
            if not client.company:
                client.company = cp_name

            client.save()

            downloadcode = generatecode(8)
            latest_report = LogiflexReport.objects.filter(client=client).order_by('-report_number').first()
            latest_number = 1
            if latest_report:
                latest_number = latest_report.report_number + 1

            logireport = LogiflexReport.objects.create(client=client, payment=servicepayment,
                                                              download_code=downloadcode,
                                                              report_type=report_type,
                                                              report_number=latest_number)
            # add route file
            logireport.routefile = route_file
            logireport.routefile_ext = ext

            # add report ID
            logireport.report_id = makereportnumber(logireport.pk, reportype)

            # add expected_delivery
            logireport.expected_delivery = now() + timedelta(days=1)

            logireport.save()
            if lite_report == 1:
                servicepayment.mark_report_used()
            elif advanced_report == 1:
                servicepayment.mark_advanced_report_used()


            # Clean and validate route file and generate logs
            # flags = ""
            print("step 1 before validating")
            # test_validator.delay(logireport.pk, route_filename)
            asynch_preprocess = test_validator.delay(logireport.pk, route_filename)
            if asynch_preprocess:
                flags = asynch_preprocess.get()

            # Save file to FreightData Model
            # print("df columns after cleaning")
            # print(df.columns)
            # print(df.head(5))

            # Run local Analysis
            # summary = run_analysis(df)

            # Convert the summary array to json format to be stored as text in the database
            # json_string = json.dumps(summary)
            # logireport.report_summary = json_string
            # logireport.save()
            # update route file
            # logireport.routefile = routefilename
            # logireport.save()

            # Save log data
            # logiflex_log = LogEntry.objects.create(report=logireport, column_report=column_report,
            #                                               date_report=date_report, citi_report=cities_report, flags=flags)

            # Send a confirmation Email to client
            email_info = {
                'subject': f"Your Fleet {report_type.capitalize()} Efficiency Report is in Progress 🚚📊",
                'to_email': [email_name, ],
                'client': client_name,
                'report_list_link': f"https://bizanalytic.com/logiflex/reports/detail/{logireport.id}/",
                'cuurentyear': now().year
            }
            senduploadmail.delay(email_info)


            message = "Report Uploaded Succssefully. Wait for a confirmation email from us."
            repstatus = "success"
            reportid = logireport.id
        else:
            message = "Report Already Uploaded Succssefully.Check the list of your reports for more details"
            repstatus = "fail"

        data = {"submessage": message, "repstatus": repstatus, "repid": reportid}

        return JsonResponse(data)


class Payment_FailView(TemplateView):
    template_name = "logiflex/payment_fail.html"


@csrf_exempt
def clean_csv(request):

    print("CSV Cleaning starts")
    # Proceed with OpenRefine cleaning
    if request.method == 'POST' and request.FILES["route_file"]:
        csv_file = request.FILES['route_file']
        df = pd.read_csv(request.FILES['route_file'])
        print(df.head(5))
        cleaned_csv = df
        print("cleaned_csv:", cleaned_csv)
        data = {"submessage": cleaned_csv}
        return JsonResponse(data)
    return JsonResponse({"error": "Invalid request"}, status=400)


class AdminReportsListView(UserPassesTestMixin, TemplateView):
    template_name = "logiflex/report_admin_list.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        query = self.request.GET.get("cat")
        requests = ChangeSubscriptionRequest.objects.filter(processed=False)
        servicepayments = ServicePayment.objects.all()
        newservicepayments = servicepayments.exclude(lite_promotion_code=None)
        # newservicepayments = newservicepayments.exclude(lite_promotion_code_used=True)
        logiclients = LogiFlexClient.objects.filter(manually_created=True)
        if query:
            query = query.lower()
            if query in ["processing", "late", "download", "canceled"]:
                reports = LogiflexReport.objects.filter(report_status=query)
            else:
                reports = LogiflexReport.objects.filter(report_approved=False, report_status__in=['processing', 'late'])
        else:
            reports = LogiflexReport.objects.filter(report_approved=False, report_status__in=['processing', 'late'])
        # reports = reports.filter(report_created=True)
        kwargs["requests"] = requests
        kwargs["reports"] = reports.order_by('-report_number')
        kwargs["servicepayments"] = newservicepayments
        kwargs["logiclients"] = logiclients
        return super(AdminReportsListView, self).get_context_data(**kwargs)


class AdminApproveReportView(UserPassesTestMixin, CreateView, JsonFormMixin):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, *args, **kwargs):
        reportid = int(request.POST.get("rx_cfr_ci"))
        print("Report ID: ", reportid)
        if reportid:
            report = LogiflexReport.objects.filter(pk=reportid).first()
            email_name = report.client.email
            client_name = report.client.contact_name
            company = report.client.company

            if not report.report_approved:
                report.report_approved = True
                report.report_date = now()
                report.report_status = "download"
                report.save()
                message = "Report Approved Successfully"
                status = "success"

                # Prepare data for customer email
                if report.report_type == "advanced":
                    rawc = report.report_carrier
                    rawd = report.report_driver
                    rawr = report.report_route
                    if rawd:
                        data = json.loads(rawd)
                        summary_json = data.get("summary_json", {})
                    elif rawc:
                        data = json.loads(rawc)
                        summary_json = data.get("summary_json", {})
                    elif rawr:
                        data = json.loads(rawr)
                        summary_json = data.get("summary_json", {})
                elif report.report_type == "lite":
                    raw = report.report_text
                    data = json.loads(raw)
                    summary_json = data.get("summary_json", {})
                # print(json.loads(summary_json))
                kpiss = ""
                for kpi in summary_json:
                    if kpi == "kpis":
                        kpiss = summary_json[kpi]
                    else:
                        print(kpi)
                    # kpiss.append({"metric": kpi.metric, "value": kpi.value})

                # Send a confirmation Email to client
                email_info = {
                    'subject': "Your Fleet Efficiency Report is Ready for your View 🚚📊",
                    'to_email': [email_name, ],
                    'client': client_name,
                    'company': company,
                    'kpis': kpiss,
                    'report_list_link': f"https://bizanalytic.com/logiflex/reports/reportview/{report.id}/?cat={report.download_code}",
                    'curentyear': now().year
                }
                sendapprovedreportmail.delay(email_info)

            else:
                message = "Report Already Approved"
                status = "success"
        else:
            message = "Report doesn't exist"
            status = "fail"

        data = {"submessage": message, "rpstatus": status}

        return JsonResponse(data)


class AdminApproveRequestView(UserPassesTestMixin, CreateView, JsonFormMixin):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, *args, **kwargs):
        requestid = int(request.POST.get("rq_cfr_ci"))

        subrequest = ChangeSubscriptionRequest.objects.filter(pk=requestid).select_related('subscription').first()
        subscription = subrequest.subscription
        if subrequest:
            if subrequest.request == "1":
                subscription.status = "2"
                subscription.date_canceled = subscription.reset_date
                subscription.save()
                subrequest.processed = True
                subrequest.save()
                email_info = {
                    'subject': f"Your Subscription will be paused on this date {subscription.date_canceled}",
                    'to_email': [subscription.client.email, ],
                    'client': subscription.client.contact_name,
                    'company': subscription.client.company,
                    'change_date': subscription.date_canceled.date(),
                    'status': "Paused",
                    'curentyear': now().year
                }
                sendapprovedreportmail.delay(email_info)
            elif subrequest.request == "2":
                subscription.status = "3"
                subscription.date_canceled = subscription.reset_date
                subscription.save()
                subrequest.processed = True
                subrequest.save()
                # Send a confirmation Email to client
                email_info = {
                    'subject': f"Your Subscription will be canceled on this date {subscription.date_canceled}",
                    'to_email': [subscription.client.email, ],
                    'client': subscription.client.contact_name,
                    'company':  subscription.client.company,
                    'change_date': subscription.date_canceled.date(),
                    'status': "Cancelled",
                    'curentyear': now().year
                }
                sendapprovedreportmail.delay(email_info)
            elif subrequest.request == "3":
                subscription.status = "4"
                subscription.is_active = True
                subscription.save()
                subrequest.processed = True
                subrequest.save()
                email_info = {
                    'subject': f"Your Subscription will be resumed on this date {now()}",
                    'to_email': [subscription.client.email, ],
                    'client': subscription.client.contact_name,
                    'company': subscription.client.company,
                    'change_date': subscription.date_canceled.date(),
                    'status': "Resumed",
                    'curentyear': now().year
                }
                sendapprovedreportmail.delay(email_info)
            message = "Request Approved Successfully"
            status = "success"
        else:
            message = "Request does not exist"
            status = "fail"
        data = {"submessage": message, "rpstatus": status}

        return JsonResponse(data)


class UpdateGasPricesView(UserPassesTestMixin, CreateView, JsonFormMixin):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, *args, **kwargs):
        # us_cities = pd.read_csv(uscities_file)
        # us_states = pd.read_csv(ussates_file)
        state_gas_prices = pd.read_csv(gasprices_file)

        # city_instances = []
        # for index, row in us_cities.iterrows():
        #     c_instance = City(
        #         cityname=row['city'],
        #         state_name=row['state_name'],
        #         state_code=row['state'],
        #         # Map other columns to model fields
        #     )
        #     city_instances.append(c_instance)
        #
        # City.objects.bulk_create(city_instances)
        #
        # state_instances = []
        # for index, row in us_states.iterrows():
        #     s_instance = State(
        #         state_name=row['name'],
        #         state_code=row['code'],
        #         # Map other columns to model fields
        #     )
        #     state_instances.append(s_instance)
        #
        # State.objects.bulk_create(state_instances)

        gas_instances = []
        for index, row in state_gas_prices.iterrows():
            g_instance = GasPriceState(
                state_code=row['code'],
                premiumprice=row['Premium'],
                regularprice=row['Regular'],
                midgradeprice=row['Mid-Grade'],
                dieselprice=row['Diesel'],

                # Map other columns to model fields
            )
            gas_instances.append(g_instance)

        GasPriceState.objects.bulk_create(gas_instances)


        status = "success"
        message = "Data Added Successfully"
        data = {"submessage": message, "rpstatus": status}

        return JsonResponse(data)


class AboutUsView(TemplateView):
    template_name = "logiflex/aboutus.html"


class PaymentSuccessfulView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        query = self.request.GET.get("cat")
        if self.request.user.is_authenticated:
            return reverse_lazy("logiflex:dashboard")
        elif query:
            client = LogiFlexClient.objects.filter(servicepayment__stripe_checkout_id=query)\
                .select_related("user").first()
            # payment = ServicePayment.objects.filter(stripe_checkout_id=query).select_related("client").first()
            if client.user or client.activated:
                return reverse_lazy("logiflex:dashboard")
            elif client:
                return reverse("logiflex:reports:newfullreport", kwargs={"pk": client.id})

        return super().get_redirect_url(*args, **kwargs)


class FullReportNewClientView(TemplateView):
    template_name = "logiflex/report_create.html"
    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        # client = LogiFlexClient.objects.filter(pk=pu).first()
        clienttype = 0
        servicepayment = ServicePayment.objects.filter(client_id=pu).select_related("client").first()
        if servicepayment and servicepayment.can_generate_report():

            if servicepayment.can_generate_report():
                kwargs["lite_allowed"] = 1
            else:
                kwargs["lite_allowed"] = 0
            if servicepayment.can_generate_advanced_report():
                kwargs["advanced_allowed"] = 1
            else:
                kwargs["advanced_allowed"] = 0

            kwargs["contact_name"] = servicepayment.client.contact_name
            kwargs["company"] = servicepayment.client.company
            kwargs["email"] = servicepayment.client.email
            clienttype = 2

        kwargs["clienttype"] = clienttype

            # kwargs["reportid"] = servicepayment.client.id

        return super(FullReportNewClientView, self).get_context_data(**kwargs)


class FullNewClientReportCreateView(CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):

        # load AJAX data from the template

        clientid = request.POST.get("cixphoto")
        client_name = request.POST.get("client_nm")
        cp_name = request.POST.get("cp_nm")
        email_name = request.POST.get("email_nm")
        email_name = email_name.lower()
        route_file = request.FILES["route_file"]
        route_filename = route_file.name
        reportype = request.POST.get("reptyp")

        report_type = None
        # Check report type
        if reportype == "1":
            report_type = "lite"
        elif reportype == "2":
            report_type = "advanced"

        reportid = None
        # client = LogiFlexClient.objects.filter(user=self.request.user).first()
        if clientid:
            servicepayment = ServicePayment.objects.filter(client_id=clientid, client__email=email_name).select_related("client").first()

            if servicepayment.can_generate_report():
                client = servicepayment.client
                # Save client and result data
                # user = servicepayment.client.user
                if not client.contact_name:
                    client.contact_name = client_name
                if not client.company:
                    client.company = cp_name
                client.activated = True
                client.save()

                downloadcode = generatecode(8)
                latest_report = LogiflexReport.objects.filter(client=client).order_by('-report_number').first()
                logireport = LogiflexReport.objects.create(client=client, payment=servicepayment,
                                                                  download_code=downloadcode,
                                                                  report_type=report_type,
                                                                  report_number=latest_report.report_number+1)
                # add route file
                logireport.routefile = route_file
                # add report ID
                currentyear = now().year
                idl = "{:06d}".format(logireport.pk)
                logireport.report_id = f"RPT-{currentyear}-{idl}"
                # add expected_delivery
                logireport.expected_delivery = logireport.date_created + timedelta(days=1)

                logireport.save()

                # Clean and validate route file and generate logs
                asynch_preprocess = test_validator.delay(logireport.pk, route_filename)
                flags = asynch_preprocess.get()
                if flags:
                    logireport.flags = flags
                    logireport.save()

                # Send a confirmation Email to client
                email_info = {
                    'subject': f"Your Fleet {report_type.capitalize()} Efficiency Report is in Progress 🚚📊",
                    'to_email': [email_name, ],
                    'client': client_name,
                    'report_list_link': f"https://bizanalytic.com/logiflex/reports/detail/{logireport.id}/",
                    'cuurentyear': now().year
                }
                senduploadmail.delay(email_info)

                message = "Report Uploaded Succssefully. Wait for a confirmation email from us."
                repstatus = "success"
                reportid = logireport.id
            else:
                message = "Report Already Uploaded Succssefully.Check the list of your reports for more details"
                repstatus = "fail"
        else:
            message = "Report cannot be created. Check with the Admin"
            repstatus = "fail"

        data = {"submessage": message, "status": repstatus, "repid": reportid}

        return JsonResponse(data)


class LogiFlexClientCreateView(UserPassesTestMixin, CreateView):
    model = LogiFlexClient
    form_class = LogiFlexClientForm
    template_name = "logiflex/client_servicepayment_form.html"
    success_url = reverse_lazy("logiflex:admin:reports")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["title"] = "Logiflex Client"

        return super().get_context_data(**kwargs)


class LogiFlexClientUpdateView(UserPassesTestMixin, UpdateView):
    model = LogiFlexClient
    form_class = LogiFlexClientForm
    template_name = "logiflex/client_servicepayment_form.html"
    success_url = reverse_lazy("logiflex:admin:reports")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        cid = makeclientnumber(self.kwargs.get('pk'))
        kwargs["cid"] = cid
        kwargs["title"] = "Logiflex Client"

        return super().get_context_data(**kwargs)


class ServicePaymentCreateView(UserPassesTestMixin, CreateView):
    model = ServicePayment
    form_class = ServicePaymentForm
    template_name = "logiflex/client_servicepayment_form.html"
    success_url = reverse_lazy("logiflex:admin:reports")

    def get_initial(self):
        promo_code = generatecode(8)
        initial = {
            "lite_promotion_code": promo_code,
        }
        return initial

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["title"] = "Service Payment"

        return super().get_context_data(**kwargs)


class ServicePaymentUpdateView(UserPassesTestMixin, UpdateView):
    model = ServicePayment
    form_class = ServicePaymentForm
    template_name = "logiflex/client_servicepayment_form.html"
    success_url = reverse_lazy("logiflex:admin:reports")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["title"] = "Service Payment"

        return super().get_context_data(**kwargs)


class AdvancedReportCreateView(LoginRequiredMixin, View, JsonFormMixin):

    def post(self, request, *args, **kwargs):

        client_name = request.POST.get("client_nm")
        cp_name = request.POST.get("cp_nm")
        email_name = request.POST.get("email_nm")
        email_name = email_name.lower()
        reportype = request.POST.get("reptyp")
        route_file = request.FILES["route_file"]

        route_filename = route_file.name
        _, ext = os.path.splitext(route_filename)
        ext = ext.lower()  # Convert to lowercase for case-insensitive comparison

        reportid = None
        client = LogiFlexClient.objects.filter(user=self.request.user).first()
        servicepayment = None
        if client:
            servicepayment = ServicePayment.objects.filter(client=client).first()
        check_report = 0
        advanced_report = 0
        print("Report Type:", reportype)
        report_type = ""
        # Check report type
        if reportype == "1":
            report_type = "lite"
            if (servicepayment and servicepayment.can_generate_report()) or not servicepayment:
                check_report = 1
        elif reportype == "2":
            report_type = "advanced"
            if servicepayment and servicepayment.can_generate_advanced_report():
                advanced_report = 1

        # print("client: ", client.pk)
        # print("Service Payment:", servicepayment.pk)
        # print("lite_report:", lite_report, "advanced_report:", advanced_report)
        # print("report_type:", report_type)
        if check_report or advanced_report:
            # print("you can generate reports")
            # Save client and result data
            user = self.request.user
            if not client.contact_name:
                client.contact_name = client_name
            if not client.company:
                client.company = cp_name

            client.save()

            downloadcode = generatecode(8)
            if check_report == 1:
                report_type = FreightOpsReport.ReportType.HEALTH_CHECK
            elif advanced_report == 1:
                report_type = FreightOpsReport.ReportType.FULL_REPORT

            logireport = FreightOpsReport.objects.create(client=client, payment=servicepayment,
                                                       download_code=downloadcode,
                                                       report_number=FreightOpsReport.generate_report_number(),
                                                       report_type=report_type
                                                        )
            # add route file information
            logireport.uploaded_file = route_file
            logireport.file_extension = ext
            logireport.file_name = route_file.name

            # add report ID
            # logireport.report_number = makereportnumber(logireport.pk, reportype)

            # add expected_delivery
            # logireport.expected_delivery = now() + timedelta(days=1)

            logireport.save()
            if check_report == 1:
                servicepayment.mark_report_used()
            elif advanced_report == 1:
                servicepayment.mark_advanced_report_used()

            start_time = time.time()
            extension_ok = True
            if ext == ".csv":
                dff = pd.read_csv(logireport.uploaded_file)
            elif ext == ".xlsx" or ext == ".xls":
                dff = pd.read_excel(logireport.uploaded_file)
            else:
                extension_ok = False

            validator = ColumnNameValidator()
            date_validator = DateValidator()

            test_columns = dff.columns
            # print("Testing with sample column variations...")
            results = validator.validate_and_correct_columns(dff)
            column_report = validator.print_validation_report(results)

            # Test date validation with sample dates
            # print("\n" + "=" * 60)
            # print("Testing date validation...")

            sample_dates = dff['Date_ship']
            date_results = date_validator.validate_date_column(sample_dates, 'TestDate')
            date_report = date_validator.print_date_validation_report(date_results)

            orig_cities = dff[['OriginCity', 'DestinationCity']]
            # print("Origine cities:", orig_cities.columns)
            uscities = City.objects.all().values()
            us_cities = pd.DataFrame(uscities)
            usstates = State.objects.all().values()
            us_states = pd.DataFrame(usstates)
            gasprices = GasPriceState.objects.all().values()
            state_diesel_price = pd.DataFrame(gasprices)
            normalizer = CityStateNormalizer(orig_cities, us_cities, us_states, state_diesel_price)
            clean_df, review_df, misscities_origin, missgstates_origin, misscities_destin, missgstates_destin, flags, dieselprices = normalizer.normalize()
            # print("clean_df")
            # print(clean_df.index)
            # print(clean_df.info())
            # data = data.drop(['OriginCity', 'DestinationCity'], axis=1)
            # data = pd.concat([data, clean_df], axis=0, ignore_index=True)
            dff.update(clean_df['OriginCity'])
            dff.update(clean_df['DestinationCity'])
            dff['Diesel_Price'] = dieselprices
            dff['Diesel_Price'] = dff['Diesel_Price'].astype(float)

            # Test date fixing
            # print("\nTesting date format fixing...")
            fixed_dates, fix_report = date_validator.fix_date_format(sample_dates, '%Y-%m-%d')

            directory_path = 'data_files/route_files/company_id_{0}/report_{1}'.format(logireport.client.id,
                                                                                       logireport.id)
            # dff.drop('Date', axis=1, inplace=True)
            # print("Data before saving to csv file")
            # print(dff.head(5))
            # print(dff.columns)
            filename = 'data_files/route_files/company_id_{0}/report_{1}/{2}'.format(logireport.client.id,
                                                                                     logireport.id,
                                                                                     logireport.file_name)
            # print("filename: ", filename)
            filepath = settings.MEDIA_ROOT + "/" + filename
            # f = open(filepath, 'w')
            dff.to_csv(filepath, index=False)

            if extension_ok:
                df, df_in_transit, df_unkown = clean_data(dff)
                df = calculate_kpis(df)

            in_transit_analysis = analyze_in_transit(df_in_transit)
            # print(in_transit_analysis)
            # print("**************************************************************************")
            # Compute data fingerprint (abuse prevention)
            carriers = sorted(df["CarrierName"].dropna().unique().tolist())
            drivers = sorted(df["DriverName"].dropna().unique().tolist()) if "DriverName" in df.columns else []
            lanes = sorted((df["OriginCity"].str.strip() + df["DestinationCity"].str.strip()).unique().tolist())
            fingerprint_input = "|".join(carriers + drivers + lanes)
            fingerprint = hashlib.sha256(fingerprint_input.encode()).hexdigest()

            logireport.data_fingerprint = fingerprint
            logireport.total_shipments = len(df)
            logireport.intransit_analysis = in_transit_analysis
            logireport.save()


            # Generate report
            narrative, analysis, score, \
            carrier_stats, driver_stats, route_stats, contingency_matrix = \
                generate_full_report(df, api_key=settings.ANTHROPIC_API_KEY)
            # print(result)
            # Parse date range
            if "Date_ship" in df.columns:
                dates = pd.to_datetime(df["Date_ship"], errors="coerce").dropna()
                if len(dates) > 0:
                    logireport.date_range_start = dates.min().date()
                    logireport.date_range_end = dates.max().date()

                # logireport.populate_from_results(narrative, analysis, score, carrier_stats, driver_stats, route_stats)

                logireport.fleet_score = score.get("score", 0)
                logireport.fleet_grade = score.get("grade", "Insufficient data")
                logireport.fleet_score_json = score
                logireport.llm_result = narrative
                logireport.save()
                # Map dimension scores
                dim_map = {
                    "On-time delivery": "score_ontime_delivery",
                    "Cost efficiency": "score_cost_efficiency",
                    "Fuel efficiency": "score_fuel_efficiency",
                    "Route utilization": "score_route_utilization",
                    "Cost predictability": "score_cost_predictability",
                }
                for dim in score.get("dimensions", []):
                    field = dim_map.get(dim["name"])
                    if field:
                        setattr(logireport, field, dim["score"])

                # Drag/strength
                drag = score.get("biggest_drag", {})
                logireport.biggest_drag_dimension = drag.get("dimension", "")
                logireport.biggest_drag_score = drag.get("dimension_score")

                strength = score.get("biggest_strength", {})
                logireport.biggest_strength_dimension = strength.get("dimension", "")
                logireport.biggest_strength_score = strength.get("dimension_score")

                imp = score.get("improvement_scenario", {})
                logireport.improvement_current = imp.get("current_fleet_score")
                logireport.improvement_projected = imp.get("projected_fleet_score")
                logireport.improvement_delta = imp.get("point_gain")

                savings = analysis.get("composite_savings", {})
                logireport.total_annual_savings = savings.get("total_identified_annual_savings", 0)
                logireport.savings_carrier_reallocation = savings.get("carrier_reallocation_annual", 0)
                logireport.savings_lane_optimization = savings.get("lane_excess_cost_annual", 0)
                logireport.savings_driver_coaching = savings.get("driver_inefficiency_annual", 0)
                logireport.savings_invoice_anomalies = savings.get("cost_anomalies_annual", 0)

                # --- OR Model Outputs ---
                logireport.carrier_optimization_json = analysis.get("carrier_optimization", {})
                logireport.lane_profitability_json = analysis.get("lane_profitability", {})
                logireport.driver_spc_json = analysis.get("driver_spc", {})
                logireport.cost_anomalies_json = analysis.get("cost_anomalies", {})

                # --- Data Quality ---
                dq = analysis.get("data_quality", {})
                logireport.total_rows = dq.get("total_rows", 0)
                logireport.total_columns = dq.get("total_columns", 0)
                logireport.has_fuel_cost = dq.get("has_fuel_cost", False)
                logireport.has_distance = dq.get("has_distance", False)
                logireport.has_weight = dq.get("has_weight", False)
                logireport.has_accessorials = dq.get("has_accessorials", False)
                logireport.has_delivery_time = dq.get("has_delivery_time", False)

                # --- Narrative ---
                # try:
                #     narrative = json.loads(narrative)
                logireport.narrative_json = narrative
                logireport.money_headline_sub = narrative.get("money_headline_sub", "")
                logireport.carriers_summary = narrative.get("carriers_summary", "")
                logireport.carriers_detailed = narrative.get("carriers_detailed", "")
                logireport.drivers_summary = narrative.get("drivers_summary", "")
                logireport.drivers_detailed = narrative.get("drivers_detailed", "")
                logireport.routes_summary = narrative.get("routes_summary", "")
                logireport.routes_detailed = narrative.get("routes_detailed", "")
                logireport.improvement_scenario_text = narrative.get("improvement_scenario", "")
                # except json.JSONDecodeError as e:
                #     logireport.llm_result = narrative

                # --- LLM Cost ---
                meta = narrative.get("_meta", {})
                logireport.llm_model = meta.get("model", "")
                logireport.llm_input_tokens = meta.get("input_tokens", 0)
                logireport.llm_output_tokens = meta.get("output_tokens", 0)
                logireport.llm_cost_usd = meta.get("estimated_cost_usd", 0)
                logireport.save()
                # --- Statistics ---
                logireport.carrier_stats_json = carrier_stats
                logireport.save()
                print(driver_stats)
                logireport.driver_stats_json = json.dumps(driver_stats)
                logireport.save()
                logireport.route_stats_json = route_stats
                logireport.save()
                logireport.contingency_analysis = contingency_matrix
                logireport.save()
                # --- Summary counts ---
                cs = carrier_stats
                ds = driver_stats
                rs = route_stats
                logireport.total_carriers = cs.get("total_carriers", 0)
                logireport.total_drivers = ds.get("total_drivers", 0)
                logireport.total_lanes = rs.get("total_lanes", 0)

            logireport.generation_time_seconds = round(time.time() - start_time, 2)
            logireport.save()

            message = "Report Uploaded Succssefully. Wait for a confirmation email from us."
            repstatus = "success"
            reportid = logireport.id
        else:
            message = "Report Already Uploaded Succssefully.Check the list of your reports for more details"
            repstatus = "fail"

        data = {"submessage": message, "repstatus": repstatus, "repid": reportid}

        return JsonResponse(data)



# raw_txt = {'narrative': '{\n  "money_headline_sub": "Carrier reallocation, lane repricing, anomaly recovery, and one flagged driver account for $117,108 in annual savings.",\n\n  "top_actions": [\n    {\n      "title": "Eliminate ABC Carriers and DEF Logistics — move their 72 combined shipments to XYZ Freight (70%) and GHI Transport (30%)",\n      "detail": "The LP optimization model confirms this is the single highest-impact move available. ABC Carriers averages $1,025.75 per shipment and DEF Logistics averages $1,033.51, while XYZ Freight comes in at $937.36 — a savings of $50.43 per shipment. Across 127 annual shipments, this reallocation saves $6,404 per month.",\n      "value": "$76,848/yr"\n    },\n    {\n      "title": "Audit and dispute GHI Transport charges on SHP0199 (Austin → Tulsa) and SHP0006 (Oklahoma City → Tulsa)",\n      "detail": "SHP0199 was billed at $1,917.96 on the Austin → Tulsa lane where the median cost is $727.52 — an overpayment of $1,190.44, or 163.6% above the lane median. SHP0006 came in at $1,889.98 against a lane median of $839.05, an overpayment of $1,050.93. Both shipments were handled by GHI Transport. Request itemized invoices immediately and withhold future payment pending resolution.",\n      "value": "$26,896/yr"\n    },\n    {\n      "title": "Review John Doe\'s fuel consumption and routing — his fuel cost per mile is statistically out of control",\n      "detail": "John Doe\'s fuel cost per mile is $0.4097, sitting 1.9 sigma above the fleet mean of $0.4011 and beyond the upper control limit of $0.4079. His average speed of 46.7 mph is the lowest in the fleet, suggesting inefficient routing or excessive idling. Addressing this through route review and driver coaching is estimated to recover $67.92 per month.",\n      "value": "$815/yr"\n    }\n  ],\n\n  "carriers_summary": "This is a fleet-wide emergency, not a carrier performance issue — every single carrier has a 0% on-time delivery rate across all 127 shipments. ABC Carriers (36 shipments, $1,025.75 avg cost), DEF Logistics (36 shipments, $1,033.51 avg cost), GHI Transport (30 shipments, $968.44 avg cost), and XYZ Freight (25 shipments, $937.36 avg cost) all failed to deliver a single shipment on time. The cost spread between the most expensive carrier (DEF Logistics at $1,033.51 avg) and the cheapest (XYZ Freight at $937.36 avg) is $96.15 per shipment — and since on-time performance is equal (uniformly zero), cost becomes the only differentiator. The single most important carrier decision right now is to stop sending volume to ABC Carriers and DEF Logistics entirely and consolidate with XYZ Freight and GHI Transport.",\n\n  "carriers_insights": [\n    {\n      "type": "warning",\n      "text": "**All four carriers** have a **0% on-time delivery rate** across all 127 shipments — this is a systemic failure pointing to either data error, a dispatch process breakdown, or an external constraint affecting the entire network."\n    },\n    {\n      "type": "finding",\n      "text": "**DEF Logistics** has the highest cost variability with a **cost CV of 0.402** and a standard deviation of $414.97 — making it the least predictable carrier in the fleet despite not being the most expensive on average."\n    },\n    {\n      "type": "opportunity",\n      "text": "**XYZ Freight** at **$937.36 avg cost per shipment** is the cheapest carrier by $96.15 vs DEF Logistics — the LP model recommends increasing XYZ Freight\'s share from 19.7% to 70%, adding 64 shipments annually."\n    },\n    {\n      "type": "finding",\n      "text": "**GHI Transport** is responsible for both cost anomalies in the dataset — SHP0199 and SHP0006 — with a combined **overpayment of $2,241.37** that projects to $26,896 annually."\n    },\n    {\n      "type": "opportunity",\n      "text": "**GHI Transport** at **$968.44 avg cost** and a cost CV of 0.377 represents a reasonable secondary carrier; the model recommends growing its share modestly from 23.6% to 30%, adding 8 shipments."\n    }\n  ],\n\n  "carriers_detailed": "The most alarming finding in this report is not the cost structure — it is that every carrier recorded a 0% on-time delivery rate across all 127 shipments. ABC Carriers: 36 late, 0 on time. DEF Logistics: 36 late, 0 on time. GHI Transport: 30 late, 0 on time. XYZ Freight: 25 late, 0 on time. Before acting on any carrier reallocation recommendation, you need to determine whether this reflects a true operational failure or a data recording issue. If it is real, your customers are receiving 100% late deliveries, which is an existential business problem. Call your top three customers this week and confirm their experience.\\n\\nSetting the on-time issue aside and comparing carriers purely on cost — which becomes the only differentiator when reliability is uniform — XYZ Freight is the clear winner at $937.36 average cost per shipment and $2.0513 per mile. GHI Transport is second at $968.44 and $2.0112 per mile. ABC Carriers ($1,025.75, $1.9769/mile) and DEF Logistics ($1,033.51, $2.0118/mile) are the most expensive and offer no compensating advantage in reliability or consistency. DEF Logistics also has the highest cost standard deviation at $414.97 (CV of 0.402), meaning you cannot predict what any given shipment will cost — a 40% swing around the average is normal for them.\\n\\nThe LP optimization model ran a mathematically optimal reallocation across all 127 shipments and produced a clear answer: eliminate ABC Carriers and DEF Logistics entirely, shift 70% of volume to XYZ Freight and 30% to GHI Transport. Under the current allocation, the fleet average cost per shipment is $997.11. Under the optimal allocation, that drops to $946.69 — a savings of $50.43 per shipment, $6,404 per month, and $76,848 per year. The model adds 64 shipments to XYZ Freight (from 25 to 89) and 8 shipments to GHI Transport (from 30 to 38). This is not a gradual transition recommendation — the math supports a hard cutover.\\n\\nHowever, one important caveat on GHI Transport: this carrier is the source of both cost anomalies detected in the dataset. SHP0199 on Austin → Tulsa was billed at $1,917.96 against a lane median of $727.52 (163.6% over), and SHP0006 on Oklahoma City → Tulsa was billed at $1,889.98 against a lane median of $839.05 (125.3% over). Before expanding GHI Transport\'s volume, get a full invoice audit on these two shipments and establish per-lane rate caps in your contract. If GHI Transport cannot explain the overcharges, consider redirecting their 30% allocation entirely to XYZ Freight and running a single-carrier model until a reliable backup is identified.",\n\n  "drivers_summary": "Like the carrier data, the driver on-time performance data shows a 0% on-time rate across all six drivers — Alex Ray, Chris Park, Emma Stone, John Doe, Mike Lee, and Sara Kim all recorded zero on-time deliveries across 127 total shipments. The industry median for on-time delivery is 85%, making this fleet 85 percentage points below benchmark. On cost efficiency, Emma Stone stands out as the most efficient driver at $1.9686 per mile, while the fleet average is $2.0103 per mile. John Doe is the only driver the statistical process control analysis flagged as out of control, specifically on fuel cost per mile, which is costing the business an estimated $815 per year above what it should.",\n\n  "drivers_detailed": "The SPC control chart analysis examined three metrics for each driver — cost per mile, fuel cost per mile, and cost variability — using a fleet mean and upper/lower control limits set at ±1.5 sigma. Only one driver, John Doe, triggered an out-of-control flag, and it was on fuel cost per mile. His value of $0.4097 sits 1.9 sigma above the fleet mean of $0.4011, exceeding the upper control limit of $0.4079. Every other driver — Alex Ray at $0.4007, Chris Park at $0.4011, Emma Stone at $0.3969, Mike Lee at $0.4004, and Sara Kim at $0.3980 — falls within the normal control band. John Doe\'s excess fuel cost translates to $67.92 per month and $815 per year in above-average fuel spend.\\n\\nLooking at cost per mile across the fleet, Emma Stone is the standout performer at $1.9686/mile, 2.0 sigma below the fleet mean — the only driver whose cost per mile falls in the lower half of the control range. This is a meaningful edge. At 11,680 total miles in the dataset, Emma Stone\'s cost efficiency advantage over the fleet mean of $2.0103/mile amounts to roughly $0.0417 per mile saved. Chris Park ($2.0276/mile) and Alex Ray ($2.0174/mile) sit slightly above mean but within normal limits. Mike Lee ($2.0156/mile) and Sara Kim ($2.0117/mile) are close to fleet average. John Doe ($2.021/mile) is modestly above average on cost per mile as well, though not enough to trigger a flag independently.\\n\\nFor John Doe specifically, the coaching conversation should focus on three areas: fuel throttle habits at highway speeds, idle time at pickup and delivery locations, and route adherence. His average speed of 46.7 mph is the lowest in the fleet (fleet range: 46.7 to 47.6 mph), which may indicate more frequent stops, idling, or suboptimal route selection. Pull his GPS and fuel transaction data for the last 30 days and compare his routing choices against the planned routes. The goal is to bring his fuel cost per mile from $0.4097 down to at or below the fleet mean of $0.4011 — a reduction of $0.0086/mile. Over his 7,941 miles in the current dataset period, that is $68.29 in savings, or $815 annualized.\\n\\nFleet-wide, the most urgent coaching topic is not fuel — it is whatever is causing the 0% on-time delivery rate. All six drivers are equally affected, which rules out individual driver behavior as the cause. This points toward systemic issues: dispatch timing, loading dock delays, unrealistic transit time windows, or a routing software problem. Convene a driver roundtable this week. Ask each driver to identify the top reason their last three deliveries were late. That conversation will tell you more than any dataset can.",\n\n  "routes_summary": "The fleet operates across 30 lanes connecting six cities — Dallas, Houston, Austin, San Antonio, Oklahoma City, and Tulsa — with an average of 4.2 shipments per lane and a fleet median cost per mile of $2.0172. The most expensive lane by total average shipment cost is Dallas → Austin at $1,387.12 per shipment over an average of 692 miles, while the most efficient lane by cost per mile is Houston → Oklahoma City at $1.8677/mile. Oklahoma City shows the most concerning network imbalance, with 21 outbound movements against only 17 inbound, generating an estimated 4 likely deadhead trips. On-time performance is 0% across all 30 lanes, which is the dominant route-level concern.",\n\n  "routes_insights": [\n    {\n      "type": "warning",\n      "text": "The **Tulsa, OK → Oklahoma City, OK** lane carries the highest cost per mile in the fleet at **$2.1263/mile** — 5.4% above the fleet median — and has only 3 shipments, suggesting an underutilized lane with no economies of scale to offset the high unit cost."\n    },\n    {\n      "type": "warning",\n      "text": "**Oklahoma City, OK** generates 4 estimated deadhead trips due to 21 outbound vs 17 inbound shipments — empty miles that cost fuel and driver time with zero revenue contribution."\n    },\n    {\n      "type": "finding",\n      "text": "The **Austin, TX → Houston, TX** lane has the highest shipment volume at 8 loads, yet costs **$2.056/mile** — 1.9% above median — generating $151.87 in excess cost that compounds due to its frequency."\n    },\n    {\n      "type": "opportunity",\n      "text": "**Houston, TX → Oklahoma City, OK** is the best-priced lane in the network at **$1.8677/mile** — 7.1% below the fleet median — and carries only 3 shipments, suggesting room to grow volume on this efficient corridor."\n    },\n    {\n      "type": "finding",\n      "text": "The **Dallas, TX → Tulsa, OK** lane has only **1 shipment** in the analysis period — a statistically unreliable data point that should not be used for pricing or planning decisions without more volume."\n    }\n  ],\n\n  "routes_detailed": "Ranking all 30 lanes by cost per mile reveals a spread from $1.8677 (Houston → Oklahoma City) to $2.1263 (Tulsa → Oklahoma City) — a 13.8% range. The five highest-cost lanes per mile are: Tulsa → Oklahoma City at $2.1263/mile (5.4% above median, $178.04 excess cost), Austin → Tulsa at $2.1128/mile (4.7% above median, $181.56 excess cost), Tulsa → Dallas at $2.1113/mile (4.7% above median, $82.37 excess cost), San Antonio → Oklahoma City at $2.0545/mile (1.9% above median), and Oklahoma City → Tulsa at $2.0563/mile (1.9% above median, $65.86 excess cost). The Austin → Tulsa lane is particularly concerning because it is also the source of the largest cost anomaly in the dataset (SHP0199, billed at $1,917.96 against a lane median of $727.52). Strip that anomaly out and the lane\'s economics improve, but the structural cost-per-mile issue remains.\\n\\nThe five best-performing lanes by cost per mile are Houston → Oklahoma City ($1.8677/mile), Houston → Austin ($1.9247/mile), Oklahoma City → San Antonio ($1.9216/mile), Dallas → Tulsa ($1.9438/mile), and Houston → Austin ($1.9411/mile). These lanes should be used as the pricing benchmark when renegotiating carrier rates on the higher-cost corridors. If GHI Transport can move freight from Houston to Oklahoma City at $1.8677/mile, there is no structural reason why the same carrier should charge $2.1263/mile from Tulsa to Oklahoma City — a comparable distance and geography. That gap is a negotiation target.\\n\\nThe network balance analysis identifies Oklahoma City as the city most at risk for deadhead costs. With 21 outbound and 17 inbound shipments, Oklahoma City has an imbalance of +4, meaning an estimated 4 trips depart Oklahoma City empty — either positioning trucks for a load or returning home without freight. San Antonio shows a smaller imbalance of +2 (20 out, 18 in), and Houston is nearly balanced at +1. Dallas is actually under-served on outbound (17 out vs 23 in), which creates an opportunity to develop more Dallas-origin freight that could fill trucks currently arriving empty. Tulsa is perfectly balanced at 20 in and 20 out. To reduce Oklahoma City deadhead, explore backhaul freight on the Oklahoma City → Dallas and Oklahoma City → Houston lanes, both of which already exist in the network at 5 and 2 shipments respectively.\\n\\nLane utilization analysis flags 10% of lanes as underused — roughly 3 of the 30 lanes. The most obvious candidate is Dallas → Tulsa with just 1 shipment, followed by Oklahoma City → Houston with 2 and Tulsa → Dallas with 2. These low-volume lanes inflate per-shipment costs because there is no frequency discount or driver familiarity with the route.', 'analysis': {'carrier_optimization': {'model_status': 'optimal', 'current_allocation': {'ABC Carriers': 0.2835, 'DEF Logistics': 0.2835, 'GHI Transport': 0.2362, 'XYZ Freight': 0.1969}, 'optimal_allocation': {'GHI Transport': 0.3, 'XYZ Freight': 0.7}, 'current_avg_cost_per_shipment': 997.11, 'optimal_avg_cost_per_shipment': 946.69, 'savings_per_shipment': 50.43, 'monthly_savings': 6404.04, 'annual_savings_estimate': 76848.44, 'current_ontime': 46.5, 'projected_ontime': 52.2, 'total_shipments_analyzed': 127, 'recommendations': [{'carrier': 'XYZ Freight', 'current_share': 19.7, 'optimal_share': 70.0, 'direction': 'increase', 'shipment_change': 64, 'avg_cost': 937.36, 'ontime_rate': 56.0}, {'carrier': 'ABC Carriers', 'current_share': 28.3, 'optimal_share': 0, 'direction': 'decrease', 'shipment_change': 36, 'avg_cost': 1025.75, 'ontime_rate': 41.7}, {'carrier': 'DEF Logistics', 'current_share': 28.3, 'optimal_share': 0, 'direction': 'decrease', 'shipment_change': 36, 'avg_cost': 1033.51, 'ontime_rate': 47.2}, {'carrier': 'GHI Transport', 'current_share': 23.6, 'optimal_share': 30.0, 'direction': 'increase', 'shipment_change': 8, 'avg_cost': 968.44, 'ontime_rate': 43.3}]}, 'lane_profitability': {'lanes': [{'lane': 'Dallas, TX → Austin, TX', 'shipment_count': 4, 'avg_freight_cost': 1387.12, 'avg_fuel_cost': 415.2, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1387.12, 'total_spend': 5548.5, 'avg_distance_miles': 692.0, 'avg_cost_per_mile': 2.0045, 'pct_above_fleet_median': -0.6, 'avg_weight_lbs': 20028.0}, {'lane': 'Dallas, TX → Tulsa, OK', 'shipment_count': 1, 'avg_freight_cost': 1282.92, 'avg_fuel_cost': 396.0, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1282.92, 'total_spend': 1282.92, 'avg_distance_miles': 660.0, 'avg_cost_per_mile': 1.9438, 'pct_above_fleet_median': -3.6, 'avg_weight_lbs': 19960.0}, {'lane': 'San Antonio, TX → Tulsa, OK', 'shipment_count': 4, 'avg_freight_cost': 1220.11, 'avg_fuel_cost': 374.25, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1220.11, 'total_spend': 4880.44, 'avg_distance_miles': 623.8, 'avg_cost_per_mile': 1.9561, 'pct_above_fleet_median': -3.0, 'avg_weight_lbs': 20500.0}, {'lane': 'Houston, TX → Dallas, TX', 'shipment_count': 5, 'avg_freight_cost': 1196.01, 'avg_fuel_cost': 350.76, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1196.01, 'total_spend': 5980.03, 'avg_distance_miles': 584.6, 'avg_cost_per_mile': 2.0459, 'pct_above_fleet_median': 1.4, 'avg_weight_lbs': 19080.0, 'excess_cost_total': 83.83}, {'lane': 'Tulsa, OK → Oklahoma City, OK', 'shipment_count': 3, 'avg_freight_cost': 1156.02, 'avg_fuel_cost': 326.2, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1156.02, 'total_spend': 3468.05, 'avg_distance_miles': 543.7, 'avg_cost_per_mile': 2.1263, 'pct_above_fleet_median': 5.4, 'avg_weight_lbs': 19064.0, 'excess_cost_total': 178.04}, {'lane': 'Oklahoma City, OK → Austin, TX', 'shipment_count': 6, 'avg_freight_cost': 1149.89, 'avg_fuel_cost': 338.6, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1149.89, 'total_spend': 6899.34, 'avg_distance_miles': 564.3, 'avg_cost_per_mile': 2.0376, 'pct_above_fleet_median': 1.0, 'avg_weight_lbs': 19026.0, 'excess_cost_total': 69.19}, {'lane': 'San Antonio, TX → Houston, TX', 'shipment_count': 3, 'avg_freight_cost': 1128.89, 'avg_fuel_cost': 333.4, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1128.89, 'total_spend': 3386.67, 'avg_distance_miles': 555.7, 'avg_cost_per_mile': 2.0316, 'pct_above_fleet_median': 0.7, 'avg_weight_lbs': 20095.0, 'excess_cost_total': 24.04}, {'lane': 'Dallas, TX → San Antonio, TX', 'shipment_count': 4, 'avg_freight_cost': 1083.18, 'avg_fuel_cost': 321.75, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1083.18, 'total_spend': 4332.71, 'avg_distance_miles': 536.2, 'avg_cost_per_mile': 2.0199, 'pct_above_fleet_median': 0.1, 'avg_weight_lbs': 19340.0, 'excess_cost_total': 5.87}, {'lane': 'Tulsa, OK → San Antonio, TX', 'shipment_count': 3, 'avg_freight_cost': 1037.73, 'avg_fuel_cost': 311.4, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1037.73, 'total_spend': 3113.19, 'avg_distance_miles': 519.0, 'avg_cost_per_mile': 1.9995, 'pct_above_fleet_median': -0.9, 'avg_weight_lbs': 21426.0}, {'lane': 'Houston, TX → San Antonio, TX', 'shipment_count': 4, 'avg_freight_cost': 1033.61, 'avg_fuel_cost': 298.8, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1033.61, 'total_spend': 4134.44, 'avg_distance_miles': 498.0, 'avg_cost_per_mile': 2.0755, 'pct_above_fleet_median': 2.9, 'avg_weight_lbs': 21163.0, 'excess_cost_total': 116.23}, {'lane': 'Oklahoma City, OK → San Antonio, TX', 'shipment_count': 4, 'avg_freight_cost': 1014.59, 'avg_fuel_cost': 316.8, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1014.59, 'total_spend': 4058.36, 'avg_distance_miles': 528.0, 'avg_cost_per_mile': 1.9216, 'pct_above_fleet_median': -4.7, 'avg_weight_lbs': 19724.0}, {'lane': 'San Antonio, TX → Austin, TX', 'shipment_count': 6, 'avg_freight_cost': 1010.48, 'avg_fuel_cost': 308.1, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1010.48, 'total_spend': 6062.89, 'avg_distance_miles': 513.5, 'avg_cost_per_mile': 1.9678, 'pct_above_fleet_median': -2.4, 'avg_weight_lbs': 19063.0}, {'lane': 'Austin, TX → Houston, TX', 'shipment_count': 8, 'avg_freight_cost': 1004.63, 'avg_fuel_cost': 293.17, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1004.63, 'total_spend': 8037.01, 'avg_distance_miles': 488.6, 'avg_cost_per_mile': 2.056, 'pct_above_fleet_median': 1.9, 'avg_weight_lbs': 18800.0, 'excess_cost_total': 151.87}, {'lane': 'Oklahoma City, OK → Dallas, TX', 'shipment_count': 5, 'avg_freight_cost': 1003.62, 'avg_fuel_cost': 303.48, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1003.62, 'total_spend': 5018.08, 'avg_distance_miles': 505.8, 'avg_cost_per_mile': 1.9842, 'pct_above_fleet_median': -1.6, 'avg_weight_lbs': 18255.0}, {'lane': 'Dallas, TX → Houston, TX', 'shipment_count': 3, 'avg_freight_cost': 1001.63, 'avg_fuel_cost': 309.0, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1001.63, 'total_spend': 3004.89, 'avg_distance_miles': 515.0, 'avg_cost_per_mile': 1.9449, 'pct_above_fleet_median': -3.6, 'avg_weight_lbs': 20905.0}, {'lane': 'Houston, TX → Austin, TX', 'shipment_count': 5, 'avg_freight_cost': 993.91, 'avg_fuel_cost': 309.84, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 993.91, 'total_spend': 4969.57, 'avg_distance_miles': 516.4, 'avg_cost_per_mile': 1.9247, 'pct_above_fleet_median': -4.6, 'avg_weight_lbs': 21798.0}, {'lane': 'Austin, TX → Dallas, TX', 'shipment_count': 7, 'avg_freight_cost': 991.17, 'avg_fuel_cost': 294.43, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 991.17, 'total_spend': 6938.18, 'avg_distance_miles': 490.7, 'avg_cost_per_mile': 2.0198, 'pct_above_fleet_median': 0.1, 'avg_weight_lbs': 19887.0, 'excess_cost_total': 9.18}, {'lane': 'Tulsa, OK → Houston, TX', 'shipment_count': 6, 'avg_freight_cost': 973.89, 'avg_fuel_cost': 288.1, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 973.89, 'total_spend': 5843.37, 'avg_distance_miles': 480.2, 'avg_cost_per_mile': 2.0282, 'pct_above_fleet_median': 0.5, 'avg_weight_lbs': 19083.0, 'excess_cost_total': 31.89}, {'lane': 'San Antonio, TX → Dallas, TX', 'shipment_count': 4, 'avg_freight_cost': 963.83, 'avg_fuel_cost': 289.05, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 963.83, 'total_spend': 3855.34, 'avg_distance_miles': 481.8, 'avg_cost_per_mile': 2.0007, 'pct_above_fleet_median': -0.8, 'avg_weight_lbs': 19220.0}, {'lane': 'Austin, TX → Oklahoma City, OK', 'shipment_count': 3, 'avg_freight_cost': 957.0, 'avg_fuel_cost': 282.8, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 957.0, 'total_spend': 2871.01, 'avg_distance_miles': 471.3, 'avg_cost_per_mile': 2.0304, 'pct_above_fleet_median': 0.7, 'avg_weight_lbs': 23296.0, 'excess_cost_total': 18.72}, {'lane': 'Austin, TX → San Antonio, TX', 'shipment_count': 3, 'avg_freight_cost': 945.97, 'avg_fuel_cost': 285.2, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 945.97, 'total_spend': 2837.92, 'avg_distance_miles': 475.3, 'avg_cost_per_mile': 1.9901, 'pct_above_fleet_median': -1.3, 'avg_weight_lbs': 19754.0}, {'lane': 'San Antonio, TX → Oklahoma City, OK', 'shipment_count': 3, 'avg_freight_cost': 933.55, 'avg_fuel_cost': 275.0, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 933.55, 'total_spend': 2800.65, 'avg_distance_miles': 458.3, 'avg_cost_per_mile': 2.0368, 'pct_above_fleet_median': 1.0, 'avg_weight_lbs': 18064.0, 'excess_cost_total': 27.03}, {'lane': 'Oklahoma City, OK → Houston, TX', 'shipment_count': 2, 'avg_freight_cost': 926.45, 'avg_fuel_cost': 294.9, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 926.45, 'total_spend': 1852.9, 'avg_distance_miles': 491.5, 'avg_cost_per_mile': 1.8849, 'pct_above_fleet_median': -6.6, 'avg_weight_lbs': 23904.0}, {'lane': 'Tulsa, OK → Dallas, TX', 'shipment_count': 2, 'avg_freight_cost': 923.7, 'avg_fuel_cost': 262.5, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 923.7, 'total_spend': 1847.4, 'avg_distance_miles': 437.5, 'avg_cost_per_mile': 2.1113, 'pct_above_fleet_median': 4.7, 'avg_weight_lbs': 20261.0, 'excess_cost_total': 82.37}, {'lane': 'Oklahoma City, OK → Tulsa, OK', 'shipment_count': 4, 'avg_freight_cost': 866.2, 'avg_fuel_cost': 252.75, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 866.2, 'total_spend': 3464.8, 'avg_distance_miles': 421.2, 'avg_cost_per_mile': 2.0563, 'pct_above_fleet_median': 1.9, 'avg_weight_lbs': 18951.0, 'excess_cost_total': 65.86}, {'lane': 'Houston, TX → Tulsa, OK', 'shipment_count': 6, 'avg_freight_cost': 860.75, 'avg_fuel_cost': 258.4, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 860.75, 'total_spend': 5164.49, 'avg_distance_miles': 430.7, 'avg_cost_per_mile': 1.9986, 'pct_above_fleet_median': -0.9, 'avg_weight_lbs': 19601.0}, {'lane': 'Austin, TX → Tulsa, OK', 'shipment_count': 5, 'avg_freight_cost': 802.43, 'avg_fuel_cost': 227.88, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 802.43, 'total_spend': 4012.17, 'avg_distance_miles': 379.8, 'avg_cost_per_mile': 2.1128, 'pct_above_fleet_median': 4.7, 'avg_weight_lbs': 19839.0, 'excess_cost_total': 181.56}, {'lane': 'Houston, TX → Oklahoma City, OK', 'shipment_count': 3, 'avg_freight_cost': 799.88, 'avg_fuel_cost': 256.2, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 799.88, 'total_spend': 2399.64, 'avg_distance_miles': 427.0, 'avg_cost_per_mile': 1.8733, 'pct_above_fleet_median': -7.1, 'avg_weight_lbs': 18658.0}, {'lane': 'Tulsa, OK → Austin, TX', 'shipment_count': 6, 'avg_freight_cost': 798.47, 'avg_fuel_cost': 238.5, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 798.47, 'total_spend': 4790.8, 'avg_distance_miles': 397.5, 'avg_cost_per_mile': 2.0087, 'pct_above_fleet_median': -0.4, 'avg_weight_lbs': 19536.0}, {'lane': 'Dallas, TX → Oklahoma City, OK', 'shipment_count': 5, 'avg_freight_cost': 752.95, 'avg_fuel_cost': 225.36, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 752.95, 'total_spend': 3764.75, 'avg_distance_miles': 375.6, 'avg_cost_per_mile': 2.0047, 'pct_above_fleet_median': -0.6, 'avg_weight_lbs': 19864.0}], 'total_lanes_analyzed': 30, 'lanes_above_median': 14, 'lanes_below_median': 16, 'fleet_median_cost_per_mile': 2.0172, 'total_excess_cost': 1045.68, 'monthly_excess_cost': 1045.68, 'annual_excess_cost_estimate': 12548.16, 'worst_lane': {'lane': 'Dallas, TX → Austin, TX', 'shipment_count': 4, 'avg_freight_cost': 1387.12, 'avg_fuel_cost': 415.2, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 1387.12, 'total_spend': 5548.5, 'avg_distance_miles': 692.0, 'avg_cost_per_mile': 2.0045, 'pct_above_fleet_median': -0.6, 'avg_weight_lbs': 20028.0}, 'best_lane': {'lane': 'Dallas, TX → Oklahoma City, OK', 'shipment_count': 5, 'avg_freight_cost': 752.95, 'avg_fuel_cost': 225.36, 'avg_accessorial_cost': 0.0, 'avg_total_cost': 752.95, 'total_spend': 3764.75, 'avg_distance_miles': 375.6, 'avg_cost_per_mile': 2.0047, 'pct_above_fleet_median': -0.6, 'avg_weight_lbs': 19864.0}, 'data_completeness': {'has_fuel_data': False, 'has_accessorial_data': False, 'has_weight_data': True, 'has_distance_data': True}}, 'driver_spc': {'drivers': [{'driver_name': 'John Doe', 'shipment_count': 17, 'ontime_rate': 0.0, 'avg_freight_cost': 941.53, 'total_freight_cost': 16005.99, 'flags': [{'metric': 'Fuel Cost per Mile', 'value': 0.4097, 'fleet_mean': 0.4011, 'sigma_position': 1.9, 'flag_type': 'above_ucl', 'estimated_monthly_excess_cost': 67.92}], 'sigma_positions': {'Cost per Mile': 0.5, 'Fuel Cost per Mile': 1.9, 'Cost Variability (Std Dev)': 0.19}, 'avg_cost_per_mile': 2.021, 'avg_fuel_per_mile': 0.4097, 'avg_speed_mph': 46.7, 'total_miles': 7941, 'is_out_of_control': True}, {'driver_name': 'Alex Ray', 'shipment_count': 17, 'ontime_rate': 0.0, 'avg_freight_cost': 972.43, 'total_freight_cost': 16531.24, 'flags': [], 'sigma_positions': {'Cost per Mile': 0.34, 'Fuel Cost per Mile': -0.1, 'Cost Variability (Std Dev)': -0.64}, 'avg_cost_per_mile': 2.0174, 'avg_fuel_per_mile': 0.4007, 'avg_speed_mph': 47.0, 'total_miles': 8183, 'is_out_of_control': False}, {'driver_name': 'Chris Park', 'shipment_count': 24, 'ontime_rate': 0.0, 'avg_freight_cost': 892.42, 'total_freight_cost': 21417.98, 'flags': [], 'sigma_positions': {'Cost per Mile': 0.82, 'Fuel Cost per Mile': -0.0, 'Cost Variability (Std Dev)': -1.55}, 'avg_cost_per_mile': 2.0276, 'avg_fuel_per_mile': 0.4011, 'avg_speed_mph': 47.6, 'total_miles': 10548, 'is_out_of_control': False}, {'driver_name': 'Emma Stone', 'shipment_count': 23, 'ontime_rate': 0.0, 'avg_freight_cost': 991.03, 'total_freight_cost': 22793.64, 'flags': [], 'sigma_positions': {'Cost per Mile': -1.97, 'Fuel Cost per Mile': -0.94, 'Cost Variability (Std Dev)': -0.07}, 'avg_cost_per_mile': 1.9686, 'avg_fuel_per_mile': 0.3969, 'avg_speed_mph': 47.5, 'total_miles': 11680, 'is_out_of_control': False}, {'driver_name': 'Mike Lee', 'shipment_count': 21, 'ontime_rate': 0.0, 'avg_freight_cost': 1194.17, 'total_freight_cost': 25077.5, 'flags': [], 'sigma_positions': {'Cost per Mile': 0.25, 'Fuel Cost per Mile': -0.16, 'Cost Variability (Std Dev)': 1.05}, 'avg_cost_per_mile': 2.0156, 'avg_fuel_per_mile': 0.4004, 'avg_speed_mph': 47.6, 'total_miles': 12362, 'is_out_of_control': False}, {'driver_name': 'Sara Kim', 'shipment_count': 25, 'ontime_rate': 0.0, 'avg_freight_cost': 991.77, 'total_freight_cost': 24794.16, 'flags': [], 'sigma_positions': {'Cost per Mile': 0.07, 'Fuel Cost per Mile': -0.7, 'Cost Variability (Std Dev)': 1.02}, 'avg_cost_per_mile': 2.0117, 'avg_fuel_per_mile': 0.398, 'avg_speed_mph': 47.0, 'total_miles': 12296, 'is_out_of_control': False}], 'fleet_summary': {'total_drivers': 6, 'out_of_control_count': 1, 'in_control_count': 5, 'fleet_avg_ontime': 0.0}, 'out_of_control_drivers': ['John Doe'], 'total_estimated_monthly_excess_cost': 67.92, 'total_estimated_annual_excess_cost': 815.0, 'control_charts': {'avg_cost_per_mile': {'metric': 'Cost per Mile', 'fleet_mean': 2.0103, 'ucl': 2.042, 'lcl': 1.9786, 'sigma': 0.0211, 'higher_is_better': False, 'drivers': [{'name': 'Alex Ray', 'value': 2.0174}, {'name': 'Chris Park', 'value': 2.0276}, {'name': 'Emma Stone', 'value': 1.9686}, {'name': 'John Doe', 'value': 2.021}, {'name': 'Mike Lee', 'value': 2.0156}, {'name': 'Sara Kim', 'value': 2.0117}]}, 'avg_fuel_per_mile': {'metric': 'Fuel Cost per Mile', 'fleet_mean': 0.4011, 'ucl': 0.4079, 'lcl': 0.3944, 'sigma': 0.0045, 'higher_is_better': False, 'drivers': [{'name': 'Alex Ray', 'value': 0.4007}, {'name': 'Chris Park', 'value': 0.4011}, {'name': 'Emma Stone', 'value': 0.3969}, {'name': 'John Doe', 'value': 0.4097}, {'name': 'Mike Lee', 'value': 0.4004}, {'name': 'Sara Kim', 'value': 0.398}]}, 'cost_std': {'metric': 'Cost Variability (Std Dev)', 'fleet_mean': 366.4795, 'ucl': 398.3296, 'lcl': 334.6295, 'sigma': 21.2334, 'higher_is_better': False, 'drivers': [{'name': 'Alex Ray', 'value': 352.8981}, {'name': 'Chris Park', 'value': 333.5186}, {'name': 'Emma Stone', 'value': 364.9946}, {'name': 'John Doe', 'value': 370.5971}, {'name': 'Mike Lee', 'value': 388.7656}, {'name': 'Sara Kim', 'value': 388.1031}]}}, 'sigma_threshold': 1.5}, 'cost_anomalies': {'anomalies': [{'shipment_id': 'SHP0199', 'lane': 'Austin, TX → Tulsa, OK', 'carrier': 'GHI Transport', 'actual_cost': 1917.96, 'lane_median_cost': 727.52, 'upper_fence': 909.32, 'overpayment': 1190.44, 'pct_above_median': 163.6, 'anomaly_type': 'high_cost', 'distance_miles': 764}, {'shipment_id': 'SHP0006', 'lane': 'Oklahoma City, OK → Tulsa, OK', 'carrier': 'GHI Transport', 'actual_cost': 1889.98, 'lane_median_cost': 839.05, 'upper_fence': 1825.78, 'overpayment': 1050.93, 'pct_above_median': 125.3, 'anomaly_type': 'high_cost', 'distance_miles': 749}], 'total_anomalies': 2, 'total_shipments_analyzed': 127, 'pct_anomalous': 1.6, 'total_overpayment': 2241.37, 'annual_overpayment_estimate': 26896.44, 'by_carrier': {'GHI Transport': {'count': 2, 'total_overpayment': 2241.37}}, 'by_lane': {'Austin, TX → Tulsa, OK': {'count': 1, 'total_overpayment': 1190.44}, 'Oklahoma City, OK → Tulsa, OK': {'count': 1, 'total_overpayment': 1050.93}}, 'iqr_multiplier_used': 1.5, 'summary': {'high_cost_anomalies': 2, 'low_cost_anomalies': 0, 'worst_overpayment': {'shipment_id': 'SHP0199', 'lane': 'Austin, TX → Tulsa, OK', 'carrier': 'GHI Transport', 'actual_cost': 1917.96, 'lane_median_cost': 727.52, 'upper_fence': 909.32, 'overpayment': 1190.44, 'pct_above_median': 163.6, 'anomaly_type': 'high_cost', 'distance_miles': 764}, 'carrier_with_most_anomalies': 'GHI Transport'}}, 'composite_savings': {'carrier_reallocation_annual': 76848.44, 'lane_excess_cost_annual': 12548.16, 'driver_inefficiency_annual': 815.0, 'cost_anomalies_annual': 26896.44, 'total_identified_annual_savings': 117108.04}, 'data_quality': {'total_rows': 127, 'total_columns': 23, 'has_fuel_cost': False, 'has_distance': True, 'has_weight': True, 'has_accessorials': False, 'has_delivery_time': True, 'has_shipment_id': True}}, 'fleet_score': {'score': 29, 'grade': 'Critical', 'dimensions': [{'name': 'On-time delivery', 'score': 0.1, 'weight': 30, 'raw_value': 0.0, 'raw_unit': '%', 'benchmark': 'Industry median: 85%'}, {'name': 'Cost efficiency', 'score': 21.3, 'weight': 25, 'raw_value': 2.0172, 'raw_unit': '$/mile', 'benchmark': '30 lanes analyzed, 47% above median'}, {'name': 'Fuel efficiency', 'score': 32.4, 'weight': 20, 'raw_value': 0.4007, 'raw_unit': '$/mile fuel', 'benchmark': 'Driver CV: 0.011 (lower = more consistent)'}, {'name': 'Route utilization', 'score': 71.5, 'weight': 15, 'raw_value': 4.2, 'raw_unit': 'shipments/lane avg', 'benchmark': '30 lanes, 10% underused, 6% network imbalance'}, {'name': 'Cost predictability', 'score': 66.9, 'weight': 10, 'raw_value': 0.4044, 'raw_unit': 'avg CV', 'benchmark': 'Anomaly rate: 1.6%'}], 'biggest_drag': {'dimension': 'On-time delivery', 'dimension_score': 0.1, 'point_impact': 30.0}, 'biggest_strength': {'dimension': 'Route utilization', 'dimension_score': 71.5, 'point_impact': 10.7}, 'improvement_scenario': {'dimension': 'On-time delivery', 'current_score': 0.1, 'improved_to': 75, 'current_fleet_score': 29, 'projected_fleet_score': 51, 'point_gain': 22}, 'data_completeness': {'has_delivery_status': True, 'has_distance': True, 'has_fuel': True, 'has_carriers': True, 'has_origins': True, 'dimensions_computed': 5, 'dimensions_possible': 5}}, 'carrier_stats': {'carriers': [{'carrier_name': 'ABC Carriers', 'total_shipments': 36, 'pct_of_total': 28.3, 'avg_freight_cost': 1025.75, 'total_freight_cost': 36926.97, 'cost_std_dev': 310.93, 'cost_cv': 0.303, 'ontime_rate': 0.0, 'late_rate': 100.0, 'ontime_shipments': 0, 'late_shipments': 36, 'avg_cost_per_mile': 1.9769, 'avg_distance': 521.6, 'avg_fuel_cost': 209.16, 'avg_cost_per_pound': 0.0508}, {'carrier_name': 'DEF Logistics', 'total_shipments': 36, 'pct_of_total': 28.3, 'avg_freight_cost': 1033.51, 'total_freight_cost': 37206.28, 'cost_std_dev': 414.97, 'cost_cv': 0.402, 'ontime_rate': 0.0, 'late_rate': 100.0, 'ontime_shipments': 0, 'late_shipments': 36, 'avg_cost_per_mile': 2.0118, 'avg_distance': 512.6, 'avg_fuel_cost': 204.82, 'avg_cost_per_pound': 0.0527}, {'carrier_name': 'GHI Transport', 'total_shipments': 30, 'pct_of_total': 23.6, 'avg_freight_cost': 968.44, 'total_freight_cost': 29053.18, 'cost_std_dev': 365.0, 'cost_cv': 0.377, 'ontime_rate': 0.0, 'late_rate': 100.0, 'ontime_shipments': 0, 'late_shipments': 30, 'avg_cost_per_mile': 2.0112, 'avg_distance': 478.4, 'avg_fuel_cost': 186.65, 'avg_cost_per_pound': 0.0504}, {'carrier_name': 'XYZ Freight', 'total_shipments': 25, 'pct_of_total': 19.7, 'avg_freight_cost': 937.36, 'total_freight_cost': 23434.08, 'cost_std_dev': 407.99, 'cost_cv': 0.435, 'ontime_rate': 0.0, 'late_rate': 100.0, 'ontime_shipments': 0, 'late_shipments': 25, 'avg_cost_per_mile': 2.0513, 'avg_distance': 457.1, 'avg_fuel_cost': 189.87, 'avg_cost_per_pound': 0.0469}], 'total_carriers': 4, 'fleet_avg_ontime': 0.0, 'fleet_avg_cost': 997.01, 'contingency_analysis': [{'better_carrier': 'DEF Logistics', 'worse_carrier': 'ABC Carriers', 'ontime_ratio': inf, 'better_otd': 0.0, 'worse_otd': 0.0}, {'better_carrier': 'GHI Transport', 'worse_carrier': 'ABC Carriers', 'ontime_ratio': inf, 'better_otd': 0.0, 'worse_otd': 0.0}, {'better_carrier': 'XYZ Freight', 'worse_carrier': 'ABC Carriers', 'ontime_ratio': inf, 'better_otd': 0.0, 'worse_otd': 0.0}]}, 'driver_stats': {'drivers': [{'driver_name': 'Alex Ray', 'total_shipments': 17, 'ontime_rate': 0.0, 'avg_freight_cost': 972.43, 'total_freight_cost': 16531.24, 'total_miles': 8183, 'avg_cost_per_mile': 2.0174, 'avg_fuel_per_mile': 0.4007, 'avg_speed_mph': 47.0}, {'driver_name': 'Chris Park', 'total_shipments': 24, 'ontime_rate': 0.0, 'avg_freight_cost': 892.42, 'total_freight_cost': 21417.98, 'total_miles': 10548, 'avg_cost_per_mile': 2.0276, 'avg_fuel_per_mile': 0.4011, 'avg_speed_mph': 47.6}, {'driver_name': 'Emma Stone', 'total_shipments': 23, 'ontime_rate': 0.0, 'avg_freight_cost': 991.03, 'total_freight_cost': 22793.64, 'total_miles': 11680, 'avg_cost_per_mile': 1.9686, 'avg_fuel_per_mile': 0.3969, 'avg_speed_mph': 47.5}, {'driver_name': 'John Doe', 'total_shipments': 17, 'ontime_rate': 0.0, 'avg_freight_cost': 941.53, 'total_freight_cost': 16005.99, 'total_miles': 7941, 'avg_cost_per_mile': 2.021, 'avg_fuel_per_mile': 0.4097, 'avg_speed_mph': 46.7}, {'driver_name': 'Mike Lee', 'total_shipments': 21, 'ontime_rate': 0.0, 'avg_freight_cost': 1194.17, 'total_freight_cost': 25077.5, 'total_miles': 12362, 'avg_cost_per_mile': 2.0156, 'avg_fuel_per_mile': 0.4004, 'avg_speed_mph': 47.6}, {'driver_name': 'Sara Kim', 'total_shipments': 25, 'ontime_rate': 0.0, 'avg_freight_cost': 991.77, 'total_freight_cost': 24794.16, 'total_miles': 12296, 'avg_cost_per_mile': 2.0117, 'avg_fuel_per_mile': 0.398, 'avg_speed_mph': 47.0}], 'total_drivers': 6, 'fleet_avg_ontime': 0.0, 'fleet_total_miles': 63010, 'fleet_avg_trip_length': 496.1, 'fleet_total_shipments': 127}, 'route_stats': {'lanes': [{'lane': 'Dallas, TX → Austin, TX', 'shipment_count': 4, 'avg_freight_cost': 1387.12, 'total_freight_cost': 5548.5, 'ontime_rate': 0.0, 'avg_distance': 692.0, 'avg_cost_per_mile': 2.004}, {'lane': 'Dallas, TX → Tulsa, OK', 'shipment_count': 1, 'avg_freight_cost': 1282.92, 'total_freight_cost': 1282.92, 'ontime_rate': 0.0, 'avg_distance': 660.0, 'avg_cost_per_mile': 1.9438}, {'lane': 'San Antonio, TX → Tulsa, OK', 'shipment_count': 4, 'avg_freight_cost': 1220.11, 'total_freight_cost': 4880.44, 'ontime_rate': 0.0, 'avg_distance': 623.8, 'avg_cost_per_mile': 1.9562}, {'lane': 'Houston, TX → Dallas, TX', 'shipment_count': 5, 'avg_freight_cost': 1196.01, 'total_freight_cost': 5980.03, 'ontime_rate': 0.0, 'avg_distance': 584.6, 'avg_cost_per_mile': 2.0388}, {'lane': 'Tulsa, OK → Oklahoma City, OK', 'shipment_count': 3, 'avg_freight_cost': 1156.02, 'total_freight_cost': 3468.05, 'ontime_rate': 0.0, 'avg_distance': 543.7, 'avg_cost_per_mile': 2.1027}, {'lane': 'Oklahoma City, OK → Austin, TX', 'shipment_count': 6, 'avg_freight_cost': 1149.89, 'total_freight_cost': 6899.34, 'ontime_rate': 0.0, 'avg_distance': 564.3, 'avg_cost_per_mile': 2.0179}, {'lane': 'San Antonio, TX → Houston, TX', 'shipment_count': 3, 'avg_freight_cost': 1128.89, 'total_freight_cost': 3386.67, 'ontime_rate': 0.0, 'avg_distance': 555.7, 'avg_cost_per_mile': 1.999}, {'lane': 'Dallas, TX → San Antonio, TX', 'shipment_count': 4, 'avg_freight_cost': 1083.18, 'total_freight_cost': 4332.71, 'ontime_rate': 0.0, 'avg_distance': 536.2, 'avg_cost_per_mile': 2.0104}, {'lane': 'Tulsa, OK → San Antonio, TX', 'shipment_count': 3, 'avg_freight_cost': 1037.73, 'total_freight_cost': 3113.19, 'ontime_rate': 0.0, 'avg_distance': 519.0, 'avg_cost_per_mile': 2.0103}, {'lane': 'Houston, TX → San Antonio, TX', 'shipment_count': 4, 'avg_freight_cost': 1033.61, 'total_freight_cost': 4134.44, 'ontime_rate': 0.0, 'avg_distance': 498.0, 'avg_cost_per_mile': 2.054}, {'lane': 'Oklahoma City, OK → San Antonio, TX', 'shipment_count': 4, 'avg_freight_cost': 1014.59, 'total_freight_cost': 4058.36, 'ontime_rate': 0.0, 'avg_distance': 528.0, 'avg_cost_per_mile': 1.9265}, {'lane': 'San Antonio, TX → Austin, TX', 'shipment_count': 6, 'avg_freight_cost': 1010.48, 'total_freight_cost': 6062.89, 'ontime_rate': 0.0, 'avg_distance': 513.5, 'avg_cost_per_mile': 1.9764}, {'lane': 'Austin, TX → Houston, TX', 'shipment_count': 8, 'avg_freight_cost': 1004.63, 'total_freight_cost': 8037.01, 'ontime_rate': 0.0, 'avg_distance': 488.6, 'avg_cost_per_mile': 2.0382}, {'lane': 'Oklahoma City, OK → Dallas, TX', 'shipment_count': 5, 'avg_freight_cost': 1003.62, 'total_freight_cost': 5018.08, 'ontime_rate': 0.0, 'avg_distance': 505.8, 'avg_cost_per_mile': 1.9896}, {'lane': 'Dallas, TX → Houston, TX', 'shipment_count': 3, 'avg_freight_cost': 1001.63, 'total_freight_cost': 3004.89, 'ontime_rate': 0.0, 'avg_distance': 515.0, 'avg_cost_per_mile': 1.9904}, {'lane': 'Houston, TX → Austin, TX', 'shipment_count': 5, 'avg_freight_cost': 993.91, 'total_freight_cost': 4969.57, 'ontime_rate': 0.0, 'avg_distance': 516.4, 'avg_cost_per_mile': 1.9411}, {'lane': 'Austin, TX → Dallas, TX', 'shipment_count': 7, 'avg_freight_cost': 991.17, 'total_freight_cost': 6938.18, 'ontime_rate': 0.0, 'avg_distance': 490.7, 'avg_cost_per_mile': 2.026}, {'lane': 'Tulsa, OK → Houston, TX', 'shipment_count': 6, 'avg_freight_cost': 973.9, 'total_freight_cost': 5843.37, 'ontime_rate': 0.0, 'avg_distance': 480.2, 'avg_cost_per_mile': 2.0392}, {'lane': 'San Antonio, TX → Dallas, TX', 'shipment_count': 4, 'avg_freight_cost': 963.83, 'total_freight_cost': 3855.34, 'ontime_rate': 0.0, 'avg_distance': 481.8, 'avg_cost_per_mile': 2.0267}, {'lane': 'Austin, TX → Oklahoma City, OK', 'shipment_count': 3, 'avg_freight_cost': 957.0, 'total_freight_cost': 2871.01, 'ontime_rate': 0.0, 'avg_distance': 471.3, 'avg_cost_per_mile': 1.9753}, {'lane': 'Austin, TX → San Antonio, TX', 'shipment_count': 3, 'avg_freight_cost': 945.97, 'total_freight_cost': 2837.92, 'ontime_rate': 0.0, 'avg_distance': 475.3, 'avg_cost_per_mile': 1.9616}, {'lane': 'San Antonio, TX → Oklahoma City, OK', 'shipment_count': 3, 'avg_freight_cost': 933.55, 'total_freight_cost': 2800.65, 'ontime_rate': 0.0, 'avg_distance': 458.3, 'avg_cost_per_mile': 2.0545}, {'lane': 'Oklahoma City, OK → Houston, TX', 'shipment_count': 2, 'avg_freight_cost': 926.45, 'total_freight_cost': 1852.9, 'ontime_rate': 0.0, 'avg_distance': 491.5, 'avg_cost_per_mile': 1.8818}, {'lane': 'Tulsa, OK → Dallas, TX', 'shipment_count': 2, 'avg_freight_cost': 923.7, 'total_freight_cost': 1847.4, 'ontime_rate': 0.0, 'avg_distance': 437.5, 'avg_cost_per_mile': 2.114}, {'lane': 'Oklahoma City, OK → Tulsa, OK', 'shipment_count': 4, 'avg_freight_cost': 866.2, 'total_freight_cost': 3464.8, 'ontime_rate': 0.0, 'avg_distance': 421.2, 'avg_cost_per_mile': 2.0487}, {'lane': 'Houston, TX → Tulsa, OK', 'shipment_count': 6, 'avg_freight_cost': 860.75, 'total_freight_cost': 5164.49, 'ontime_rate': 0.0, 'avg_distance': 430.7, 'avg_cost_per_mile': 1.9999}, {'lane': 'Austin, TX → Tulsa, OK', 'shipment_count': 5, 'avg_freight_cost': 802.43, 'total_freight_cost': 4012.17, 'ontime_rate': 0.0, 'avg_distance': 379.8, 'avg_cost_per_mile': 2.1057}, {'lane': 'Houston, TX → Oklahoma City, OK', 'shipment_count': 3, 'avg_freight_cost': 799.88, 'total_freight_cost': 2399.64, 'ontime_rate': 0.0, 'avg_distance': 427.0, 'avg_cost_per_mile': 1.8677}, {'lane': 'Tulsa, OK → Austin, TX', 'shipment_count': 6, 'avg_freight_cost': 798.47, 'total_freight_cost': 4790.8, 'ontime_rate': 0.0, 'avg_distance': 397.5, 'avg_cost_per_mile': 2.0284}, {'lane': 'Dallas, TX → Oklahoma City, OK', 'shipment_count': 5, 'avg_freight_cost': 752.95, 'total_freight_cost': 3764.75, 'ontime_rate': 0.0, 'avg_distance': 375.6, 'avg_cost_per_mile': 2.0107}], 'total_lanes': 30, 'fleet_avg_cost_per_mile': 2.0096, 'fleet_median_cost_per_mile': 2.0172, 'fleet_avg_distance': 496.1, 'network_balance': [{'city': 'Dallas, TX', 'outbound': 17, 'inbound': 23, 'imbalance': -6, 'likely_deadhead_trips': 0}, {'city': 'Oklahoma City, OK', 'outbound': 21, 'inbound': 17, 'imbalance': 4, 'likely_deadhead_trips': 4}, {'city': 'Houston, TX', 'outbound': 23, 'inbound': 22, 'imbalance': 1, 'likely_deadhead_trips': 1}, {'city': 'Austin, TX', 'outbound': 26, 'inbound': 27, 'imbalance': -1, 'likely_deadhead_trips': 0}, {'city': 'Tulsa, OK', 'outbound': 20, 'inbound': 20, 'imbalance': 0, 'likely_deadhead_trips': 0}, {'city': 'San Antonio, TX', 'outbound': 20, 'inbound': 18, 'imbalance': 2, 'likely_deadhead_trips': 2}]}}