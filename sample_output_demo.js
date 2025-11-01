// Sample output demonstration for FileNos Generator
// This shows what the CSV file would contain

function generateSampleFileNos(sampleYears = 3, sampleNumbers = 10) {
    const years = [1981, 1982, 2025]; // Show first 2 years and last year
    const numbers = Array.from({length: sampleNumbers}, (_, i) => i + 1);
    
    const fileNos = [];
    
    years.forEach(year => {
        numbers.forEach(number => {
            fileNos.push({
                Year: year,
                Number: number,
                FileNo: `CON-AG-RC-${year}-${number}`
            });
        });
    });
    
    return fileNos;
}

function arrayToCSV(data) {
    const headers = ['Year', 'Number', 'FileNo'];
    const csvRows = [headers.join(',')];
    
    data.forEach(item => {
        const row = [
            item.Year,
            item.Number,
            `"${item.FileNo}"`
        ];
        csvRows.push(row.join(','));
    });
    
    return csvRows.join('\n');
}

// Generate sample data
console.log('=== FileNos Generator Sample Output ===\n');

const sampleData = generateSampleFileNos();
const csvOutput = arrayToCSV(sampleData);

console.log('Sample CSV Output (first 10 numbers from years 1981, 1982, and 2025):');
console.log('---');
console.log(csvOutput);
console.log('---\n');

console.log('Full File Statistics:');
console.log('- Years: 1981 to 2025 (45 years)');
console.log('- Numbers per year: 1 to 5000');
console.log('- Total records: ' + (45 * 5000).toLocaleString());
console.log('- Estimated file size: ~6-8 MB');
console.log('- File format: CSV with headers');
console.log('- Filename: FileNos_1981_2025.csv');

console.log('\nSample FileNo patterns:');
console.log('- First record: CON-AG-RC-1981-1');
console.log('- Last record of 1981: CON-AG-RC-1981-5000');
console.log('- First record of 1982: CON-AG-RC-1982-1');
console.log('- Last record overall: CON-AG-RC-2025-5000');