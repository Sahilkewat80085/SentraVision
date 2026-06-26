import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  timeout: 60000
});

export async function uploadVideo(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/upload", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}

export async function getStatus(videoId) {
  const { data } = await api.get(`/status/${videoId}`);
  return data;
}

export async function getRoi(videoId, page = 1, pageSize = 50) {
  const { data } = await api.get(`/roi/${videoId}`, {
    params: { page, page_size: pageSize }
  });
  return data;
}
