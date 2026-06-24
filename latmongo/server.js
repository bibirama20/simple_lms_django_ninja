const express = require('express');
const path = require('path');
const crypto = require('crypto');
const { MongoClient } = require('mongodb');

const app = express();
const PORT = process.env.PORT || 3000;
const MONGO_URL = process.env.MONGO_URL || 'mongodb://mongo:27017';
const DB_NAME = process.env.DB_NAME || 'latihan';

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.urlencoded({ extended: true }));

let db;

async function connectDB() {
  const client = new MongoClient(MONGO_URL);
  await client.connect();
  db = client.db(DB_NAME);
  console.log(`Terhubung ke MongoDB: ${MONGO_URL}/${DB_NAME}`);
}

app.get('/', async (req, res) => {
  const todos = await db.collection('todo').find().sort({ created_at: -1 }).toArray();
  res.render('index', { todos });
});

app.post('/todos', async (req, res) => {
  const title = (req.body.title || '').trim();

  if (!title) {
    return res.redirect('/');
  }

  const now = new Date();

  await db.collection('todo').insertOne({
    user_id: (req.body.user_id || '').trim() || crypto.randomUUID(),
    title,
    description: (req.body.description || '').trim(),
    created_at: now,
    updated_at: now,
  });

  res.redirect('/');
});

connectDB()
  .then(() => {
    app.listen(PORT, () => console.log(`latmongo app berjalan di port ${PORT}`));
  })
  .catch((err) => {
    console.error('Gagal konek ke MongoDB:', err);
    process.exit(1);
  });
