"""
File Number Generator
Generates file numbers for all 12 categories with proper registry assignment
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Generator
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FileNumberGenerator:
    """Generate file numbers with proper categorization and registry assignment"""
    
    def __init__(self):
        # File number categories (12 types)
        self.categories = [
            'RES', 'COM', 'AG',                    # Basic land use
            'RES-RC', 'COM-RC', 'AG-RC',           # Land use with record
            'CON-RES', 'CON-COM', 'CON-AG',        # Conversion land use
            'CON-RES-RC', 'CON-COM-RC', 'CON-AG-RC' # Conversion + record
        ]
        
        # Configuration from environment
        self.start_year = int(os.getenv('START_YEAR', 1981))
        self.end_year = int(os.getenv('END_YEAR', 2025))
        self.numbers_per_year = int(os.getenv('NUMBERS_PER_YEAR', 10000))
        self.records_per_group = int(os.getenv('RECORDS_PER_GROUP', 100))
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
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
            Registry assignment (Registry 1, Registry 2, or Registry 3)
        """
        # Registry 3: Any file number containing "CON" (overrides year rules)
        if 'CON' in file_number:
            return 'Registry 3'
        
        # Registry 1: Years 1981-1991
        if 1981 <= year <= 1991:
            return 'Registry 1'
        
        # Registry 2: Years 1992-2025
        if 1992 <= year <= 2025:
            return 'Registry 2'
        
        # Default fallback
        return 'Registry 2'
    
    def generate_file_numbers(self, categories: List[str] = None, max_per_category: int = None) -> Generator[Dict[str, Any], None, None]:
        """
        Generate file numbers for specified categories
        Args:
            categories: List of categories to generate (default: all 12)
            max_per_category: Maximum records per category (default: all years/numbers)
        Yields:
            Dictionary with file number data
        """
        if categories is None:
            categories = self.categories
        
        years = list(range(self.start_year, self.end_year + 1))
        
        # Global counters for group and batch numbering
        global_record_count = 0
        
        for category in categories:
            self.logger.info(f"Generating file numbers for category: {category}")
            category_record_count = 0
            
            for year in years:
                numbers_range = range(1, self.numbers_per_year + 1)
                
                # Apply limit if specified
                if max_per_category:
                    remaining = max_per_category - category_record_count
                    if remaining <= 0:
                        break
                    numbers_range = range(1, min(self.numbers_per_year + 1, remaining + 1))
                
                for number in numbers_range:
                    global_record_count += 1
                    category_record_count += 1
                    
                    # Generate file number
                    file_number = f"{category}-{year}-{number}"
                    
                    # Calculate group and batch (both same logic: 100 records each)
                    group_number = ((global_record_count - 1) // self.records_per_group) + 1
                    batch_number = group_number  # Same as group for this implementation
                    
                    # Extract land use and assign registry
                    land_use = self.extract_land_use(file_number)
                    registry = self.assign_registry(file_number, year)
                    
                    yield {
                        'awaiting_fileno': file_number,
                        'created_by': 'Generated',
                        'number': global_record_count,
                        'year': year,
                        'landuse': land_use,
                        'created_at': datetime.now(),
                        'registry': registry,
                        'mls_fileno': None,
                        'mapping': 0,
                        'group': group_number,
                        'sys_batch_no': batch_number
                    }
                    
                    # Break if we've reached the category limit
                    if max_per_category and category_record_count >= max_per_category:
                        break
                
                # Break year loop if category limit reached
                if max_per_category and category_record_count >= max_per_category:
                    break
            
            self.logger.info(f"Generated {category_record_count} records for {category}")
    
    def generate_sample_data(self, records_per_category: int = 10) -> List[Dict[str, Any]]:
        """
        Generate a small sample of data for testing
        Args:
            records_per_category: Number of records to generate per category
        Returns:
            List of file number records
        """
        self.logger.info(f"Generating sample data: {records_per_category} records per category")
        
        sample_data = []
        for record in self.generate_file_numbers(max_per_category=records_per_category):
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
            category = record['awaiting_fileno'].split('-')[0]
            if 'CON' in record['awaiting_fileno']:
                parts = record['awaiting_fileno'].split('-')
                if len(parts) >= 3:
                    category = '-'.join(parts[:2]) if parts[1] in ['RES', 'COM', 'AG'] else parts[0]
                    if len(parts) >= 4 and parts[2] == 'RC':
                        category = '-'.join(parts[:3])
            
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
    
    # Generate sample data (10 records per category = 120 total)
    sample_records = generator.generate_sample_data(records_per_category=10)
    
    # Print first few records
    print(f"\nGenerated {len(sample_records)} sample records")
    print("\nFirst 5 records:")
    for i, record in enumerate(sample_records[:5]):
        print(f"{i+1}. {record['awaiting_fileno']} | {record['registry']} | Group {record['group']} | {record['landuse']}")
    
    # Print last few records
    print("\nLast 5 records:")
    for i, record in enumerate(sample_records[-5:], len(sample_records)-4):
        print(f"{i}. {record['awaiting_fileno']} | {record['registry']} | Group {record['group']} | {record['landuse']}")
    
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