import express from 'express';
import { config } from 'dotenv';
import { setupRoutes } from './routes';
import { setupDatabase } from './database';

// Load environment variables
config();

const app = express();
const port = process.env.PORT || 3000;

// Middleware setup
app.use(express.json());

// Setup routes and database
setupRoutes(app);
setupDatabase();

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
}); 