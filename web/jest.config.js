// Jest configuration to prevent hanging tests
module.exports = {
  // Set a global timeout for all tests (30 seconds)
  testTimeout: 30000,
  
  // Force exit after tests complete
  forceExit: true,
  
  // Limit the number of workers to prevent resource exhaustion
  maxWorkers: process.env.CI ? 2 : '50%',
  
  // Set a timeout for the test suite itself
  testRunner: 'jest-circus/runner',
  
  // Detect open handles that might cause tests to hang
  detectOpenHandles: true,
  
  // Inherit from the default create-react-app configuration
  preset: 'react-scripts',
  
  // Collect coverage from all relevant files
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/index.js',
    '!src/setupTests.js',
    '!src/**/*.test.{js,jsx}',
    '!src/**/*.spec.{js,jsx}'
  ],
  
  // Set coverage thresholds
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 75,
      statements: 75
    }
  },
  
  // Map file extensions for imports
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
  }
};