/* Main JavaScript functionality for Sensor Hub */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    SensorHub.init();
});

// Main application object
const SensorHub = {
    // Configuration
    config: {
        refreshInterval: 30000, // Default 30 seconds
        units: 'metric', // 'metric' or 'imperial'
        timezone: 'local', // Default to local timezone
        apiEndpoint: '/api',
        chartColors: {
            temperature: '#dc3545',
            humidity: '#007bff',
            pressure: '#28a745',
            dew_point: '#ffc107'
        }
    },

    // Initialize the application
    init: function() {
        // Load saved unit preference
        const savedUnits = localStorage.getItem('sensorHubUnits');
        if (savedUnits && (savedUnits === 'metric' || savedUnits === 'imperial')) {
            this.config.units = savedUnits;
            const unitSelect = document.getElementById('unit-select');
            if (unitSelect) {
                unitSelect.value = savedUnits;
            }
        }

        // Load saved timezone preference
        const savedTimezone = localStorage.getItem('sensorHubTimezone');
        if (savedTimezone) {
            this.config.timezone = savedTimezone;
            const timezoneSelect = document.getElementById('timezone-select');
            if (timezoneSelect) {
                timezoneSelect.value = savedTimezone;
            }
        }

        this.setupEventListeners();
        this.setupAutoRefresh();
        this.updateStatusIndicators();
        this.updateRefreshTimestamp();
        this.loadInitialSensorData(); // Load initial sensor data from template
        console.log('Sensor Hub initialized');
    },

    // Setup event listeners
    setupEventListeners: function() {
        // Refresh rate selector
        const refreshRateSelect = document.getElementById('refresh-rate-select');
        if (refreshRateSelect) {
            refreshRateSelect.addEventListener('change', function() {
                const newInterval = parseInt(this.value) * 1000; // Convert to milliseconds
                SensorHub.updateRefreshRate(newInterval);
            });
        }

        // Unit selector
        const unitSelect = document.getElementById('unit-select');
        if (unitSelect) {
            unitSelect.addEventListener('change', function() {
                SensorHub.updateUnits(this.value);
            });
        }

        // Timezone selector
        const timezoneSelect = document.getElementById('timezone-select');
        if (timezoneSelect) {
            timezoneSelect.addEventListener('change', function() {
                SensorHub.updateTimezone(this.value);
            });
        }

        // Time range selectors
        document.addEventListener('change', function(e) {
            if (e.target.matches('.time-range-select')) {
                SensorHub.updateTimeRange(e.target.value);
            }
        });

        // Listen for localStorage changes from other pages
        window.addEventListener('storage', function(e) {
            if (e.key === 'sensorHubUnits') {
                const unitSelect = document.getElementById('unit-select');
                if (unitSelect && unitSelect.value !== e.newValue) {
                    unitSelect.value = e.newValue;
                    SensorHub.config.units = e.newValue;
                    SensorHub.refreshSensors(); // Refresh to apply new units
                }
            } else if (e.key === 'sensorHubTimezone') {
                const timezoneSelect = document.getElementById('timezone-select');
                if (timezoneSelect && timezoneSelect.value !== e.newValue) {
                    timezoneSelect.value = e.newValue;
                    SensorHub.config.timezone = e.newValue;
                    SensorHub.refreshSensors(); // Refresh to apply new timezone
                }
            }
        });
    },

    // Load initial sensor data from template
    loadInitialSensorData: function() {
        const sensorCards = document.querySelectorAll('.sensor-card');
        sensorCards.forEach(card => {
            const rawDataScript = card.querySelector('.sensor-raw-data');
            if (rawDataScript) {
                try {
                    const rawData = JSON.parse(rawDataScript.textContent);
                    console.log('Loading initial data for sensor:', card.dataset.sensorId, rawData);
                    this.updateSensorDataDisplay(card, rawData);
                    // Remove the script tag as it's no longer needed
                    rawDataScript.remove();
                } catch (error) {
                    console.error('Error parsing initial sensor data:', error);
                }
            }
        });
    },

    // Refresh a specific sensor (used internally by auto-refresh)
    refreshSensor: function(sensorId) {
        console.log(`Refreshing sensor: ${sensorId}`);
        const sensorCard = document.querySelector(`[data-sensor-id="${sensorId}"]`);
        if (sensorCard) {
            console.log(`Found sensor card for: ${sensorId}`);
            this.setLoadingState(sensorCard, true);
            
            fetch(`${this.config.apiEndpoint}/sensors/${sensorId}`)
                .then(response => {
                    console.log(`API response for ${sensorId}:`, response.status);
                    return response.json();
                })
                .then(data => {
                    console.log(`Data received for ${sensorId}:`, data);
                    if (data.status === 'success') {
                        this.updateSensorCard(sensorCard, data.sensor);
                    } else {
                        this.showError(`Failed to refresh sensor ${sensorId}: ${data.error}`);
                    }
                })
                .catch(error => {
                    console.error(`Network error refreshing sensor ${sensorId}:`, error);
                    this.showError(`Network error refreshing sensor ${sensorId}: ${error.message}`);
                })
                .finally(() => {
                    this.setLoadingState(sensorCard, false);
                });
        } else {
            console.warn(`No sensor card found for: ${sensorId}`);
        }
    },

    // Refresh all sensors (used by auto-refresh)
    refreshAllSensors: function() {
        console.log('Auto-refreshing all sensors...');
        
        const sensorCards = document.querySelectorAll('.sensor-card');
        sensorCards.forEach(card => {
            const sensorId = card.dataset.sensorId;
            if (sensorId) {
                this.refreshSensor(sensorId);
            }
        });
        
        // Update refresh timestamp
        this.updateRefreshTimestamp();
    },

    // Update the refresh timestamp display
    updateRefreshTimestamp: function() {
        const timestampElement = document.getElementById('refresh-timestamp');
        if (timestampElement) {
            const now = new Date();
            timestampElement.textContent = now.toLocaleTimeString();
        }
    },

    // Update sensor card with new data
    updateSensorCard: function(card, sensorData) {
        // Update status badge
        const statusBadge = card.querySelector('.badge');
        if (statusBadge) {
            statusBadge.textContent = sensorData.status.charAt(0).toUpperCase() + sensorData.status.slice(1);
            statusBadge.className = `badge bg-${this.getStatusColor(sensorData.status)}`;
        }

        // Update last reading time
        const lastUpdate = card.querySelector('.last-update');
        if (lastUpdate && sensorData.last_reading_time) {
            lastUpdate.setAttribute('data-timestamp', sensorData.last_reading_time);
            
            try {
                // Parse as UTC timestamp using helper function
                const timestamp = this.parseUTCTimestamp(sensorData.last_reading_time);
                if (isNaN(timestamp.getTime())) {
                    console.error('Invalid timestamp:', sensorData.last_reading_time);
                    lastUpdate.textContent = 'Invalid time';
                } else {
                    lastUpdate.textContent = this.formatTimeAgo(timestamp);
                    // Add a title showing the full time in selected timezone
                    lastUpdate.title = `Last reading: ${this.formatTimestampInTimezone(sensorData.last_reading_time, this.config.timezone)}`;
                }
            } catch (error) {
                console.error('Error parsing timestamp:', error, sensorData.last_reading_time);
                lastUpdate.textContent = 'Time parse error';
            }
        }

        // Update sensor data if available
        if (sensorData.latest_reading && sensorData.latest_reading.data) {
            this.updateSensorDataDisplay(card, sensorData.latest_reading.data);
        }
    },

    // Update sensor data display
    updateSensorDataDisplay: function(card, data) {
        const dataContainer = card.querySelector('.sensor-data');
        if (!dataContainer) return;

        // Store the raw data on the card for unit conversion
        card.dataset.sensorRawData = JSON.stringify(data);

        // Get sensor type from the card to filter relevant fields
        const sensorType = this.getSensorTypeFromCard(card);
        const relevantFields = this.getRelevantFieldsForSensorType(sensorType, data);

        let html = '<div class="row">';
        
        Object.entries(relevantFields).forEach(([key, value]) => {
            html += `
                <div class="col-6 mb-2">
                    <div class="text-center p-2 bg-light rounded">
                        <div class="h4 mb-0 text-primary">
                            ${this.formatSensorValue(key, value)}
                        </div>
                        <small class="text-muted">${this.formatSensorLabel(key)}</small>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        dataContainer.innerHTML = html;
    },

    // Get sensor type from card
    getSensorTypeFromCard: function(card) {
        const sensorInfo = card.querySelector('.sensor-info');
        if (sensorInfo) {
            const typeText = sensorInfo.textContent;
            const match = typeText.match(/Type:\s*(\w+)/);
            return match ? match[1] : null;
        }
        return null;
    },

    // Get relevant fields for sensor type
    getRelevantFieldsForSensorType: function(sensorType, data) {
        const relevantFields = {};
        
        if (sensorType === 'ltr329') {
            // LTR-329 shows light level and IR level
            if (data.light_level !== null && data.light_level !== undefined) {
                relevantFields.light_level = data.light_level;
            }
            if (data.ir_level !== null && data.ir_level !== undefined) {
                relevantFields.ir_level = data.ir_level;
            }
        } else if (sensorType === 'bme280') {
            // BME280 shows temperature, humidity, pressure
            ['temperature', 'humidity', 'pressure', 'dew_point'].forEach(field => {
                if (data[field] !== null && data[field] !== undefined) {
                    relevantFields[field] = data[field];
                }
            });
        } else {
            // For unknown sensor types, show all non-null fields
            Object.entries(data).forEach(([key, value]) => {
                if (value !== null && value !== undefined) {
                    relevantFields[key] = value;
                }
            });
        }
        
        return relevantFields;
    },

    // Format sensor value for display
    formatSensorValue: function(key, value) {
        const formatters = {
            temperature: (v) => this.formatTemperature(parseFloat(v)),
            humidity: (v) => `${parseFloat(v).toFixed(1)}%`,
            pressure: (v) => this.formatPressure(parseFloat(v)),
            dew_point: (v) => this.formatTemperature(parseFloat(v)),
            light_level: (v) => `${Math.round(parseFloat(v))}`, // Raw CH0 value
            ir_level: (v) => `${Math.round(parseFloat(v))}`    // Raw CH1 value
        };
        
        return formatters[key] ? formatters[key](value) : value;
    },

    // Format sensor label for display
    formatSensorLabel: function(key) {
        const labels = {
            temperature: 'Temperature',
            humidity: 'Humidity',
            pressure: 'Pressure',
            dew_point: 'Dew Point',
            light_level: 'CH0 (Visible+IR)',
            ir_level: 'CH1 (IR Only)'
        };

        return labels[key] || key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    },

    // Get status color class
    getStatusColor: function(status) {
        const colors = {
            active: 'success',
            error: 'danger',
            unavailable: 'secondary',
            warning: 'warning'
        };
        return colors[status] || 'secondary';
    },

    // Set loading state on element
    setLoadingState: function(element, loading) {
        if (loading) {
            element.classList.add('loading');
            const refreshBtn = element.querySelector('.refresh-btn');
            if (refreshBtn) {
                refreshBtn.disabled = true;
                refreshBtn.innerHTML = '<span class="spinner"></span>';
            }
        } else {
            element.classList.remove('loading');
            const refreshBtn = element.querySelector('.refresh-btn');
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-sync me-1"></i>Refresh';
            }
        }
    },

    // Show error message
    showError: function(message) {
        console.error(message);
        
        // Show toast notification if available
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const toastHtml = `
                <div class="toast align-items-center text-white bg-danger border-0" role="alert">
                    <div class="d-flex">
                        <div class="toast-body">${message}</div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                                data-bs-dismiss="toast"></button>
                    </div>
                </div>
            `;
            
            let toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
                document.body.appendChild(toastContainer);
            }
            
            toastContainer.insertAdjacentHTML('beforeend', toastHtml);
            const toastElement = toastContainer.lastElementChild;
            const toast = new bootstrap.Toast(toastElement);
            toast.show();
            
            // Remove toast element after it's hidden
            toastElement.addEventListener('hidden.bs.toast', () => {
                toastElement.remove();
            });
        }
    },

    // Format timestamp to "X time ago" format
    formatTimeAgo: function(date) {
        if (!date || isNaN(date.getTime())) {
            return 'Invalid time';
        }
        
        const now = new Date();
        const diff = Math.floor((now - date) / 1000); // seconds

        // Handle negative time differences (future dates)
        if (diff < 0) {
            return `${Math.abs(diff)} seconds in future`;
        }

        if (diff < 60) {
            return `${diff} seconds ago`;
        } else if (diff < 3600) {
            return `${Math.floor(diff / 60)} minutes ago`;
        } else if (diff < 86400) {
            return `${Math.floor(diff / 3600)} hours ago`;
        } else {
            return `${Math.floor(diff / 86400)} days ago`;
        }
    },

    // Parse UTC timestamp properly
    parseUTCTimestamp: function(timestamp) {
        // If timestamp doesn't end with 'Z', assume it's UTC and add 'Z'
        const utcTimestamp = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
        return new Date(utcTimestamp);
    },

    // Format timestamp for display in selected timezone
    formatTimestampInTimezone: function(timestamp, timezone) {
        const date = this.parseUTCTimestamp(timestamp);
        if (isNaN(date.getTime())) {
            return 'Invalid time';
        }
        
        if (timezone === 'local') {
            return date.toLocaleString();
        } else if (timezone === 'UTC') {
            return date.toISOString().replace('T', ' ').replace('.000Z', ' UTC');
        } else {
            try {
                return date.toLocaleString('en-US', {
                    timeZone: timezone,
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    timeZoneName: 'short'
                });
            } catch (error) {
                console.error('Invalid timezone:', timezone, error);
                return date.toLocaleString(); // Fallback to local time
            }
        }
    },

    // Format timestamp for local display (backward compatibility)
    formatLocalTimestamp: function(timestamp) {
        return this.formatTimestampInTimezone(timestamp, this.config.timezone);
    },

    // Update status indicators  
    updateStatusIndicators: function() {
        // Update time displays that are already on the page
        const timeElements = document.querySelectorAll('.last-update[data-timestamp]');
        timeElements.forEach(element => {
            const timestamp = element.getAttribute('data-timestamp');
            if (timestamp) {
                // Parse as UTC timestamp using helper function
                const date = this.parseUTCTimestamp(timestamp);
                element.textContent = this.formatTimeAgo(date);
                // Update title with full local time
                element.title = `Last reading: ${this.formatLocalTimestamp(timestamp)}`;
            }
        });
    },

    // Setup auto-refresh (no manual controls)
    setupAutoRefresh: function() {
        // Initialize refresh rate display
        this.updateRefreshRateDisplay();
        
        // Start auto-refresh immediately
        this.startAutoRefresh();
        
        // Update timestamps every minute
        setInterval(() => {
            this.updateStatusIndicators();
        }, 60000);
    },

    // Start auto-refresh
    startAutoRefresh: function() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        console.log(`Starting auto-refresh with interval: ${this.config.refreshInterval}ms`);
        this.autoRefreshInterval = setInterval(() => {
            console.log('Auto-refresh triggered');
            this.refreshAllSensors();
        }, this.config.refreshInterval);
    },

    // Update refresh rate
    updateRefreshRate: function(newInterval) {
        this.config.refreshInterval = newInterval;
        console.log(`Refresh rate updated to ${newInterval/1000} seconds`);
        
        // Restart auto-refresh with new interval
        this.startAutoRefresh();
        
        // Update the display
        this.updateRefreshRateDisplay();
    },

    // Update refresh rate display
    updateRefreshRateDisplay: function() {
        const displayElement = document.getElementById('refresh-rate-display');
        if (displayElement) {
            const seconds = this.config.refreshInterval / 1000;
            if (seconds >= 60) {
                const minutes = Math.floor(seconds / 60);
                const remainingSeconds = seconds % 60;
                if (remainingSeconds === 0) {
                    displayElement.textContent = `${minutes}m`;
                } else {
                    displayElement.textContent = `${minutes}m ${remainingSeconds}s`;
                }
            } else {
                displayElement.textContent = `${seconds}s`;
            }
        }
    },

    // Update units
    updateUnits: function(newUnits) {
        this.config.units = newUnits;
        console.log(`Units updated to ${newUnits}`);
        
        // Update all displayed sensor data
        this.refreshAllSensorDisplays();
        
        // Store preference in localStorage
        localStorage.setItem('sensorHubUnits', newUnits);
    },

    // Update timezone
    updateTimezone: function(newTimezone) {
        this.config.timezone = newTimezone;
        console.log(`Timezone updated to ${newTimezone}`);
        
        // Update all displayed timestamps
        this.refreshAllTimestamps();
        
        // Store preference in localStorage
        localStorage.setItem('sensorHubTimezone', newTimezone);
    },

    // Refresh all timestamps with new timezone
    refreshAllTimestamps: function() {
        // Update status indicators with new timezone
        this.updateStatusIndicators();
        
        // Update refresh timestamp
        this.updateRefreshTimestamp();
        
        // If there are any chart displays that need updating, refresh them
        const sensorCards = document.querySelectorAll('.sensor-card');
        sensorCards.forEach(card => {
            const lastUpdate = card.querySelector('.last-update');
            if (lastUpdate) {
                const timestamp = lastUpdate.getAttribute('data-timestamp');
                if (timestamp) {
                    const date = this.parseUTCTimestamp(timestamp);
                    lastUpdate.textContent = this.formatTimeAgo(date);
                    lastUpdate.title = `Last reading: ${this.formatTimestampInTimezone(timestamp, this.config.timezone)}`;
                }
            }
        });
    },

    convertPressure: function(hpa) {
        if (this.config.units === 'imperial') {
            return hpa * 0.02953; // Convert hPa to inHg
        }
        return hpa;
    },

    convertTemperature: function(celsius) {
        if (this.config.units === 'imperial') {
            return (celsius * 9/5) + 32;
        }
        return celsius;
    },

    getTemperatureUnit: function() {
        return this.config.units === 'imperial' ? '°F' : '°C';
    },

    getPressureUnit: function() {
        return this.config.units === 'imperial' ? ' inHg' : ' hPa';
    },

    formatTemperature: function(celsius) {
        const converted = this.convertTemperature(celsius);
        return `${converted.toFixed(1)}${this.getTemperatureUnit()}`;
    },

    formatPressure: function(hpa) {
        const converted = this.convertPressure(hpa);
        const decimals = this.config.units === 'imperial' ? 2 : 1;
        return `${converted.toFixed(decimals)}${this.getPressureUnit()}`;
    },

    // Refresh all sensor displays with current unit settings
    refreshAllSensorDisplays: function() {
        const sensorCards = document.querySelectorAll('.sensor-card');
        sensorCards.forEach(card => {
            // Get stored raw sensor data and re-display with new units
            const rawDataString = card.dataset.sensorRawData;
            if (rawDataString) {
                try {
                    const rawData = JSON.parse(rawDataString);
                    this.updateSensorDataDisplay(card, rawData);
                } catch (error) {
                    console.error('Error parsing stored sensor data:', error);
                    // Fallback to re-fetching data
                    const sensorId = card.dataset.sensorId;
                    if (sensorId) {
                        this.refreshSensor(sensorId);
                    }
                }
            } else {
                // No stored data, re-fetch
                const sensorId = card.dataset.sensorId;
                if (sensorId) {
                    this.refreshSensor(sensorId);
                }
            }
        });
    },

    // Update time range (for charts and data views)
    updateTimeRange: function(hours) {
        const currentUrl = new URL(window.location);
        currentUrl.searchParams.set('hours', hours);
        window.location.href = currentUrl.toString();
    },

    // Utility functions
    utils: {
        // Debounce function calls
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        // Throttle function calls
        throttle: function(func, limit) {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        }
    }
};

// Export for use in other scripts
window.SensorHub = SensorHub;
