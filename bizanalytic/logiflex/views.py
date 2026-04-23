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
from .utils.report_generator import generate_full_report
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
                df = clean_data(dff)
                df = calculate_kpis(df)

            # Compute data fingerprint (abuse prevention)
            carriers = sorted(df["CarrierName"].dropna().unique().tolist())
            drivers = sorted(df["DriverName"].dropna().unique().tolist()) if "DriverName" in df.columns else []
            lanes = sorted((df["OriginCity"].str.strip() + df["DestinationCity"].str.strip()).unique().tolist())
            fingerprint_input = "|".join(carriers + drivers + lanes)
            fingerprint = hashlib.sha256(fingerprint_input.encode()).hexdigest()

            logireport.data_fingerprint = fingerprint
            logireport.total_shipments = len(df)

            logireport.save()


            # Generate report
            result = generate_full_report(df, api_key=settings.ANTHROPIC_API_KEY)
            print(result)
            # Parse date range
            if "Date_ship" in df.columns:
                dates = pd.to_datetime(df["Date_ship"], errors="coerce").dropna()
                if len(dates) > 0:
                    logireport.date_range_start = dates.min().date()
                    logireport.date_range_end = dates.max().date()

            logireport.populate_from_results(result)
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
