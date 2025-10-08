const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// Connect MongoDB
mongoose.connect('mongodb://127.0.0.1:27017/waste', { useNewUrlParser: true, useUnifiedTopology: true });

// Schema
const wasteSchema = new mongoose.Schema({
  waste_type: String,
  quantity: Number,
  date: { type: Date, default: Date.now }
});
const Waste = mongoose.model('Waste', wasteSchema);

// Routes
app.post('/add_waste', async (req, res) => {
  const item = new Waste(req.body);
  await item.save();
  res.json({ success: true });
});

app.get('/waste_items', async (req, res) => {
  const items = await Waste.find().sort({ date: -1 });
  res.json(items);
});

// Start server
app.listen(3000, () => console.log('Server running on http://localhost:3000'));
