import axios, { AxiosRequestConfig, AxiosResponse, Method } from "axios";

// Initializing Axios instance
const axiosInstance = axios.create({ withCredentials: true });

export const apiURL = import.meta.env.VITE_API_URL || "http://localhost:7377";

interface AxiosRequestConfigPatch extends Omit<AxiosRequestConfig, "method"> {
  method?: Method; // axios sets it as string, which is unhelpful and can lead to bugs
}

export function backendApi<T>(
  config: AxiosRequestConfigPatch
): Promise<AxiosResponse<T>> {
  return axiosInstance.request<T>({ baseURL: apiURL, ...config });
}
