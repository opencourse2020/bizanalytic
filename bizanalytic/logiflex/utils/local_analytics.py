import pandas as pd
import numpy as np
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import json
from celery import shared_task
from .prompts import *
from bizanalytic.logiflex.models import *
from openai import OpenAI
from django.conf import settings
from datetime import datetime
from .report_helpers import *

OPENAI_KEY = settings.OPENAI_KEY
client = OpenAI(api_key=OPENAI_KEY)

# 1- Cleaning Data
def clean_data(df_clean):
    # df_clean = pd.read_csv(report.routefile)
    # print("File after load", report.routefile)
    # print(df_clean.head(5))
    # print(df_clean.columns)
    # 1- Remove Duplicate ShipmentID
    df_clean.drop_duplicates(subset=['ShipmentID'], inplace=True)

    # 2- Clean and prepare categorical data columns
    # CarrierName
    distinct_CarrierName = df_clean['CarrierName'].unique()
    print("CarrierName")
    print(distinct_CarrierName)

    # DriverName
    distinct_DriverName = df_clean['DriverName'].unique()
    print("DriverName")
    print(distinct_DriverName)

    # DeliveryStatus
    distinct_DeliveryStatus = df_clean['DeliveryStatus'].unique()
    print("DeliveryStatus")
    print(distinct_DeliveryStatus)

    # OriginCity
    distinct_OriginCity = df_clean['OriginCity'].unique()
    print("OriginCity")
    print(distinct_OriginCity)

    # DestinationCity
    distinct_DestinationCity = df_clean['DestinationCity'].unique()
    print("DestinationCity")
    print(distinct_DestinationCity)

    # 3- Clean and prepare Numerical Data columns
    # enfore numerical type on numerical columns
    df_clean['Distance_Miles'] = pd.to_numeric(df_clean['Distance_Miles'], errors='coerce')
    df_clean['LoadWeight_lbs'] = pd.to_numeric(df_clean['LoadWeight_lbs'], errors='coerce')
    df_clean['FuelCost_USD'] = pd.to_numeric(df_clean['FuelCost_USD'], errors='coerce')
    df_clean['FreightCost_USD'] = pd.to_numeric(df_clean['FreightCost_USD'], errors='coerce')
    df_clean['DeliveryTime_hrs'] = pd.to_numeric(df_clean['DeliveryTime_hrs'], errors='coerce')

    # fill in the missing values
    df_clean['Distance_Miles'].fillna(df_clean['Distance_Miles'].mean(), inplace=True)
    df_clean['LoadWeight_lbs'].fillna(df_clean['LoadWeight_lbs'].mean(), inplace=True)
    df_clean['FuelCost_USD'].fillna(df_clean['FuelCost_USD'].mean(), inplace=True)
    df_clean['FreightCost_USD'].fillna(df_clean['FreightCost_USD'].mean(), inplace=True)
    df_clean['DeliveryTime_hrs'].fillna(df_clean['DeliveryTime_hrs'].mean(), inplace=True)

    # 4- Clean and prepare Date Data columns
    df_clean['Date'] = pd.to_datetime(df_clean['Date'], errors='coerce')
    df_clean['Date'].fillna(df_clean['Date'].mode()[0], inplace=True)

    # 5- Remove In-Transit data
    delivery_data = df_clean[df_clean['DeliveryStatus'].isin(['Delivered', 'Delayed'])]
    return delivery_data


# 2- Calculate KPis
def calculate_kpis(df):
    df['CostPerMile'] = df['FuelCost_USD'] / df['Distance_Miles']
    df['CostPerHour'] = df['FreightCost_USD'] / df['DeliveryTime_hrs']
    df['TotalCostPerMile'] = df['FreightCost_USD'] / df['Distance_Miles']
    df['CostPerPound'] = df['FreightCost_USD'] / df['LoadWeight_lbs']
    # df['OnTime'] = df['DeliveryStatus'].apply(lambda x: 1 if x == 'Delivered' else 0)
    df['CostPerPoundMile'] = df['FreightCost_USD'] / (df['LoadWeight_lbs'] * df['Distance_Miles'])
    df['Speed'] = df['Distance_Miles'] / df['DeliveryTime_hrs']  # mph
    df['OnTime'] = np.where(df['DeliveryStatus'] == 'Delivered', 1, 0)
    df['MilesPerHour'] = df['Distance_Miles'] / df['DeliveryTime_hrs']
    df['StopsPerDay'] = 24 / df['DeliveryTime_hrs']  # Theoretical max if working 24h
    df['FuelEfficiency'] = df['Distance_Miles'] / (df['FuelCost_USD'] / df['Diesel_Price'].astype(float))  # MPG assuming $3.50/gallon
    return df

# *************************************************************************************************************
# *******************************  Carrier Analysis ***********************************************************
# *************************************************************************************************************

def prepare_carrier_stats(df):
    # Calculate on-time rate per carrier
    carrier_stats = df.groupby('CarrierName').agg({
        'DeliveryStatus': lambda x: (x == 'Delivered').sum() / len(x),  # On-time rate
        'FreightCost_USD': 'mean',
        'Distance_Miles': 'median',
        'CostPerMile': 'mean',
        'CostPerPound': 'mean',
        'OnTime': 'count',
    }).rename(columns={
        'DeliveryStatus': 'OnTimeRate',
        'FreightCost_USD': 'AvgFreightCost',
        'Distance_Miles': 'MedianDistance',
        'CostPerMile': 'AvgCostPerMile',
        'CostPerPound': 'AvgCostPerPound',
        'OnTime': 'TotalShipments'
    })

    # Convert to percentage and sort
    carrier_stats['OnTimeRate'] = (carrier_stats['OnTimeRate'] * 100).round(1)
    carrier_stats = carrier_stats.sort_values('OnTimeRate', ascending=False)
    return carrier_stats


def calculate_cost_efficiency(carrier_stats):
    # Sort by cost per mile
    cost_efficiency = carrier_stats.sort_values('AvgCostPerMile')
    # cost_efficiency = cost_efficiency.reset_index()
    return cost_efficiency[['AvgCostPerMile', 'AvgCostPerPound']]


# reliability analysis
def reliability_analysis(carrier_stats):
    # Sort by on-time rate
    reliability = carrier_stats.sort_values('OnTimeRate', ascending=False)
    # reliability = reliability.reset_index()
    return reliability[['OnTimeRate', 'TotalShipments']]


# Calculate on-time rate per carrier
def calculate_ontime_rate(group):
    delivered = (group['DeliveryStatus'] == 'Delivered').sum()
    total = len(group)
    return delivered / total


def run_contingency_analysis(delivery_data):
    carrier_stats = delivery_data.groupby('CarrierName').apply(calculate_ontime_rate, include_groups=False).reset_index(
        name='OnTimeRate').sort_values('OnTimeRate')

    # Identify worst performer
    worst_carrier = carrier_stats.iloc[0]['CarrierName']
    worst_rate = carrier_stats.iloc[0]['OnTimeRate']
    competitors = carrier_stats[carrier_stats['CarrierName'] != worst_carrier]['CarrierName']

    print(f"Carrier with lowest on-time rate: {worst_carrier} ({worst_rate:.1%})")
    print("\nPerforming contingency analysis against competitors:")

    # Prepare contingency tables and run Fisher's Exact Test
    results = []
    for competitor in competitors:
        # Create 2x2 contingency table
        contingency_table = [
            [
                # Competitor delivered
                len(delivery_data[(delivery_data['CarrierName'] == competitor) &
                                  (delivery_data['DeliveryStatus'] == 'Delivered')]),
                # Competitor delayed
                len(delivery_data[(delivery_data['CarrierName'] == competitor) &
                                  (delivery_data['DeliveryStatus'] == 'Delayed')])
            ],
            [
                # Worst carrier delivered
                len(delivery_data[(delivery_data['CarrierName'] == worst_carrier) &
                                  (delivery_data['DeliveryStatus'] == 'Delivered')]),
                # Worst carrier delayed
                len(delivery_data[(delivery_data['CarrierName'] == worst_carrier) &
                                  (delivery_data['DeliveryStatus'] == 'Delayed')])
            ]
        ]

        # Run Fisher's Exact Test
        odds_ratio, p_value = stats.fisher_exact(contingency_table)
        results.append({
            'Competitor': competitor,
            'Odds_Ratio': odds_ratio,
            'P_Value': p_value,
            'Competitor_OnTime': contingency_table[0][0] / (contingency_table[0][0] + contingency_table[0][1]),
            'Worst_Carrier_OnTime': contingency_table[1][0] / (contingency_table[1][0] + contingency_table[1][1])
        })

        print(f"\n{worst_carrier} vs {competitor}:")
        print(pd.DataFrame(contingency_table,
                           index=[competitor, worst_carrier],
                           columns=['Delivered', 'Delayed']))
        print(f"Odds Ratio: {odds_ratio:.2f} (p={p_value:.4f})")

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('Odds_Ratio', ascending=False)
    return results_df, worst_carrier

# *************************************************************************************************************
# *******************************  Driver Analysis ***********************************************************
# *************************************************************************************************************


# Prepare the Data
def prepare_driver_stats(df):
    # Group by driver
    driver_stats = df.groupby('DriverName').agg({
        'Distance_Miles': ['sum', 'mean'],
        'MilesPerHour': 'median',
        'StopsPerDay': 'median',
        'FuelEfficiency': 'median',
        'OnTime': 'mean',
        'FreightCost_USD': 'count'
    }).round(2)

    # Flatten multi-index columns
    driver_stats.columns = ['_'.join(col).strip() for col in driver_stats.columns.values]
    driver_stats = driver_stats.rename(columns={
        'Distance_Miles_sum': 'TotalMiles',
        'Distance_Miles_mean': 'AvgTripLength',
        'MilesPerHour_median': 'MedianSpeed',
        'StopsPerDay_median': 'MedianStopsPerDay',
        'FuelEfficiency_median': 'MedianMPG',
        'OnTime_mean': 'OnTimeRate',
        'FreightCost_USD_count': 'TripCount'
    })

    # Filter drivers with sufficient data (min 5 trips)
    driver_stats = driver_stats[driver_stats['TripCount'] >= 5].sort_values('MedianMPG', ascending=False)
    return driver_stats


# Driver Performance Benchmarking
def benchmark_drivers(driver_stats, driverstat):
    top_drivers = driver_stats.nlargest(3, driverstat)[['MedianMPG', 'MedianSpeed', 'OnTimeRate', 'TotalMiles']]
    bottom_drivers = driver_stats.nsmallest(3, driverstat)[['MedianMPG', 'MedianSpeed', 'OnTimeRate', 'TotalMiles']]

    return top_drivers, bottom_drivers


# Statistical Analysis - Identifying Significant Outlier
def identify_outliers(driver_stats):
    # Z-score analysis for MPG
    driver_stats['MPG_ZScore'] = np.abs(stats.zscore(driver_stats['MedianMPG']))
    mpg_outliers = driver_stats[driver_stats['MPG_ZScore'] > 2]
    return mpg_outliers


def performance_benchmarking(driver_stats, d_stat):
    # performing_drivers = driver_stats.sort_values(d_stat, ascending=True)
    # performing_drivers = performing_drivers.head(1)
    # performing_drivers.reset_index(inplace=True)
    # worstperformance = performing_drivers[d_stat].iloc[0].item()
    # worstdriver = performing_drivers['DriverName'].iloc[0]

    top_drivers, bottom_drivers = benchmark_drivers(driver_stats, d_stat)
    if d_stat == "MedianMPG":
        topmsg = "Best Ranked drivers in function of Miles per gallon (fuel-efficient):"
        botmsg = "the least fuel-efficient drivers and worst Ranked in function of Miles per gallon:"
    elif d_stat == "MedianSpeed":
        topmsg = "Best Ranked drivers in function of driving speed (the fastest drivers):"
        botmsg = "Worst Ranked drivers in function of driving speed (the slowest drivers):"
    elif d_stat == "OnTimeRate":
        topmsg = "Best Ranked drivers in function of ontime rate and completed deliveries (the most reliable drivers):"
        botmsg = "Worst Ranked drivers in function of ontime rate and completed deliveries (the least reliable drivers):"
    elif d_stat == "TotalMiles":
        topmsg = "Best Ranked drivers in function of Total Miles traveled:"
        botmsg = "Worst Ranked drivers in function of Total Miles traveled:"

    topdrivers = [topmsg]
    bottomdrivers = [botmsg]
    i = 1
    for row in top_drivers.itertuples():
        if d_stat == "MedianMPG":
            topdrivers.append(f"- driver {row.Index} achieved fuel-efficient of {row.MedianMPG} and ranked number {i}")
        elif d_stat == "MedianSpeed":
            topdrivers.append(f"- driver {row.Index} Median Speed is {row.MedianSpeed} and ranked number {i}")
        elif d_stat == "OnTimeRate":
            topdrivers.append(f"- driver {row.Index} reliability is {row.OnTimeRate} and ranked number {i}")
        elif d_stat == "TotalMiles":
            topdrivers.append(f"- driver {row.Index} traveled {row.TotalMiles} and ranked number {i}")
        i += 1

    j = len(driver_stats[d_stat])
    for row in bottom_drivers.itertuples():
        if d_stat == "MedianMPG":
            bottomdrivers.append(f"- driver {row.Index} achieved fuel-efficient of {row.MedianMPG} and ranked number {j}")
        elif d_stat == "MedianSpeed":
            bottomdrivers.append(f"- driver {row.Index} Median Speed is {row.MedianSpeed} and ranked number {j}")
        elif d_stat == "OnTimeRate":
            bottomdrivers.append(f"- driver {row.Index} reliability is {row.OnTimeRate} and ranked number {j}")
        elif d_stat == "TotalMiles":
            bottomdrivers.append(f"- driver {row.Index} traveled {row.TotalMiles} ranked number {j}")
        j -= 1
    return topdrivers, bottomdrivers

# *************************************************************************************************************
# *******************************  Routes Analysis ***********************************************************
# *************************************************************************************************************

def prepare_route_stats(df):
    # Group by route (Origin-Destination pairs)
    route_stats = df.groupby(['OriginCity', 'DestinationCity']).agg({
        'Distance_Miles': 'mean',
        'CostPerMile': ['mean', 'std'],
        'CostPerPoundMile': 'mean',
        'Speed': 'median',
        'OnTime': 'mean',
        'FreightCost_USD': 'count'
    }).round(2)

    # Flatten multi-index columns
    route_stats.columns = ['_'.join(col).strip() for col in route_stats.columns.values]
    route_stats = route_stats.rename(columns={
        'Distance_Miles_mean': 'AvgDistance',
        'CostPerMile_mean': 'AvgCostPerMile',
        'CostPerMile_std': 'CostPerMile_StDev',
        'CostPerPoundMile_mean': 'AvgCostPerPoundMile',
        'Speed_median': 'MedianSpeed',
        'OnTime_mean': 'OnTimeRate',
        'FreightCost_USD_count': 'ShipmentCount'
    })

    # Filter routes with sufficient data (min 5 shipments)
    route_stats = route_stats.sort_values('AvgCostPerMile', ascending=False)
    # route_stats = route_stats[route_stats['ShipmentCount'] >= 5].sort_values('AvgCostPerMile', ascending=False)
    return route_stats


# Z-score analysis for cost anomalies
# Action: Investigate root causes for these 2σ outliers.
def analyze_cost_anomalies(routestats):
    routestats['CostZScore'] = np.abs(stats.zscore(routestats['AvgCostPerMile']))
    high_cost_routes = routestats[routestats['CostZScore'] > 2]
    return high_cost_routes


# Predicting Route Costs
def predict_cost(df):

    # Prepare features
    X = df[['Distance_Miles', 'LoadWeight_lbs', 'DeliveryTime_hrs']]
    y = df['TotalCostPerMile']

    # Train model
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = RandomForestRegressor()
    model.fit(X_train, y_train)

    # Identify overpayments
    df['PredictedCost'] = model.predict(X)
    df['CostVariance'] = df['TotalCostPerMile'] - df['PredictedCost']
    df['PredictedTotalCost'] = df['PredictedCost'] * df['Distance_Miles']

    # Flag high-variance routes (Predicted Low cost routes)
    high_variance = df[df['CostVariance'] > 0.035].groupby(
        ['OriginCity', 'DestinationCity']).agg({
            'CostVariance': 'mean',
            'TotalCostPerMile': 'mean',
            'PredictedCost': 'mean',
        }).round(2)

    high_variance = high_variance.sort_values('CostVariance', ascending=False)


    # Flag low-variance routes (Predicted High cost routes)
    low_variance = df[df['CostVariance'] < 0].groupby(
        ['OriginCity', 'DestinationCity']).agg({
            'CostVariance': 'mean',
            'TotalCostPerMile': 'mean',
            'PredictedCost': 'mean',
        }).round(2)

    low_variance = low_variance.sort_values('CostVariance', ascending=True)
    return high_variance, low_variance

@shared_task(name='run_local_analysis')
def run_analysis(dff):
    # Start Local Analysis

    # 1- Load csv to pandas dataframe
    # dff = pd.read_csv(logireport.routefile)

    print("Prepare for cleaning")
    print("****************************************")
    # print("File", logireport.routefile)
    # print(dff.head(5))

    # 2- Prepare data
    df = clean_data(dff)
    df = calculate_kpis(df)
    summary = []
    # *****************************************************************************************************************************
    # 3- Start Carrier Analysis

    # to add to summary
    carrier_stats = prepare_carrier_stats(df)
    summary.append("Carrier performance analysis based on: ontime rate (delivered shipments), "
                   "average freight cost, median distance in miles, average cost per mile "
                   "(FuelCost_USD/Distance_Miles, average cost per pound "
                   "(FreightCost_USD/LoadWeight_lbs), Total Shipments (total delivered):")
    summary.append(carrier_stats.to_markdown())
    summary.append("\n")

    efficient_carriers = calculate_cost_efficiency(carrier_stats)

    # to add to summary
    efficientcarriers = efficient_carriers[['AvgCostPerMile', 'AvgCostPerPound']].to_markdown()
    summary.append("the cost-efficient data table is:")
    summary.append(efficientcarriers)
    summary.append("\n")
    summary.append("The most efficient carrier:")
    efficient_carriers = efficient_carriers.reset_index()
    most_efficient_carriers = efficient_carriers['CarrierName'][0]
    summary.append(most_efficient_carriers)
    summary.append("\n")

    reliable_carriers = reliability_analysis(carrier_stats)

    # to add to summary
    reliablecarriers = reliable_carriers[['OnTimeRate', 'TotalShipments']].to_markdown()
    summary.append("the reliability data table is:")
    summary.append(reliablecarriers)
    summary.append("\n")
    summary.append("The most reliable carrier:")
    reliable_carriers = reliable_carriers.reset_index()
    most_reliable_carriers = reliable_carriers['CarrierName'][0]
    summary.append(most_reliable_carriers)
    summary.append("\n")

    # Visualizations
    # 1. Cost vs. Reliability (Scatter Plot) [ x='AvgFreightCost', y='OnTimeRate', data=carrier_stats ]
    # 2. Cost Distribution (Boxplot)  [ data=df, x='CarrierName', y='CostPerMile' ]

    hcarvar, lcarvar, costreliability_action, contingency_result, contingency_action = prepare_data_report(df)

    summary.append("Contingency table, worst carrier compared to competitors in function of ontime rate:")
    summary.extend(contingency_result)
    summary.append("\n")

    # *****************************************************************************************************************************
    # 4- Start Driver Analysis

    driver_stats = prepare_driver_stats(df)

    # to add to summary
    driverstats = driver_stats.to_markdown()
    summary.append("Driver performance analysis based on: Total Miles, Median MPG, Median Speed, and OnTime Rate ")
    summary.append(driverstats)
    summary.append("\n")

    # to add to summary
    topdrivers = []
    bottomdrivers = []
    for driverstat in ['TotalMiles', 'MedianMPG', 'MedianSpeed', 'OnTimeRate']:
        topdriverss, bottomdriverss = performance_benchmarking(driver_stats, driverstat)
        topdrivers.extend(topdriverss)
        topdrivers.append("\n")
        bottomdrivers.extend(bottomdriverss)
        bottomdrivers.append("\n")

    summary.extend(topdrivers)
    summary.extend(bottomdrivers)
    summary.append("\n")

    mpg_outliers = identify_outliers(driver_stats)
    summary.append("outlier drivers with miles per gallon (MPG) Z-score greater than 2 sigma ")
    summary.append(mpg_outliers.to_markdown())
    summary.append("Recommended Actions: e.g., Recommend eco-driving training for these drivers.")
    summary.append("\n")

    # Action: Recommend eco-driving training for these drivers.

    # Visualizations
    # 1- Driver Efficiency Matrix - scatterplot  (data=driver_stats, x='MedianSpeed', y='MedianMPG')
    # Quadrant Analysis:
    # Top - Right(Ideal): High speed + high efficiency
    # Bottom - Right(Risky): Fast but inefficient
    # Top - Left(Caution): Efficient but slow
    # 2- Driver Performance Distribution - boxplot ( data=df,  x='DriverName', y='MilesPerHour')
    # Which driver has the widest speed variability (potential unsafe driving).

    # *****************************************************************************************************************************
    # 5- Start Route Analysis

    route_stats = prepare_route_stats(df)
    summary.append("Route Efficiency Analysis based on: ontime rate (delivered shipments), "
                   "average cost per mile (FuelCost_USD/Distance_Miles, average distance and others:")
    summary.append(route_stats.to_markdown())
    summary.append("\n")

    high_cost_routes = analyze_cost_anomalies(route_stats)
    summary.append("Z-score analysis for average cost per mile anomalies. identify routes with z-score > 2:")
    summary.append(high_cost_routes[['AvgCostPerMile', 'CostZScore']].to_markdown())
    summary.append("Recommended Actions: e.g., Investigate root causes for these 2σ outliers.")
    summary.append("\n")

    return summary, hcarvar, lcarvar, costreliability_action, contingency_result, contingency_action


    # high_variance, low_variance = predict_cost(df)

    # Visualizations
    # 1- Cost Efficiency Heatmap (data=route_stats, columns='DestinationCity', values='AvgCostPerMile', title=Route Cost Efficiency Heatmap)
    # 2- Speed vs. Cost Bubble Chart - scatterplot (data=route_stats, x='MedianSpeed', y='AvgCostPerMile', title='Route Efficiency: Speed vs. Cost')


def process_route_info(ds):
    distance = []
    fuelcost = []
    loadweight = []
    deliveryhrs = []
    freightcost = []

    for index, row in ds.iterrows():
        distance.append(row['Distance_Miles'].item())
        fuelcost.append(row['FuelCost_USD'].item())
        loadweight.append(row['LoadWeight_lbs'].item())
        deliveryhrs.append(row['DeliveryTime_hrs'].item())
        freightcost.append(row['FreightCost_USD'].item())

    distance_str = f"Distance: count: {distance[0]} - Average: {distance[1]} - Min: {distance[3]} - Max {distance[7]}"
    fuelcost_str = f"FuelCost: count: {fuelcost[0]} - Average: {fuelcost[1]} - Min: {fuelcost[3]} - Max {fuelcost[7]}"
    loadweight_str = f"LoadWeight: count: {loadweight[0]} - Average: {loadweight[1]} - Min: {loadweight[3]} - Max {loadweight[7]}"
    deliveryhrs_str = f"DeliveryHrs: count: {deliveryhrs[0]} - Average: {deliveryhrs[1]} - Min: {deliveryhrs[3]} - Max {deliveryhrs[7]}"

    return distance_str, fuelcost_str, loadweight_str, deliveryhrs_str


def summarize_df_for_prompt(df: pd.DataFrame, max_rows: int = 10) -> str:
    """Compact summary to control tokens in prompt while preserving signal."""
    contingency_matrix = ["contingency analysis based on on time deliveries rate: "]
    cols = ", ".join(df.columns.astype(str).tolist())

    info = {
        "rows": len(df),
        "columns": len(df.columns),
    }
    # Summary of kpis
    df_clean = df[df['DeliveryStatus'].isin(['Delivered', 'Delayed'])]
    df_clean = calculate_kpis(df_clean)
    sample = df_clean.head(max_rows).to_csv(index=False)
    carrier_stats = prepare_carrier_stats(df_clean)
    driver_stats = prepare_driver_stats(df_clean).reset_index().to_csv(index=False)
    route_stats = prepare_route_stats(df_clean).reset_index()
    best_routes = route_stats.tail(3)
    worst_routes = route_stats.head(3)
    best_routes = best_routes[['AvgDistance', 'AvgCostPerMile', 'OnTimeRate']].to_csv(index=False)
    worst_routes = worst_routes[['AvgDistance', 'AvgCostPerMile', 'OnTimeRate']].to_csv(index=False)
    cost_efficiency = calculate_cost_efficiency(carrier_stats).head(1)
    cost_efficiency = cost_efficiency[['AvgCostPerMile', 'AvgCostPerPound']].to_markdown()
    reliability = reliability_analysis(carrier_stats).head(1)
    reliability = reliability[['OnTimeRate', 'TotalShipments']].to_markdown()
    carrier_stats = carrier_stats.to_csv(index=False)
    results_df, worst_carrier = run_contingency_analysis(df_clean)


    for idx, row in results_df.iterrows():
        print("contingency_matrix:", contingency_matrix)
        competitor = row['Competitor']
        odds_ratio = row['Odds_Ratio']
        # p_value = row['P_Value']
        contingency_matrix.append(f"{competitor} is {odds_ratio:.2f}x to deliver on time than {worst_carrier}")

    return (
        f"Columns: {cols}\n"
        f"Shape: rows={len(df_clean)}, cols={info['columns']}\n"
        f"Sample (first {max_rows} rows):\n{sample}"
        f"carriers kpis: {carrier_stats}\n"
        f"Drivers kpis: {driver_stats}\n"
        f"Best Routes in terms of average cost per mile: {best_routes}"
        f"Worst Routes in terms of average cost per mile: {worst_routes}"
        f"most efficient carrier: {cost_efficiency}\n"
        f"Most Reliable Carrier: {reliability}\n"
        f"Carrier with lowest on-time rate: {worst_carrier}"
        f"{contingency_matrix}"
    )


def read_csv_into_text_and_df(file_obj) -> tuple[str, pd.DataFrame]:
    data = file_obj.read()
    # Reset pointer for safety if needed
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    # df = pd.read_csv(io.BytesIO(data))
    # also return as plain text for prompt
    csv_text = data.decode("utf-8", errors="ignore")
    return csv_text


# @shared_task(name='run_llm_analysis')
def run_LLM_analysis(flags, summary_for_prompt, client_name):

    user_prompt = f"""
                                Analyze freight route data for client: {client_name}.

                                Objective:
                                - Executive-ready Fleet Efficiency Report with BI charts, KPIs, and actionable recommendations.
                                - Include city/state already normalized in the data.

                                Data notes:
                                - The dataset is already cleaned to 'City, ST' format for origins/destinations.
                                - Potential data issues flagged by preprocessing are provided below.
                                - only delivered and delayed shipments are considered for calculations. In-Transit cannot be used as we don't know if they will late or on time

                                Preprocessing flags:
                                {flags}

                                Dataset (compact summary for analysis):
                                {summary_for_prompt}

                                Output:
                                - STRICTLY return a single JSON object matching the provided schema.
                                - Include Chart.js-ready configs in summary_json.charts[].config (full chart config).
                                """
    # if not report.report_prompt:
    #     report.report_prompt = user_prompt

    print("user_prompt: ", user_prompt)

    # Call Responses API with JSON schema enforcement

    resp = client.responses.create(model="gpt-4.1",
                                   temperature=0.2,
                                   max_output_tokens=3500,
                                   text={"format": {"type": "json_schema", "name": "freight_bi_dual_output",
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
                                                                                "value": {"type": ["string", "number"]},
                                                                                "note": {"type": "string"}
                                                                            },
                                                                            "required": ["metric", "value", "note"],
                                                                            "additionalProperties": False,
                                                                        }
                                                                    },
                                                                    "charts": {
                                                                        "type": "array",
                                                                        "items": {
                                                                            "type": "object",
                                                                            "properties": {
                                                                                "title": {"type": "string"},
                                                                                "type": {"type": "string"},
                                                                                # bar|line|pie|scatter
                                                                                "config": {
                                                                                    "type": "object",
                                                                                    "properties": {
                                                                                        "type": {"type": "string"},
                                                                                        "data": {"type": "string"},
                                                                                        "options": {"type": "string"},
                                                                                    },
                                                                                    "required": ["type", "data",
                                                                                                 "options"],
                                                                                    "additionalProperties": False,

                                                                                }
                                                                                # Full Chart.js config: {type,data,options}
                                                                            },
                                                                            "required": ["title", "type", "config"],
                                                                            "additionalProperties": False,
                                                                        }
                                                                    },
                                                                    "data_quality": {
                                                                        "type": "object",
                                                                        "properties": {
                                                                            "flags": {"type": "array",
                                                                                      "items": {"type": "string"}}
                                                                        },
                                                                        "required": ["flags"],
                                                                        "additionalProperties": False,
                                                                    },
                                                                    "recommendations": {
                                                                        "type": "array",
                                                                        "items": {"type": "string"}
                                                                    }
                                                                },
                                                                "required": ["client", "kpis", "charts", "data_quality",
                                                                             "recommendations"],
                                                                "additionalProperties": False,
                                                            }
                                                        },
                                                        "required": ["markdown_report", "summary_json"],
                                                        "additionalProperties": False,
                                                    },
                                                    # "strict": True,
                                                    }},
                                   input=[
                                       {"role": "system", "content": SYSTEM_PROMPT},
                                       {"role": "user", "content": user_prompt}], )
    try:
        raw = resp.output_text
    except Exception:
        # Fallback: dig into content structure
        raw = ""
        if hasattr(resp, "output") and resp.output:
            # collect all text parts
            for blk in resp.output:
                if hasattr(blk, "content"):
                    for c in blk.content:
                        if getattr(c, "type", "") == "output_text":
                            raw += c.text

    return raw


def run_carrier_analysis(flags, carrier_stats, client_name):
    summary_for_prompt = carrier_stats

    user_prompt = f"""
                                    Analyze freight route data for client: {client_name}.
    
                                    Objective:
                                    - Executive-ready Fleet Efficiency Report KPIs, and actionable recommendations.
                                    
                                    Data notes:
                                    - The dataset represent a summary of carriers performance Comparative Table with some kpis
                                    
                                    Preprocessing flags:
                                    {flags}
    
                                    Dataset (compact summary for analysis):
                                    {summary_for_prompt}
                                    """

    # Call Responses API with JSON schema enforcement
    resp = client.responses.create(model="gpt-4.1",
                                   temperature=0.2,
                                   max_output_tokens=3500,

                                   input=[
                                       {"role": "system", "content": carrier_system_prompt},
                                       {"role": "user", "content": user_prompt}], )
    try:
        raw = resp.output_text
    except Exception:
        # Fallback: dig into content structure
        raw = ""
        if hasattr(resp, "output") and resp.output:
            # collect all text parts
            for blk in resp.output:
                if hasattr(blk, "content"):
                    for c in blk.content:
                        if getattr(c, "type", "") == "output_text":
                            raw += c.text

    return raw


def run_driver_analysis(flags, driver_stats, client_name):

    user_prompt = f"""
                        Analyze freight route data for client: {client_name}.

                        Objective:
                        - Executive-ready Fleet Efficiency Report KPIs, and actionable recommendations.

                        Data notes:
                        - The dataset represent a summary of drivers performance Comparative Table with some kpis

                        Preprocessing flags:
                        {flags}

                        Dataset (compact summary for analysis):
                        {driver_stats}
                        """

    # Call Responses API with JSON schema enforcement
    resp = client.responses.create(model="gpt-4.1",
                                   temperature=0.2,
                                   max_output_tokens=3500,

                                   input=[
                                       {"role": "system", "content": driver_system_prompt},
                                       {"role": "user", "content": user_prompt}], )
    try:
        raw = resp.output_text
    except Exception:
        # Fallback: dig into content structure
        raw = ""
        if hasattr(resp, "output") and resp.output:
            # collect all text parts
            for blk in resp.output:
                if hasattr(blk, "content"):
                    for c in blk.content:
                        if getattr(c, "type", "") == "output_text":
                            raw += c.text


    return raw


def run_route_analysis(flags, route_stats, client_name):

    summary_for_prompt = route_stats

    user_prompt = f"""
                                    Analyze freight route data for client: {client_name}.

                                    Objective:
                                    - Executive-ready Fleet Efficiency Report KPIs, and actionable recommendations.

                                    Data notes:
                                    - The dataset represent a summary of routes performance Comparative Table with some kpis

                                    Preprocessing flags:
                                    {flags}

                                    Dataset (compact summary for analysis):
                                    {summary_for_prompt}
                                    """

    # Call Responses API with JSON schema enforcement
    resp = client.responses.create(model="gpt-4.1",
                                   temperature=0.2,
                                   max_output_tokens=3500,

                                   input=[
                                       {"role": "system", "content": route_system_prompt},
                                       {"role": "user", "content": user_prompt}], )
    try:
        raw = resp.output_text
    except Exception:
        # Fallback: dig into content structure
        raw = ""
        if hasattr(resp, "output") and resp.output:
            # collect all text parts
            for blk in resp.output:
                if hasattr(blk, "content"):
                    for c in blk.content:
                        if getattr(c, "type", "") == "output_text":
                            raw += c.text

    return raw


@shared_task(name='run_all_llm_analysis')
def run_All_LLM_Analysis():
    reports = LogiflexReport.objects.filter(report_text={},
                                            report_status__in=['processing', 'late'],
                                            report_approved=False).select_related("client")
    print("Reports to be analyzed", reports.count())
    # print(reports.count())
    numreports = reports.count()
    if reports:
        for report in reports:
            log = LogEntry.objects.filter(report=report).first()
            flags = ""
            if log:
                flags = json.dumps(log.flags, indent=2)
            if report.report_type == "lite":
                # Check file extension
                extension_ok = True
                if report.routefile_ext == ".csv":
                    df = pd.read_csv(report.routefile)
                elif report.routefile_ext == ".xlsx" or report.routefile_ext == ".xls":
                    df = pd.read_excel(report.routefile)
                else:
                    extension_ok = False
                if extension_ok:
                    summary_for_prompt = summarize_df_for_prompt(df, max_rows=10)
                    raw = run_LLM_analysis(flags, summary_for_prompt, report.client.company)
                    report.report_text = raw
                    report.report_status = "download"
                    report.report_date = datetime.now()
                    report.save()
            elif report.report_type == "advanced":

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
                    # Carrier Analysis
                    carrier_stats = prepare_carrier_stats(df)
                    driver_stats = prepare_driver_stats(df)
                    route_stats = prepare_route_stats(df)
                    report.report_carrier = run_carrier_analysis(flags, carrier_stats, report.client.company)
                    report.report_driver = run_driver_analysis(flags, driver_stats, report.client.company)
                    report.report_route = run_route_analysis(flags, route_stats, report.client.company)
                    report.report_status = "download"
                    report.report_date = datetime.now()
                    report.save()
            # raw = asynch_preprocess.get()
            numreports = reports.count()
    else:
        numreports = 0
    return f"{numreports} are processed"


def prepare_data_report(df):

    # Carrier Contingency Analysis
    results_df, worst_carrier = run_contingency_analysis(df)
    costreliability_action = []
    contingency_result = []
    contingency_action = []
    for idx, row in results_df.iterrows():
        competitor = row['Competitor']
        odds_ratio = row['Odds_Ratio']
        p_value = row['P_Value']
        contingency_result.append(
            f"<strong class='comp'>{competitor}</strong> is <strong class='odds'>{odds_ratio:.2f}x</strong> to deliver on time than <strong class='worst'>{worst_carrier}</strong>")
    print("Result number of competitors", results_df['Competitor'].count())
    if results_df['Competitor'].count() >= 2:
        contingency_action.append(f"Move some of the Shipments from <strong class='worst'>{worst_carrier}</strong> to <strong class='comp'>{results_df.iloc[0]['Competitor']}</strong> and <strong class='comp'>{results_df.iloc[1]['Competitor']}</strong>")
    elif results_df['Competitor'].count() == 1:
        contingency_action.append(f"Move some of the Shipments from <strong class='worst'>{worst_carrier}</strong> to <strong class='comp'>{results_df.iloc[0]['Competitor']}</strong>")

    # Carrier Reliability Vs Cost Analysis
    q3 = df.groupby('CarrierName')['CostPerMile'].quantile(0.75).reset_index()
    q1 = df.groupby('CarrierName')['CostPerMile'].quantile(0.25).reset_index()
    median = df.groupby('CarrierName')['CostPerMile'].median().reset_index()
    q3m = q3['CostPerMile'] - median['CostPerMile']
    mq1 = median['CostPerMile'] - q1['CostPerMile']
    giqr = abs(q3m - mq1)
    hcar = q3.iloc[giqr.idxmax()]['CarrierName']
    lcar = q3.iloc[giqr.idxmin()]['CarrierName']
    hcarvar = f"<strong class='comp'>{hcar}</strong> has the widest cost variance (high risk due to volatility)"
    lcarvar = f"<strong class='comp'>{lcar}</strong> has more consistent cost variance"

    iqr = q3['CostPerMile'] - q1['CostPerMile']
    min_iqr_index = iqr.idxmin()
    lowiqr = q3.iloc[min_iqr_index]['CarrierName']

    costreliability_action.append(f"Negotiate consistent rates with <strong class='comp'>{hcar}</strong>")
    costreliability_action.append(f"Shift more Shipments to <strong class='comp'>{lowiqr}</strong> If the goal is better predictability & cost stability.")


    return hcarvar, lcarvar, costreliability_action, contingency_result, contingency_action


def prepare_driver_analysis(driver_stats):
    # driver_stats = prepare_driver_stats(df).reset_index()
    mpgmean = driver_stats['MedianMPG'].mean()
    ontimemean = driver_stats['OnTimeRate'].mean()
    mphmean = driver_stats['MedianSpeed'].mean()

    hhh = []
    hhl = []
    hll = []
    hlh = []
    lll = []
    llh = []
    lhl = []
    lhh = []
    topleft = []
    bottomright = []
    bottomleft = []
    for index, row in driver_stats.iterrows():
        if row['OnTimeRate'] > ontimemean and row['MedianMPG'] > mpgmean and row['MedianSpeed'] > mphmean:
            hhh.append(index)
        elif row['OnTimeRate'] > ontimemean and row['MedianMPG'] > mpgmean and row['MedianSpeed'] < mphmean:
            hhl.append(index)
        elif row['OnTimeRate'] > ontimemean and row['MedianMPG'] < mpgmean and row['MedianSpeed'] > mphmean:
            hlh.append(index)
        elif row['OnTimeRate'] > ontimemean and row['MedianMPG'] < mpgmean and row['MedianSpeed'] < mphmean:
            hll.append(index)
        elif row['OnTimeRate'] < ontimemean and row['MedianMPG'] < mpgmean and row['MedianSpeed'] > mphmean:
            llh.append(index)
        elif row['OnTimeRate'] < ontimemean and row['MedianMPG'] > mpgmean and row['MedianSpeed'] > mphmean:
            lhh.append(index)
        elif row['OnTimeRate'] < ontimemean and row['MedianMPG'] < mpgmean and row['MedianSpeed'] < mphmean:
            lll.append(index)
        elif row['OnTimeRate'] < ontimemean and row['MedianMPG'] > mpgmean and row['MedianSpeed'] < mphmean:
            lhl.append(index)

    driver_actions = []
    drivers_training = ""

    hhhs = ""
    hhls = ""
    hlls = ""
    hlhs = ""
    llls = ""
    llhs = ""
    lhls = ""
    lhhs = ""
    driver_messages = []
    driver_extended_message = []
    if hhh:
        drivers = ""
        i = 0
        for driver in hhh:
            drivers += driver
            i = i + 1
            if i < len(hhh):
                drivers += ", "
        hhhs = f"<strong class='comp'>{drivers}</strong>: Reliable, Efficient, AND Fast"
        driver_messages.append(hhhs)
        driver_extended_message.append({'ref': 'hhhs', 'msg': hhhs, 'extmsg': elite})

    if hhl:
        drivers = ""
        i = 0
        for driver in hhl:
            drivers += driver
            i = i + 1
            if i < len(hhl):
                drivers += ", "
        hhls = f"<strong class='comp'>{drivers}</strong>:  Methodical, Cautious, and Process-Oriented."
        driver_messages.append(hhls)
        driver_extended_message.append({'ref': 'hhls', 'msg': hhls, 'extmsg': steady_turtle})

    if hlh:
        drivers = ""
        i = 0
        for driver in hlh:
            drivers += driver
            i = i + 1
            if i < len(hlh):
                drivers += ", "
        hlhs = f"<strong class='bottom'>{drivers}</strong>: Effective but Brutally Inefficient"
        driver_actions.append(f"<strong class='bottom'>{drivers}</strong>: Coaching, Not Punishment and Eco-Driving Training.")
        driver_messages.append(hlhs)
        driver_extended_message.append({'ref': 'hlhs', 'msg': hlhs, 'extmsg': stremroller})

    if hll:
        drivers = ""
        i = 0
        for driver in hll:
            drivers += driver
            i = i + 1
            if i < len(hll):
                drivers += ", "
        hlls = f"<strong class='bottom'>{drivers}</strong>: High Reliability but Slow & Low Efficiency"
        drivers_training = drivers + ", "
        driver_messages.append(hlls)
        driver_extended_message.append({'ref': 'hlls', 'msg': hlls, 'extmsg': crawler})

    if lhh:
        drivers = ""
        i = 0
        for driver in lhh:
            drivers += driver
            i = i + 1
            if i < len(lhh):
                drivers += ", "
        lhhs = f"<strong class='bottom'>{drivers}</strong>: Strong Technical driving skills at the Cost of Low Reliability"
        driver_actions.append(f"<strong class='bottom'>{drivers}</strong>: must get targeted coaching focused on route compliance and smooth driving techniques.")
        driver_messages.append(lhhs)
        driver_extended_message.append({'ref': 'lhhs', 'msg': lhhs, 'extmsg': cowboy})

    if lhl:
        drivers = ""
        i = 0
        for driver in lhl:
            drivers += driver
            i = i + 1
            if i < len(lhl):
                drivers += ", "
        lhls = f"<strong class='bottom'>{drivers}</strong>: Efficient but Slow & Unreliable"
        drivers_training = drivers + ", "
        driver_messages.append(lhls)
        driver_extended_message.append({'ref': 'lhls', 'msg': lhls, 'extmsg': inconsistent_miler})

    if llh:
        drivers = ""
        i = 0
        for driver in llh:
            drivers += driver
            i = i + 1
            if i < len(llh):
                drivers += ", "
        llhs = f"<strong class='bottom'>{drivers}</strong>: Aggressive and Impatient, Disregarding Safety, Procedures, and Fuel Economy."
        drivers_training = drivers + ", "
        driver_actions.append(f"<strong class='bottom'>{drivers}</strong>: Immediate Intervention, Retraining Mandatory.")
        driver_messages.append(llhs)
        driver_extended_message.append({'ref': 'llhs', 'msg': llhs, 'extmsg': reckless_rocket})

    if lll:
        drivers = ""
        i = 0
        for driver in lll:
            drivers += driver
            i = i + 1
            if i < len(lll):
                drivers += ", "
        llls = f"<strong class='bottom'>{drivers}</strong>: Disengaged, Poorly Trained, or Facing Significant External Challenges"
        drivers_training = drivers + ", "
        driver_actions.append(f"<strong class='bottom'>{drivers}</strong>: Immediate and Severe Intervention.")
        driver_messages.append(llls)
        driver_extended_message.append({'ref': 'llls', 'msg': llls, 'extmsg': underperformer})

        # driver_actions.append(f"Recommend Eco-Driving training for these drivers: <strong class='worst'>{drivers_training}</strong>")
        driver_actions.append(f"Check Trucks' Mechanical state, Fuel Quality and Scheduled Maintenance.")

    return driver_messages, driver_actions, driver_extended_message


def prepare_driver_costvariance(df):
    costreliability_action = []

    q3 = df.groupby('DriverName')['CostPerMile'].quantile(0.75).reset_index()
    q1 = df.groupby('DriverName')['CostPerMile'].quantile(0.25).reset_index()
    median = df.groupby('DriverName')['CostPerMile'].median().reset_index()
    q3m = q3['CostPerMile'] - median['CostPerMile']
    mq1 = median['CostPerMile'] - q1['CostPerMile']
    giqr = abs(q3m - mq1)
    hcar = q3.iloc[giqr.idxmax()]['DriverName']
    lcar = q3.iloc[giqr.idxmin()]['DriverName']
    hcarvar = f"<strong class='comp'>{hcar}</strong> has the widest cost variance (high risk due to volatility)"
    lcarvar = f"<strong class='comp'>{lcar}</strong> has more consistent cost variance"

    iqr = q3['CostPerMile'] - q1['CostPerMile']
    min_iqr_index = iqr.idxmin()
    lowiqr = q3.iloc[min_iqr_index]['DriverName']

    costreliability_action.append(f"Focus on Training(Eco-driving techniques, Route optimization, Vehicle maintenance awareness), Investigate Underlying Causes (Vehicle Assignment,Route Difficulty, Cargo Load) for  <strong class='comp'>{hcar}</strong>")
    costreliability_action.append(f"<strong class='comp'>{lowiqr}</strong> performance is the benchmark for the group. Recognize and Replicate Good Performance")

    return hcarvar, lcarvar, costreliability_action