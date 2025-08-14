import pandas as pd
import numpy as np
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split


# 1- Cleaning Data
def clean_data(report):
    df = pd.read_csv(report.routefile)
    print(df.head(5))
    print(df.columns)
    # 1- Remove Duplicate ShipmentID
    df.drop_duplicates(subset=['ShipmentID'], inplace=True)

    # 2- Clean and prepare categorical data columns
    # CarrierName
    distinct_CarrierName = df['CarrierName'].unique()
    print("CarrierName")
    print(distinct_CarrierName)

    # DriverName
    distinct_DriverName = df['DriverName'].unique()
    print("DriverName")
    print(distinct_DriverName)

    # DeliveryStatus
    distinct_DeliveryStatus = df['DeliveryStatus'].unique()
    print("DeliveryStatus")
    print(distinct_DeliveryStatus)

    # OriginCity
    distinct_OriginCity = df['OriginCity'].unique()
    print("OriginCity")
    print(distinct_OriginCity)

    # DestinationCity
    distinct_DestinationCity = df['DestinationCity'].unique()
    print("DestinationCity")
    print(distinct_DestinationCity)

    # 3- Clean and prepare Numerical Data columns
    # enfore numerical type on numerical columns
    df['Distance_Miles'] = pd.to_numeric(df['Distance_Miles'], errors='coerce')
    df['LoadWeight_lbs'] = pd.to_numeric(df['LoadWeight_lbs'], errors='coerce')
    df['FuelCost_USD'] = pd.to_numeric(df['FuelCost_USD'], errors='coerce')
    df['FreightCost_USD'] = pd.to_numeric(df['FreightCost_USD'], errors='coerce')
    df['DeliveryTime_hrs'] = pd.to_numeric(df['DeliveryTime_hrs'], errors='coerce')

    # fill in the missing values
    df['Distance_Miles'].fillna(df['Distance_Miles'].mean(), inplace=True)
    df['LoadWeight_lbs'].fillna(df['LoadWeight_lbs'].mean(), inplace=True)
    df['FuelCost_USD'].fillna(df['FuelCost_USD'].mean(), inplace=True)
    df['FreightCost_USD'].fillna(df['FreightCost_USD'].mean(), inplace=True)
    df['DeliveryTime_hrs'].fillna(df['DeliveryTime_hrs'].mean(), inplace=True)

    # 4- Clean and prepare Date Data columns
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Date'].fillna(df['Date'].mode()[0], inplace=True)

    # 5- Remove In-Transit data
    delivery_data = df[df['DeliveryStatus'].isin(['Delivered', 'Delayed'])]
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


