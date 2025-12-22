# Instagram Token Refresh Test Suite

This test suite provides comprehensive testing for the Instagram token refresh functionality implemented in the hair similarity application.

## Test Structure

### Core Tests (`test_instagram_token_refresh.py`)
- **Token Management Tests**: Test loading, saving, and refreshing of Instagram tokens
- **API Request Tests**: Test the `make_instagram_request` function with automatic retry
- **Integration Tests**: Test Instagram API functions with token refresh integration

### Registration Flow Tests (`test_registration_with_token_refresh.py`)
- **Creator Profile Creation**: Test registration flow with valid Instagram data
- **Fallback Mechanism**: Test fallback to mock data when Instagram API fails
- **Token Refresh Integration**: Test token refresh during registration process

### Performance Tests (`test_performance.py`)
- **Token Caching Performance**: Test that token caching improves performance
- **API Retry Performance**: Test performance of retry mechanism
- **Concurrent Access**: Test thread safety of token refresh
- **Memory Usage**: Test memory efficiency of token operations

## Running Tests

### Run All Tests
```bash
python tests/test_runner.py
```

### Run Specific Test Files
```bash
# Core token refresh tests
python tests/test_instagram_token_refresh.py

# Registration flow tests
python tests/test_registration_with_token_refresh.py

# Performance tests
python tests/test_performance.py
```

### Run with Verbose Output
```bash
python -m unittest tests.test_instagram_token_refresh -v
```

## Test Coverage

The test suite covers:

### ✅ Token Management
- Loading token info from file
- Saving token info to file
- Handling file corruption
- Token refresh API calls
- Fallback to original token

### ✅ API Request Handling
- Successful API requests
- Token error detection and retry
- Maximum retry limits
- Network error handling

### ✅ Registration Flow Integration
- Creator profile creation with valid Instagram data
- Fallback to mock data when Instagram fails
- Token refresh during registration
- Database integration

### ✅ Performance and Reliability
- Token caching performance
- Concurrent access safety
- Memory usage efficiency
- Large response handling

## Mock Data

The tests use mock data to avoid making real Instagram API calls:

- **Mock Tokens**: Test tokens that simulate real Instagram access tokens
- **Mock Responses**: Simulated Instagram API responses
- **Mock Errors**: Simulated API errors for testing error handling

## Test Configuration

Test configuration is managed in `test_config.py`:

- **Test Credentials**: Mock Instagram API credentials
- **Performance Thresholds**: Maximum acceptable times for operations
- **Test Data**: Mock data for consistent testing

## Expected Test Results

When all tests pass, you should see:

```
Tests run: 25
Failures: 0
Errors: 0
Success rate: 100.0%
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure the app directory is in the Python path
2. **File Permission Errors**: Ensure write permissions for test files
3. **Mock Failures**: Check that mock objects are properly configured

### Debug Mode

Run tests with debug output:
```bash
python -m unittest tests.test_instagram_token_refresh -v -s
```

## Adding New Tests

To add new tests:

1. Create a new test file following the naming pattern `test_*.py`
2. Import the necessary modules and test classes
3. Create test methods starting with `test_`
4. Use appropriate assertions and mocks
5. Add the new test file to the test runner

## Test Data Cleanup

Tests automatically clean up:
- Temporary token files
- Test data directories
- Mock files

No manual cleanup is required.
