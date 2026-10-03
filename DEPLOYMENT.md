# Deployment Guide for Todo Chatbot Application

## Backend Deployment (Render)

### Prerequisites
- Render account
- OpenRouter API key

### Steps
1. Create a new Web Service on Render
2. Connect to your GitHub repository
3. Set the following environment variables:
   - `OPEN_ROUTER_API_KEY`: Your OpenRouter API key
   - `OPEN_ROUTER_URL`: `https://openrouter.ai/api/v1/chat/completions`
   - `DATABASE_URL`: Your PostgreSQL database URL (from Neon or other provider)
4. Use the `render.yaml` file in the `backend/` directory for automatic configuration
5. The start command will be automatically detected as `python start_server.py`

### Expected Result
- You'll get a URL like `https://your-app-name.onrender.com`

## Frontend Deployment (Vercel)

### Prerequisites
- Vercel account
- Deployed backend URL

### Steps
1. Go to https://vercel.com and create a new project
2. Import your GitHub repository
3. Set the following environment variable:
   - `NEXT_PUBLIC_API_URL`: The URL of your deployed backend (e.g., `https://your-app-name.onrender.com`)
4. Build command: `next build`
5. Output directory: `.next`
6. The configuration in `vercel.json` will be automatically detected

### Expected Result
- You'll get a URL like `https://your-project-name.vercel.app`

## Environment Variables Reference

### Backend (Render)
| Variable | Value | Description |
|----------|-------|-------------|
| `OPEN_ROUTER_API_KEY` | Your API key | OpenRouter API key for AI chat functionality |
| `OPEN_ROUTER_URL` | `https://openrouter.ai/api/v1/chat/completions` | OpenRouter API endpoint |
| `DATABASE_URL` | PostgreSQL URL | Connection string for your PostgreSQL database |

### Frontend (Vercel)
| Variable | Value | Description |
|----------|-------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL | The URL of your deployed backend server |

## Post-Deployment Verification

After both deployments are complete, verify the following:

1. Visit the frontend URL
2. Confirm that:
   - Login/Signup works
   - Chatbot responds to messages
   - Task creation, listing, updating, and deletion work
   - All functionality connects properly to the backend

## Troubleshooting

### Frontend 404 Errors
- Ensure `vercel.json` has the correct route configuration
- Verify `next.config.js` has `output: "standalone"`
- Check that environment variables are properly set

### API Connection Issues
- Confirm that `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Verify the backend is accessible at the specified URL
- Check CORS settings on the backend

### Chat Functionality Not Working
- Ensure `OPEN_ROUTER_API_KEY` is set correctly in the backend
- Verify the OpenRouter URL is properly configured
- Check that the backend can reach the OpenRouter API