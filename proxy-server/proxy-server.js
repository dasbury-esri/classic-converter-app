

import express from 'express';
import fetch from 'node-fetch'; // npm install node-fetch@2
import sizeOf from 'image-size' // npm isntall image-size
const app = express();

app.get('/image-dimensions', async (req, res) => {
  const imageUrl = req.query.url;
  if (!imageUrl) return res.status(400).json({ error: 'Missing url parameter' });
  try {
    const response = await fetch(imageUrl);
    if (!response.ok) return res.status(response.status).json({ error: 'Failed to fetch image' });
    const buffer = await response.buffer();
    const dimensions = sizeOf(buffer);
    res.json(dimensions); // { width: ..., height: ... }
  } catch (err) {
    res.status(500).json({ error: 'Error fetching image or reading dimensions' });
  }
});

app.get('/proxy-image', async (req, res) => {
  const imageUrl = req.query.url;
  if (!imageUrl) {
    return res.status(400).send('Missing url parameter');
  }

  try {
    const response = await fetch(imageUrl);
    if (!response.ok) {
      return res.status(response.status).send('Failed to fetch image');
    }
    // Set CORS headers
    res.set('Access-Control-Allow-Origin', '*');
    res.set('Content-Type', response.headers.get('content-type') || 'image/jpeg');
    response.body.pipe(res);
  } catch (err) {
    res.status(500).send('Error fetching image');
  }
});

app.get('/proxy-feature', async (req, res) => {
  console.log('Proxying feature request:', req.query.url);
  const featureUrl = req.query.url;
  if (!featureUrl) {
    return res.status(400).send('Missing url parameter');
  }
  const safeUrl = featureUrl.replace(/^http:/i, 'https:');
  try {
    const response = await fetch(safeUrl);
    if (!response.ok) {
      return res.status(response.status).send('Failed to fetch feature service');
    }
    res.set('Access-Control-Allow-Origin', '*');
    res.set('Content-Type', response.headers.get('content-type') || 'application/json');
    response.body.pipe(res);
  } catch (err) {
    res.status(500).send('Error fetching feature service');
  }
});

// eslint-disable-next-line no-undef
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Proxy server running on port ${PORT}`);
});