import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// API key should be set via environment variable VITE_API_KEY or localStorage
export const API_KEY = import.meta.env.VITE_API_KEY || localStorage.getItem('searchsift_api_key') || ''

export async function apiCall<T>(endpoint: string): Promise<T> {
  const response = await fetch(endpoint, {
    headers: { 'X-API-Key': API_KEY }
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export function getCategoryBadgeClass(category: string): string {
  const map: Record<string, string> = {
    'Work': 'badge-work',
    'Coding': 'badge-coding',
    'AI': 'badge-ai',
    'Research': 'badge-research',
    'Shopping': 'badge-shopping',
    'Social': 'badge-social',
    'News': 'badge-news',
    'Entertainment': 'badge-entertainment',
    'Finance': 'badge-finance',
    'Health': 'badge-health',
    'Travel': 'badge-travel',
    'Sports': 'badge-sports',
    'Other': 'badge-other',
  }
  return map[category] || 'badge-other'
}

export function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleString()
}

export function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
