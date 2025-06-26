#!/usr/bin/env node

/**
 * Test validation script for IntentVerse Web UI
 * Validates test file syntax and structure without running them
 */

const fs = require('fs');
const path = require('path');

// ANSI color codes for console output
const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
  bold: '\x1b[1m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function findTestFiles(dir) {
  const testFiles = [];
  
  function scanDirectory(currentDir) {
    const items = fs.readdirSync(currentDir);
    
    for (const item of items) {
      const fullPath = path.join(currentDir, item);
      const stat = fs.statSync(fullPath);
      
      if (stat.isDirectory() && !item.startsWith('.') && item !== 'node_modules') {
        scanDirectory(fullPath);
      } else if (stat.isFile() && (item.endsWith('.test.js') || item.endsWith('.test.jsx'))) {
        testFiles.push(fullPath);
      }
    }
  }
  
  scanDirectory(dir);
  return testFiles;
}

function validateTestFile(filePath) {
  const issues = [];
  
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    
    // Check for basic test structure
    if (!content.includes('describe(')) {
      issues.push('Missing describe() block');
    }
    
    if (!content.includes('it(') && !content.includes('test(')) {
      issues.push('Missing test cases (it() or test())');
    }
    
    // Check for proper imports
    if (content.includes('from \'react\'') && !content.includes('import React')) {
      issues.push('Missing React import');
    }
    
    if (content.includes('@testing-library/react') && !content.includes('render')) {
      issues.push('Missing render import from @testing-library/react');
    }
    
    // Check for mock cleanup
    if (content.includes('jest.mock') && !content.includes('jest.clearAllMocks')) {
      issues.push('Consider adding jest.clearAllMocks() in beforeEach()');
    }
    
    // Check for async test handling
    if (content.includes('await ') && !content.includes('waitFor')) {
      issues.push('Async operations should use waitFor() for proper testing');
    }
    
    // Check for accessibility considerations
    if (content.includes('getByRole') || content.includes('getByLabelText')) {
      // Good - using accessible queries
    } else if (content.includes('getByTestId')) {
      // Acceptable but suggest accessible alternatives
    }
    
    return { valid: issues.length === 0, issues };
    
  } catch (error) {
    return { valid: false, issues: [`File read error: ${error.message}`] };
  }
}

function generateTestSummary(testFiles) {
  const summary = {
    total: testFiles.length,
    valid: 0,
    withIssues: 0,
    coverage: {
      api: 0,
      components: 0,
      pages: 0,
      app: 0
    }
  };
  
  testFiles.forEach(file => {
    const validation = validateTestFile(file);
    
    if (validation.valid) {
      summary.valid++;
    } else {
      summary.withIssues++;
    }
    
    // Categorize test files
    if (file.includes('/api/')) summary.coverage.api++;
    else if (file.includes('/components/')) summary.coverage.components++;
    else if (file.includes('/pages/')) summary.coverage.pages++;
    else if (file.includes('App.test')) summary.coverage.app++;
  });
  
  return summary;
}

function main() {
  log('🧪 IntentVerse Web UI Test Validation', 'bold');
  log('=====================================\n', 'bold');
  
  const srcDir = path.join(__dirname, 'src');
  
  if (!fs.existsSync(srcDir)) {
    log('❌ Source directory not found: ' + srcDir, 'red');
    process.exit(1);
  }
  
  log('📁 Scanning for test files...', 'blue');
  const testFiles = findTestFiles(srcDir);
  
  if (testFiles.length === 0) {
    log('❌ No test files found!', 'red');
    process.exit(1);
  }
  
  log(`✅ Found ${testFiles.length} test files\n`, 'green');
  
  // Validate each test file
  let allValid = true;
  
  testFiles.forEach(file => {
    const relativePath = path.relative(srcDir, file);
    const validation = validateTestFile(file);
    
    if (validation.valid) {
      log(`✅ ${relativePath}`, 'green');
    } else {
      log(`⚠️  ${relativePath}`, 'yellow');
      validation.issues.forEach(issue => {
        log(`   - ${issue}`, 'yellow');
      });
      allValid = false;
    }
  });
  
  // Generate summary
  log('\n📊 Test Suite Summary', 'bold');
  log('====================', 'bold');
  
  const summary = generateTestSummary(testFiles);
  
  log(`Total test files: ${summary.total}`, 'blue');
  log(`Valid files: ${summary.valid}`, 'green');
  log(`Files with issues: ${summary.withIssues}`, summary.withIssues > 0 ? 'yellow' : 'green');
  
  log('\n📈 Coverage by Category:', 'bold');
  log(`API tests: ${summary.coverage.api}`, 'blue');
  log(`Component tests: ${summary.coverage.components}`, 'blue');
  log(`Page tests: ${summary.coverage.pages}`, 'blue');
  log(`App tests: ${summary.coverage.app}`, 'blue');
  
  // Test file list
  log('\n📋 Test Files:', 'bold');
  testFiles.forEach(file => {
    const relativePath = path.relative(srcDir, file);
    log(`   ${relativePath}`, 'blue');
  });
  
  log('\n🎯 Test Framework Configuration:', 'bold');
  log('   Framework: Jest + React Testing Library', 'blue');
  log('   Coverage threshold: 70% (branches, functions, lines, statements)', 'blue');
  log('   Setup file: setupTests.js', 'blue');
  log('   Mock strategy: API mocking + component isolation', 'blue');
  
  if (allValid) {
    log('\n🎉 All test files are valid and ready to run!', 'green');
    log('Run "npm test" to execute the test suite.', 'green');
  } else {
    log('\n⚠️  Some test files have issues that should be addressed.', 'yellow');
    log('These are suggestions for improvement, not blocking errors.', 'yellow');
  }
  
  log('\n📚 For detailed testing documentation, see: TEST_DOCUMENTATION.md', 'blue');
}

if (require.main === module) {
  main();
}

module.exports = { findTestFiles, validateTestFile, generateTestSummary };