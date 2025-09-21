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
        console.log('SensorHub: Loading initial sensor data...');
        const sensorCards = document.querySelectorAll('.sensor-card');
        console.log('SensorHub: Found', sensorCards.length, 'sensor cards');
        
        sensorCards.forEach((card, index) => {
            console.log('SensorHub: Processing card', index, 'with ID:', card.dataset.sensorId);
            const rawDataScript = card.querySelector('.sensor-raw-data');
            
            if (rawDataScript) {
                try {
                    const rawData = JSON.parse(rawDataScript.textContent);
                    console.log('SensorHub: Raw data for', card.dataset.sensorId, ':', rawData);
                    this.updateSensorDataDisplay(card, rawData);
                    rawDataScript.remove();
                    console.log('SensorHub: Successfully updated display for', card.dataset.sensorId);
                } catch (error) {
                    console.error('SensorHub: Error parsing sensor data for', card.dataset.sensorId, ':', error);
                }
            } else {
                console.log('SensorHub: No raw data script found for card', card.dataset.sensorId);
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
            
            // Fetch current sensor data for all sensors and filter by sensorId
            fetch(`${this.config.apiEndpoint}/sensors/current`)
                .then(response => {
                    console.log(`API response for current sensors:`, response.status);
                    return response.json();
                })
                .then(data => {
                    console.log(`Current sensors data received:`, data);
                    if (data.sensors) {
                        // Find the specific sensor in the response
                        const sensorData = data.sensors.find(s => s.sensor_id === sensorId);
                        if (sensorData) {
                            console.log(`Data found for ${sensorId}:`, sensorData);
                            this.updateSensorCard(sensorCard, sensorData);
                        } else {
                            console.warn(`No data found for sensor ${sensorId}`);
                            this.showError(`No data available for sensor ${sensorId}`);
                        }
                    } else {
                        this.showError(`Invalid response format from sensors API`);
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
        if (lastUpdate && sensorData.latest_reading) {
            // Get timestamp from the API response
            let timestamp_value = sensorData.latest_reading.timestamp;
            
            if (timestamp_value) {
                lastUpdate.setAttribute('data-timestamp', timestamp_value);
                
                try {
                    let timestamp;
                    // Handle different timestamp formats
                    if (typeof timestamp_value === 'number') {
                        // Unix timestamp (e.g., from LTR329/MPU6050)
                        timestamp = new Date(timestamp_value * 1000);
                    } else {
                        // ISO string or other format (e.g., from BME280)
                        timestamp = this.parseUTCTimestamp(timestamp_value);
                    }
                    
                    if (isNaN(timestamp.getTime())) {
                        console.error('Invalid timestamp:', timestamp_value);
                        lastUpdate.textContent = 'Invalid time';
                    } else {
                        lastUpdate.textContent = this.formatTimeAgo(timestamp);
                        // Add a title showing the full time in selected timezone
                        lastUpdate.title = `Last reading: ${this.formatTimestampInTimezone(timestamp_value, this.config.timezone)}`;
                    }
                } catch (error) {
                    console.error('Error parsing timestamp:', error, timestamp_value);
                    lastUpdate.textContent = 'Time parse error';
                }
            }
        }

        // Update sensor data if available
        if (sensorData.latest_reading) {
            // Handle different API response formats
            let data;
            if (sensorData.latest_reading.data) {
                // BME280 format: data is nested in .data field
                data = sensorData.latest_reading.data;
            } else {
                // LTR329/MPU6050 format: data is directly in latest_reading
                data = sensorData.latest_reading;
                // Remove metadata fields to keep only sensor values
                const metadataFields = ['timestamp', 'sensor_id', 'sensor_type', 'status'];
                data = Object.fromEntries(
                    Object.entries(data).filter(([key]) => !metadataFields.includes(key))
                );
            }
            this.updateSensorDataDisplay(card, data);
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
        } else if (sensorType === 'mpu6050') {
            // MPU6050 shows accelerometer, gyroscope, and temperature
            if (data.temperature !== null && data.temperature !== undefined) {
                relevantFields.temperature = data.temperature;
            }
            if (data.accel_x !== null && data.accel_x !== undefined) {
                relevantFields.accel_x = data.accel_x;
            }
            if (data.accel_y !== null && data.accel_y !== undefined) {
                relevantFields.accel_y = data.accel_y;
            }
            if (data.accel_z !== null && data.accel_z !== undefined) {
                relevantFields.accel_z = data.accel_z;
            }
        } else {
            // For unknown sensor types, show all non-null fields
            Object.entries(data).forEach(([key, value]) => {
                if (value !== null && value !== undefined && key !== 'timestamp') {
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
            ir_level: (v) => `${Math.round(parseFloat(v))}`,    // Raw CH1 value
            accel_x: (v) => `${parseFloat(v).toFixed(2)}g`,
            accel_y: (v) => `${parseFloat(v).toFixed(2)}g`,
            accel_z: (v) => `${parseFloat(v).toFixed(2)}g`,
            gyro_x: (v) => `${parseFloat(v).toFixed(1)}°/s`,
            gyro_y: (v) => `${parseFloat(v).toFixed(1)}°/s`,
            gyro_z: (v) => `${parseFloat(v).toFixed(1)}°/s`
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
            ir_level: 'CH1 (IR Only)',
            accel_x: 'Accel X',
            accel_y: 'Accel Y', 
            accel_z: 'Accel Z',
            gyro_x: 'Gyro X',
            gyro_y: 'Gyro Y',
            gyro_z: 'Gyro Z'
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
        let date;
        // Handle different timestamp formats
        if (typeof timestamp === 'string' && (timestamp.includes('-') || timestamp.includes('T'))) {
            // ISO string format
            date = this.parseUTCTimestamp(timestamp);
        } else {
            // Unix timestamp format (string or number)
            const timestampNum = typeof timestamp === 'string' ? parseFloat(timestamp) : timestamp;
            date = new Date(timestampNum * 1000);
        }
        
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
            if (timestamp && timestamp !== 'None' && timestamp !== 'null') {
                try {
                    let date;
                    // Handle different timestamp formats
                    if (timestamp.includes('-') || timestamp.includes('T')) {
                        // ISO string format (e.g., "2025-09-21T15:30:00")
                        date = this.parseUTCTimestamp(timestamp);
                    } else {
                        // Unix timestamp format (e.g., "1758468569.7065759")
                        const timestampNum = parseFloat(timestamp);
                        if (isNaN(timestampNum)) {
                            throw new Error('Invalid timestamp number');
                        }
                        date = new Date(timestampNum * 1000);
                    }
                    
                    if (date && !isNaN(date.getTime())) {
                        element.textContent = this.formatTimeAgo(date);
                    } else {
                        element.textContent = 'Invalid time';
                    }
                } catch (error) {
                    element.textContent = 'Parse error';
                }
            } else {
                element.textContent = 'No timestamp';
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
                    let date;
                    // Handle different timestamp formats
                    if (timestamp.includes('-') || timestamp.includes('T')) {
                        // ISO string format
                        date = this.parseUTCTimestamp(timestamp);
                    } else {
                        // Unix timestamp format
                        const timestampNum = parseFloat(timestamp);
                        date = new Date(timestampNum * 1000);
                    }
                    
                    if (!isNaN(date.getTime())) {
                        lastUpdate.textContent = this.formatTimeAgo(date);
                        lastUpdate.title = `Last reading: ${this.formatTimestampInTimezone(timestamp, this.config.timezone)}`;
                    } else {
                        lastUpdate.textContent = 'Invalid time';
                    }
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
