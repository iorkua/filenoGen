# File Number Generation System

A comprehensive Python-based system for generating and managing file numbers with database integration, Excel import capabilities, and automated tracking ID generation.

## 🚀 Features

### Core Functionality
- **Automated File Number Generation**: Generates 5.4M file numbers across 12 categories
- **Registry Assignment**: Intelligent registry assignment based on year and category rules
- **Excel Data Import**: Import existing file records from Excel files
- **Tracking ID Generation**: Auto-generates unique tracking IDs (format: TRK-B9010697-C2474)
- **Database Integration**: Full SQL Server integration with transaction management
- **Progress Tracking**: Real-time progress monitoring for large operations

### File Number Categories
1. **RES** - Residential
2. **COM** - Commercial  
3. **AG** - Agriculture
4. **RES-RC** - Residential Recertification
5. **COM-RC** - Commercial Recertification
6. **AG-RC** - Agriculture Recertification
7. **CON-RES** - Conversion to Residential
8. **CON-COM** - Conversion to Commercial
9. **CON-AG** - Conversion to Agriculture
10. **CON-RES-RC** - Conversion to Residential + Recertification
11. **CON-COM-RC** - Conversion to Commercial + Recertification
12. **CON-AG-RC** - Conversion to Agriculture + Recertification

### Registry Assignment Rules
- **Registry 1**: Years 1981-1991
- **Registry 2**: Years 1992-2025  
- **Registry 3**: Any file number containing "CON" (overrides year rules)

## 📊 Data Volume
- **Years Covered**: 1981-2025 (45 years)
- **Numbers per Category per Year**: 10,000
- **Total Categories**: 12
- **Total Records**: 5,400,000 file numbers
- **Processing Groups**: 54,000 groups (100 records each)

## 🛠️ Technology Stack
- **Python 3.13.6**
- **SQL Server** with pyodbc and pymssql drivers
- **pandas** for data manipulation
- **openpyxl** for Excel file processing
- **python-dotenv** for environment configuration

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- SQL Server (2016 or higher)
- Windows OS (for ODBC drivers)
- 8GB+ RAM recommended for large operations

### Database Requirements
- SQL Server instance with appropriate permissions
- Tables: `grouping` and `fileNumber` 
- Network connectivity to database server

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd filenoGen
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows
# source .venv/bin/activate  # On Linux/macOS
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy `.env.example` to `.env` and update with your database credentials:
```bash
cp .env.example .env
```

Edit `.env` file:
```env
DB_HOST=your_sql_server
DB_PORT=1433
DB_NAME=your_database
DB_USER=your_username
DB_PASSWORD=your_password
DB_DRIVER=ODBC Driver 17 for SQL Server
```

## 📖 Usage

### File Number Generation

#### Generate All File Numbers (5.4M records)
```bash
python src/production_insertion.py
```

#### Test with Sample Data
```bash
python test_import.py
```

### Excel Data Import

#### Import from Excel File
```bash
python src/excel_importer.py
```

#### Preview Excel File Structure
```bash
python preview_excel.py
```

### Database Operations

#### Check Database Connection
```bash
python src/database_connection.py
```

#### Verify Table Structure
```bash
python check_table.py
```

## 📁 Project Structure

```
filenoGen/
├── src/                          # Source code
│   ├── database_connection.py    # Database connectivity
│   ├── file_number_generator.py  # File number generation logic
│   ├── excel_importer.py        # Excel import functionality
│   └── production_insertion.py   # Production file number insertion
├── filenumber_gen.html           # Original HTML generator
├── file_number_insertion_plan.md # Project documentation
├── preview_excel.py              # Excel preview utility
├── test_import.py               # Testing utilities
├── check_table.py               # Database verification
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

## 🔧 Configuration

### Database Tables

#### grouping Table
```sql
CREATE TABLE [dbo].[grouping] (
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [awaiting_fileno] NVARCHAR(50),
    [created_by] NVARCHAR(50),
    [number] INT,
    [year] INT,
    [landuse] NVARCHAR(20),
    [created_at] DATETIME,
    [registry] NVARCHAR(20),
    [mls_fileno] NVARCHAR(50),
    [mapping] INT,
    [group] INT,
    [sys_batch_no] INT
)
```

#### fileNumber Table
```sql
CREATE TABLE [dbo].[fileNumber] (
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [kangisFileNo] NVARCHAR(100),
    [mlsfNo] NVARCHAR(100),
    [NewKANGISFileNo] NVARCHAR(100),
    [FileName] NVARCHAR(255),
    [created_at] DATETIME,
    [location] NVARCHAR(255),
    [created_by] NVARCHAR(100),
    [type] NVARCHAR(50),
    [is_deleted] BIT,
    [SOURCE] NVARCHAR(50),
    [plot_no] NVARCHAR(100),
    [tp_no] NVARCHAR(100),
    [tracking_id] NVARCHAR(50),
    [date_migrated] NVARCHAR(MAX),
    [migrated_by] NVARCHAR(MAX),
    [migration_source] NVARCHAR(MAX)
)
```

## 📊 Performance Metrics

### File Number Generation
- **Processing Speed**: ~1,800 records/second
- **Total Time**: ~50 minutes for 5.4M records
- **Memory Usage**: <500MB peak
- **Batch Size**: 1,000 records per batch
- **Transaction Size**: 10,000 records per transaction

### Excel Import
- **Processing Speed**: ~2,000 records/second
- **Total Time**: ~2 minutes for 11,250 records
- **Success Rate**: 100%
- **Batch Processing**: 1,000 records per batch

## 🔍 Validation & Testing

### Data Validation Queries
```sql
-- Check total records
SELECT COUNT(*) FROM [dbo].[grouping]

-- Verify registry distribution
SELECT [registry], COUNT(*) FROM [dbo].[grouping] GROUP BY [registry]

-- Check land use distribution  
SELECT [landuse], COUNT(*) FROM [dbo].[grouping] GROUP BY [landuse]

-- Verify year ranges
SELECT MIN([year]), MAX([year]) FROM [dbo].[grouping]
```

### Testing Utilities
- **test_import.py**: Test Excel import with sample data
- **preview_excel.py**: Analyze Excel file structure
- **check_table.py**: Verify database table structure

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check SQL Server connectivity
telnet your_server 1433

# Verify ODBC drivers
python -c "import pyodbc; print(pyodbc.drivers())"
```

#### Import Errors
- Verify Excel file exists and has correct column names
- Check database permissions
- Ensure sufficient disk space

#### Performance Issues
- Reduce batch size for lower memory systems
- Check database server resources
- Verify network connectivity

## 📝 Logging

All operations are logged with timestamps:
- **File Generation**: `production_insertion.log`
- **Excel Import**: `excel_import.log`
- **Database Operations**: Console output with INFO level

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Review the troubleshooting section
- Check the logs for detailed error information

## 🎯 Roadmap

- [ ] Web interface for file number generation
- [ ] API endpoints for external integration
- [ ] Advanced reporting and analytics
- [ ] Automated backup and recovery
- [ ] Multi-database support

---

**Note**: This system is designed for KANGIS GIS file number management and can be adapted for other similar use cases.