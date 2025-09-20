#!/bin/bash

# Sensor Hub Test Runner
# Comprehensive test execution script with multiple options

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_status() {
    local status="$1"
    local message="$2"
    case "$status" in
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "error") echo -e "${RED}❌ $message${NC}" ;;
        "info") echo -e "${BLUE}ℹ️  $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "running") echo -e "${CYAN}🔄 $message${NC}" ;;
    esac
}

print_header() {
    echo
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Function to check if poetry is available
check_poetry() {
    if ! command -v poetry &> /dev/null; then
        print_status "error" "Poetry not found. Please install Poetry first."
        exit 1
    fi
}

# Function to install test dependencies
install_test_deps() {
    print_status "info" "Installing test dependencies..."
    poetry install --with dev
    
    # Install additional test packages if not in pyproject.toml
    poetry add --group dev pytest-timeout pytest-mock factory-boy
}

# Function to run unit tests
run_unit_tests() {
    print_header "🧪 Running Unit Tests"
    
    print_status "running" "Executing unit tests..."
    poetry run pytest tests/unit/ \
        --tb=short \
        --cov=src/sensor_hub \
        --cov-report=term-missing \
        --cov-report=html:htmlcov/unit \
        -m "unit" \
        -v
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_status "success" "Unit tests passed!"
    else
        print_status "error" "Unit tests failed!"
        return $exit_code
    fi
}

# Function to run integration tests
run_integration_tests() {
    print_header "🔗 Running Integration Tests"
    
    print_status "running" "Executing integration tests..."
    poetry run pytest tests/integration/ \
        --tb=short \
        --cov=src/sensor_hub \
        --cov-report=term-missing \
        --cov-report=html:htmlcov/integration \
        -m "integration" \
        -v
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_status "success" "Integration tests passed!"
    else
        print_status "error" "Integration tests failed!"
        return $exit_code
    fi
}

# Function to run all tests
run_all_tests() {
    print_header "🚀 Running Complete Test Suite"
    
    print_status "running" "Executing all tests..."
    poetry run pytest tests/ \
        --tb=short \
        --cov=src/sensor_hub \
        --cov-report=term-missing \
        --cov-report=html:htmlcov/complete \
        --cov-fail-under=75 \
        --durations=10 \
        -v
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_status "success" "All tests passed!"
    else
        print_status "error" "Some tests failed!"
        return $exit_code
    fi
}

# Function to run quick tests (no coverage)
run_quick_tests() {
    print_header "⚡ Running Quick Tests"
    
    print_status "running" "Executing quick test run..."
    poetry run pytest tests/ \
        --tb=line \
        -x \
        -q
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_status "success" "Quick tests passed!"
    else
        print_status "error" "Quick tests failed!"
        return $exit_code
    fi
}

# Function to run specific test file or function
run_specific_test() {
    local test_path="$1"
    print_header "🎯 Running Specific Test: $test_path"
    
    print_status "running" "Executing $test_path..."
    poetry run pytest "$test_path" \
        --tb=short \
        -v
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_status "success" "Test passed!"
    else
        print_status "error" "Test failed!"
        return $exit_code
    fi
}

# Function to run tests with specific markers
run_marked_tests() {
    local marker="$1"
    print_header "🏷️  Running Tests with Marker: $marker"
    
    print_status "running" "Executing tests marked with '$marker'..."
    poetry run pytest tests/ \
        -m "$marker" \
        --tb=short \
        -v
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_status "success" "Marked tests passed!"
    else
        print_status "error" "Marked tests failed!"
        return $exit_code
    fi
}

# Function to generate coverage report
generate_coverage_report() {
    print_header "📊 Generating Coverage Report"
    
    print_status "running" "Generating comprehensive coverage report..."
    
    # Run tests with coverage
    poetry run pytest tests/ \
        --cov=src/sensor_hub \
        --cov-report=html:htmlcov \
        --cov-report=xml:coverage.xml \
        --cov-report=term-missing \
        --cov-fail-under=70 \
        --quiet
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_status "success" "Coverage report generated!"
        print_status "info" "HTML report: htmlcov/index.html"
        print_status "info" "XML report: coverage.xml"
    else
        print_status "warning" "Coverage below threshold or tests failed"
        return $exit_code
    fi
}

# Function to lint test code
lint_tests() {
    print_header "🔍 Linting Test Code"
    
    if command -v flake8 &> /dev/null; then
        print_status "running" "Running flake8 on test code..."
        poetry run flake8 tests/ --max-line-length=88 --extend-ignore=E203,W503
        
        if [ $? -eq 0 ]; then
            print_status "success" "Test code linting passed!"
        else
            print_status "warning" "Test code has linting issues"
        fi
    else
        print_status "info" "flake8 not available, skipping test linting"
    fi
}

# Function to run tests in watch mode
watch_tests() {
    print_header "👀 Running Tests in Watch Mode"
    
    if command -v pytest-watch &> /dev/null; then
        print_status "info" "Starting test watch mode (press Ctrl+C to stop)..."
        poetry run ptw tests/ -- --tb=short -q
    else
        print_status "warning" "pytest-watch not installed. Install with: pip install pytest-watch"
        print_status "info" "Falling back to single test run..."
        run_quick_tests
    fi
}

# Function to clean test artifacts
clean_test_artifacts() {
    print_header "🧹 Cleaning Test Artifacts"
    
    print_status "running" "Removing test artifacts..."
    
    # Remove coverage files
    rm -rf htmlcov/
    rm -f coverage.xml
    rm -f .coverage
    
    # Remove pytest cache
    rm -rf .pytest_cache/
    rm -rf tests/__pycache__/
    rm -rf tests/*/__pycache__/
    
    # Remove Python cache files
    find tests/ -name "*.pyc" -delete
    find tests/ -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    print_status "success" "Test artifacts cleaned!"
}

# Function to show test statistics
show_test_stats() {
    print_header "📈 Test Statistics"
    
    print_status "info" "Collecting test statistics..."
    
    # Count test files and functions
    local unit_tests=$(find tests/unit -name "test_*.py" | wc -l)
    local integration_tests=$(find tests/integration -name "test_*.py" | wc -l)
    local total_test_functions=$(grep -r "def test_" tests/ | wc -l)
    
    echo
    echo -e "${CYAN}Test Files:${NC}"
    echo "  Unit test files: $unit_tests"
    echo "  Integration test files: $integration_tests"
    echo "  Total test functions: $total_test_functions"
    
    # Show recent test results if available
    if [ -f ".pytest_cache/v/cache/lastfailed" ]; then
        echo
        echo -e "${CYAN}Recent Test Results:${NC}"
        local failed_count=$(cat .pytest_cache/v/cache/lastfailed | grep -o '"' | wc -l)
        failed_count=$((failed_count / 2))
        if [ $failed_count -gt 0 ]; then
            print_status "warning" "$failed_count tests failed in last run"
        else
            print_status "success" "All tests passed in last run"
        fi
    fi
}

# Function to show help
show_help() {
    echo -e "${BOLD}${CYAN}Sensor Hub Test Runner${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./run_tests.sh [command] [options]"
    echo
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${GREEN}all${NC}          Run complete test suite with coverage"
    echo -e "  ${GREEN}unit${NC}         Run unit tests only"
    echo -e "  ${GREEN}integration${NC}  Run integration tests only"
    echo -e "  ${GREEN}quick${NC}        Run quick tests (no coverage)"
    echo -e "  ${GREEN}coverage${NC}     Generate coverage report"
    echo -e "  ${GREEN}lint${NC}         Lint test code"
    echo -e "  ${GREEN}watch${NC}        Run tests in watch mode"
    echo -e "  ${GREEN}clean${NC}        Clean test artifacts"
    echo -e "  ${GREEN}stats${NC}        Show test statistics"
    echo -e "  ${GREEN}install${NC}      Install test dependencies"
    echo -e "  ${GREEN}help${NC}         Show this help message"
    echo
    echo -e "${BOLD}Specific Test Execution:${NC}"
    echo "  ./run_tests.sh file <test_file>     Run specific test file"
    echo "  ./run_tests.sh marker <marker>      Run tests with specific marker"
    echo
    echo -e "${BOLD}Examples:${NC}"
    echo "  ./run_tests.sh all                  # Run all tests"
    echo "  ./run_tests.sh unit                 # Run unit tests only"
    echo "  ./run_tests.sh file tests/unit/test_models.py"
    echo "  ./run_tests.sh marker api           # Run API tests"
    echo
    echo -e "${BOLD}Available Markers:${NC}"
    echo "  unit, integration, api, models, sensors, web, slow, hardware"
}

# Main execution
case "${1:-help}" in
    "all")
        check_poetry
        run_all_tests
        ;;
    "unit") 
        check_poetry
        run_unit_tests
        ;;
    "integration")
        check_poetry
        run_integration_tests
        ;;
    "quick")
        check_poetry
        run_quick_tests
        ;;
    "file")
        if [ -z "$2" ]; then
            print_status "error" "Please specify a test file"
            exit 1
        fi
        check_poetry
        run_specific_test "$2"
        ;;
    "marker")
        if [ -z "$2" ]; then
            print_status "error" "Please specify a test marker"
            exit 1
        fi
        check_poetry
        run_marked_tests "$2"
        ;;
    "coverage")
        check_poetry
        generate_coverage_report
        ;;
    "lint")
        check_poetry
        lint_tests
        ;;
    "watch")
        check_poetry
        watch_tests
        ;;
    "clean")
        clean_test_artifacts
        ;;
    "stats")
        show_test_stats
        ;;
    "install")
        check_poetry
        install_test_deps
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo
        show_help
        exit 1
        ;;
esac