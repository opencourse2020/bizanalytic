import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from typing import Dict, List, Tuple, Optional, Union
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
import re
from datetime import datetime, date
import warnings

warnings.filterwarnings('ignore')


class ColumnValidator(BaseEstimator, TransformerMixin):
    """Custom transformer to validate and intelligently correct column labels"""

    def __init__(self, similarity_threshold=0.6):
        # Expected columns based on the provided CSV file
        self.expected_columns = [
            'ShipmentID', 'Date', 'OriginCity', 'DestinationCity',
            'Distance_Miles', 'FuelCost_USD', 'DriverName', 'CarrierName',
            'LoadWeight_lbs', 'DeliveryStatus', 'DeliveryTime_hrs', 'FreightCost_USD'
        ]

        # Alternative names and common variations for each column
        self.column_aliases = {
            'ShipmentID': ['shipment_id', 'shipmentid', 'shipment_number', 'shipment_no',
                           'ship_id', 'tracking_id', 'order_id', 'id', 'shipment'],
            'Date': ['date', 'shipment_date', 'ship_date', 'delivery_date', 'timestamp',
                     'created_date', 'order_date', 'pickup_date'],
            'OriginCity': ['origin_city', 'origincity', 'origin', 'pickup_city', 'source_city',
                           'from_city', 'departure_city', 'start_city', 'pickup_location'],
            'DestinationCity': ['destination_city', 'destinationcity', 'destination', 'delivery_city',
                                'target_city', 'to_city', 'arrival_city', 'end_city', 'delivery_location'],
            'Distance_Miles': ['distance_miles', 'distance', 'miles', 'total_distance', 'route_distance',
                               'travel_distance', 'trip_distance', 'mileage'],
            'FuelCost_USD': ['fuel_cost_usd', 'fuel_cost', 'fuelcost', 'gas_cost', 'fuel_expense',
                             'fuel_price', 'gas_expense', 'fuel_charges'],
            'DriverName': ['driver_name', 'drivername', 'driver', 'operator', 'trucker',
                           'driver_id', 'operator_name', 'pilot'],
            'CarrierName': ['carrier_name', 'carriername', 'carrier', 'company', 'transport_company',
                            'shipping_company', 'logistics_company', 'freight_company', 'vendor'],
            'LoadWeight_lbs': ['load_weight_lbs', 'loadweight', 'weight', 'cargo_weight', 'freight_weight',
                               'payload', 'load_weight', 'shipment_weight', 'total_weight'],
            'DeliveryStatus': ['delivery_status', 'deliverystatus', 'status', 'shipment_status',
                               'order_status', 'tracking_status', 'current_status', 'state'],
            'DeliveryTime_hrs': ['delivery_time_hrs', 'delivery_time', 'deliverytime', 'travel_time',
                                 'transit_time', 'trip_time', 'duration', 'time_hours', 'elapsed_time'],
            'FreightCost_USD': ['freight_cost_usd', 'freight_cost', 'freightcost', 'shipping_cost',
                                'transport_cost', 'delivery_cost', 'logistics_cost', 'total_cost', 'charge']
        }

        # Expected data types for validation
        self.expected_dtypes = {
            'ShipmentID': 'object',
            'Date': 'object',  # Will be converted to datetime later
            'OriginCity': 'object',
            'DestinationCity': 'object',
            'Distance_Miles': 'numeric',
            'FuelCost_USD': 'numeric',
            'DriverName': 'object',
            'CarrierName': 'object',
            'LoadWeight_lbs': 'numeric',
            'DeliveryStatus': 'object',
            'DeliveryTime_hrs': 'numeric',
            'FreightCost_USD': 'numeric'
        }

        # Valid values for categorical columns
        self.valid_delivery_statuses = ['Delivered', 'In-Transit', 'Delayed']
        self.similarity_threshold = similarity_threshold
        self.column_mapping = {}

    def _calculate_similarity(self, str1, str2):
        """Calculate similarity between two strings using multiple methods"""
        from difflib import SequenceMatcher

        # Normalize strings for comparison
        s1 = str1.lower().replace('_', '').replace(' ', '').replace('-', '')
        s2 = str2.lower().replace('_', '').replace(' ', '').replace('-', '')

        # Calculate similarity using SequenceMatcher
        similarity = SequenceMatcher(None, s1, s2).ratio()

        # Bonus for exact substring matches
        if s1 in s2 or s2 in s1:
            similarity += 0.2

        # Bonus for common keywords
        keywords = ['id', 'date', 'city', 'distance', 'cost', 'name', 'weight', 'status', 'time']
        for keyword in keywords:
            if keyword in s1 and keyword in s2:
                similarity += 0.1

        return min(similarity, 1.0)

    def _find_best_match(self, input_column):
        """Find the best matching expected column for an input column"""
        best_match = None
        best_score = 0

        # Check exact matches first (case insensitive)
        for expected_col in self.expected_columns:
            if input_column.lower() == expected_col.lower():
                return expected_col, 1.0

        # Check alias matches
        for expected_col, aliases in self.column_aliases.items():
            for alias in aliases:
                print("alias:", alias)
                print("input_column", input_column.lower())
                if input_column.lower() == alias.lower():
                    return expected_col, 0.95

        # Calculate similarity scores
        for expected_col in self.expected_columns:
            # Direct similarity
            score = self._calculate_similarity(input_column, expected_col)

            # Check against aliases
            for alias in self.column_aliases.get(expected_col, []):
                alias_score = self._calculate_similarity(input_column, alias)
                score = max(score, alias_score)

            if score > best_score:
                best_score = score
                best_match = expected_col

        return best_match, best_score

    def _intelligent_column_mapping(self, input_columns):
        """Create intelligent mapping between input columns and expected columns"""
        mapping = {}
        used_expected_cols = set()
        suggestions = []

        print("🔍 Intelligent Column Matching:")
        print("-" * 50)

        for input_col in input_columns:
            best_match, score = self._find_best_match(input_col)

            if score >= self.similarity_threshold and best_match not in used_expected_cols:
                mapping[input_col] = best_match
                used_expected_cols.add(best_match)

                if score == 1.0:
                    print(f"✅ '{input_col}' → '{best_match}' (exact match)")
                elif score >= 0.95:
                    print(f"✅ '{input_col}' → '{best_match}' (alias match)")
                else:
                    print(f"🔄 '{input_col}' → '{best_match}' (similarity: {score:.2f})")
                    suggestions.append(f"Mapped '{input_col}' to '{best_match}' with {score:.1%} confidence")
            else:
                if best_match in used_expected_cols:
                    print(f"⚠️  '{input_col}' → No mapping ('{best_match}' already used)")
                else:
                    print(f"⚠️  '{input_col}' → No mapping (best match: '{best_match}', score: {score:.2f})")

        # Check for missing expected columns
        missing_expected = set(self.expected_columns) - used_expected_cols
        if missing_expected:
            print(f"\n⚠️  Missing expected columns: {list(missing_expected)}")

        return mapping, suggestions

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_copy = X.copy()
        validation_issues = []

        # Check for missing columns
        missing_columns = set(self.expected_columns) - set(X_copy.columns)
        if missing_columns:
            validation_issues.append(f"Missing columns: {list(missing_columns)}")

        # Check for extra columns
        extra_columns = set(X_copy.columns) - set(self.expected_columns)
        if extra_columns:
            validation_issues.append(f"Unexpected columns found: {list(extra_columns)}")

        # Validate column names (case-sensitive)
        for col in X_copy.columns:
            if col in self.expected_columns:
                # Check data type compatibility
                if col in self.expected_dtypes:
                    expected_type = self.expected_dtypes[col]
                    if expected_type == 'numeric':
                        # Try to convert to numeric, identify non-numeric values
                        try:
                            pd.to_numeric(X_copy[col], errors='raise')
                        except:
                            non_numeric_count = pd.to_numeric(X_copy[col], errors='coerce').isna().sum()
                            if non_numeric_count > 0:
                                validation_issues.append(
                                    f"Column '{col}' contains {non_numeric_count} non-numeric values")

        # Validate DeliveryStatus values
        if 'DeliveryStatus' in X_copy.columns:
            invalid_statuses = set(X_copy['DeliveryStatus'].dropna().unique()) - set(self.valid_delivery_statuses)
            if invalid_statuses:
                validation_issues.append(f"Invalid DeliveryStatus values: {list(invalid_statuses)}")

        # Validate ShipmentID format (should follow SHP#### pattern)
        if 'ShipmentID' in X_copy.columns:
            invalid_shipment_ids = X_copy[~X_copy['ShipmentID'].str.match(r'SHP\d{4}', na=False)]
            if not invalid_shipment_ids.empty:
                validation_issues.append(f"Invalid ShipmentID format found in {len(invalid_shipment_ids)} records")

        # Print validation results
        if validation_issues:
            print("⚠️  COLUMN VALIDATION ISSUES FOUND:")
            for issue in validation_issues:
                print(f"   • {issue}")
            print()
        else:
            print("✓ Column validation passed - all columns match expected structure")

        # Add validation summary to dataframe
        X_copy.attrs['validation_issues'] = validation_issues
        X_copy.attrs['validation_passed'] = len(validation_issues) == 0

        return X_copy

    def get_expected_columns(self):
        """Return list of expected column names"""
        return self.expected_columns.copy()

    def get_column_info(self):
        """Return detailed information about expected columns"""
        info = []
        for col in self.expected_columns:
            dtype = self.expected_dtypes.get(col, 'object')
            info.append({
                'column': col,
                'expected_type': dtype,
                'description': self._get_column_description(col)
            })
        return pd.DataFrame(info)

    def _get_column_description(self, column):
        """Get description for each column"""
        descriptions = {
            'ShipmentID': 'Unique identifier for each shipment (format: SHP####)',
            'Date': 'Shipment date in various formats',
            'OriginCity': 'Origin city and state',
            'DestinationCity': 'Destination city and state',
            'Distance_Miles': 'Distance in miles (numeric)',
            'FuelCost_USD': 'Fuel cost in USD (numeric)',
            'DriverName': 'Name of the driver',
            'CarrierName': 'Name of the carrier company',
            'LoadWeight_lbs': 'Load weight in pounds (numeric)',
            'DeliveryStatus': 'Status: Delivered, In-Transit, or Delayed',
            'DeliveryTime_hrs': 'Delivery time in hours (numeric)',
            'FreightCost_USD': 'Freight cost in USD (numeric)'
        }
        return descriptions.get(column, 'No description available')


class DateCleaner(BaseEstimator, TransformerMixin):
    """Custom transformer to clean and standardize date formats"""

    def __init__(self, date_column='Date'):
        self.date_column = date_column

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_copy = X.copy()

        def parse_date(date_str):
            if pd.isna(date_str):
                return pd.NaT

            date_str = str(date_str).strip()

            # Handle different date formats
            formats = [
                '%Y-%m-%d',  # 2025-07-01
                '%m-%d-%Y',  # 07-01-2025
                '%Y/%m/%d',  # 2025/07/01
                '%m/%d/%Y'  # 07/01/2025
            ]

            for fmt in formats:
                try:
                    return pd.to_datetime(date_str, format=fmt)
                except:
                    continue

            # Try general parsing as fallback
            try:
                return pd.to_datetime(date_str)
            except:
                return pd.NaT

        X_copy[self.date_column] = X_copy[self.date_column].apply(parse_date)
        return X_copy


class LocationCleaner(BaseEstimator, TransformerMixin):
    """Custom transformer to clean and standardize location data"""

    def __init__(self, location_columns=['OriginCity', 'DestinationCity']):
        self.location_columns = location_columns

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_copy = X.copy()

        def clean_location(location_str):
            if pd.isna(location_str):
                return location_str

            location_str = str(location_str).strip()

            # Remove extra quotes
            location_str = location_str.strip('"\'')

            # Standardize state abbreviations and city formats
            city_state_mapping = {
                'Austin': 'Austin, TX',
                'Dallas': 'Dallas, TX',
                'Houston': 'Houston, TX',
                'Tulsa': 'Tulsa, OK',
                'San Antonio': 'San Antonio, TX'
            }

            if location_str in city_state_mapping:
                return city_state_mapping[location_str]

            return location_str

        for col in self.location_columns:
            if col in X_copy.columns:
                X_copy[col] = X_copy[col].apply(clean_location)

        return X_copy


class CarrierNameCleaner(BaseEstimator, TransformerMixin):
    """Custom transformer to standardize carrier names"""

    def __init__(self, carrier_column='CarrierName'):
        self.carrier_column = carrier_column

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_copy = X.copy()

        def clean_carrier_name(name):
            if pd.isna(name):
                return name

            name = str(name).strip()

            # Standardize common carrier name variations
            carrier_mapping = {
                'ABC': 'ABC Carriers',
                'DEF': 'DEF Logistics',
                'GHI': 'GHI Transport',
                'XYZ': 'XYZ Freight'
            }

            if name in carrier_mapping:
                return carrier_mapping[name]

            return name

        X_copy[self.carrier_column] = X_copy[self.carrier_column].apply(clean_carrier_name)
        return X_copy


class OutlierDetector(BaseEstimator, TransformerMixin):
    """Custom transformer to detect and handle outliers using IQR method"""

    def __init__(self, columns=None, method='cap', threshold=1.5):
        self.columns = columns
        self.method = method  # 'cap', 'remove', or 'flag'
        self.threshold = threshold
        self.bounds = {}

    def fit(self, X, y=None):
        if self.columns is None:
            # Auto-detect numeric columns
            self.columns = X.select_dtypes(include=[np.number]).columns.tolist()

        for col in self.columns:
            if col in X.columns:
                Q1 = X[col].quantile(0.25)
                Q3 = X[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - self.threshold * IQR
                upper_bound = Q3 + self.threshold * IQR
                self.bounds[col] = (lower_bound, upper_bound)

        return self

    def transform(self, X):
        X_copy = X.copy()

        for col in self.columns:
            if col in X_copy.columns and col in self.bounds:
                lower_bound, upper_bound = self.bounds[col]

                if self.method == 'cap':
                    X_copy[col] = X_copy[col].clip(lower=lower_bound, upper=upper_bound)
                elif self.method == 'flag':
                    X_copy[f'{col}_outlier'] = (
                            (X_copy[col] < lower_bound) |
                            (X_copy[col] > upper_bound)
                    )

        return X_copy


class DataValidator(BaseEstimator, TransformerMixin):
    """Custom transformer to validate data consistency and business rules"""

    def __init__(self):
        pass

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_copy = X.copy()

        # Add validation flags
        X_copy['data_quality_issues'] = 0

        # Check for negative values where they shouldn't exist
        negative_cols = ['Distance_Miles', 'FuelCost_USD', 'LoadWeight_lbs',
                         'DeliveryTime_hrs', 'FreightCost_USD']
        for col in negative_cols:
            if col in X_copy.columns:
                mask = X_copy[col] < 0
                X_copy.loc[mask, 'data_quality_issues'] += 1
                X_copy.loc[mask, col] = np.abs(X_copy.loc[mask, col])  # Fix negative values

        # Check for unrealistic delivery times (> 24 hours for these distances)
        if 'DeliveryTime_hrs' in X_copy.columns:
            unrealistic_time = X_copy['DeliveryTime_hrs'] > 24
            X_copy.loc[unrealistic_time, 'data_quality_issues'] += 1

        # Check for fuel cost consistency (rough validation)
        if all(col in X_copy.columns for col in ['FuelCost_USD', 'Distance_Miles']):
            fuel_per_mile = X_copy['FuelCost_USD'] / X_copy['Distance_Miles']
            # Flag extremely high or low fuel costs per mile
            fuel_outliers = (fuel_per_mile < 0.1) | (fuel_per_mile > 2.0)
            X_copy.loc[fuel_outliers, 'data_quality_issues'] += 1

        return X_copy


def create_cleaning_pipeline():
    """Create a comprehensive data cleaning pipeline"""

    pipeline = Pipeline([
        ('column_validator', ColumnValidator()),  # Added column validation as first step
        ('date_cleaner', DateCleaner()),
        ('location_cleaner', LocationCleaner()),
        ('carrier_cleaner', CarrierNameCleaner()),
        ('validator', DataValidator()),
        ('outlier_detector', OutlierDetector(
            columns=['Distance_Miles', 'FuelCost_USD', 'LoadWeight_lbs',
                     'DeliveryTime_hrs', 'FreightCost_USD'],
            method='cap'
        ))
    ])

    return pipeline


def validate_file_structure(file_path):
    """Validate file structure and show intelligent column matching"""

    print("=" * 60)
    print("FILE STRUCTURE VALIDATION & INTELLIGENT COLUMN MATCHING")
    print("=" * 60)

    try:
        # Read just the header to check structure
        df_sample = pd.read_csv(file_path, nrows=5)

        # Create validator to check structure and perform intelligent matching
        validator = ColumnValidator()
        validator.fit(df_sample)  # This will create the intelligent mapping

        print(f"\nFile: {file_path}")
        print(f"Detected columns ({len(df_sample.columns)}):")
        for i, col in enumerate(df_sample.columns, 1):
            print(f"  {i:2d}. {col}")

        print(f"\nExpected columns ({len(validator.expected_columns)}):")
        for i, col in enumerate(validator.expected_columns, 1):
            print(f"  {i:2d}. {col}")

        # Show mapping results
        if validator.column_mapping:
            print(f"\n📋 Column Mapping Summary:")
            print(f"   Successful mappings: {len(validator.column_mapping)}")
            mapped_expected = set(validator.column_mapping.values())
            unmapped_expected = set(validator.expected_columns) - mapped_expected
            if unmapped_expected:
                print(f"   Unmapped expected columns: {list(unmapped_expected)}")

        # Calculate success rate
        success_rate = len(validator.column_mapping) / len(validator.expected_columns)
        print(f"\n📊 Mapping Success Rate: {success_rate:.1%}")

        if success_rate >= 0.8:
            print("✅ Excellent column mapping - ready for processing!")
            return True
        elif success_rate >= 0.6:
            print("⚠️  Good column mapping - some manual review recommended")
            return True
        else:
            print("❌ Poor column mapping - manual intervention may be needed")
            return False

    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False


def load_and_clean_data(file_path):
    """Load and clean the freight routes data with enhanced validation"""

    # First, validate file structure
    structure_valid = validate_file_structure(file_path)

    # Load the data
    try:
        df = pd.read_csv(file_path)
        print(f"\n📊 Loaded {len(df)} records with {len(df.columns)} columns")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None

    # Display initial data info
    print(f"\nInitial Data Summary:")
    print(f"Shape: {df.shape}")
    print(f"Missing values per column:")
    missing_summary = df.isnull().sum()
    for col, missing_count in missing_summary.items():
        if missing_count > 0:
            percentage = (missing_count / len(df)) * 100
            print(f"  {col}: {missing_count} ({percentage:.1f}%)")

    if missing_summary.sum() == 0:
        print("  No missing values detected ✓")

    # Create and apply cleaning pipeline
    cleaning_pipeline = create_cleaning_pipeline()

    print(f"\n🔧 Applying cleaning pipeline...")
    try:
        df_cleaned = cleaning_pipeline.fit_transform(df)
        print("✅ Cleaning pipeline completed successfully")

        # Check if validation passed
        if hasattr(df_cleaned, 'attrs'):
            if 'validation_passed' in df_cleaned.attrs and df_cleaned.attrs['validation_passed']:
                print("✅ All validation checks passed")
            elif 'validation_issues' in df_cleaned.attrs:
                print("⚠️  Some validation issues were found but processing continued")

            # Show corrections made
            if 'corrections_made' in df_cleaned.attrs and df_cleaned.attrs['corrections_made']:
                print("🔧 Column corrections applied successfully")

            # Show mapping summary
            if 'column_mapping' in df_cleaned.attrs and df_cleaned.attrs['column_mapping']:
                mapping_count = len(df_cleaned.attrs['column_mapping'])
                print(f"📋 {mapping_count} columns were intelligently mapped")

    except Exception as e:
        print(f"❌ Error in cleaning pipeline: {e}")
        return None

    # Post-cleaning summary
    print(f"\n📈 Cleaned Data Summary:")
    print(f"Shape: {df_cleaned.shape}")

    missing_after = df_cleaned.isnull().sum().sum()
    if missing_after > 0:
        print(f"Missing values after cleaning: {missing_after}")
    else:
        print("No missing values after cleaning ✓")

    # Data quality report
    if 'data_quality_issues' in df_cleaned.columns:
        quality_issues = df_cleaned['data_quality_issues'].sum()
        records_with_issues = (df_cleaned['data_quality_issues'] > 0).sum()
        print(f"\n📋 Data Quality Report:")
        print(f"  Total quality issues detected: {quality_issues}")
        print(f"  Records with issues: {records_with_issues} ({(records_with_issues / len(df_cleaned) * 100):.1f}%)")

    return df_cleaned


def show_column_info():
    """Display detailed information about expected columns"""

    validator = ColumnValidator()
    column_info = validator.get_column_info()

    print("\n" + "=" * 80)
    print("EXPECTED COLUMN STRUCTURE")
    print("=" * 80)

    for _, row in column_info.iterrows():
        print(f"Column: {row['column']}")
        print(f"  Type: {row['expected_type']}")
        print(f"  Description: {row['description']}")
        print()


def generate_data_quality_report(df_original, df_cleaned):
    """Generate a comprehensive data quality report"""

    report = {
        'original_shape': df_original.shape,
        'cleaned_shape': df_cleaned.shape,
        'missing_values_before': df_original.isnull().sum().sum(),
        'missing_values_after': df_cleaned.isnull().sum().sum(),
        'duplicates_before': df_original.duplicated().sum(),
        'duplicates_after': df_cleaned.duplicated().sum()
    }

    print("\n" + "=" * 50)
    print("DATA QUALITY REPORT")
    print("=" * 50)
    print(f"Original Records: {report['original_shape'][0]}")
    print(f"Cleaned Records: {report['cleaned_shape'][0]}")
    print(f"Original Columns: {report['original_shape'][1]}")
    print(f"Cleaned Columns: {report['cleaned_shape'][1]}")
    print(f"Missing Values Removed: {report['missing_values_before'] - report['missing_values_after']}")
    print(f"Duplicate Records: {report['duplicates_before']}")

    # Column-specific analysis
    print(f"\nColumn Analysis:")
    for col in df_original.columns:
        if col in df_cleaned.columns:
            orig_nulls = df_original[col].isnull().sum()
            clean_nulls = df_cleaned[col].isnull().sum()
            print(f"  {col}: {orig_nulls} → {clean_nulls} missing values")

    return report


# Test the ColumnValidator class
def test_column_validator():
    """Test function to verify ColumnValidator works correctly"""
    print("🧪 Testing ColumnValidator...")

    # Create test data with different column names
    test_data = pd.DataFrame({
        'shipment_id': ['SHP0001', 'SHP0002'],
        'pickup_date': ['2025-07-01', '2025-07-02'],
        'pickup_city': ['Austin, TX', 'Dallas, TX'],
        'delivery_city': ['Houston, TX', 'Tulsa, OK'],
        'distance': [300, 400],
        'fuel_cost': [100.50, 150.75]
    })

    # Test the validator
    validator = ColumnValidator()

    try:
        validator.fit(test_data)
        transformed = validator.transform(test_data)
        print("✅ ColumnValidator test passed!")
        print(f"Original columns: {list(test_data.columns)}")
        print(f"Transformed columns: {list(transformed.columns)}")
        return True
    except Exception as e:
        print(f"❌ ColumnValidator test failed: {e}")
        return False


# Example usage
if __name__ == "__main__":

    # Test the validator first
    if test_column_validator():
        print("\n" + "=" * 60)

        # Display expected column structure
        show_column_info()

        # Load and clean the data
        df_cleaned = load_and_clean_data('freight_routes_sample_200.csv')

    if df_cleaned is not None:
        # Display sample of cleaned data
        print(f"\n📋 Sample of cleaned data:")
        print(df_cleaned.head())

        # Show data types after cleaning
        print(f"\n📊 Data types after cleaning:")
        print(df_cleaned.dtypes)

        # Save cleaned data
        df_cleaned.to_csv('freight_routes_cleaned.csv', index=False)
        print(f"\n💾 Cleaned data saved to 'freight_routes_cleaned.csv'")

        # Optional: Create additional features
        if all(col in df_cleaned.columns for col in ['FuelCost_USD', 'Distance_Miles']):
            df_cleaned['fuel_efficiency'] = df_cleaned['FuelCost_USD'] / df_cleaned['Distance_Miles']

        if all(col in df_cleaned.columns for col in ['FreightCost_USD', 'LoadWeight_lbs']):
            df_cleaned['cost_per_pound'] = df_cleaned['FreightCost_USD'] / df_cleaned['LoadWeight_lbs']

        print(f"\n🔧 Additional features created")
        print(f"📏 Final dataset shape: {df_cleaned.shape}")

        # Final validation summary
        print(f"\n" + "=" * 60)
        print("FINAL CLEANING SUMMARY")
        print("=" * 60)
        print(f"✅ Processing completed successfully")
        print(f"📊 Records processed: {len(df_cleaned)}")
        print(f"📈 Columns in final dataset: {len(df_cleaned.columns)}")
        if 'data_quality_issues' in df_cleaned.columns:
            clean_records = (df_cleaned['data_quality_issues'] == 0).sum()
            print(f"🎯 Clean records (no issues): {clean_records} ({(clean_records / len(df_cleaned) * 100):.1f}%)")

    else:
        print("❌ Data cleaning failed. Please check the file and try again.")