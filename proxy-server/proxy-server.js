const express = require('express');
const fetch = require('node-fetch'); // npm install node-fetch@2
const app = express();

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
  try {
    const response = await fetch(featureUrl);
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

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Image proxy server running on port ${PORT}`);
});