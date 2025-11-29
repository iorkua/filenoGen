# File Number Query Builder
## Interactive Registry-Category-Year Selection Tool

This document provides an interactive query builder using HTML dropdowns to filter file numbers by Registry, Category Type, and Year.

---

## Interactive Query Builder

<div style="border: 2px solid #333; padding: 20px; background-color: #f9f9f9; border-radius: 8px; margin: 20px 0;">

### Select Criteria

**Step 1: Choose Registry**

<select id="registrySelect" onchange="updateCategories()">
  <option value="">-- Select Registry --</option>
  <option value="1">Registry 1 (Standard: 1981-1991)</option>
  <option value="2">Registry 2 (Standard: 1992-2025)</option>
  <option value="3">Registry 3 (Conversion: 1981-2025)</option>
</select>

**Step 2: Choose Category Type**

<select id="categorySelect" onchange="updateYears()">
  <option value="">-- Select Category --</option>
</select>

**Step 3: Choose Year**

<select id="yearSelect">
  <option value="">-- Select Year --</option>
</select>

**Step 4: Build Query**

<button onclick="buildQuery()" style="padding: 10px 20px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;">Generate File Number Type</button>

---

### Query Result

<div id="result" style="margin-top: 20px; padding: 15px; background-color: #e8f4f8; border-left: 4px solid #007bff; display: none;">
  <strong>File Number Type:</strong> <span id="resultValue" style="font-family: monospace; font-size: 18px; color: #d9534f;"></span>
</div>

---

### Configuration Data

<script>
const registryData = {
  "1": {
    name: "Registry 1 (Standard)",
    years: [1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1991],
    categories: ["RES", "COM", "IND", "AG", "RES-RC", "COM-RC", "IND-RC", "AG-RC"]
  },
  "2": {
    name: "Registry 2 (Standard)",
    years: [1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    categories: ["RES", "COM", "IND", "AG", "RES-RC", "COM-RC", "IND-RC", "AG-RC"]
  },
  "3": {
    name: "Registry 3 (Conversion)",
    years: [1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    categories: ["CON-RES", "CON-COM", "CON-IND", "CON-AG", "CON-RES-RC", "CON-COM-RC", "CON-IND-RC", "CON-AG-RC"]
  }
};

function updateCategories() {
  const registrySelect = document.getElementById("registrySelect");
  const categorySelect = document.getElementById("categorySelect");
  const yearSelect = document.getElementById("yearSelect");
  const registry = registrySelect.value;
  
  // Reset dropdowns
  categorySelect.innerHTML = '<option value="">-- Select Category --</option>';
  yearSelect.innerHTML = '<option value="">-- Select Year --</option>';
  document.getElementById("result").style.display = "none";
  
  if (!registry) return;
  
  // Populate categories
  const categories = registryData[registry].categories;
  categories.forEach(cat => {
    const option = document.createElement("option");
    option.value = cat;
    option.textContent = cat;
    categorySelect.appendChild(option);
  });
}

function updateYears() {
  const registrySelect = document.getElementById("registrySelect");
  const yearSelect = document.getElementById("yearSelect");
  const registry = registrySelect.value;
  
  // Reset year dropdown
  yearSelect.innerHTML = '<option value="">-- Select Year --</option>';
  document.getElementById("result").style.display = "none";
  
  if (!registry) return;
  
  // Populate years
  const years = registryData[registry].years;
  years.forEach(year => {
    const option = document.createElement("option");
    option.value = year;
    option.textContent = year;
    yearSelect.appendChild(option);
  });
}

function buildQuery() {
  const registrySelect = document.getElementById("registrySelect");
  const categorySelect = document.getElementById("categorySelect");
  const yearSelect = document.getElementById("yearSelect");
  
  const registry = registrySelect.value;
  const category = categorySelect.value;
  const year = yearSelect.value;
  
  if (!registry || !category || !year) {
    alert("Please select Registry, Category, and Year");
    return;
  }
  
  const fileNumberType = `${category}-${year}`;
  document.getElementById("resultValue").textContent = fileNumberType;
  document.getElementById("result").style.display = "block";
  
  // Log query for potential use
  console.log(`Query: Registry=${registry}, Category=${category}, Year=${year}, FileNumberType=${fileNumberType}`);
}
</script>

</div>

---

## Registry Details

### Registry 1 (Standard: 1981-1991)

| Category | Available Years | Examples |
|----------|-----------------|----------|
| RES | 1981-1991 | RES-1981, RES-1985, RES-1991 |
| COM | 1981-1991 | COM-1981, COM-1985, COM-1991 |
| IND | 1981-1991 | IND-1981, IND-1985, IND-1991 |
| AG | 1981-1991 | AG-1981, AG-1985, AG-1991 |
| RES-RC | 1981-1991 | RES-RC-1981, RES-RC-1985, RES-RC-1991 |
| COM-RC | 1981-1991 | COM-RC-1981, COM-RC-1985, COM-RC-1991 |
| IND-RC | 1981-1991 | IND-RC-1981, IND-RC-1985, IND-RC-1991 |
| AG-RC | 1981-1991 | AG-RC-1981, AG-RC-1985, AG-RC-1991 |

**Total Types:** 8 categories × 11 years = **88 file number types**

---

### Registry 2 (Standard: 1992-2025)

| Category | Available Years | Examples |
|----------|-----------------|----------|
| RES | 1992-2025 | RES-1992, RES-2000, RES-2025 |
| COM | 1992-2025 | COM-1992, COM-2000, COM-2025 |
| IND | 1992-2025 | IND-1992, IND-2000, IND-2025 |
| AG | 1992-2025 | AG-1992, AG-2000, AG-2025 |
| RES-RC | 1992-2025 | RES-RC-1992, RES-RC-2000, RES-RC-2025 |
| COM-RC | 1992-2025 | COM-RC-1992, COM-RC-2000, COM-RC-2025 |
| IND-RC | 1992-2025 | IND-RC-1992, IND-RC-2000, IND-RC-2025 |
| AG-RC | 1992-2025 | AG-RC-1992, AG-RC-2000, AG-RC-2025 |

**Total Types:** 8 categories × 34 years = **272 file number types**

---

### Registry 3 (Conversion: 1981-2025)

| Category | Available Years | Examples |
|----------|-----------------|----------|
| CON-RES | 1981-2025 | CON-RES-1981, CON-RES-2000, CON-RES-2025 |
| CON-COM | 1981-2025 | CON-COM-1981, CON-COM-2000, CON-COM-2025 |
| CON-IND | 1981-2025 | CON-IND-1981, CON-IND-2000, CON-IND-2025 |
| CON-AG | 1981-2025 | CON-AG-1981, CON-AG-2000, CON-AG-2025 |
| CON-RES-RC | 1981-2025 | CON-RES-RC-1981, CON-RES-RC-2000, CON-RES-RC-2025 |
| CON-COM-RC | 1981-2025 | CON-COM-RC-1981, CON-COM-RC-2000, CON-COM-RC-2025 |
| CON-IND-RC | 1981-2025 | CON-IND-RC-1981, CON-IND-RC-2000, CON-IND-RC-2025 |
| CON-AG-RC | 1981-2025 | CON-AG-RC-1981, CON-AG-RC-2000, CON-AG-RC-2025 |

**Total Types:** 8 categories × 45 years = **360 file number types**

---

## Query Examples

### Common Queries

| Query | Result |
|-------|--------|
| Registry 1 + RES + 1985 | RES-1985 |
| Registry 2 + COM + 2020 | COM-2020 |
| Registry 3 + CON-RES + 2025 | CON-RES-2025 |
| Registry 1 + IND-RC + 1990 | IND-RC-1990 |
| Registry 3 + CON-AG-RC + 1981 | CON-AG-RC-1981 |

### Query Patterns

- **Standard Residential (Registry 1, 1980s):** RES-1981, RES-1982, ..., RES-1991
- **Standard Commercial (Registry 2, 2000s):** COM-2000, COM-2001, ..., COM-2009
- **Conversion Industrial (Registry 3, All Years):** CON-IND-1981 through CON-IND-2025
- **Recertified Types (All Registries):** *-RC-YYYY patterns

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Registries | 3 |
| Total Categories | 16 |
| Total Years Spanned | 45 (1981-2025) |
| Total File Number Types | 720 |
| Registry 1 Types | 88 |
| Registry 2 Types | 272 |
| Registry 3 Types | 360 |

---

**Last Updated:** November 21, 2025  
**Version:** 1.0

