// Example: Fetch and display image from Netlify function
async function fetchProxyImage(imageUrl: string): Promise<string> {
  const proxyUrl = `/api/proxy-image?url=${encodeURIComponent(imageUrl)}`;
  const response = await fetch(proxyUrl);
  if (!response.ok) throw new Error('Failed to fetch image');
  const contentType = response.headers.get('Content-Type') || 'image/jpeg';
  const base64 = await response.text();
  // Build data URL for <img src="">
  return `data:${contentType};base64,${base64}`;
}

// Usage in a React component
import { useEffect, useState } from 'react';

export function ProxyImage({ imageUrl }: { imageUrl: string }) {
  const [src, setSrc] = useState<string>('');

  useEffect(() => {
    fetchProxyImage(imageUrl).then(setSrc).catch(console.error);
  }, [imageUrl]);

  return src ? <img src={src} alt="Proxy" /> : <span>Loading...</span>;
}