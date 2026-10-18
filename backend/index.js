import express from 'express';
import cors from 'cors';
import 'dotenv/config'; // Safely loads environment variables

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors()); // Crucial: Allows the frontend container to talk to this API
app.use(express.json()); // Allows the API to read incoming JSON data bodies

// Start Server
app.listen(PORT, () => {
  console.log(`Scout backend running on http://localhost:${PORT}`);
});
