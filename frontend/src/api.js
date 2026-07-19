import axios from "axios";

// Create configured Axios instance
export const api = axios.create({
  baseURL: "/api",
  timeout: 60000, // 60 seconds timeout
});

// Request Interceptor: Logs details about outgoing requests
api.interceptors.request.use(
  (config) => {
    console.debug(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.params || "");
    return config;
  },
  (error) => {
    console.error("[API Request Error]", error);
    return Promise.reject(error);
  }
);

// Response Interceptor: Logs details and parses standard backend validation structures
api.interceptors.response.use(
  (response) => {
    console.debug(`[API Response] ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    const errorDetails = error.response?.data?.detail || error.message || "Network Error";
    console.error(`[API Response Error] ${error.config?.url}:`, errorDetails);
    
    // Normalize error format for component consumption
    return Promise.reject(new Error(errorDetails));
  }
);

/**
 * Uploads a video file to the backend processing pipeline.
 * @param {File} file - Raw video file from user selection
 */
export async function uploadVideo(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/upload", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}

/**
 * Fetches the execution state and video stats of a processing job.
 * @param {string} videoId - Unique UUID of target video
 */
export async function getStatus(videoId) {
  const { data } = await api.get(`/status/${videoId}`);
  return data;
}

/**
 * Retrieves paginated face detection bounding box data.
 * @param {string} videoId - Unique UUID of target video
 * @param {number} page - Result page index
 * @param {number} pageSize - Number of items to query
 */
export async function getRoi(videoId, page = 1, pageSize = 50) {
  const { data } = await api.get(`/roi/${videoId}`, {
    params: { page, page_size: pageSize }
  });
  return data;
}

