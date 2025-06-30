/**
 * WebSocket client for real-time updates
 */

// Event listeners for WebSocket events
const listeners = {
  timeline_event: [],
  initial_events: [],
  connection_established: [],
  connection_closed: [],
  connection_error: [],
};

// WebSocket connection
let socket = null;
let reconnectTimeout = null;
let isConnecting = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 2000; // 2 seconds

/**
 * Initialize a WebSocket connection
 * @param {string} channel - The channel to connect to (e.g., "timeline")
 * @returns {Promise<WebSocket>} - The WebSocket connection
 */
export const initializeWebSocket = (channel) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    console.log(`WebSocket already connected to ${channel}`);
    return Promise.resolve(socket);
  }

  if (isConnecting) {
    console.log('WebSocket connection already in progress');
    return new Promise((resolve) => {
      const checkConnection = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          clearInterval(checkConnection);
          resolve(socket);
        }
      }, 100);
    });
  }

  isConnecting = true;
  
  // Get the auth token
  const token = localStorage.getItem('authToken');
  
  // Create the WebSocket URL with the token
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.hostname}:8000/api/v1/${channel}/ws${token ? `?token=${token}` : ''}`;
  
  return new Promise((resolve, reject) => {
    try {
      socket = new WebSocket(wsUrl);
      
      socket.onopen = () => {
        console.log(`WebSocket connected to ${channel}`);
        isConnecting = false;
        reconnectAttempts = 0;
        
        // Set up a ping interval to keep the connection alive
        const pingInterval = setInterval(() => {
          if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send('ping');
          } else {
            clearInterval(pingInterval);
          }
        }, 30000); // Send a ping every 30 seconds
        
        // Notify listeners
        notifyListeners('connection_established', { channel });
        resolve(socket);
      };
      
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type && listeners[data.type]) {
            notifyListeners(data.type, data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      socket.onclose = (event) => {
        console.log(`WebSocket disconnected from ${channel}:`, event.code, event.reason);
        isConnecting = false;
        
        // Notify listeners
        notifyListeners('connection_closed', { 
          code: event.code,
          reason: event.reason,
          channel 
        });
        
        // Attempt to reconnect if the connection was closed unexpectedly
        if (event.code !== 1000 && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          reconnect(channel);
        }
      };
      
      socket.onerror = (error) => {
        console.error(`WebSocket error on ${channel}:`, error);
        isConnecting = false;
        
        // Notify listeners
        notifyListeners('connection_error', { error, channel });
        
        // Reject the promise if the connection fails
        reject(error);
      };
    } catch (error) {
      console.error(`Error initializing WebSocket for ${channel}:`, error);
      isConnecting = false;
      reject(error);
    }
  });
};

/**
 * Reconnect to the WebSocket
 * @param {string} channel - The channel to reconnect to
 */
const reconnect = (channel) => {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
  }
  
  reconnectAttempts++;
  const delay = RECONNECT_DELAY * reconnectAttempts;
  
  console.log(`Attempting to reconnect to ${channel} in ${delay}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
  
  reconnectTimeout = setTimeout(() => {
    initializeWebSocket(channel).catch(() => {
      // If reconnection fails, we'll try again in the onclose handler
    });
  }, delay);
};

/**
 * Close the WebSocket connection
 */
export const closeWebSocket = () => {
  if (socket) {
    socket.close(1000, 'Client closed connection');
    socket = null;
  }
  
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }
  
  isConnecting = false;
  reconnectAttempts = 0;
};

/**
 * Add an event listener for WebSocket events
 * @param {string} eventType - The event type to listen for
 * @param {Function} callback - The callback function
 * @returns {Function} - A function to remove the listener
 */
export const addWebSocketListener = (eventType, callback) => {
  if (!listeners[eventType]) {
    listeners[eventType] = [];
  }
  
  listeners[eventType].push(callback);
  
  // Return a function to remove the listener
  return () => {
    if (listeners[eventType]) {
      const index = listeners[eventType].indexOf(callback);
      if (index !== -1) {
        listeners[eventType].splice(index, 1);
      }
    }
  };
};

/**
 * Notify all listeners of an event
 * @param {string} eventType - The event type
 * @param {object} data - The event data
 */
const notifyListeners = (eventType, data) => {
  if (listeners[eventType]) {
    listeners[eventType].forEach((callback) => {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in ${eventType} listener:`, error);
      }
    });
  }
};

/**
 * Get the WebSocket connection status
 * @returns {string} - The connection status
 */
export const getWebSocketStatus = () => {
  if (!socket) {
    return 'CLOSED';
  }
  
  switch (socket.readyState) {
    case WebSocket.CONNECTING:
      return 'CONNECTING';
    case WebSocket.OPEN:
      return 'OPEN';
    case WebSocket.CLOSING:
      return 'CLOSING';
    case WebSocket.CLOSED:
      return 'CLOSED';
    default:
      return 'UNKNOWN';
  }
};