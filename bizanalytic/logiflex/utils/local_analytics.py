import pandas as pd
import numpy as np
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import json

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
    df['FuelEfficiency'] = df['Distance_Miles'] / (df['FuelCost_USD'] / 3.50)  # MPG assuming $3.50/gallon
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

    results_df, worst_carrier = run_contingency_analysis(df)

    # to add to summary
    contingency_result = []

    for idx, row in results_df.iterrows():
        competitor = row['Competitor']
        odds_ratio = row['Odds_Ratio']
        p_value = row['P_Value']
        contingency_result.append(
            f"{competitor} is {odds_ratio:.2f}x to deliver on time than {worst_carrier} (p={p_value:.4f})")

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

    return summary


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


def summarize_df_for_prompt(df: pd.DataFrame, max_rows: int = 20) -> str:
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
    driver_stats = prepare_driver_stats(df_clean).to_markdown()
    route_stats = prepare_route_stats(df_clean).to_markdown()
    cost_efficiency = calculate_cost_efficiency(carrier_stats).head(1)
    cost_efficiency = cost_efficiency[['AvgCostPerMile', 'AvgCostPerPound']].to_markdown()
    reliability = reliability_analysis(carrier_stats).head(1)
    reliability = reliability[['OnTimeRate', 'TotalShipments']].to_markdown()
    carrier_stats = carrier_stats.to_markdown()
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
        f"carriers stats: {carrier_stats}"
        f"Drivers stats: {driver_stats}"
        f"Routes Stats: {route_stats}"
        f"most efficient carrier: {cost_efficiency}"
        f"Most Reliable Carrier: {reliability}"
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

