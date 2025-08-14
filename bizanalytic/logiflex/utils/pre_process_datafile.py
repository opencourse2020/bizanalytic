import re
import os
import difflib
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional, Union
from difflib import get_close_matches
import time
from django.conf import settings


staticfolder = settings.STATIC_ROOT

uscities_file = staticfolder + "/assets/sample/major_uscities.csv"
sample_data = staticfolder + "/assets/sample/freight_routes_sample_2001.csv"

class DateValidator:
    def __init__(self):
        # Common date formats to try
        self.date_formats = [
            '%Y-%m-%d',  # 2025-07-01
            '%m/%d/%Y',  # 07/01/2025
            '%d/%m/%Y',  # 01/07/2025
            '%Y/%m/%d',  # 2025/07/01
            '%m-%d-%Y',  # 07-01-2025
            '%d-%m-%Y',  # 01-07-2025
            '%Y%m%d',  # 20250701
            '%m/%d/%y',  # 07/01/25
            '%d/%m/%y',  # 01/07/25
            '%y-%m-%d',  # 25-07-01
            '%b %d, %Y',  # Jul 01, 2025
            '%B %d, %Y',  # July 01, 2025
            '%d %b %Y',  # 01 Jul 2025
            '%d %B %Y',  # 01 July 2025
            '%m-%d-%Y',  # 07-01-2025
            '%d.%m.%Y',  # 01.07.2025
            '%Y.%m.%d',  # 2025.07.01
        ]

        # Regex patterns for date detection
        self.date_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
            r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',  # YYYY/MM/DD
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2}',  # MM/DD/YY or DD/MM/YY
            r'\d{8}',  # YYYYMMDD
            r'\d{1,2}-\d{2}-\d{4}',  # M-DD-YYYY or MM-DD-YYYY
            r'\w{3,9}\s+\d{1,2},?\s+\d{4}',  # Month DD, YYYY
            r'\d{1,2}\s+\w{3,9}\s+\d{4}',  # DD Month YYYY
        ]

    def detect_date_format(self, date_string: str) -> Optional[str]:
        """Try to detect the date format of a given string"""
        date_string = str(date_string).strip()

        for fmt in self.date_formats:
            try:
                datetime.strptime(date_string, fmt)
                return fmt
            except ValueError:
                continue
        return None

    def parse_date(self, date_string: str) -> Tuple[Optional[datetime], Optional[str], str]:
        """
        Parse a date string and return (parsed_date, format_used, status)
        Status can be: 'success', 'invalid', 'empty', 'ambiguous'
        """
        if pd.isna(date_string) or str(date_string).strip() == '':
            return None, None, 'empty'

        date_string = str(date_string).strip()

        # Try each format
        for fmt in self.date_formats:
            try:
                parsed_date = datetime.strptime(date_string, fmt)
                return parsed_date, fmt, 'success'
            except ValueError:
                continue

        # Check if it matches date patterns but couldn't be parsed
        for pattern in self.date_patterns:
            if re.match(pattern, date_string):
                return None, None, 'ambiguous'

        return None, None, 'invalid'

    def validate_date_column(self, date_values: List[Union[str, datetime, date]],
                             column_name: str = 'Date',
                             min_valid_percentage: float = 0.8) -> Dict:
        """
        Validate a column of date values
        Returns comprehensive validation results
        """
        results = {
            'column_name': column_name,
            'total_values': len(date_values),
            'valid_dates': 0,
            'invalid_dates': 0,
            'empty_dates': 0,
            'ambiguous_dates': 0,
            'date_formats_found': {},
            'validation_details': [],
            'issues': [],
            'recommendations': [],
            'is_valid': False,
            'date_range': None,
            'most_common_format': None
        }

        format_counts = {}
        parsed_dates = []

        for i, value in enumerate(date_values):
            parsed_date, format_used, status = self.parse_date(value)

            detail = {
                'index': i,
                'original_value': str(value),
                'parsed_date': parsed_date,
                'format_detected': format_used,
                'status': status
            }

            results['validation_details'].append(detail)

            if status == 'success':
                results['valid_dates'] += 1
                parsed_dates.append(parsed_date)
                format_counts[format_used] = format_counts.get(format_used, 0) + 1
            elif status == 'invalid':
                results['invalid_dates'] += 1
                results['issues'].append(f"Row {i}: Invalid date format '{value}'")
            elif status == 'empty':
                results['empty_dates'] += 1
            elif status == 'ambiguous':
                results['ambiguous_dates'] += 1
                results['issues'].append(f"Row {i}: Ambiguous date format '{value}' - could not parse")

        # Calculate statistics
        total_non_empty = results['total_values'] - results['empty_dates']
        if total_non_empty > 0:
            valid_percentage = results['valid_dates'] / total_non_empty
            results['is_valid'] = valid_percentage >= min_valid_percentage

        # Find most common format
        if format_counts:
            results['most_common_format'] = max(format_counts, key=format_counts.get)
            results['date_formats_found'] = format_counts

        # Calculate date range
        if parsed_dates:
            results['date_range'] = {
                'min_date': min(parsed_dates),
                'max_date': max(parsed_dates),
                'span_days': (max(parsed_dates) - min(parsed_dates)).days
            }

        # Generate recommendations
        self._generate_date_recommendations(results)

        return results

    def _generate_date_recommendations(self, results: Dict):
        """Generate recommendations based on validation results"""
        recommendations = []

        # Check for multiple date formats
        if len(results['date_formats_found']) > 1:
            recommendations.append(
                f"Multiple date formats detected. Consider standardizing to '{results['most_common_format']}'"
            )

        # Check for high percentage of invalid dates
        total_non_empty = results['total_values'] - results['empty_dates']
        if total_non_empty > 0:
            invalid_percentage = (results['invalid_dates'] + results['ambiguous_dates']) / total_non_empty
            if invalid_percentage > 0.1:  # More than 10% invalid
                recommendations.append(
                    f"{invalid_percentage:.1%} of dates are invalid or ambiguous. Manual review recommended."
                )

        # Check for suspicious date ranges
        if results['date_range']:
            current_year = datetime.now().year
            min_year = results['date_range']['min_date'].year
            max_year = results['date_range']['max_date'].year

            if min_year < 1900:
                recommendations.append(f"Dates before 1900 detected (earliest: {min_year}). Verify data accuracy.")

            if max_year > current_year + 1:
                recommendations.append(
                    f"Future dates beyond next year detected (latest: {max_year}). Verify data accuracy.")

            if results['date_range']['span_days'] > 365 * 10:  # More than 10 years
                recommendations.append(
                    f"Date range spans {results['date_range']['span_days']} days. Verify if this is expected.")

        # Check for empty dates
        if results['empty_dates'] > 0:
            empty_percentage = results['empty_dates'] / results['total_values']
            if empty_percentage > 0.05:  # More than 5% empty
                recommendations.append(
                    f"{empty_percentage:.1%} of dates are empty. Consider data completion."
                )

        results['recommendations'] = recommendations

    def fix_date_format(self, date_values: List[str],
                        target_format: str = '%Y-%m-%d') -> Tuple[List[str], Dict]:
        """
        Attempt to fix and standardize date formats
        Returns (fixed_dates, fix_report)
        """
        fixed_dates = []
        fix_report = {
            'total_processed': len(date_values),
            'successfully_fixed': 0,
            'could_not_fix': 0,
            'already_correct': 0,
            'fixes_made': []
        }

        for i, value in enumerate(date_values):
            parsed_date, detected_format, status = self.parse_date(value)

            if status == 'success':
                fixed_date = parsed_date.strftime(target_format)
                fixed_dates.append(fixed_date)

                if detected_format != target_format:
                    fix_report['successfully_fixed'] += 1
                    fix_report['fixes_made'].append({
                        'index': i,
                        'original': str(value),
                        'fixed': fixed_date,
                        'original_format': detected_format
                    })
                else:
                    fix_report['already_correct'] += 1
            else:
                # Keep original value if we can't parse it
                fixed_dates.append(str(value))
                fix_report['could_not_fix'] += 1

        return fixed_dates, fix_report

    def print_date_validation_report(self, results: Dict):
        date_message = ""
        """Print a formatted date validation report"""
        date_message = f"=== DATE VALIDATION REPORT: {results['column_name']} ===\n"
        date_message = date_message + "@@#@@"

        # Summary statistics
        date_message = date_message + "SUMMARY:\n"
        date_message = date_message + "@@#@@"
        date_message = date_message + f"  Total values: {results['total_values']}"
        date_message = date_message + "@@#@@"
        date_message = date_message + f"  Valid dates: {results['valid_dates']}"
        date_message = date_message + "@@#@@"
        date_message = date_message + f"  Invalid dates: {results['invalid_dates']}"
        date_message = date_message + "@@#@@"
        date_message = date_message + f"  Empty dates: {results['empty_dates']}"
        date_message = date_message + "@@#@@"
        date_message = date_message + f"  Ambiguous dates: {results['ambiguous_dates']}"
        date_message = date_message + "@@#@@"
        date_message = date_message + f"  Overall valid: {'✓' if results['is_valid'] else '✗'}\n"
        date_message = date_message + "@@#@@"

        # Date formats found
        if results['date_formats_found']:
            date_message = date_message + "DATE FORMATS DETECTED:\n"
            date_message = date_message + "@@#@@"
            for fmt, count in results['date_formats_found'].items():
                date_message = date_message + f"  {fmt}: {count} occurrences"
                date_message = date_message + "@@#@@"
            date_message = date_message + f"  Most common: {results['most_common_format']}\n"
            date_message = date_message + "@@#@@"

        # Date range
        if results['date_range']:
            date_message = date_message + "DATE RANGE:\n"
            date_message = date_message + "@@#@@"
            date_message = date_message + f"  From: {results['date_range']['min_date'].strftime('%Y-%m-%d')}"
            date_message = date_message + "@@#@@"
            date_message = date_message + f"  To: {results['date_range']['max_date'].strftime('%Y-%m-%d')}"
            date_message = date_message + "@@#@@"
            date_message = date_message + f"  Span: {results['date_range']['span_days']} days\n"
            date_message = date_message + "@@#@@"

        # Issues
        if results['issues']:
            date_message = date_message + "ISSUES FOUND:\n"
            date_message = date_message + "@@#@@"
            for issue in results['issues'][:10]:  # Show first 10 issues
                date_message = date_message + f"  ⚠️  {issue}"
                date_message = date_message + "@@#@@"
            if len(results['issues']) > 10:
                date_message = date_message + f"  ... and {len(results['issues']) - 10} more issues\n"
                date_message = date_message + "@@#@@"

        # Recommendations
        if results['recommendations']:
            date_message = date_message + "RECOMMENDATIONS:\n"
            date_message = date_message + "@@#@@"
            for rec in results['recommendations']:
                date_message = date_message + f"  💡 {rec}"
                date_message = date_message + "@@#@@"

        date_message = date_message + "\n" + "=" * 10
        return date_message

class ColumnNameValidator:
    def __init__(self):
        # Define expected column names for freight routes data
        self.expected_columns = [
            'ShipmentID',
            'Date',
            'OriginCity',
            'DestinationCity',
            'Distance_Miles',
            'FuelCost_USD',
            'DriverName',
            'CarrierName',
            'LoadWeight_lbs',
            'DeliveryStatus',
            'DeliveryTime_hrs',
            'FreightCost_USD'
        ]

        # Define regex patterns for common variations
        self.column_patterns = {
            r'shipment.*id': 'ShipmentID',
            r'ship.*id': 'ShipmentID',
            r'id': 'ShipmentID',
            r'date.*': 'Date',
            r'origin.*city': 'OriginCity',
            r'origin': 'OriginCity',
            r'from.*city': 'OriginCity',
            r'source.*city': 'OriginCity',
            r'destination.*city': 'DestinationCity',
            r'dest.*city': 'DestinationCity',
            r'to.*city': 'DestinationCity',
            r'target.*city': 'DestinationCity',
            r'distance.*mile': 'Distance_Miles',
            r'distance': 'Distance_Miles',
            r'miles': 'Distance_Miles',
            r'fuel.*cost': 'FuelCost_USD',
            r'fuel.*price': 'FuelCost_USD',
            r'fuel': 'FuelCost_USD',
            r'driver.*name': 'DriverName',
            r'driver': 'DriverName',
            r'carrier.*name': 'CarrierName',
            r'carrier': 'CarrierName',
            r'company': 'CarrierName',
            r'load.*weight': 'LoadWeight_lbs',
            r'weight.*lbs': 'LoadWeight_lbs',
            r'weight': 'LoadWeight_lbs',
            r'cargo.*weight': 'LoadWeight_lbs',
            r'delivery.*status': 'DeliveryStatus',
            r'status': 'DeliveryStatus',
            r'delivery.*time.*hrs': 'DeliveryTime_hrs',
            r'delivery.*time': 'DeliveryTime_hrs',
            r'time.*hrs': 'DeliveryTime_hrs',
            r'hours': 'DeliveryTime_hrs',
            r'freight.*cost': 'FreightCost_USD',
            r'freight.*price': 'FreightCost_USD',
            r'cost.*usd': 'FreightCost_USD',
            r'total.*cost': 'FreightCost_USD'
        }

    def clean_column_name(self, col_name: str) -> str:
        """Clean column name by removing extra whitespace and normalizing case"""
        if pd.isna(col_name):
            return ""

        # Convert to string and strip whitespace
        cleaned = str(col_name).strip()

        # Remove extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned

    def regex_match(self, col_name: str) -> Optional[str]:
        """Try to match column name using regex patterns"""
        col_lower = col_name.lower()

        for pattern, expected in self.column_patterns.items():
            if re.search(pattern, col_lower, re.IGNORECASE):
                return expected

        return None

    def fuzzy_match(self, col_name: str, threshold: float = 0.6) -> Optional[str]:
        """Use difflib to find the closest matching expected column name"""
        matches = difflib.get_close_matches(
            col_name,
            self.expected_columns,
            n=1,
            cutoff=threshold
        )

        return matches[0] if matches else None

    def suggest_correction(self, col_name: str) -> Tuple[str, str, float]:
        """
        Suggest the best correction for a column name
        Returns: (original, suggested, confidence_score)
        """
        cleaned = self.clean_column_name(col_name)

        # First try exact match (case insensitive)
        for expected in self.expected_columns:
            if cleaned.lower() == expected.lower():
                return cleaned, expected, 1.0

        # Try regex matching
        regex_match = self.regex_match(cleaned)
        if regex_match:
            # Calculate confidence based on regex match
            confidence = 0.9 if len(cleaned) > 3 else 0.8
            return cleaned, regex_match, confidence

        # Try fuzzy matching
        fuzzy_match = self.fuzzy_match(cleaned)
        if fuzzy_match:
            # Calculate confidence using sequence matcher
            confidence = difflib.SequenceMatcher(None, cleaned.lower(), fuzzy_match.lower()).ratio()
            return cleaned, fuzzy_match, confidence

        # No good match found
        return cleaned, cleaned, 0.0

    def validate_and_correct_columns(self, df: pd.DataFrame = None,
                                     auto_correct: bool = True,
                                     min_confidence: float = 0.6) -> Dict:
        """
        Validate and optionally correct all column names
        Returns dictionary with results and mapping
        """
        column_names = df.columns.tolist() if df is not None else []

        results = {
            'original_columns': column_names,
            'corrected_columns': [],
            'corrections_made': {},
            'validation_report': [],
            'column_mapping': {},
            'errors': []
        }

        corrected_columns = []

        for i, col in enumerate(column_names):
            original, suggested, confidence = self.suggest_correction(col)

            # Create validation report entry
            report_entry = {
                'index': i,
                'original': col,
                'cleaned': original,
                'suggested': suggested,
                'confidence': confidence,
                'action': 'none'
            }

            if confidence == 1.0:
                # Exact match (possibly after cleaning)
                corrected_columns.append(suggested)
                report_entry['action'] = 'exact_match' if original == suggested else 'cleaned'
                results['column_mapping'][col] = suggested

            elif confidence >= min_confidence and auto_correct:
                # Auto-correct with sufficient confidence
                corrected_columns.append(suggested)
                results['corrections_made'][col] = suggested
                results['column_mapping'][col] = suggested
                report_entry['action'] = 'auto_corrected'
                df.rename(columns={col: suggested}, inplace=True)

            elif confidence > 0:
                # Low confidence - keep original but flag for review
                corrected_columns.append(original)
                results['column_mapping'][col] = original
                report_entry['action'] = 'needs_review'
                results['errors'].append(f"Low confidence match for '{col}' -> '{suggested}' ({confidence:.2f})")

            else:
                # No match found
                corrected_columns.append(original)
                results['column_mapping'][col] = original
                report_entry['action'] = 'no_match'
                results['errors'].append(f"No suitable match found for column '{col}'")

            results['validation_report'].append(report_entry)

        results['corrected_columns'] = corrected_columns
        return results

    def validate_csv_columns(self, csv_file_path: str = None, df: pd.DataFrame = None) -> Dict:
        """Validate columns from CSV file or DataFrame"""
        if df is None:
            if csv_file_path is None:
                raise ValueError("Either csv_file_path or df must be provided")
            df = pd.read_csv(csv_file_path)

        return self.validate_and_correct_columns(df)

    def validate_csv_with_dates(self, csv_file_path: str = None, df: pd.DataFrame = None,
                                date_column: str = None) -> Tuple[Dict, Dict]:
        """
        Validate both columns and date data in CSV
        Returns (column_validation_results, date_validation_results)
        """
        if df is None:
            if csv_file_path is None:
                raise ValueError("Either csv_file_path or df must be provided")
            df = pd.read_csv(csv_file_path)

        # Validate column names
        column_results = self.validate_and_correct_columns(df)

        # Find date column
        if date_column is None:
            # Try to find date column automatically
            for col in column_results['corrected_columns']:
                if 'date' in col.lower():
                    date_column = col
                    break

        date_results = None
        if date_column and date_column in df.columns:
            date_validator = DateValidator()
            # Use original column name if it exists in DataFrame
            original_date_col = None
            for orig, corrected in column_results['column_mapping'].items():
                if corrected == date_column:
                    original_date_col = orig
                    break

            actual_col_name = original_date_col if original_date_col and original_date_col in df.columns else date_column
            if actual_col_name in df.columns:
                date_results = date_validator.validate_date_column(
                    df[actual_col_name].tolist(),
                    column_name=actual_col_name
                )

        return column_results, date_results

    def print_validation_report(self, results: Dict):
        """Print a formatted validation report"""
        column_result = "=== COLUMN VALIDATION REPORT ===\n"
        column_result = column_result + "@@#@@"
        column_result = column_result + f"\nTotal columns: {len(results['original_columns'])}\n"
        column_result = column_result + "@@#@@"
        column_result = column_result + f"Corrections made: {len(results['corrections_made'])}\n"
        column_result = column_result + "@@#@@"
        column_result = column_result + f"Errors/Warnings: {len(results['errors'])}\n"
        column_result = column_result + "@@#@@"

        # Print corrections made
        if results['corrections_made']:
            column_result = column_result + "CORRECTIONS MADE:\n"
            column_result = column_result + "@@#@@"
            for original, corrected in results['corrections_made'].items():
                column_result = column_result + f"  '{original}' -> '{corrected}'\n"
                column_result = column_result + "@@#@@"
            column_result = column_result + "\n"
            column_result = column_result + "@@#@@"
            # Print detailed report
        # column_result = column_result + "DETAILED REPORT:\n"
        # column_result = column_result + "@@#@@"
        # column_result = column_result + f"{'Index':<5} {'Original':<20} {'Suggested':<20} {'Confidence':<10} {'Action':<15}\n"
        # column_result = column_result + "@@#@@"
        # column_result = column_result + "-" * 75
        # column_result = column_result + "@@#@@"
        #
        # for entry in results['validation_report']:
        #     column_result = column_result + f"{entry['index']:<5} {entry['original'][:19]:<20} {entry['suggested'][:19]:<20} " f"{entry['confidence']:<10.2f} {entry['action']:<15}\n"
        #     column_result = column_result + "@@#@@"
        # Print errors/warnings
        if results['errors']:
            column_result = column_result + f"\nERRORS/WARNINGS:\n"
            column_result = column_result + "@@#@@"
            for error in results['errors']:
                column_result = column_result + f"  ⚠️  {error}"
                column_result = column_result + "@@#@@"

        column_result = column_result + "\n" + "=" * 10
        return column_result

class CityStateNormalizer:
    def __init__(self, df: pd.DataFrame, us_city_state_ref: pd.DataFrame, state_default="TX", fuzzy_cutoff=0.8):
        """
        :param df: DataFrame containing OriginCity and DestinationCity columns.
        :param us_city_state_ref: DataFrame with columns ['City', 'State'] for all known US cities.
        :param state_default: Default state if missing and cannot be determined.
        :param fuzzy_cutoff: Similarity threshold for fuzzy matching.
        """
        self.df = df.copy()
        self.state_default = state_default.upper()
        self.fuzzy_cutoff = fuzzy_cutoff
        self.cityreport_origin = 0
        self.statereport_origin = 0
        self.cityreport_destin = 0
        self.statereport_destin = 0

        # Build reference dict
        self.known_map = {self._clean_city(row["city"]): row["state"].upper()
                          for _, row in us_city_state_ref.iterrows()}
        self.unknown_cities = []  # For manual review
        # self.geolocator = Nominatim(user_agent="city_state_normalizer")
        # print(self.known_map)

    def _clean_city(self, city):
        """Normalize city string: remove noise, title case."""
        if pd.isna(city):
            return None
        city = re.sub(r'\s+', ' ', str(city).strip())
        city = re.sub(r'[^a-zA-Z\s\-]', '', city)
        return city.title()

    def _split_city_state(self, value):
        """Split into (city, state) if both exist, else (city, None)."""
        if not value:
            return None, None
        parts = [p.strip() for p in value.split(",")]
        if len(parts) == 2:
            return self._clean_city(parts[0]), parts[1].upper()
        return self._clean_city(parts[0]), None

    def _guess_city(self, city):
        """Guess closest city from known map using fuzzy matching."""
        if not city:
            return None
        if city in self.known_map:
            return city
        matches = get_close_matches(city, self.known_map.keys(), n=1, cutoff=self.fuzzy_cutoff)
        return matches[0] if matches else None

    def _geocode_state(self, city):
        """Use geocoding API to detect state."""
        try:
            location = self.geolocator.geocode(f"{city}, USA", exactly_one=True)
            time.sleep(1)  # Avoid rate limit
            if location and "address" in location.raw:
                state_code = location.raw["address"].get("state_code")
                if state_code:
                    return state_code.upper()
        except Exception:
            pass
        return None

    def normalize_column(self, col):
        """Normalize one city column."""
        normalized = []
        guessed_city = ""
        # print("column analyzed:", col)
        # print(self.df[col].head(5))
        # print(self.df.columns)
        for val in self.df[col]:
            # print("val:", val)
            city, state = self._split_city_state(val)
            if city:
            # print(f"{city} - {state}")
                guessed_city = self._guess_city(city)
            else:
                if col == "OriginCity":
                    self.cityreport_origin += 1
                else:
                    self.cityreport_destin += 1

            # If fuzzy match found
            if guessed_city:
                city = guessed_city
                if not state:
                    if col == "OriginCity":
                        self.statereport_origin += 1
                    else:
                        self.statereport_destin += 1
                    state = self.known_map[city]
                    self.unknown_cities.append({"Column": col, "Original": val})
                    print("city:", city, "-", state)
            # else:
            #     # Try geocoding if not in known list
            #     geo_state = self._geocode_state(city)
            #     if geo_state:
            #         state = geo_state
            #     else:
            #         # Couldn't recognize city
            #         self.unknown_cities.append({"Column": col, "Original": val})
            #         state = state or self.state_default

            normalized.append(f"{city}, {state}")
        # print("lenght of normalized: ", len(normalized))
        # print("Normalized data:", normalized)
        # self.df = self.df.drop(col, axis=1)
        self.df[col] = normalized

    def normalize(self):
        """Normalize both OriginCity and DestinationCity."""
        for col in ["OriginCity", "DestinationCity"]:
            if col not in self.df.columns:
                raise ValueError(f"Missing required column: {col}")
            self.normalize_column(col)
        return self.df, pd.DataFrame(self.unknown_cities), self.cityreport_origin, self.statereport_origin, self.cityreport_destin, self.statereport_destin


# Example usage and testing
def test_validator(routefile, report, routefilename):

# load us cities file
    us_cities = pd.read_csv(uscities_file)
    print(us_cities.head(5))
# Load sample data
    data = pd.read_csv(report.routefile)

    """Test the validator with sample data"""
    validator = ColumnNameValidator()
    date_validator = DateValidator()

    test_columns = data.columns
    # print("Testing with sample column variations...")
    results = validator.validate_and_correct_columns(data)
    column_report = validator.print_validation_report(results)

    # Test date validation with sample dates
    # print("\n" + "=" * 60)
    # print("Testing date validation...")


    sample_dates = data['Date']
    date_results = date_validator.validate_date_column(sample_dates, 'TestDate')
    date_report = date_validator.print_date_validation_report(date_results)

    # Test date fixing
    # print("\nTesting date format fixing...")
    fixed_dates, fix_report = date_validator.fix_date_format(sample_dates, '%Y-%m-%d')
    data['Date'] = fixed_dates
    date_report = date_report + "@@#@@"
    date_report = date_report + "\nFIX REPORT:\n"
    date_report = date_report + "@@#@@"
    date_report = date_report + f"  Successfully fixed: {fix_report['successfully_fixed']}"
    date_report = date_report + "@@#@@"
    date_report = date_report + f"  Could not fix: {fix_report['could_not_fix']}"
    date_report = date_report + "@@#@@"
    date_report = date_report + f"  Already correct: {fix_report['already_correct']}"

    if fix_report['fixes_made']:
        date_report = date_report + "@@#@@"
        date_report = date_report + "\nFIXES MADE:"
        for fix in fix_report['fixes_made'][:5]:  # Show first 5
            date_report = date_report + "@@#@@"
            date_report = date_report + f"  '{fix['original']}' -> '{fix['fixed']}' (was {fix['original_format']})"

    orig_cities = data[['OriginCity', 'DestinationCity']]
    # print("Origine cities:", orig_cities.columns)
    normalizer = CityStateNormalizer(orig_cities, us_cities)
    clean_df, review_df, misscities_origin, missgstates_origin, misscities_destin, missgstates_destin = normalizer.normalize()
    # print("clean_df")
    # print(clean_df.index)
    # print(clean_df.info())
    # data = data.drop(['OriginCity', 'DestinationCity'], axis=1)
    # data = pd.concat([data, clean_df], axis=0, ignore_index=True)
    data.update(clean_df['OriginCity'])
    data.update(clean_df['DestinationCity'])


    cities_report = "Cleaned data\n"
    cities_report = cities_report + "@@#@@"
    cities_report = cities_report + f"Number of missing City names in Original cities column: {misscities_origin}"
    cities_report = cities_report + "@@#@@"
    cities_report = cities_report + f"Number of missing State names in Original cities column: {missgstates_origin}"
    cities_report = cities_report + "@@#@@"
    cities_report = cities_report + f"Number of missing City names in Destination cities column: {misscities_destin}"
    cities_report = cities_report + "@@#@@"
    cities_report = cities_report + f"Number of missing State names in Destination cities column: {missgstates_destin}"
    # cities_report = cities_report + "@@#@@"
    # cities_report = cities_report + "\nUnknown cities for review"
    # cities_report = cities_report + review_df  # Unknown cities for review
    directory_path = 'data_files/route_files/company_id_{0}/report_{1}'.format(report.client.id, report.id)

    # if not os.path.exists(directory_path):
    #     os.makedirs(directory_path)
    # if report.routefile:
    #     if os.path.isfile(report.routefile.path):
    #         os.remove(report.routefile.path)
    print("Data before saving to csv file")
    print(data.head(5))
    print(data.columns)
    filename = 'data_files/route_files/company_id_{0}/report_{1}/{2}'.format(report.client.id, report.id, routefilename)
    print("filename: ", filename)
    filepath = settings.MEDIA_ROOT + "/" + filename
    f = open(filepath, 'w')
    data.to_csv(f, index=False)
    f.close() # Explicitly close the file

    return column_report, date_report, cities_report, filename

