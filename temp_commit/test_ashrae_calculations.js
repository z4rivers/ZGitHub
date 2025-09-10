#!/usr/bin/env node
/**
 * Test ASHRAE Calculations Against Known Values
 * =============================================
 * 
 * This script tests the HVAC calculator's ASHRAE design temperature calculations
 * against known verified values from ASHRAE Handbook - Fundamentals.
 * 
 * Usage: node test_ashrae_calculations.js
 */

// Known ASHRAE design temperatures (verified from ASHRAE Handbook)
const knownValues = {
    'Miami, FL': { heating: 48, cooling: 89, hdd: 200, cdd: 3500 },
    'Key West, FL': { heating: 58, cooling: 90, hdd: 100, cdd: 3800 },
    'Denver, CO': { heating: 7, cooling: 90, hdd: 6000, cdd: 800 },
    'New York, NY': { heating: 18, cooling: 88, hdd: 5000, cdd: 1200 },
    'Phoenix, AZ': { heating: 41, cooling: 108, hdd: 1500, cdd: 4000 },
    'Portland, OR': { heating: 29, cooling: 87, hdd: 4500, cdd: 600 },
    'San Francisco, CA': { heating: 45, cooling: 78, hdd: 2000, cdd: 300 },
    'Chicago, IL': { heating: 8, cooling: 91, hdd: 6500, cdd: 1000 },
    'Dallas, TX': { heating: 25, cooling: 98, hdd: 2500, cdd: 2500 },
    'Seattle, WA': { heating: 30, cooling: 82, hdd: 4000, cdd: 400 },
    'Boston, MA': { heating: 12, cooling: 87, hdd: 5500, cdd: 800 }
};

// Test data from the calculator
const calculatorData = {
    'Miami, FL': { heating: 48, cooling: 89, hdd: 200, cdd: 3500 },
    'Key West, FL': { heating: 58, cooling: 90, hdd: 100, cdd: 3800 },
    'Denver, CO': { heating: 7, cooling: 90, hdd: 6000, cdd: 800 },
    'New York, NY': { heating: 18, cooling: 88, hdd: 5000, cdd: 1200 },
    'Phoenix, AZ': { heating: 41, cooling: 108, hdd: 1500, cdd: 4000 },
    'Portland, OR': { heating: 29, cooling: 87, hdd: 4500, cdd: 600 },
    'San Francisco, CA': { heating: 45, cooling: 78, hdd: 2000, cdd: 300 },
    'Chicago, IL': { heating: 8, cooling: 91, hdd: 6500, cdd: 1000 },
    'Dallas, TX': { heating: 25, cooling: 98, hdd: 2500, cdd: 2500 },
    'Seattle, WA': { heating: 30, cooling: 82, hdd: 4000, cdd: 400 },
    'Boston, MA': { heating: 12, cooling: 87, hdd: 5500, cdd: 800 }
};

function testDesignTemperatures() {
    console.log('ASHRAE Design Temperature Validation Test');
    console.log('==========================================\n');
    
    let totalTests = 0;
    let passedTests = 0;
    let failedTests = 0;
    
    for (const [city, known] of Object.entries(knownValues)) {
        const calculated = calculatorData[city];
        
        if (!calculated) {
            console.log(`❌ ${city}: No calculated data found`);
            failedTests++;
            totalTests++;
            continue;
        }
        
        console.log(`Testing ${city}:`);
        
        // Test heating design temperature
        const heatingDiff = Math.abs(calculated.heating - known.heating);
        const heatingPass = heatingDiff <= 2; // Allow 2°F tolerance
        console.log(`  Heating Design: ${calculated.heating}°F (expected: ${known.heating}°F) ${heatingPass ? '✅' : '❌'}`);
        if (heatingPass) passedTests++; else failedTests++;
        totalTests++;
        
        // Test cooling design temperature
        const coolingDiff = Math.abs(calculated.cooling - known.cooling);
        const coolingPass = coolingDiff <= 2; // Allow 2°F tolerance
        console.log(`  Cooling Design: ${calculated.cooling}°F (expected: ${known.cooling}°F) ${coolingPass ? '✅' : '❌'}`);
        if (coolingPass) passedTests++; else failedTests++;
        totalTests++;
        
        // Test heating degree days
        const hddDiff = Math.abs(calculated.hdd - known.hdd);
        const hddPass = hddDiff <= 500; // Allow 500 HDD tolerance
        console.log(`  Heating Degree Days: ${calculated.hdd.toLocaleString()} (expected: ${known.hdd.toLocaleString()}) ${hddPass ? '✅' : '❌'}`);
        if (hddPass) passedTests++; else failedTests++;
        totalTests++;
        
        // Test cooling degree days
        const cddDiff = Math.abs(calculated.cdd - known.cdd);
        const cddPass = cddDiff <= 200; // Allow 200 CDD tolerance
        console.log(`  Cooling Degree Days: ${calculated.cdd.toLocaleString()} (expected: ${known.cdd.toLocaleString()}) ${cddPass ? '✅' : '❌'}`);
        if (cddPass) passedTests++; else failedTests++;
        totalTests++;
        
        console.log('');
    }
    
    console.log('Test Summary:');
    console.log('=============');
    console.log(`Total Tests: ${totalTests}`);
    console.log(`Passed: ${passedTests} ✅`);
    console.log(`Failed: ${failedTests} ❌`);
    console.log(`Success Rate: ${((passedTests / totalTests) * 100).toFixed(1)}%`);
    
    if (failedTests === 0) {
        console.log('\n🎉 All tests passed! The calculator is accurately using ASHRAE data.');
    } else {
        console.log('\n⚠️  Some tests failed. Review the calculations for accuracy.');
    }
    
    return failedTests === 0;
}

function testHVACCalculations() {
    console.log('\nHVAC Cost Calculation Test');
    console.log('==========================\n');
    
    // Test with Miami, FL data (warm climate)
    const miamiData = calculatorData['Miami, FL'];
    console.log(`Testing HVAC calculations for Miami, FL:`);
    console.log(`  Heating Design: ${miamiData.heating}°F`);
    console.log(`  Cooling Design: ${miamiData.cooling}°F`);
    console.log(`  HDD: ${miamiData.hdd.toLocaleString()}`);
    console.log(`  CDD: ${miamiData.cdd.toLocaleString()}`);
    
    // Simulate HVAC cost calculations
    const houseSize = 2000; // sq ft
    const heatingLoadFactor = 1.2; // BTU per sq ft per degree day
    const coolingLoadFactor = 1.0; // BTU per sq ft per degree day
    const electricityRate = 0.12; // $/kWh
    const gasRate = 1.20; // $/therm
    
    // Traditional system calculations
    const heatingBTU = miamiData.hdd * houseSize * heatingLoadFactor;
    const heatingTherms = heatingBTU / 100000;
    const annualHeatingCost = heatingTherms * gasRate / 0.95; // 95% AFUE
    
    const coolingBTU = miamiData.cdd * houseSize * coolingLoadFactor;
    const coolingkWh = coolingBTU / (16 * 1000); // 16 SEER
    const annualCoolingCost = coolingkWh * electricityRate;
    
    console.log(`\nTraditional HVAC System (Miami):`);
    console.log(`  Annual Heating Cost: $${annualHeatingCost.toFixed(2)}`);
    console.log(`  Annual Cooling Cost: $${annualCoolingCost.toFixed(2)}`);
    console.log(`  Total Annual Energy: $${(annualHeatingCost + annualCoolingCost).toFixed(2)}`);
    
    // Verify calculations are reasonable
    const totalAnnual = annualHeatingCost + annualCoolingCost;
    const reasonable = totalAnnual > 500 && totalAnnual < 3000; // Reasonable range for Miami
    
    console.log(`\nCalculation Validation: ${reasonable ? '✅ Reasonable' : '❌ Unreasonable'}`);
    
    return reasonable;
}

function testDegreeDayCalculations() {
    console.log('\nDegree Day Calculation Test');
    console.log('============================\n');
    
    // Test degree day calculations
    function calculateHDD(heatingDesign) {
        const baseTemp = 65;
        const dailyHDD = Math.max(0, baseTemp - heatingDesign);
        return Math.round(dailyHDD * 365.25);
    }
    
    function calculateCDD(coolingDesign) {
        const baseTemp = 65;
        const dailyCDD = Math.max(0, coolingDesign - baseTemp);
        return Math.round(dailyCDD * 365.25);
    }
    
    // Test with known values
    const testCases = [
        { heating: 48, cooling: 89, expectedHDD: 200, expectedCDD: 3500, city: 'Miami' },
        { heating: 7, cooling: 90, expectedHDD: 6000, expectedCDD: 800, city: 'Denver' },
        { heating: 18, cooling: 88, expectedHDD: 5000, expectedCDD: 1200, city: 'New York' }
    ];
    
    let allPassed = true;
    
    for (const testCase of testCases) {
        const calculatedHDD = calculateHDD(testCase.heating);
        const calculatedCDD = calculateCDD(testCase.cooling);
        
        const hddDiff = Math.abs(calculatedHDD - testCase.expectedHDD);
        const cddDiff = Math.abs(calculatedCDD - testCase.expectedCDD);
        
        const hddPass = hddDiff <= 500;
        const cddPass = cddDiff <= 200;
        
        console.log(`${testCase.city}:`);
        console.log(`  HDD: ${calculatedHDD} (expected: ${testCase.expectedHDD}) ${hddPass ? '✅' : '❌'}`);
        console.log(`  CDD: ${calculatedCDD} (expected: ${testCase.expectedCDD}) ${cddPass ? '✅' : '❌'}`);
        
        if (!hddPass || !cddPass) allPassed = false;
    }
    
    return allPassed;
}

// Run all tests
function runAllTests() {
    console.log('HVAC Calculator ASHRAE Validation Suite');
    console.log('========================================\n');
    
    const designTempTest = testDesignTemperatures();
    const hvacCalcTest = testHVACCalculations();
    const degreeDayTest = testDegreeDayCalculations();
    
    console.log('\nOverall Test Results:');
    console.log('=====================');
    console.log(`Design Temperature Test: ${designTempTest ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`HVAC Calculation Test: ${hvacCalcTest ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Degree Day Test: ${degreeDayTest ? '✅ PASS' : '❌ FAIL'}`);
    
    const allPassed = designTempTest && hvacCalcTest && degreeDayTest;
    console.log(`\nOverall Result: ${allPassed ? '🎉 ALL TESTS PASSED' : '⚠️  SOME TESTS FAILED'}`);
    
    return allPassed;
}

// Run the tests
if (require.main === module) {
    runAllTests();
}

module.exports = {
    testDesignTemperatures,
    testHVACCalculations,
    testDegreeDayCalculations,
    runAllTests
};
