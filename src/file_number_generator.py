"""
File Number Generator
Generates file numbers for all configured categories with proper registry assignment
"""

import os
import random
import string
from datetime import datetime
from typing import List, Dict, Any, Generator, Optional, Iterable
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FileNumberGenerator:
    """Generate file numbers with proper categorization and registry assignment"""
    
    def __init__(self):
        # Registry-driven category sequencing
        self.registry_sequences = [
            {
                'registry': '1',
                'categories': ['RES', 'COM', 'IND', 'AG', 'RES-RC', 'COM-RC', 'IND-RC', 'AG-RC'],
                'year_range': (1981, 1991)
            },
            {
                'registry': '2',
                'categories': ['RES', 'COM', 'IND', 'AG', 'RES-RC', 'COM-RC', 'IND-RC', 'AG-RC'],
                'year_range': (1992, 2025)
            },
            {
                'registry': '3',
                'categories': ['CON-RES', 'CON-COM', 'CON-IND', 'CON-AG', 'CON-RES-RC', 'CON-COM-RC', 'CON-IND-RC', 'CON-AG-RC'],
                'year_range': (1981, 2025)
            }
        ]

        ordered_categories: List[str] = []
        for sequence in self.registry_sequences:
            for category in sequence['categories']:
                if category not in ordered_categories:
                    ordered_categories.append(category)
        self.categories = ordered_categories

        # Configuration from environment
        self.start_year = int(os.getenv('START_YEAR', 1981))
        self.end_year = int(os.getenv('END_YEAR', 2025))
        self.numbers_per_year = int(os.getenv('NUMBERS_PER_YEAR', 10000))
        self.records_per_group = int(os.getenv('RECORDS_PER_GROUP', 100))

        # Registry year ranges (inclusive)
        self.registry_year_ranges = {
            '1': (1981, 1991),
            '2': (1992, 2025)
        }
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Initialize internal counters that can persist across generator calls
        self.reset_counters()

    def reset_counters(self) -> None:
        """Reset global record and registry counters."""
        self._global_record_count = 0
        self._registry_counts: Dict[str, int] = {}
        
    def extract_land_use(self, file_number: str) -> str:
        """
        Extract land use from file number prefix
        Args:
            file_number: The complete file number (e.g., 'CON-RES-RC-1981-1')
        Returns:
            Full land use name (Residential, Commercial, or Agriculture)
        """
        if 'RES' in file_number:
            return 'Residential'
        elif 'COM' in file_number:
            return 'Commercial'
        elif 'IND' in file_number:
            return 'Industrial'
        elif 'AG' in file_number:
            return 'Agriculture'
        else:
            return 'UNKNOWN'
    
    def assign_registry(self, file_number: str, year: int) -> str:
        """
        Assign registry based on year and CON prefix rules
        Args:
            file_number: The complete file number
            year: The year from the file number
        Returns:
            Registry assignment (1, 2, or 3)
        """
        # Registry 3: Any file number containing "CON" (overrides year rules)
        if 'CON' in file_number:
            return '3'
        
        start_1, end_1 = self.registry_year_ranges['1']
        if start_1 <= year <= end_1:
            return '1'

        start_2, end_2 = self.registry_year_ranges['2']
        if start_2 <= year <= end_2:
            return '2'
        
        # Default fallback
        return '2'
    
    def generate_tracking_id(self) -> str:
        """
        Generate a unique tracking ID in the format TRK-YZ9C71TL-7VHX8
        Returns:
            Tracking ID string
        """
        # Generate 8-character alphanumeric string (first part)
        part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Generate 5-character alphanumeric string (second part)  
        part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        
        return f"TRK-{part1}-{part2}"
    
    def generate_file_numbers(
        self,
        categories: Optional[Iterable[str]] = None,
        max_per_category: Optional[int] = None,
        *,
        reset_counters: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Generate file numbers for specified categories
        Args:
            categories: List of categories to generate (default: all configured categories)
            max_per_category: Maximum records per category (default: all years/numbers)
        Yields:
            Dictionary with file number data
        """
        if reset_counters:
            self.reset_counters()

        category_filter = None
        if categories is not None:
            category_filter = {category.upper() for category in categories}

        category_counts: Dict[str, int] = {}
        
        for sequence in self.registry_sequences:
            seq_start, seq_end = sequence['year_range']
            seq_start = max(seq_start, self.start_year)
            seq_end = min(seq_end, self.end_year)
            if seq_start > seq_end:
                continue
            registry_id = sequence.get('registry')
            if registry_id is not None and registry_id not in self._registry_counts:
                self._registry_counts[registry_id] = 0

            for category in sequence['categories']:
                if category_filter and category not in category_filter:
                    continue

                category_counts.setdefault(category, 0)
                generated_before = category_counts[category]

                self.logger.info(
                    f"Generating file numbers for category: {category} (Years {seq_start}-{seq_end})"
                )

                for year in range(seq_start, seq_end + 1):
                    if max_per_category:
                        remaining = max_per_category - category_counts[category]
                        if remaining <= 0:
                            break
                        number_cap = min(self.numbers_per_year, remaining)
                    else:
                        number_cap = self.numbers_per_year

                    for number in range(1, number_cap + 1):
                        self._global_record_count += 1
                        category_counts[category] += 1

                        file_number = f"{category}-{year}-{number}"
                        group_number = ((self._global_record_count - 1) // self.records_per_group) + 1
                        batch_number = group_number

                        land_use = self.extract_land_use(file_number)
                        registry = self.assign_registry(file_number, year)
                        self._registry_counts.setdefault(registry, 0)
                        self._registry_counts[registry] += 1
                        registry_batch_no = ((self._registry_counts[registry] - 1) // self.records_per_group) + 1
                        tracking_id = self.generate_tracking_id()

                        yield {
                            'awaiting_fileno': file_number,
                            'created_by': 'Generated',
                            'number': self._global_record_count,
                            'year': year,
                            'landuse': land_use,
                            'created_at': datetime.now(),
                            'registry': registry,
                            'mls_fileno': None,
                            'mapping': 0,
                            'group': group_number,
                            'sys_batch_no': batch_number,
                            'registry_batch_no': registry_batch_no,
                            'tracking_id': tracking_id,
                            'category': category
                        }

                        if max_per_category and category_counts[category] >= max_per_category:
                            break

                    if max_per_category and category_counts[category] >= max_per_category:
                        break

                generated_now = category_counts[category] - generated_before
                self.logger.info(f"Generated {generated_now} records for {category}")
    
    def generate_sample_data(
        self,
        records_per_category: int = 10,
        categories: Optional[Iterable[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate a small sample of data for testing
        Args:
            records_per_category: Number of records to generate per category
            categories: Optional subset of categories to generate
        Returns:
            List of file number records
        """
        if categories:
            category_list = [cat.upper() for cat in categories]
            category_info = ', '.join(category_list)
        else:
            category_list = None
            category_info = 'all categories'
        self.logger.info(
            f"Generating sample data: {records_per_category} records per category for {category_info}"
        )
        
        sample_data = []
        for record in self.generate_file_numbers(categories=category_list, max_per_category=records_per_category):
            sample_data.append(record)
        
        self.logger.info(f"Generated {len(sample_data)} total sample records")
        return sample_data
    
    def get_category_stats(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about generated records
        Args:
            records: List of generated records
        Returns:
            Statistics dictionary
        """
        stats = {
            'total_records': len(records),
            'categories': {},
            'registries': {},
            'land_uses': {},
            'year_range': {'min': None, 'max': None},
            'groups': {'min': None, 'max': None, 'count': 0}
        }
        
        # Count by category, registry, land use
        for record in records:
            # Extract category from file number
            fileno_parts = record['awaiting_fileno'].split('-')
            category = fileno_parts[0]

            if category == 'CON':
                if len(fileno_parts) >= 3:
                    category = '-'.join(fileno_parts[:3]) if fileno_parts[2] == 'RC' else '-'.join(fileno_parts[:2])
            elif len(fileno_parts) >= 2 and fileno_parts[1] == 'RC':
                category = '-'.join(fileno_parts[:2])
            
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            stats['registries'][record['registry']] = stats['registries'].get(record['registry'], 0) + 1
            stats['land_uses'][record['landuse']] = stats['land_uses'].get(record['landuse'], 0) + 1
            
            # Year range
            year = record['year']
            if stats['year_range']['min'] is None or year < stats['year_range']['min']:
                stats['year_range']['min'] = year
            if stats['year_range']['max'] is None or year > stats['year_range']['max']:
                stats['year_range']['max'] = year
            
            # Group range
            group = record['group']
            if stats['groups']['min'] is None or group < stats['groups']['min']:
                stats['groups']['min'] = group
            if stats['groups']['max'] is None or group > stats['groups']['max']:
                stats['groups']['max'] = group
        
        stats['groups']['count'] = stats['groups']['max'] - stats['groups']['min'] + 1 if stats['groups']['max'] else 0
        
        return stats


def main():
    """Test the file number generator"""
    print("Testing File Number Generator")
    print("=" * 50)
    
    generator = FileNumberGenerator()
    
    # Generate sample data (10 records per category)
    sample_records = generator.generate_sample_data(records_per_category=10)
    
    # Print first few records
    print(f"\nGenerated {len(sample_records)} sample records")
    print("\nFirst 5 records:")
    for i, record in enumerate(sample_records[:5]):
        print(
            f"{i+1}. {record['awaiting_fileno']} | Registry {record['registry']}"
            f" | Group {record['group']} | Registry Batch {record['registry_batch_no']} | {record['landuse']}"
        )
    
    # Print last few records
    print("\nLast 5 records:")
    for i, record in enumerate(sample_records[-5:], len(sample_records)-4):
        print(
            f"{i}. {record['awaiting_fileno']} | Registry {record['registry']}"
            f" | Group {record['group']} | Registry Batch {record['registry_batch_no']} | {record['landuse']}"
        )
    
    # Get and display statistics
    print("\n" + "=" * 50)
    stats = generator.get_category_stats(sample_records)
    
    print(f"Total Records: {stats['total_records']}")
    print(f"Year Range: {stats['year_range']['min']} - {stats['year_range']['max']}")
    print(f"Groups: {stats['groups']['min']} - {stats['groups']['max']} ({stats['groups']['count']} groups)")
    
    print(f"\nBy Registry:")
    for registry, count in stats['registries'].items():
        print(f"  {registry}: {count} records")
    
    print(f"\nBy Land Use:")
    for landuse, count in stats['land_uses'].items():
        print(f"  {landuse}: {count} records")
    
    print(f"\nBy Category:")
    for category, count in stats['categories'].items():
        print(f"  {category}: {count} records")


if __name__ == "__main__":
    main()